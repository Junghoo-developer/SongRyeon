import json

from songryeon_core.core.schemas import R1GraphGoalFrame, R2GraphNodeSelectionFrame
from songryeon_core.loops.r_loop_vessel_one_step import _r3_input_payload


RAW_ID = "graph:raw_source:internal_document:order_236"
RAW_TEXT = "ORDER 236 selected RawSource original text. " * 80


def test_r3_payload_prioritizes_selected_raw_text_and_compacts_provenance() -> None:
    r1 = _r1_with_large_provenance()
    r2 = _r2_with_large_provenance(r1.frame_id)
    selected = {
        "candidate_node_id": RAW_ID,
        "candidate_kind": "raw_source",
        "node_kind": "raw_source",
        "data_kind": "internal_document",
        "summary_depth": 0,
        "source_leaf_count": 1,
        "source_summary_count": 0,
        "raw_original_text_status": "available",
        "raw_original_text_data_ids": ["source_text:internal_document:order_236"],
        "raw_original_text_char_count": len(RAW_TEXT),
        "raw_original_text_materials": [
            {
                "source_text_data_id": "source_text:internal_document:order_236",
                "text": RAW_TEXT,
                "text_char_count": len(RAW_TEXT),
                "info_class": "absolute",
            }
        ],
        "hierarchy_child_node_ids": [],
        "hierarchy_child_candidate_records": [],
    }

    payload = _r3_input_payload(
        user_question="ORDER 236 원문을 확인해",
        r1=r1,
        r2=r2,
        selected_record=selected,
    )
    encoded = json.dumps(payload, ensure_ascii=False)

    keys = list(payload)
    assert keys.index("selected_candidate_record") < keys.index("r1_goal")
    assert payload["selected_candidate_record"]["raw_original_text_materials"][0][
        "text"
    ] == RAW_TEXT
    assert "source_trace_ids" not in payload["r1_goal"]
    assert "source_data_ids" not in payload["r1_goal"]
    if "r2_selection" in payload:
        assert "source_trace_ids" not in payload["r2_selection"]
        assert "source_data_ids" not in payload["r2_selection"]
    assert "trace_bulk_0999" not in encoded
    assert len(encoded) < 12_000

    assert len(r1.source_trace_ids) == 1_000
    assert len(r2.source_trace_ids) == 1_000


def _r1_with_large_provenance() -> R1GraphGoalFrame:
    return R1GraphGoalFrame(
        frame_id="R1:order_236",
        graph_search_goal="Inspect selected raw original text.",
        required_information_granularity="raw",
        allowed_summary_depth=1,
        max_traversal_depth=6,
        max_branch_switches=0,
        max_node_reads=6,
        max_context_tokens=8000,
        stop_condition="Stop when the original text is sufficient.",
        source_graph_guide_packet_id="r_loop:vessel_read_packet:order_236",
        source_data_ids=[
            "r_loop:vessel_read_packet:order_236",
            *[f"data_bulk_{index:04d}" for index in range(1000)],
        ],
        source_trace_ids=[f"trace_bulk_{index:04d}" for index in range(1000)],
        generated_by="LLM:test:R1",
        semantic_judgement_status="ran",
    )


def _r2_with_large_provenance(r1_frame_id: str) -> R2GraphNodeSelectionFrame:
    return R2GraphNodeSelectionFrame(
        frame_id="R2:order_236",
        selection_scope="r_loop_vessel_read_packet",
        available_graph_node_ids=[RAW_ID],
        selection_status="selected",
        selected_graph_node_id=RAW_ID,
        selection_reason="The official candidate is the requested raw source.",
        expected_information_granularity="raw",
        expected_source_kind="raw_source",
        source_r1_goal_frame_id=r1_frame_id,
        source_data_ids=[f"r2_data_bulk_{index:04d}" for index in range(1000)],
        source_trace_ids=[f"r2_trace_bulk_{index:04d}" for index in range(1000)],
        generated_by="LLM:test:R2",
        semantic_judgement_status="ran",
    )
