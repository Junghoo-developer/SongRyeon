import json

from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselCandidateLayerSurfaceFrame,
    RLoopVesselTraverseFakeLLMAdapter,
    _r2_continuation_work_order,
    run_r_loop_vessel_traverse,
)

from tests.test_order_183_r_vessel_hierarchical_child_surface import _time_axis_row
from tests.test_order_184_r_vessel_multi_step_traversal import _record_packet


def test_entry_selection_contract_depends_on_count_not_axis_name() -> None:
    surface = _surface(
        [
            "graph:axis:time",
            "graph:axis:future_meaning",
        ]
    )

    work_order = _r2_continuation_work_order(
        candidate_layer_surface=surface,
        previous_step_memory_packet=None,
    )

    assert work_order["work_order_status"] == "entry_selection"
    assert work_order["candidate_count"] == 2
    assert work_order["none_selected_allowed"] is False
    assert work_order["stop_allowed"] is False
    assert "TimeAxis" not in str(work_order["next_selection_task"])


def test_empty_entry_surface_allows_none_selected() -> None:
    work_order = _r2_continuation_work_order(
        candidate_layer_surface=_surface([]),
        previous_step_memory_packet=None,
    )

    assert work_order["candidate_count"] == 0
    assert work_order["none_selected_allowed"] is True
    assert work_order["stop_allowed"] is True


def test_first_step_none_selected_is_repaired_to_official_candidate() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[_time_axis_row()],
        summary_rows=[],
    )
    adapter = _FirstStepNoneSelectedOnceAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_235",
        user_question="공식 entry 후보에서 시작해 계층적으로 탐색해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_235_entry_repair",
        input_ref=[packet_event_id],
    )

    assert adapter.returned_bad_none_selected is True
    assert result.result_frame.traverse_status == "completed"
    assert result.r2_selections[0].selection_status == "selected"
    assert result.r2_selections[0].selected_graph_node_id == "graph:axis:time"


def _surface(candidate_ids: list[str]) -> RLoopVesselCandidateLayerSurfaceFrame:
    records = []
    available_surface_ids = []
    if candidate_ids:
        available_surface_ids = ["surface:entry:axis"]
        records = [
            {
                "surface_id": "surface:entry:axis",
                "candidate_graph_node_ids": candidate_ids,
                "candidate_count": len(candidate_ids),
                "branch_role": "graph_axis",
            }
        ]
    return RLoopVesselCandidateLayerSurfaceFrame(
        frame_id="R:order_235:surface",
        created_at="2026-07-10T00:00:00",
        source_packet_id="r_loop:vessel_read_packet:order_235",
        surface_count=len(records),
        total_candidate_count=len(candidate_ids),
        available_surface_ids=available_surface_ids,
        surface_records=records,
        source_data_ids=[],
        source_trace_ids=[],
    )


class _FirstStepNoneSelectedOnceAdapter(RLoopVesselTraverseFakeLLMAdapter):
    def __init__(self) -> None:
        self.returned_bad_none_selected = False

    def complete(self, request):
        if (
            "R2 Vessel Node Selector" in request.prompt
            and not self.returned_bad_none_selected
            and "schema_repair_request" not in request.input_payload
        ):
            self.returned_bad_none_selected = True
            from songryeon_core.llm.base import LLMResponse

            return LLMResponse(
                model_id=self.model_id,
                text=json.dumps(
                    {
                        "selection_status": "none_selected",
                        "selected_surface_ref": None,
                        "selected_node_ref": None,
                        "selection_reason": "intentional bad first-step stop",
                        "expected_information_granularity": "unknown",
                        "expected_source_kind": "entry",
                    }
                ),
            )
        return super().complete(request)
