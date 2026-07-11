from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselStepMemoryPacketFrame,
    _r2_continuation_work_order,
    _r_step_memory_llm_view,
)

from tests.test_order_235_r2_generic_entry_selection_contract import _surface


def test_effective_continue_requires_r2_selection_even_when_r3_said_stop() -> None:
    memory = _step_memory(
        continuation_status="continue_deeper",
        r3_action="stop",
    )

    work_order = _r2_continuation_work_order(
        candidate_layer_surface=_surface(["graph:entry:one", "graph:entry:two"]),
        previous_step_memory_packet=memory,
    )

    assert work_order["none_selected_allowed"] is False
    assert work_order["stop_allowed"] is False
    assert work_order["reason_code"] == (
        "CODE_STATUS:r_loop_continuation_requires_selection"
    )


def test_r2_previous_memory_view_drops_full_provenance() -> None:
    memory = _step_memory(
        continuation_status="continue_deeper",
        r3_action="deeper",
    )
    view = _r_step_memory_llm_view(memory)

    assert view["packet_id"] == memory.packet_id
    assert view["continuation_status"] == "continue_deeper"
    assert "source_trace_ids" not in view
    assert "source_data_ids" not in view
    assert "trace_bulk_0999" not in str(view)
    assert len(memory.source_trace_ids) == 1_000


def _step_memory(
    *,
    continuation_status: str,
    r3_action: str,
) -> RLoopVesselStepMemoryPacketFrame:
    return RLoopVesselStepMemoryPacketFrame(
        packet_id="r_loop:vessel_step_memory:order_237",
        turn_id="turn_order_237",
        step_index=1,
        target="R_LOOP",
        mode="vessel_r_step_memory",
        source_read_packet_id="r_loop:vessel_read_packet:order_237",
        source_candidate_surface_frame_id="R:order_237:surface",
        source_r2_selection_frame_id="R2:order_237",
        source_r3_inspection_frame_id="R3:order_237",
        source_continuation_frame_id="R:order_237:continuation",
        selected_graph_node_id="graph:axis:time",
        inspected_graph_node_id="graph:axis:time",
        selected_node_kind="time_axis",
        selected_summary_depth=0,
        selected_source_leaf_count=0,
        selected_is_terminal_material=False,
        selected_is_raw_original_material=False,
        selected_raw_original_text_status="not_applicable",
        selected_raw_original_text_data_ids=[],
        selected_raw_original_text_char_count=0,
        selected_has_raw_original_text=False,
        visible_child_candidate_node_ids=["graph:entry:one", "graph:entry:two"],
        visible_child_candidate_count=2,
        r3_recommended_next_action=r3_action,
        continuation_status=continuation_status,
        source_trace_ids=[f"trace_bulk_{index:04d}" for index in range(1_000)],
        source_data_ids=[f"data_bulk_{index:04d}" for index in range(1_000)],
    )
