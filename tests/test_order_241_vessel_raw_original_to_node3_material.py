from songryeon_core.core.schemas import (
    Node3VesselRMaterial,
    Node3VesselRMaterialItem,
    _validate_node3_vessel_r_material_item,
)
from songryeon_core.nodes.node_2_handoff import (
    _node3_vessel_r_material_item,
    _node3_vessel_r_material_llm_payload,
)


RAW_ID = "graph:raw_source:internal_document:order_241"
SOURCE_TEXT_ID = "source_text:internal_document:order_241"
RAW_TEXT = "ORDER 241 원문은 자르지 않고 Node3까지 전달된다."


def test_rawsource_item_preserves_exact_original_text_and_provenance() -> None:
    item = _raw_item()

    assert item.material_kind == "raw_original"
    assert item.raw_text == RAW_TEXT
    assert item.raw_text_char_count == len(RAW_TEXT)
    assert item.summary_text == ""
    assert item.text_payload_status == "included_raw_original_text"
    assert RAW_ID in item.source_data_ids
    assert SOURCE_TEXT_ID in item.source_data_ids
    _validate_node3_vessel_r_material_item(item)


def test_raw_primary_llm_payload_uses_original_and_omits_auxiliary_summary() -> None:
    raw_item = _raw_item()
    summary_item = Node3VesselRMaterialItem(
        graph_node_id="graph:summary:source_leaf:order_241",
        material_label="Vessel R material #1",
        material_kind="summary",
        display_name="ORDER 241 leaf summary",
        node_kind="summary",
        data_kind="source_leaf_summary",
        summary_depth=1,
        source_leaf_count=1,
        source_summary_count=0,
        info_class="relative",
        generated_by="LLM:test",
        summary_text="보조 요약",
        summary_text_char_count=5,
        text_payload_status="included_summary_text",
        source_data_ids=["graph:summary:source_leaf:order_241"],
    )
    material = Node3VesselRMaterial(
        source_data_id="r_loop:vessel_return_packet:order_241",
        material_status="present",
        traverse_status="completed",
        r_loop_task_status="sufficient",
        failure_type=None,
        failure_reason=None,
        traversal_path_count=2,
        selected_graph_node_ids=[summary_item.graph_node_id, raw_item.graph_node_id],
        inspected_graph_node_ids=[summary_item.graph_node_id, raw_item.graph_node_id],
        summary_material_count=1,
        raw_original_material_count=1,
        material_items=[summary_item, raw_item],
        source_data_ids=["r_loop:vessel_return_packet:order_241"],
    )

    payload = _node3_vessel_r_material_llm_payload(
        material,
        raw_original_primary=True,
    )

    assert payload["material_delivery_mode"] == "raw_original_primary"
    assert payload["visible_material_count"] == 1
    assert payload["omitted_auxiliary_summary_count"] == 1
    assert payload["items"][0]["raw_text"] == RAW_TEXT
    assert payload["items"][0]["text_payload_status"] == (
        "included_raw_original_text"
    )
    assert "graph_node_id" not in payload["items"][0]


def _raw_item() -> Node3VesselRMaterialItem:
    return _node3_vessel_r_material_item(
        graph_node_id=RAW_ID,
        record={
            "candidate_node_id": RAW_ID,
            "candidate_kind": "raw_source",
            "node_kind": "raw_source",
            "data_kind": "internal_document",
            "display_name": "ORDER 241 RawSource",
            "summary_depth": 0,
            "source_leaf_count": 1,
            "source_summary_count": 0,
            "raw_original_text_status": "available",
            "raw_original_text_data_ids": [SOURCE_TEXT_ID],
            "raw_original_text_char_count": len(RAW_TEXT),
            "raw_original_text_materials": [
                {
                    "source_text_data_id": SOURCE_TEXT_ID,
                    "text": RAW_TEXT,
                    "text_char_count": len(RAW_TEXT),
                }
            ],
        },
        index=2,
    )
