import json

from songryeon_core.core.r_loop_vessel_read_packet import (
    R_LOOP_VESSEL_SOURCE_LEAF_RAW_RESOLUTION_POLICY_ID,
    build_r_loop_vessel_read_packet_from_neo4j,
)
from songryeon_core.loops.r_loop_vessel_one_step import _selected_candidate_record

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
    _time_bundle_row,
)
from tests.test_order_188_r_vessel_raw_original_cap import _raw_source_chain_row


RAW_ID = "graph:raw_source:internal_document:order_233_exact"
SUMMARY_ID = "graph:summary:source_leaf:order_233_exact"


def test_source_leaf_exact_raw_target_is_appended_outside_base_candidates() -> None:
    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_233_exact_raw_resolution",
        created_at=READ_AT,
        limit=3,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[]),
                _time_bundle_row(),
                _raw_source_chain_row(
                    raw_id=RAW_ID,
                    next_raw_id=None,
                    parent_id="graph:source_kind_bundle:not_in_base_surface",
                ),
            ],
            summary_rows=[_source_leaf_summary_row(RAW_ID)],
        ),
    )

    entry_ids = [record["candidate_node_id"] for record in packet.entry_candidate_records]
    assert packet.source_leaf_raw_resolution_policy_id == (
        R_LOOP_VESSEL_SOURCE_LEAF_RAW_RESOLUTION_POLICY_ID
    )
    assert packet.source_leaf_raw_target_node_ids == [RAW_ID]
    assert packet.source_leaf_raw_resolved_node_ids == [RAW_ID]
    assert packet.source_leaf_raw_appended_node_ids == [RAW_ID]
    assert packet.source_leaf_raw_missing_node_ids == []
    assert RAW_ID in entry_ids

    selected = _selected_candidate_record(packet, SUMMARY_ID)
    assert selected["hierarchy_child_node_ids"] == [RAW_ID]
    assert selected["hierarchy_child_candidate_records"][0]["candidate_kind"] == (
        "raw_source"
    )


def test_missing_exact_raw_target_is_recorded_without_substitution() -> None:
    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_233_missing_raw_resolution",
        created_at=READ_AT,
        limit=3,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[]),
                _time_bundle_row(),
            ],
            summary_rows=[_source_leaf_summary_row(RAW_ID)],
        ),
    )

    assert packet.source_leaf_raw_target_node_ids == [RAW_ID]
    assert packet.source_leaf_raw_resolved_node_ids == []
    assert packet.source_leaf_raw_appended_node_ids == []
    assert packet.source_leaf_raw_missing_node_ids == [RAW_ID]
    assert any("missing=1" in line for line in packet.packet_lines)


def _source_leaf_summary_row(raw_id: str) -> dict[str, object]:
    return {
        "summary_node_id": SUMMARY_ID,
        "summary_display_name": "Source leaf summary for ORDER 233",
        "data_kind": "source_leaf_summary",
        "info_class": "relative",
        "generated_by": "LLM:fake:night_summarize_source_leaf",
        "payload_json": json.dumps(
            {
                "data_kind": "source_leaf_summary",
                "summary_depth": 1,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": raw_id,
                "target_node_kind": "raw_source",
                "source_leaf_count": 1,
                "source_summary_count": 0,
                "source_graph_node_ids": [raw_id],
                "source_data_ids": [raw_id],
                "source_trace_ids": ["trace:order_233:summary"],
                "summary_text": "ORDER 233 exact raw resolution test summary.",
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": raw_id,
        "target_display_name": "Raw Source for ORDER 233",
        "target_node_kind": "raw_source",
    }
