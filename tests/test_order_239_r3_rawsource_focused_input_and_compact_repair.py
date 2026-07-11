import json

from songryeon_core.core.schemas import R1GraphGoalFrame, R2GraphNodeSelectionFrame
from songryeon_core.loops.r_loop_vessel_one_step import (
    _r3_input_payload,
    _r3_schema_repair_input_payload,
)


RAW_ID = "graph:raw_source:internal_document:order_239"
RAW_TEXT = "가나다라마바사 ORDER 239 원문 " * 180


def test_rawsource_r3_input_keeps_full_text_and_drops_bulk_provenance() -> None:
    payload = _raw_payload()
    encoded = json.dumps(payload, ensure_ascii=False)

    assert payload["selected_candidate_record"]["raw_original_text_materials"][0][
        "text"
    ] == RAW_TEXT
    assert "r2_selection" not in payload
    assert "source_data_ids" not in payload
    assert "hierarchy_read_policy" not in payload
    assert "r3_status_contract" not in payload
    assert "r2_bulk_0999" not in encoded
    assert len(encoded) < len(RAW_TEXT) + 2_500


def test_r3_repair_is_compact_and_preserves_structural_contract() -> None:
    base_payload = _raw_payload()
    repaired = _r3_schema_repair_input_payload(
        base_payload=base_payload,
        failed_payload={
            "current_information_granularity": "low_summary",
            "sufficiency_status": "insufficient",
            "granularity_problem_status": "needs_lower_granularity",
            "branch_problem_status": "none",
            "recommended_next_action": "deeper",
            "inspection_reason": "The original was mistaken for a summary.",
        },
        failure_reason="structural contract failed",
    )
    encoded = json.dumps(repaired, ensure_ascii=False)

    assert RAW_TEXT not in encoded
    assert "selected_candidate_record" not in repaired
    assert repaired["r3_enum_repair_table"][
        "current_information_granularity"
    ] == ["raw"]
    assert "deeper" not in repaired["r3_enum_repair_table"][
        "recommended_next_action"
    ]
    assert len(encoded) < 2_500


def _raw_payload() -> dict[str, object]:
    r1 = R1GraphGoalFrame(
        frame_id="R1:order_239",
        graph_search_goal="Explain what the selected ORDER proposes from its original text.",
        required_information_granularity="raw",
        allowed_summary_depth=1,
        max_traversal_depth=6,
        max_branch_switches=1,
        max_node_reads=6,
        max_context_tokens=8000,
        stop_condition="Stop when the original text answers the exact question.",
        source_graph_guide_packet_id="r_loop:vessel_read_packet:order_239",
        source_data_ids=["r_loop:vessel_read_packet:order_239"],
        source_trace_ids=["trace_order_239_r1"],
        generated_by="LLM:test:R1",
        semantic_judgement_status="ran",
    )
    r2 = R2GraphNodeSelectionFrame(
        frame_id="R2:order_239",
        selection_scope="r_loop_vessel_read_packet",
        available_graph_node_ids=[RAW_ID],
        selection_status="selected",
        selected_graph_node_id=RAW_ID,
        selection_reason="The official candidate is the requested original.",
        expected_information_granularity="raw",
        expected_source_kind="internal_document",
        source_r1_goal_frame_id=r1.frame_id,
        source_data_ids=[f"r2_bulk_{index:04d}" for index in range(1000)],
        source_trace_ids=[f"trace_bulk_{index:04d}" for index in range(1000)],
        generated_by="LLM:test:R2",
        semantic_judgement_status="ran",
    )
    return _r3_input_payload(
        user_question="ORDER 239가 제안하는 내용을 원문 기준으로 설명해줘.",
        r1=r1,
        r2=r2,
        selected_record={
            "candidate_node_id": RAW_ID,
            "candidate_kind": "raw_source",
            "node_kind": "raw_source",
            "data_kind": "internal_document",
            "raw_original_text_status": "available",
            "raw_original_text_char_count": len(RAW_TEXT),
            "raw_original_text_materials": [
                {
                    "text": RAW_TEXT,
                    "text_char_count": len(RAW_TEXT),
                    "path": "Administrative_Reform_1/04_Orders/ORDER_239.md",
                    "source_kind": "internal_document",
                    "info_class": "absolute_copied_source",
                }
            ],
            "hierarchy_child_node_ids": [],
            "hierarchy_child_candidate_records": [],
        },
    )
