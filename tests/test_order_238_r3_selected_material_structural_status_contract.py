from songryeon_core.core.schemas import R1GraphGoalFrame, R2GraphNodeSelectionFrame
from songryeon_core.loops.r_loop_vessel_one_step import (
    _r3_input_payload,
    _r3_schema_repair_input_payload,
)


RAW_ID = "graph:raw_source:internal_document:order_238"
RAW_TEXT = "ORDER 238 raw original text"


def test_raw_leaf_narrows_r3_structural_status_choices() -> None:
    payload = _raw_leaf_payload()

    facts = payload["selected_material_structural_facts"]
    assert facts["raw_original_text_available"] is True
    assert facts["hierarchy_child_candidate_count"] == 0
    assert facts["current_information_granularity_constraint"] == "raw"
    assert facts["deeper_action_available"] is False
    assert facts["info_class"] == "absolute"
    assert facts["semantic_judgement_status"] == "not_run"

    allowed = payload["allowed_r3_status_values"]
    assert allowed["current_information_granularity"] == ["raw"]
    assert "deeper" not in allowed["recommended_next_action"]
    assert set(allowed["recommended_next_action"]) == {
        "stop",
        "switch_branch",
        "fail",
    }


def test_r3_repair_preserves_narrowed_structural_status_choices() -> None:
    base_payload = _raw_leaf_payload()
    repaired = _r3_schema_repair_input_payload(
        base_payload=base_payload,
        failed_payload={
            "current_information_granularity": "low_summary",
            "sufficiency_status": "insufficient",
            "granularity_problem_status": "needs_lower_granularity",
            "branch_problem_status": "none",
            "recommended_next_action": "deeper",
            "inspection_reason": "mistook the original for a summary",
        },
        failure_reason="R3 structural status contract failed",
    )

    assert repaired["r3_enum_repair_table"] == base_payload[
        "allowed_r3_status_values"
    ]
    assert repaired["r3_enum_repair_table"][
        "current_information_granularity"
    ] == ["raw"]
    assert "deeper" not in repaired["r3_enum_repair_table"][
        "recommended_next_action"
    ]


def _raw_leaf_payload() -> dict[str, object]:
    r1 = R1GraphGoalFrame(
        frame_id="R1:order_238",
        graph_search_goal="Inspect the selected original text.",
        required_information_granularity="raw",
        allowed_summary_depth=1,
        max_traversal_depth=6,
        max_branch_switches=1,
        max_node_reads=6,
        max_context_tokens=8000,
        stop_condition="Stop when the selected original is sufficient.",
        source_graph_guide_packet_id="r_loop:vessel_read_packet:order_238",
        source_data_ids=["r_loop:vessel_read_packet:order_238"],
        source_trace_ids=["trace_order_238_r1"],
        generated_by="LLM:test:R1",
        semantic_judgement_status="ran",
    )
    r2 = R2GraphNodeSelectionFrame(
        frame_id="R2:order_238",
        selection_scope="r_loop_vessel_read_packet",
        available_graph_node_ids=[RAW_ID],
        selection_status="selected",
        selected_graph_node_id=RAW_ID,
        selection_reason="The selected record is the requested source.",
        expected_information_granularity="raw",
        expected_source_kind="internal_document",
        source_r1_goal_frame_id=r1.frame_id,
        source_data_ids=[r1.frame_id],
        source_trace_ids=["trace_order_238_r2"],
        generated_by="LLM:test:R2",
        semantic_judgement_status="ran",
    )
    selected = {
        "candidate_node_id": RAW_ID,
        "candidate_kind": "raw_source",
        "node_kind": "raw_source",
        "data_kind": "internal_document",
        "summary_depth": 0,
        "raw_original_text_status": "available",
        "raw_original_text_char_count": len(RAW_TEXT),
        "raw_original_text_data_ids": ["source_text:internal_document:order_238"],
        "raw_original_text_materials": [
            {
                "source_text_data_id": "source_text:internal_document:order_238",
                "text": RAW_TEXT,
                "text_char_count": len(RAW_TEXT),
            }
        ],
        "hierarchy_child_node_ids": [],
        "hierarchy_child_candidate_records": [],
    }
    return _r3_input_payload(
        user_question="ORDER 238 원문을 확인해",
        r1=r1,
        r2=r2,
        selected_record=selected,
    )
