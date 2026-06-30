from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import ToolUseBudgetFrame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop_continuation import record_l_loop_continuation_decision
from songryeon_core.loops.l_loop_revision_tool_attempt import run_l_loop_revision_tool_attempt
from songryeon_core.nodes.l2_query_setter import (
    l2_revision_query_plan_data_id,
    run_l2_revision_query_planner,
    selected_query_from_plan,
    selected_target_tool_from_plan,
)
from songryeon_core.nodes.l3_result_keeper import (
    l3_revision_achievement_frame_data_id,
    run_l3_revision_result_keeper,
)


class RevisionPayloadAdapter:
    model_id = "order-122-revision-payload-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_revision_l2_accepts_read_doc_for_exact_unread_candidate() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_revision_input(
        data_store=data_store,
        trace_id=trace_id,
        unread_doc_ids=["ORDER_122_DOC.md"],
        remaining_query_attempts=0,
        remaining_read_doc_calls=1,
    )

    run_l2_revision_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_122",
        revision_input_data_id="L2:revision_input:0001",
        adapter=RevisionPayloadAdapter(_read_doc_plan("ORDER_122_DOC.md")),
    )

    plan_payload = data_store.require_record(l2_revision_query_plan_data_id(1)).payload
    assert isinstance(plan_payload, dict)
    assert selected_target_tool_from_plan(plan_payload) == "read_doc"
    assert selected_query_from_plan(plan_payload) == "ORDER_122_DOC.md"


def test_revision_l2_rejects_read_doc_outside_unread_candidates() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_revision_input(
        data_store=data_store,
        trace_id=trace_id,
        unread_doc_ids=["ORDER_122_DOC.md"],
        remaining_query_attempts=0,
        remaining_read_doc_calls=1,
    )

    with pytest.raises(ValueError, match="L2 revision query planner failed: schema_failed"):
        run_l2_revision_query_planner(
            trace_store=trace_store,
            data_store=data_store,
            turn_id="turn_order_122",
            revision_input_data_id="L2:revision_input:0001",
            adapter=RevisionPayloadAdapter(_read_doc_plan("OTHER_DOC.md")),
        )


def test_continuation_allows_read_path_after_query_budget_exhaustion() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        payload={
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "partial",
            "read_doc_ids": [],
            "search_result_doc_ids": ["ORDER_122_DOC.md"],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        payload={"query_text": "previous query"},
    )
    data_store.create_record(
        data_id="tool_budget:turn_order_122:0008",
        data_type="tool_use_budget",
        payload=asdict(
            _budget_frame(
                budget_id="tool_budget:turn_order_122:0008",
                max_query_attempts=8,
                query_count=8,
                max_read_doc_calls=1,
                read_doc_count=0,
                tool_call_count=8,
                max_tool_calls=10,
            )
        ),
    )

    _, _, frame = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_122",
        attempt_index=8,
        max_attempts=12,
        l3_achievement_data_id="L3:achievement_frame",
        l2_query_frame_data_id="L2:query_frame",
    )

    assert frame.continuation_status == "continue"
    assert frame.next_target_node == "L2"
    assert frame.unread_candidate_doc_ids == ["ORDER_122_DOC.md"]


def test_revision_read_doc_increments_read_count_without_query_count(tmp_path) -> None:
    doc_id = "ORDER_122_DOC.md"
    (tmp_path / doc_id).write_text("# ORDER 122\n\n읽어야 하는 후보 원문.", encoding="utf-8")
    trace_store, data_store, trace_id = _stores()
    _record_l1_goal(data_store=data_store, trace_id=trace_id)
    _record_revision_query_frame(
        data_store=data_store,
        trace_id=trace_id,
        doc_id=doc_id,
    )
    data_store.create_record(
        data_id="tool_budget:turn_order_122:0008",
        data_type="tool_use_budget",
        payload=asdict(
            _budget_frame(
                budget_id="tool_budget:turn_order_122:0008",
                max_query_attempts=8,
                query_count=8,
                max_read_doc_calls=1,
                read_doc_count=0,
                tool_call_count=8,
                max_tool_calls=10,
            )
        ),
    )

    result = run_l_loop_revision_tool_attempt(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_122",
        revision_query_frame_data_id="L2:revision_query_frame:0001",
        document_root=tmp_path,
        max_tool_calls=10,
        max_query_attempts=8,
        max_read_doc_calls=1,
        max_input_chars=6000,
    )

    budget_payload = data_store.require_record(result.tool_budget_data_id).payload
    assert result.tool_name == "read_doc"
    assert isinstance(budget_payload, dict)
    assert budget_payload["query_count"] == 8
    assert budget_payload["read_doc_count"] == 1
    assert budget_payload["read_doc_ids"] == [doc_id]
    assert budget_payload["stop_reason"] == "completed"

    run_l3_revision_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_122",
        attempt_index=1,
        revision_query_frame_data_id="L2:revision_query_frame:0001",
        revision_tool_source_trace_ids=result.source_trace_ids,
        revision_tool_source_data_ids=result.source_data_ids,
        user_query="ORDER_122 문서를 읽어줘",
    )
    achievement_payload = data_store.require_record(l3_revision_achievement_frame_data_id(1)).payload
    assert isinstance(achievement_payload, dict)
    assert doc_id in achievement_payload["read_doc_ids"]


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_122",
        actor="test",
        event_type="node_output",
        output_ref=["source:test"],
        schema_status="passed",
    )
    return trace_store, data_store, event.event_id


def _record_revision_input(
    *,
    data_store: DataStore,
    trace_id: str,
    unread_doc_ids: list[str],
    remaining_query_attempts: int,
    remaining_read_doc_calls: int,
) -> None:
    data_store.create_record(
        data_id="L2:revision_input:0001",
        data_type="node_input:L2_revision_input_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L2:revision_input:0001",
            "turn_id": "turn_order_122",
            "attempt_index": 1,
            "max_attempts": 3,
            "macro_goal": "read unread candidate",
            "micro_goal": "use exact unread candidate doc id",
            "previous_query_text": "previous query",
            "previous_tool_name": "search_docs",
            "read_document_names": [],
            "unread_candidate_doc_ids": unread_doc_ids,
            "unread_candidate_summaries": [
                f"doc_id={doc_id}; preview=후보 문서" for doc_id in unread_doc_ids
            ],
            "l3_goal_status": "partial",
            "l3_goal_match_status": "partial",
            "l3_semantic_goal_match_status": "partial",
            "l3_feedback_text": "need more original documents",
            "remaining_tool_calls": 2,
            "remaining_query_attempts": remaining_query_attempts,
            "remaining_read_doc_calls": remaining_read_doc_calls,
            "source_trace_ids": [trace_id],
            "source_data_ids": ["L:continuation:0001"],
            "schema_name": "L2RevisionInputFrame",
            "schema_version": "0.1",
        },
    )


def _read_doc_plan(doc_id: str) -> dict[str, object]:
    return {
        "planner_mode": "revision_llm",
        "selected_candidate_id": "L2:revision_query_candidate_0001",
        "candidates": [
            {
                "candidate_id": "L2:revision_query_candidate_0001",
                "query_text": doc_id,
                "purpose": "query 예산 없이 보존된 unread candidate를 원문 읽는다.",
                "expected_signal": "read_doc 원문",
                "priority": 1,
                "target_tool_name": "read_doc",
                "source_data_ids": ["L2:revision_input:0001"],
            }
        ],
    }


def _record_l1_goal(*, data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": "turn_order_122",
            "macro_goal": "read requested document",
            "micro_goal": "read one candidate",
            "minimum_read_documents": 1,
            "source_trace_ids": [trace_id],
            "source_data_ids": [],
        },
    )


def _record_revision_query_frame(
    *,
    data_store: DataStore,
    trace_id: str,
    doc_id: str,
) -> None:
    data_store.create_record(
        data_id="L2:revision_query_frame:0001",
        data_type="node_output:L2_revision_query_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L2:revision_query_frame:0001",
            "turn_id": "turn_order_122",
            "query_text": doc_id,
            "query_source": "revision_llm_query_plan",
            "query_mode": "direct_doc_read",
            "target_tool_name": "read_doc",
            "source_trace_ids": [trace_id],
            "source_data_ids": ["L2:revision_query_plan:0001"],
        },
    )


def _budget_frame(
    *,
    budget_id: str,
    max_query_attempts: int,
    query_count: int,
    max_read_doc_calls: int,
    read_doc_count: int,
    tool_call_count: int,
    max_tool_calls: int,
) -> ToolUseBudgetFrame:
    return ToolUseBudgetFrame(
        budget_id=budget_id,
        turn_id="turn_order_122",
        loop_id="L",
        sequence_index=8,
        max_tool_calls=max_tool_calls,
        search_top_k=2,
        max_query_attempts=max_query_attempts,
        max_query_candidates=max_query_attempts,
        max_read_doc_calls=max_read_doc_calls,
        max_input_chars=6000,
        tool_call_count=tool_call_count,
        query_count=query_count,
        read_doc_count=read_doc_count,
        input_chars_used=100,
        executed_queries=[f"query {index}" for index in range(query_count)],
        read_doc_ids=[],
        cache_statuses=[],
        stop_reason="within_budget",
        reason="CODE_STATUS:test_budget",
        source_trace_ids=["trace:test"],
        source_data_ids=["L2:query_frame"],
    )
