from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L3AchievementFrame,
    Node4GatekeeperFrame,
    validate_l3_achievement_frame,
    validate_node4_gatekeeper_frame,
)
from songryeon_core.nodes.l3_result_keeper import (
    L3_ACHIEVEMENT_FRAME_DATA_ID,
    _annotate_revision_evidence_delta,
)
from songryeon_core.runtime.terminal_view import render_runtime_view


def _achievement(
    *,
    frame_id: str,
    status: str,
    read_doc_ids: list[str],
    read_code_file_paths: list[str] | None = None,
    search_result_doc_ids: list[str] | None = None,
) -> L3AchievementFrame:
    code_paths = list(read_code_file_paths or [])
    candidate_ids = list(search_result_doc_ids or [])
    original_count = len(read_doc_ids) + len(code_paths)
    return L3AchievementFrame(
        frame_id=frame_id,
        turn_id="turn_order_281",
        achievement_status=status,
        reason="ORDER_281 test frame",
        target_goal_data_id="L1:goal_frame",
        preserved_info_frame_id="L3:preserved_info_frame",
        candidate_count=len(candidate_ids),
        read_doc_ids=list(read_doc_ids),
        actual_read_doc_count=len(read_doc_ids),
        read_code_file_paths=code_paths,
        actual_read_code_file_count=len(code_paths),
        search_result_doc_ids=candidate_ids,
        original_material_count=original_count,
        evidence_acquisition_status=(
            "original_material_acquired"
            if original_count > 0
            else "candidates_only"
            if candidate_ids
            else "none"
        ),
    )


def _store_previous(frame: L3AchievementFrame) -> DataStore:
    validate_l3_achievement_frame(frame)
    store = DataStore()
    store.create_record(
        data_id=L3_ACHIEVEMENT_FRAME_DATA_ID,
        data_type="node_output:L3_achievement_frame",
        payload=asdict(frame),
        source_trace_id="trace_order_281_previous",
    )
    return store


def test_revision_records_status_change_without_new_original_material() -> None:
    previous = _achievement(
        frame_id=L3_ACHIEVEMENT_FRAME_DATA_ID,
        status="partial",
        read_doc_ids=["docs/old.md"],
        search_result_doc_ids=["docs/old.md"],
    )
    store = _store_previous(previous)
    current = _achievement(
        frame_id="L3:revision_achievement:0001",
        status="achieved",
        read_doc_ids=["docs/old.md"],
        search_result_doc_ids=["docs/old.md", "docs/new_candidate.md"],
    )

    annotated = _annotate_revision_evidence_delta(
        frame=current,
        data_store=store,
        attempt_index=1,
        id_namespace=None,
    )
    validate_l3_achievement_frame(annotated)

    assert annotated.revision_evidence_delta_status == "recorded"
    assert annotated.previous_achievement_frame_id == L3_ACHIEVEMENT_FRAME_DATA_ID
    assert annotated.new_read_doc_ids == []
    assert annotated.new_read_doc_count == 0
    assert annotated.new_read_code_file_count == 0
    assert annotated.new_original_material_count == 0
    assert annotated.evidence_set_changed is False
    assert annotated.candidate_set_changed is True
    assert annotated.achievement_status_changed is True
    assert annotated.achievement_changed_without_new_original_material is True
    assert L3_ACHIEVEMENT_FRAME_DATA_ID in annotated.source_data_ids
    assert "trace_order_281_previous" in annotated.source_trace_ids


def test_revision_records_exact_new_document_and_code_originals() -> None:
    previous = _achievement(
        frame_id=L3_ACHIEVEMENT_FRAME_DATA_ID,
        status="partial",
        read_doc_ids=["docs/old.md"],
        search_result_doc_ids=["docs/old.md", "docs/new.md"],
    )
    store = _store_previous(previous)
    current = _achievement(
        frame_id="L3:revision_achievement:0001",
        status="achieved",
        read_doc_ids=["docs/old.md", "docs/new.md"],
        read_code_file_paths=["songryeon_core/new.py"],
        search_result_doc_ids=["docs/old.md", "docs/new.md"],
    )

    annotated = _annotate_revision_evidence_delta(
        frame=current,
        data_store=store,
        attempt_index=1,
        id_namespace=None,
    )
    validate_l3_achievement_frame(annotated)

    assert annotated.new_read_doc_ids == ["docs/new.md"]
    assert annotated.new_read_doc_count == 1
    assert annotated.new_read_code_file_paths == ["songryeon_core/new.py"]
    assert annotated.new_read_code_file_count == 1
    assert annotated.new_original_material_count == 2
    assert annotated.evidence_set_changed is True
    assert annotated.candidate_set_changed is False
    assert annotated.achievement_changed_without_new_original_material is False


def test_missing_previous_frame_is_explicit_and_does_not_invent_delta() -> None:
    current = _achievement(
        frame_id="L3:revision_achievement:0001",
        status="partial",
        read_doc_ids=["docs/current.md"],
        search_result_doc_ids=["docs/current.md"],
    )

    annotated = _annotate_revision_evidence_delta(
        frame=current,
        data_store=DataStore(),
        attempt_index=1,
        id_namespace=None,
    )
    validate_l3_achievement_frame(annotated)

    assert annotated.revision_evidence_delta_status == "previous_frame_missing"
    assert annotated.previous_achievement_frame_id is None
    assert annotated.new_original_material_count == 0
    assert annotated.evidence_set_changed is False


def test_node4_scope_is_fixed_and_runtime_displays_both_boundaries() -> None:
    previous = _achievement(
        frame_id=L3_ACHIEVEMENT_FRAME_DATA_ID,
        status="partial",
        read_doc_ids=["docs/old.md"],
        search_result_doc_ids=["docs/old.md"],
    )
    store = _store_previous(previous)
    current = _achievement(
        frame_id="L3:revision_achievement:0001",
        status="achieved",
        read_doc_ids=["docs/old.md"],
        search_result_doc_ids=["docs/old.md", "docs/new_candidate.md"],
    )
    annotated = _annotate_revision_evidence_delta(
        frame=current,
        data_store=store,
        attempt_index=1,
        id_namespace=None,
    )
    gate = Node4GatekeeperFrame(
        gate_id="node_4:gatekeeper_frame",
        turn_id="turn_order_281",
        report_id="node_3:report",
        boundary_id="node_2:boundary",
        gate_status="pass",
        reason="supplied evidence is internally consistent",
        gate_generation_source="LLM:test",
        llm_gate_status="pass",
    )
    validate_node4_gatekeeper_frame(gate)

    rendered = render_runtime_view(
        {
            "status": "ok",
            "data_records": [
                {
                    "data_id": annotated.frame_id,
                    "data_type": "node_output:L3_revision_achievement_frame",
                    "payload": asdict(annotated),
                },
                {
                    "data_id": gate.gate_id,
                    "data_type": "node_output:node4_gatekeeper_frame",
                    "payload": asdict(gate),
                },
            ],
        },
        user_input="ORDER_281 runtime boundary",
    )

    assert "L3 revision 근거 변화 [CODE]" in rendered
    assert "new_read_doc=0" in rendered
    assert "changed_without_new_original=True" in rendered
    assert "evidence=supplied_evidence_bundle" in rendered
    assert "project_currentness=not_run" in rendered

    with pytest.raises(ValueError, match="gate_evidence_scope"):
        validate_node4_gatekeeper_frame(
            replace(gate, gate_evidence_scope="whole_project_currentness")
        )
