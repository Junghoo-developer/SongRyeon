from __future__ import annotations

import pytest

from songryeon_core.core.schemas import (
    L_LOOP_ACTIVITY_LEDGER_DATA_TYPE,
    LLoopActivityLedgerFrame,
    validate_l_loop_activity_ledger_frame,
)
from songryeon_core.runtime.dry_run import run_dry_turn


def test_l_loop_activity_ledger_is_recorded_from_dry_turn() -> None:
    result = run_dry_turn()
    records = {
        item["data_id"]: item
        for item in result["data_records"]
        if isinstance(item, dict)
    }
    ledger_record = records.get("L:activity_ledger_frame")
    assert ledger_record is not None
    assert ledger_record["data_type"] == L_LOOP_ACTIVITY_LEDGER_DATA_TYPE
    ledger = ledger_record["payload"]

    assert ledger["generated_by"] == "CODE:L_LOOP_ACTIVITY_LEDGER"
    assert ledger["info_class"] == "absolute"
    assert ledger["semantic_judgement_status"] == "not_run"
    assert ledger["turn_capsule_graph_node_id"] == "graph:raw_capsule:turn_dry_001"
    assert ledger["return_summary_frame_id"] == "L:return_summary_frame"
    assert ledger["document_material_packet_frame_id"] == "node_0:document_material_packet_frame"
    assert "L1:goal_frame" in ledger["goal_data_ids"]
    assert "L2:query_frame" in ledger["query_data_ids"]
    assert "L3:achievement_frame" in ledger["achievement_data_ids"]
    assert ledger["output_data_id_count"] == len(ledger["output_data_ids"])
    assert ledger["tool_result_count"] == len(ledger["tool_result_data_ids"])
    assert ledger["actual_read_doc_count"] == len(ledger["read_doc_ids"])
    assert ledger["search_candidate_doc_count"] == len(ledger["search_candidate_doc_ids"])


def test_l_loop_activity_ledger_sources_include_indexed_records() -> None:
    result = run_dry_turn()
    records = {
        item["data_id"]: item["payload"]
        for item in result["data_records"]
        if isinstance(item, dict)
    }
    ledger = records["L:activity_ledger_frame"]
    source_data_ids = set(ledger["source_data_ids"])
    required = {
        "L:run_frame:0001",
        "L:return_summary_frame",
        "node_0:document_material_packet_frame",
        *ledger["output_data_ids"],
    }

    assert required <= source_data_ids
    for record in ledger["activity_records"]:
        assert record["data_id"] in source_data_ids


def test_l_loop_activity_ledger_validator_rejects_semantic_status() -> None:
    frame = LLoopActivityLedgerFrame(
        frame_id="L:activity_ledger_frame",
        turn_id="turn_test",
        run_index=1,
        turn_capsule_graph_node_id="graph:raw_capsule:turn_test",
        run_frame_data_ids=["L:run_frame:0001"],
        output_data_ids=["L:run_frame:0001"],
        output_data_id_count=1,
        activity_records=[
            {
                "stage": "run_frame",
                "data_id": "L:run_frame:0001",
                "source_field": "run_frame_data_ids",
            }
        ],
        source_data_ids=["L:run_frame:0001"],
        semantic_judgement_status="ran",
    )

    with pytest.raises(ValueError, match="semantic_judgement_status"):
        validate_l_loop_activity_ledger_frame(frame)
