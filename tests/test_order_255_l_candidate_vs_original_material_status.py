from __future__ import annotations

from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MemoryPacketFrom0, MetainfoBoundary, ZeroState
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.nodes.node_0_memory_supplier import (
    record_l_loop_return_summary_for_node1,
)
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools import tool_runner as tool_runner_module


def test_candidate_only_read_result_is_not_original_material(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_searchable_document(tmp_path)

    def empty_read_doc(*, root: str | Path, doc_id: str) -> dict[str, object]:
        return {"doc_id": doc_id, "text": "", "char_count": 0}

    monkeypatch.setattr(tool_runner_module, "read_doc", empty_read_doc)
    trace_store, data_store, result = _run_l_loop(
        tmp_path,
        turn_id="turn_order_255_empty",
        l1_goal_adapter=SongRyeonAllNodesFakeLLMAdapter(),
    )

    assert result.final_control_decision == "stop_candidate_only"
    control = _payload(data_store, result.final_control_data_id)
    assert control["decision"] == "stop_candidate_only"
    assert control["reason"] == "CODE_STATUS:stop_candidate_only_without_original_material"

    achievement = _latest_payload(data_store, "node_output:L3_achievement_frame")
    assert achievement["candidate_count"] > 0
    assert achievement["actual_read_doc_count"] == 0
    assert achievement["original_material_count"] == 0
    assert achievement["evidence_acquisition_status"] == "candidates_only"
    assert achievement["original_material_required_count"] == 2
    assert achievement["original_material_requirement_status"] == "unsatisfied"
    assert achievement["achievement_status"] == "partial"

    _, _, return_summary_id, _ = record_l_loop_return_summary_for_node1(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_255_empty",
        zero_state=ZeroState(),
        input_ref=result.source_trace_ids,
        source_data_ids=result.output_data_ids,
    )
    return_summary = _payload(data_store, return_summary_id)
    assert return_summary["search_candidate_count"] > 0
    assert return_summary["actual_read_doc_count"] == 0
    assert return_summary["evidence_acquisition_status"] == "candidates_only"
    assert return_summary["original_material_count"] == 0
    assert return_summary["original_material_requirement_status"] == "unsatisfied"

    handoff_trace = trace_store.create_event(
        turn_id="turn_order_255_empty",
        actor="test",
        event_type="node_output",
        output_ref=["node_2:handoff_frame"],
        schema_status="passed",
    )
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_255_empty",
        user_question="needle 후보의 원문을 확인해줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[handoff_trace.event_id],
        source_data_ids=[return_summary_id],
    )
    assert brief.l_evidence_acquisition_status == "candidates_only"
    assert brief.l_original_material_count == 0
    assert brief.l_original_material_requirement_status == "unsatisfied"

    rendered = render_runtime_view(
        {"data_records": data_store.to_records()},
        user_input="ORDER_255 candidate-only",
    )
    assert "L3 근거 확보 절대상태: candidates_only" in rendered
    assert "status=candidates_only" in rendered


def test_nonempty_read_doc_is_original_material(tmp_path: Path) -> None:
    _write_searchable_document(tmp_path)
    _, data_store, result = _run_l_loop(tmp_path, turn_id="turn_order_255_original")

    assert result.final_control_decision == "stop_success"
    achievement = _latest_payload(data_store, "node_output:L3_achievement_frame")
    assert achievement["actual_read_doc_count"] == 1
    assert achievement["original_material_count"] == 1
    assert achievement["evidence_acquisition_status"] == "original_material_acquired"
    assert achievement["achievement_status"] == "achieved"


def _run_l_loop(
    root: Path,
    *,
    turn_id: str,
    l1_goal_adapter: object | None = None,
) -> tuple[TraceStore, DataStore, object]:
    trace_store = TraceStore()
    data_store = DataStore()
    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=MemoryPacketFrom0(target="L", trace_evidence_ids=[]),
        search_query="needle",
        document_root=root,
        l1_goal_adapter=l1_goal_adapter,
        max_tool_calls=5,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )
    return trace_store, data_store, result


def _write_searchable_document(root: Path) -> None:
    (root / "NEEDLE_DOCUMENT.md").write_text(
        "# Needle\n\nneedle original material",
        encoding="utf-8",
    )


def _payload(data_store: DataStore, data_id: str | None) -> dict[str, object]:
    assert isinstance(data_id, str) and data_id
    payload = data_store.require_record(data_id).payload
    assert isinstance(payload, dict)
    return payload


def _latest_payload(data_store: DataStore, data_type: str) -> dict[str, object]:
    matches = [
        record
        for record in data_store.list_records()
        if record.data_type == data_type
    ]
    assert matches
    payload = matches[-1].payload
    assert isinstance(payload, dict)
    return payload
