from __future__ import annotations

from dataclasses import asdict

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import CodeReadRangeRecord
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.l2_revision_input import record_l2_revision_input_frame
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools.code_tools import read_code_file
from songryeon_core.tools.tool_efficiency_policy import (
    BudgetConsistencyError,
    record_tool_use_budget_frame,
)


TURN_ID = "turn_order_258"
TOOL_RESULT_ID = "tool_result:read_code_file:order_258"
MEMORY_PACKET_ID = "memory_packet:L2:l3_continuation_summary_for_L2:0001"


def test_read_code_file_reports_exact_requested_range_and_truncation(tmp_path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("abcdefghij", encoding="utf-8")

    payload = read_code_file(
        root=tmp_path,
        file_path="sample.py",
        start_char=3,
        max_chars=4,
    )

    assert payload["text"] == "defg"
    assert payload["requested_start_char"] == 3
    assert payload["range_start_char"] == 3
    assert payload["range_end_char_exclusive"] == 7
    assert payload["returned_char_count"] == 4
    assert payload["total_char_count"] == 10
    assert payload["truncated_before"] is True
    assert payload["truncated_after"] is True
    assert payload["truncated"] is True


def test_code_read_budget_rejects_a_range_after_budget_is_exhausted() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    code_range = _code_range()

    with pytest.raises(BudgetConsistencyError, match="read_code_file_count"):
        record_tool_use_budget_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=TURN_ID,
            sequence_index=1,
            max_tool_calls=1,
            search_top_k=1,
            max_query_attempts=1,
            max_read_doc_calls=1,
            max_input_chars=12000,
            tool_call_count=1,
            executed_queries=[],
            read_doc_ids=[],
            cache_statuses=[],
            input_chars_used=4,
            stop_reason="within_budget",
            reason="test",
            max_read_code_file_calls=0,
            read_code_file_ranges=[code_range],
        )


def test_revision_input_preserves_code_range_history_and_remaining_budget() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    seed = trace_store.create_event(
        turn_id=TURN_ID,
        actor="test",
        event_type="node_output",
        output_ref=["seed:order_258"],
        schema_status="passed",
    )
    _record_revision_sources(data_store=data_store, trace_id=seed.event_id)
    _, budget_id = record_tool_use_budget_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        sequence_index=1,
        max_tool_calls=3,
        search_top_k=1,
        max_query_attempts=1,
        max_read_doc_calls=1,
        max_input_chars=12000,
        tool_call_count=1,
        executed_queries=[],
        read_doc_ids=[],
        cache_statuses=[],
        input_chars_used=4,
        stop_reason="within_budget",
        reason="one code range was read",
        max_read_code_file_calls=2,
        read_code_file_ranges=[_code_range()],
        source_trace_ids=[seed.event_id],
        source_data_ids=[TOOL_RESULT_ID],
    )

    _, _, frame = record_l2_revision_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        continuation_frame_id="L:continuation:0001",
    )

    assert frame.previous_tool_name == "read_code_file"
    assert frame.remaining_read_code_file_calls == 1
    assert frame.read_code_file_ranges == [_code_range()]
    assert len(frame.code_read_continuation_options) == 1
    assert frame.code_read_continuation_options[0].file_path == "sample.py"
    assert frame.code_read_continuation_options[0].start_char == 7
    assert TOOL_RESULT_ID in frame.source_data_ids
    assert budget_id in frame.source_data_ids


def test_terminal_displays_code_read_budget_range_and_truncation() -> None:
    payload = {
        "budget_id": "tool_budget:turn_order_258:0001",
        "turn_id": TURN_ID,
        "loop_id": "L",
        "sequence_index": 1,
        "max_tool_calls": 3,
        "search_top_k": 1,
        "max_query_attempts": 1,
        "max_query_candidates": 1,
        "max_read_doc_calls": 1,
        "max_input_chars": 12000,
        "tool_call_count": 1,
        "query_count": 0,
        "read_doc_count": 0,
        "input_chars_used": 4,
        "max_read_code_file_calls": 2,
        "read_code_file_count": 1,
        "read_code_file_ranges": [asdict(_code_range())],
        "executed_queries": [],
        "read_doc_ids": [],
        "cache_statuses": [],
        "duplicate_query_count": 0,
        "duplicate_doc_count": 0,
        "stop_reason": "within_budget",
        "reason": "test",
        "condition_flags": ["within_budget"],
        "source_trace_ids": [],
        "source_data_ids": [TOOL_RESULT_ID],
        "schema_name": "ToolUseBudgetFrame",
        "schema_version": "0.1",
    }
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "test", "transport": "fake"},
            "trace_count": 0,
            "data_record_count": 1,
            "data_records": [
                {
                    "data_id": payload["budget_id"],
                    "data_type": "tool_use_budget",
                    "payload": payload,
                }
            ],
        },
        user_input="test",
    )

    assert "read_code_file=1/2" in rendered
    assert "sample.py [3, 7)/10" in rendered
    assert "truncated_before=True" in rendered
    assert "truncated_after=True" in rendered


def _code_range() -> CodeReadRangeRecord:
    return CodeReadRangeRecord(
        tool_result_data_id=TOOL_RESULT_ID,
        file_path="sample.py",
        requested_start_char=3,
        range_start_char=3,
        range_end_char_exclusive=7,
        returned_char_count=4,
        total_char_count=10,
        truncated_before=True,
        truncated_after=True,
        read_status="ok",
    )


def _record_revision_sources(*, data_store: DataStore, trace_id: str) -> None:
    records = [
        (
            "L1:goal_frame",
            "node_output:L1_goal_frame",
            {"macro_goal": "inspect code", "micro_goal": "continue exact code reading"},
        ),
        (
            "L2:query_frame",
            "node_output:L2_query_frame",
            {"query_text": "sample.py", "target_tool_name": "read_code_file"},
        ),
        (
            "L3:achievement_frame",
            "node_output:L3_achievement_frame",
            {
                "achievement_status": "partial",
                "goal_match_status": "partial",
                "semantic_goal_match_status": "partial",
                "reason": "more source text may be required",
            },
        ),
        (
            "L:continuation:0001",
            "node_output:L_loop_continuation_frame",
            {
                "attempt_index": 1,
                "max_attempts": 2,
                "continuation_status": "continue",
                "source_l3_achievement_id": "L3:achievement_frame",
                "source_l2_query_frame_id": "L2:query_frame",
                "read_doc_ids": [],
                "unread_candidate_doc_ids": [],
                "source_trace_ids": [trace_id],
            },
        ),
        (
            MEMORY_PACKET_ID,
            "memory_packet:l3_continuation_summary_for_L2",
            {"source_trace_ids": [trace_id]},
        ),
        (
            TOOL_RESULT_ID,
            "tool_result:read_code_file",
            {
                "file_path": "sample.py",
                "read_status": "ok",
                "text": "defg",
                "requested_start_char": 3,
                "range_start_char": 3,
                "range_end_char_exclusive": 7,
                "returned_char_count": 4,
                "total_char_count": 10,
                "truncated_before": True,
                "truncated_after": True,
                "truncated": True,
            },
        ),
    ]
    for data_id, data_type, payload in records:
        data_store.create_record(
            data_id=data_id,
            data_type=data_type,
            source_trace_id=trace_id,
            payload=payload,
        )
