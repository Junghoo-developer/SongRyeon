import json
from pathlib import Path

from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)

from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _record_packet,
    _source_kind_row,
    _summary_row,
)


ROOT = Path(__file__).resolve().parents[1]


def test_r1_prompt_preserves_explicit_raw_material_intent() -> None:
    prompt = (ROOT / "songryeon_core/prompts/r1_vessel_goal_setter_v0.md").read_text(
        encoding="utf-8"
    )

    assert "evidence level" in prompt
    assert "original text, raw source, or RawSource" in prompt
    assert '"required_material_level": "overview"' in prompt
    assert '"required_material_count": 1' in prompt
    assert "use `raw_original`" in prompt
    assert "Do not output `min_traversal_depth`" in prompt


def test_node3_vessel_only_turn_uses_focused_payload() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )
    run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_240_traverse",
        user_question="Vessel 요약 재료를 찾아줘",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_240_traverse",
        input_ref=[packet_event_id],
    )
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_240_brief",
        user_question="Vessel 요약 재료로 답해줘",
        handoff_frame_id="node_2:handoff:order_240",
        boundary=MetainfoBoundary(),
        input_trace_ids=[packet_event_id],
        source_data_ids=["node_2:handoff:order_240"],
    )

    payload = node3_brief_llm_payload(brief)
    encoded = json.dumps(payload, ensure_ascii=False)

    assert payload["evidence_source_mode"] == "vessel_r_focused"
    assert payload["vessel_r_material"]["status"] == "present"
    assert payload["vessel_r_material"]["summary_material_count"] == 1
    assert "document_material_packet" not in payload
    assert "search_candidate_scope" not in payload
    assert "runtime_task_sequence" not in payload
    assert "Code source kind bundle summary for R traversal." in encoded
    assert "graph:" not in encoded
    assert len(encoded) < 6_000
