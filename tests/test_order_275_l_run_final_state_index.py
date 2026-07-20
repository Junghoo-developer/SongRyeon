from __future__ import annotations

from pathlib import Path

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    LLoopFinalStateIndexFrame,
    MemoryPacketFrom0,
    validate_l_loop_final_state_index_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.loops.l_loop_final_state import record_l_loop_final_state_index
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_runtime_view


def test_final_state_index_preserves_failed_control_and_latest_achieved_revision() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    control_trace = trace_store.create_event(
        turn_id="turn_order_275",
        actor="L_controller",
        event_type="node_output",
        output_ref=["L:control_frame:0001"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L:control_frame:0001",
        data_type="node_output:L_loop_control_frame",
        source_trace_id=control_trace.event_id,
        payload={"decision": "stop_failed"},
    )
    revision_trace = trace_store.create_event(
        turn_id="turn_order_275",
        actor="L3",
        event_type="node_output",
        output_ref=["L3:revision_achievement_frame:0001"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L3:revision_achievement_frame:0001",
        data_type="node_output:L3_revision_achievement_frame",
        source_trace_id=revision_trace.event_id,
        payload={
            "achievement_status": "achieved",
            "achievement_generation_source": "LLM:TEST_L3",
        },
    )
    continuation_trace = trace_store.create_event(
        turn_id="turn_order_275",
        actor="L_continuation_controller",
        event_type="node_output",
        output_ref=["L:continuation_frame:0001"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L:continuation_frame:0001",
        data_type="node_output:L_loop_continuation_frame",
        source_trace_id=continuation_trace.event_id,
        payload={"continuation_status": "stop_achieved"},
    )

    _, data_id, frame = record_l_loop_final_state_index(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_275",
        latest_l3_achievement_data_id="L3:revision_achievement_frame:0001",
        pre_revision_terminal_control_data_id="L:control_frame:0001",
        final_continuation_data_id="L:continuation_frame:0001",
    )

    assert data_id == "L:final_state_index_frame"
    assert frame.pre_revision_terminal_control_decision == "stop_failed"
    assert frame.pre_revision_terminal_control_scope == (
        "legacy_pre_revision_terminal_control"
    )
    assert frame.latest_l3_achievement_status == "achieved"
    assert frame.final_status_source_data_id == "L3:revision_achievement_frame:0001"
    assert frame.final_status_source_kind == "latest_l3_achievement"
    assert frame.final_continuation_status == "stop_achieved"
    assert frame.generated_by == "CODE:L_LOOP_FINAL_STATE_INDEXER"
    assert frame.semantic_judgement_status == "not_run"


def test_final_state_index_rejects_a_different_final_status_source() -> None:
    frame = LLoopFinalStateIndexFrame(
        frame_id="L:final_state_index_frame",
        turn_id="turn_order_275_invalid",
        run_index=1,
        latest_l3_achievement_data_id="L3:revision_achievement_frame:0001",
        latest_l3_achievement_status="achieved",
        latest_l3_achievement_generation_source="LLM:TEST_L3",
        final_status_source_data_id="L3:achievement_frame",
        source_data_ids=[
            "L3:revision_achievement_frame:0001",
            "L3:achievement_frame",
        ],
    )

    with pytest.raises(ValueError, match="final source must equal latest L3"):
        validate_l_loop_final_state_index_frame(frame)


def test_run_l_loop_records_final_state_index_and_terminal_separates_states(
    tmp_path: Path,
) -> None:
    (tmp_path / "ORDER_275_TARGET.md").write_text(
        "# ORDER 275\n\norder_275_unique_target original material",
        encoding="utf-8",
    )
    trace_store = TraceStore()
    data_store = DataStore()

    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_275_integrated",
        memory_packet=MemoryPacketFrom0(target="L", trace_evidence_ids=[]),
        search_query="order_275_unique_target",
        document_root=tmp_path,
        max_tool_calls=5,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    assert result.final_state_index_data_ids == ["L:final_state_index_frame"]
    assert "L:final_state_index_frame" in result.output_data_ids
    payload = data_store.require_record("L:final_state_index_frame").payload
    assert isinstance(payload, dict)
    assert payload["latest_l3_achievement_data_id"] == result.achievement_data_ids[-1]
    assert payload["final_status_source_data_id"] == result.achievement_data_ids[-1]
    assert payload["pre_revision_terminal_control_decision"] == (
        result.final_control_decision
    )

    rendered = render_runtime_view(
        {"data_records": data_store.to_records()},
        user_input="ORDER_275 상태 색인 확인",
    )
    assert "L 최종 상태 색인 [CODE]" in rendered
    assert "최초 도구 종료 판단" in rendered
    assert "revision 포함 최신 상태" in rendered


def test_dry_turn_exports_legacy_scope_and_canonical_latest_status() -> None:
    result = run_dry_turn(
        "ORDER_275 발주서 원문을 확인해줘",
        turn_id="turn_order_275_export",
        force_l_route=True,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    assert result["l_loop_final_state_index_data_id"]
    assert result["l_loop_final_decision_scope"] == (
        "legacy_pre_revision_terminal_control"
    )
    assert result["l_loop_final_status_source_data_id"] == (
        result["l_loop_latest_l3_achievement_data_id"]
    )
    assert result["l_loop_final_status_source_kind"] == "latest_l3_achievement"
    ledgers = [
        item["payload"]
        for item in result["data_records"]
        if item.get("data_type") == "loop_activity:l_loop_activity_ledger_frame"
    ]
    assert ledgers
    assert ledgers[-1]["final_state_index_data_ids"] == [
        result["l_loop_final_state_index_data_id"]
    ]
    assert any(
        record.get("stage") == "final_state_index"
        for record in ledgers[-1]["activity_records"]
    )
