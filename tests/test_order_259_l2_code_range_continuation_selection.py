from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    CodeReadRangeRecord,
    L2QueryPlanCandidate,
    L2QueryPlanFrame,
    validate_l2_query_plan_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop_continuation import (
    record_l_loop_continuation_decision,
)
from songryeon_core.loops.l_loop_revision_tool_attempt import (
    run_l_loop_revision_tool_attempt,
)
from songryeon_core.nodes.l2_query_setter import (
    l2_revision_query_plan_data_id,
    run_l2_revision_query_planner,
    run_l2_revision_query_setter,
)
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools.tool_efficiency_policy import (
    build_code_read_continuation_options,
    record_tool_use_budget_frame,
)


TURN_ID = "turn_order_259"
SOURCE_PATH = "sample.py"
FIRST_TOOL_RESULT_ID = "tool_result:read_code_file:order_259:first"


class RevisionPlanAdapter:
    model_id = "order-259-revision-plan"

    def __init__(self, *, start_char: int) -> None:
        self.start_char = start_char

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "planner_mode": "revision_llm",
            "selected_candidate_id": "L2:revision_query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:revision_query_candidate_0001",
                    "query_text": SOURCE_PATH,
                    "purpose": "Continue the same truncated source file.",
                    "expected_signal": "The next exact source range is returned.",
                    "priority": 1,
                    "target_tool_name": "read_code_file",
                    "read_code_file_start_char": self.start_char,
                    "source_data_ids": ["L2:revision_input:0001"],
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload),
            model_id=self.model_id,
            raw=payload,
        )


def test_code_builds_only_the_next_unread_continuation_start() -> None:
    first = _range_record(start=0, end=12000, total=25000, tool_id=FIRST_TOOL_RESULT_ID)
    second = _range_record(
        start=12000,
        end=24000,
        total=25000,
        tool_id="tool_result:read_code_file:order_259:second",
    )

    first_options = build_code_read_continuation_options([first])
    second_options = build_code_read_continuation_options([first, second])

    assert [(item.file_path, item.start_char) for item in first_options] == [
        (SOURCE_PATH, 12000)
    ]
    assert [(item.file_path, item.start_char) for item in second_options] == [
        (SOURCE_PATH, 24000)
    ]
    assert second_options[0].remaining_char_count == 1000


def test_revision_l2_selects_an_exact_code_continuation_option() -> None:
    trace_store, data_store, trace_id = _revision_stores()
    _record_revision_input(data_store=data_store, trace_id=trace_id)

    run_l2_revision_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        revision_input_data_id="L2:revision_input:0001",
        adapter=RevisionPlanAdapter(start_char=12000),
        available_tools=[{"tool_name": "read_code_file", "read_only": True}],
    )
    run_l2_revision_query_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        revision_query_plan_data_id=l2_revision_query_plan_data_id(1),
    )

    query_payload = data_store.require_record("L2:revision_query_frame:0001").payload
    assert isinstance(query_payload, dict)
    assert query_payload["query_text"] == SOURCE_PATH
    assert query_payload["target_tool_name"] == "read_code_file"
    assert query_payload["read_code_file_start_char"] == 12000


def test_revision_l2_rejects_rereading_the_same_prefix() -> None:
    trace_store, data_store, trace_id = _revision_stores()
    _record_revision_input(data_store=data_store, trace_id=trace_id)

    with pytest.raises(ValueError, match="L2 revision query planner failed: schema_failed"):
        run_l2_revision_query_planner(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=TURN_ID,
            revision_input_data_id="L2:revision_input:0001",
            adapter=RevisionPlanAdapter(start_char=0),
            available_tools=[{"tool_name": "read_code_file", "read_only": True}],
        )


def test_initial_l2_rejects_a_nonzero_code_start() -> None:
    frame = L2QueryPlanFrame(
        frame_id="L2:query_plan_frame",
        turn_id=TURN_ID,
        planner_mode="llm",
        selected_candidate_id="candidate_1",
        candidates=[
            L2QueryPlanCandidate(
                candidate_id="candidate_1",
                query_text=SOURCE_PATH,
                purpose="invalid initial continuation",
                expected_signal="source text",
                priority=1,
                target_tool_name="read_code_file",
                read_code_file_start_char=12000,
                source_data_ids=["L1:goal_frame"],
            )
        ],
        source_trace_ids=["trace_1"],
        source_data_ids=["L1:goal_frame"],
    )

    with pytest.raises(ValueError, match="initial L2 read_code_file candidate"):
        validate_l2_query_plan_frame(frame)


def test_continuation_stays_open_for_code_read_when_query_budget_is_zero() -> None:
    trace_store, data_store, trace_id = _revision_stores()
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        source_trace_id=trace_id,
        payload={"query_text": SOURCE_PATH, "target_tool_name": "read_code_file"},
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        source_trace_id=trace_id,
        payload={
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "partial",
            "read_doc_ids": [],
            "search_result_doc_ids": [],
        },
    )
    record_tool_use_budget_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        sequence_index=1,
        max_tool_calls=2,
        search_top_k=1,
        max_query_attempts=1,
        max_read_doc_calls=1,
        max_input_chars=24000,
        tool_call_count=1,
        executed_queries=["already used query"],
        read_doc_ids=[],
        cache_statuses=[],
        input_chars_used=12000,
        stop_reason="within_budget",
        reason="first source range was read",
        max_read_code_file_calls=2,
        read_code_file_ranges=[_range_record()],
    )

    _, _, frame = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        attempt_index=1,
        max_attempts=2,
        source_trace_ids=[trace_id],
    )

    assert frame.continuation_status == "continue"
    assert frame.continuation_reason_code == (
        "CODE_STATUS:l3_not_achieved_read_next_code_range_after_query_budget"
    )
    assert [(item.file_path, item.start_char) for item in frame.code_read_continuation_options] == [
        (SOURCE_PATH, 12000)
    ]


def test_revision_tool_reads_the_next_exact_12000_character_range(tmp_path) -> None:
    source = tmp_path / SOURCE_PATH
    source.write_text("a" * 12000 + "b" * 12000 + "c" * 1000, encoding="utf-8")
    trace_store, data_store, trace_id = _revision_stores()
    data_store.create_record(
        data_id="L2:revision_query_frame:0001",
        data_type="node_output:L2_revision_query_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L2:revision_query_frame:0001",
            "turn_id": TURN_ID,
            "query_text": SOURCE_PATH,
            "query_source": "revision_llm_query_plan",
            "query_mode": "code_file_read",
            "target_tool_name": "read_code_file",
            "read_code_file_start_char": 12000,
            "source_trace_ids": [trace_id],
            "source_data_ids": ["L2:revision_query_plan:0001"],
        },
    )
    record_tool_use_budget_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        sequence_index=1,
        max_tool_calls=2,
        search_top_k=1,
        max_query_attempts=1,
        max_read_doc_calls=1,
        max_input_chars=30000,
        tool_call_count=1,
        executed_queries=[],
        read_doc_ids=[],
        cache_statuses=[],
        input_chars_used=12000,
        stop_reason="within_budget",
        reason="first source range was read",
        max_read_code_file_calls=2,
        read_code_file_ranges=[_range_record()],
    )

    result = run_l_loop_revision_tool_attempt(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        revision_query_frame_data_id="L2:revision_query_frame:0001",
        document_root=tmp_path,
        code_root=tmp_path,
        max_tool_calls=2,
        max_query_attempts=1,
        max_read_doc_calls=1,
        max_read_code_file_calls=2,
        max_input_chars=30000,
    )

    tool_payload = data_store.require_record(result.tool_result_data_id).payload
    budget_payload = data_store.require_record(result.tool_budget_data_id).payload
    assert isinstance(tool_payload, dict)
    assert isinstance(budget_payload, dict)
    assert tool_payload["text"] == "b" * 12000
    assert tool_payload["range_start_char"] == 12000
    assert tool_payload["range_end_char_exclusive"] == 24000
    assert tool_payload["truncated_before"] is True
    assert tool_payload["truncated_after"] is True
    assert budget_payload["read_code_file_count"] == 2
    assert [item["range_start_char"] for item in budget_payload["read_code_file_ranges"]] == [
        0,
        12000,
    ]


def test_terminal_displays_revision_code_start_char() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "test", "transport": "fake"},
            "trace_count": 0,
            "data_record_count": 1,
            "data_records": [
                {
                    "data_id": "L2:revision_query_frame:0001",
                    "data_type": "node_output:L2_revision_query_frame",
                    "payload": {
                        "frame_id": "L2:revision_query_frame:0001",
                        "query_text": SOURCE_PATH,
                        "query_source": "revision_llm_query_plan",
                        "target_tool_name": "read_code_file",
                        "read_code_file_start_char": 12000,
                    },
                }
            ],
        },
        user_input="test",
    )

    assert "code range start: 12000" in rendered


def _range_record(
    *,
    start: int = 0,
    end: int = 12000,
    total: int = 25000,
    tool_id: str = FIRST_TOOL_RESULT_ID,
) -> CodeReadRangeRecord:
    return CodeReadRangeRecord(
        tool_result_data_id=tool_id,
        file_path=SOURCE_PATH,
        requested_start_char=start,
        range_start_char=start,
        range_end_char_exclusive=end,
        returned_char_count=end - start,
        total_char_count=total,
        truncated_before=start > 0,
        truncated_after=end < total,
        read_status="ok",
    )


def _revision_stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id=TURN_ID,
        actor="test",
        event_type="node_output",
        output_ref=["source:order_259"],
        schema_status="passed",
    )
    return trace_store, data_store, event.event_id


def _record_revision_input(*, data_store: DataStore, trace_id: str) -> None:
    code_range = _range_record()
    option = build_code_read_continuation_options([code_range])[0]
    data_store.create_record(
        data_id="L2:revision_input:0001",
        data_type="node_input:L2_revision_input_frame",
        source_trace_id=trace_id,
        payload={
            "attempt_index": 1,
            "remaining_query_attempts": 0,
            "remaining_read_doc_calls": 0,
            "remaining_read_code_file_calls": 1,
            "unread_candidate_doc_ids": [],
            "unread_candidate_summaries": [],
            "read_code_file_ranges": [asdict(code_range)],
            "code_read_continuation_options": [asdict(option)],
            "source_trace_ids": [trace_id],
            "source_data_ids": [FIRST_TOOL_RESULT_ID],
        },
    )
