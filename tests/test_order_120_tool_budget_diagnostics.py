from __future__ import annotations

from dataclasses import asdict

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import ToolUseBudgetFrame, validate_tool_use_budget_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_continuation import record_l_loop_continuation_decision
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_pretty_turn
from songryeon_core.runtime.user_turn import _structure_failure_diagnostics
from songryeon_core.tools.tool_efficiency_policy import (
    BudgetConsistencyError,
    record_tool_use_budget_frame,
)


LIVE_LIKE_INPUT = (
    "지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. "
    "단, 이건 네 해석이라는 점을 밝혀줘."
)


def test_tool_use_budget_validator_keeps_query_count_limit() -> None:
    frame = _budget_frame(
        budget_id="tool_budget:test:invalid",
        max_query_attempts=1,
        query_count=2,
        executed_queries=["first", "second"],
    )

    with pytest.raises(ValueError, match="query_count must not exceed max_query_attempts"):
        validate_tool_use_budget_frame(frame)


def test_valid_tool_use_budget_frame_records_successfully() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    event_id, budget_id = record_tool_use_budget_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_120",
        sequence_index=1,
        max_tool_calls=3,
        search_top_k=2,
        max_query_attempts=2,
        max_read_doc_calls=1,
        max_input_chars=1000,
        tool_call_count=1,
        executed_queries=["alpha"],
        read_doc_ids=[],
        cache_statuses=[],
        input_chars_used=10,
        stop_reason="within_budget",
        reason="CODE_STATUS:test_valid_budget",
        source_trace_ids=["trace:test"],
        source_data_ids=["source:test"],
    )

    record = data_store.require_record(budget_id)
    payload = record.payload
    assert event_id
    assert isinstance(payload, dict)
    assert payload["query_count"] == 1
    assert payload["max_query_attempts"] == 2
    assert payload["tool_call_count"] == 1
    assert payload["max_tool_calls"] == 3
    assert payload["read_doc_count"] == 0
    assert payload["max_read_doc_calls"] == 1


def test_budget_failure_diagnostics_expose_query_count_mismatch() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    with pytest.raises(BudgetConsistencyError) as exc_info:
        record_tool_use_budget_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id="turn_order_120",
            sequence_index=2,
            max_tool_calls=3,
            search_top_k=2,
            max_query_attempts=1,
            max_read_doc_calls=1,
            max_input_chars=1000,
            tool_call_count=1,
            executed_queries=["alpha", "beta"],
            read_doc_ids=[],
            cache_statuses=[],
            input_chars_used=20,
            stop_reason="within_budget",
            reason="CODE_STATUS:test_invalid_budget",
            source_trace_ids=["trace:test"],
            source_data_ids=["route:L", "L:budget_plan_frame"],
        )

    diagnostics = exc_info.value.budget_diagnostics
    assert diagnostics["budget_failure_type"] == "query_count_exceeded_max_query_attempts"
    assert diagnostics["budget_failure_frame_id"] == "tool_budget:turn_order_120:0002"
    assert diagnostics["budget_failure_query_count"] == 2
    assert diagnostics["budget_failure_max_query_attempts"] == 1
    assert diagnostics["budget_failure_tool_calls"] == 1
    assert diagnostics["budget_failure_max_tool_calls"] == 3
    assert diagnostics["budget_failure_read_doc_count"] == 0
    assert diagnostics["budget_failure_max_read_doc"] == 1
    assert diagnostics["budget_failure_stage"] == "record_tool_use_budget_frame:validate"


def test_structure_failed_renderer_includes_budget_failure_diagnostics() -> None:
    diagnostics = _structure_failure_diagnostics(
        BudgetConsistencyError(
            "ToolUseBudgetFrame.query_count must not exceed max_query_attempts",
            diagnostics={
                "budget_failure_type": "query_count_exceeded_max_query_attempts",
                "budget_failure_reason": (
                    "ToolUseBudgetFrame.query_count must not exceed max_query_attempts"
                ),
                "budget_failure_frame_id": "tool_budget:turn_order_120:0002",
                "budget_failure_source_data_ids": ["route:L", "L:budget_plan_frame"],
                "budget_failure_route": "L",
                "budget_failure_l_run_id": "L:run:0001",
                "budget_failure_query_count": 2,
                "budget_failure_max_query_attempts": 1,
                "budget_failure_tool_calls": 1,
                "budget_failure_max_tool_calls": 3,
                "budget_failure_read_doc_count": 0,
                "budget_failure_max_read_doc": 1,
                "budget_failure_stage": "record_tool_use_budget_frame:validate",
            },
        )
    )
    result = {
        "status": "structure_failed",
        "trace_count": 0,
        "data_record_count": 0,
        **diagnostics,
    }

    rendered = render_pretty_turn(result, user_input=LIVE_LIKE_INPUT)

    assert "budget_failure_type: query_count_exceeded_max_query_attempts" in rendered
    assert "budget_failure_query_count: 2" in rendered
    assert "budget_failure_max_query_attempts: 1" in rendered
    assert "예산 진단: type=query_count_exceeded_max_query_attempts" in rendered
    assert "query=2/1" in rendered


def test_continuation_continues_when_query_budget_exhausted_but_unread_read_path_exists() -> None:
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
            "search_result_doc_ids": ["doc:unread"],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        payload={"query_text": "previous query"},
    )
    exhausted_budget = _budget_frame(
        budget_id="tool_budget:turn_order_120:0008",
        max_query_attempts=8,
        query_count=8,
        executed_queries=[f"query {index}" for index in range(8)],
    )
    data_store.create_record(
        data_id=exhausted_budget.budget_id,
        data_type="tool_use_budget",
        payload=asdict(exhausted_budget),
    )

    _, _, frame = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_120",
        attempt_index=8,
        max_attempts=12,
        l3_achievement_data_id="L3:achievement_frame",
        l2_query_frame_data_id="L2:query_frame",
    )

    assert frame.continuation_status == "continue"
    assert (
        frame.continuation_reason_code
        == "CODE_STATUS:l3_not_achieved_read_unread_candidate_after_query_budget"
    )
    assert frame.next_target_node == "L2"


def test_continuation_stops_when_query_budget_exhausted_and_no_unread_read_path() -> None:
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
            "search_result_doc_ids": [],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        payload={"query_text": "previous query"},
    )
    exhausted_budget = _budget_frame(
        budget_id="tool_budget:turn_order_120:0008",
        max_query_attempts=8,
        query_count=8,
        executed_queries=[f"query {index}" for index in range(8)],
    )
    data_store.create_record(
        data_id=exhausted_budget.budget_id,
        data_type="tool_use_budget",
        payload=asdict(exhausted_budget),
    )

    _, _, frame = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_120",
        attempt_index=8,
        max_attempts=12,
        l3_achievement_data_id="L3:achievement_frame",
        l2_query_frame_data_id="L2:query_frame",
    )

    assert frame.continuation_status == "stop_budget_exhausted"
    assert frame.continuation_reason_code == "CODE_STATUS:continuation_query_budget_exhausted"
    assert frame.next_target_node == "loop_return_summary"


def test_live_like_opinion_input_no_budget_query_count_structure_failure() -> None:
    result = run_dry_turn(user_input=LIVE_LIKE_INPUT)

    assert result["current_route"] == "2"
    for record in result["data_records"]:
        if record.get("data_type") != "tool_use_budget":
            continue
        payload = record.get("payload")
        assert isinstance(payload, dict)
        assert payload["query_count"] <= payload["max_query_attempts"]


def _budget_frame(
    *,
    budget_id: str,
    max_query_attempts: int,
    query_count: int,
    executed_queries: list[str],
) -> ToolUseBudgetFrame:
    return ToolUseBudgetFrame(
        budget_id=budget_id,
        turn_id="turn_order_120",
        loop_id="L",
        sequence_index=1,
        max_tool_calls=3,
        search_top_k=2,
        max_query_attempts=max_query_attempts,
        max_query_candidates=max_query_attempts,
        max_read_doc_calls=1,
        max_input_chars=1000,
        tool_call_count=1,
        query_count=query_count,
        read_doc_count=0,
        input_chars_used=10,
        executed_queries=executed_queries,
        read_doc_ids=[],
        cache_statuses=[],
        stop_reason="within_budget",
        reason="CODE_STATUS:test_budget_frame",
    )
