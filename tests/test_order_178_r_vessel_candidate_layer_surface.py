import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
    build_r_loop_vessel_read_packet_from_neo4j,
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import (
    R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_DATA_TYPE,
    R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_GENERATOR,
    R_LOOP_VESSEL_SURFACE_SELECTION_DATA_TYPE,
    run_r_loop_vessel_one_step,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
    _entry_rows,
)


def test_read_packet_balances_summary_candidate_kinds_before_limit() -> None:
    result = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_178_balanced_packet",
        created_at=READ_AT,
        limit=3,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[],
            summary_rows=[
                *[
                    _active_summary_row(
                        suffix=f"source_{index:02d}",
                        data_kind="source_leaf_summary",
                        summary_depth=1,
                    )
                    for index in range(10)
                ],
                _active_summary_row(
                    suffix="token_01",
                    data_kind="token_budget_bundle_summary",
                    summary_depth=2,
                ),
            ],
        ),
    )

    data_kinds = {
        record["data_kind"]
        for record in result.summary_candidate_records
    }
    assert result.summary_candidate_count == 3
    assert "source_leaf_summary" in data_kinds
    assert "token_budget_bundle_summary" in data_kinds


def test_candidate_layer_surface_is_absolute_and_text_free() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()
    adapter = CapturingSurfaceAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_178",
        user_question="source summary와 token layer summary 연결을 한 단계만 봐줘",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_178_surface",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.candidate_layer_surface is not None
    assert result.candidate_layer_surface.generated_by == (
        R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_GENERATOR
    )
    assert result.candidate_layer_surface.info_class == "absolute"
    assert result.candidate_layer_surface.semantic_judgement_status == "not_run"
    assert result.candidate_layer_surface.surface_count >= 2
    assert "summary_text" not in json.dumps(
        result.candidate_layer_surface.surface_records,
        ensure_ascii=False,
    )
    surface_record = data_store.require_record(result.candidate_layer_surface.frame_id)
    assert surface_record.data_type == R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_DATA_TYPE


def test_r2_payload_uses_core_entry_surfaces_not_flat_summaries() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()
    adapter = CapturingSurfaceAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_178",
        user_question="token layer summary 후보를 먼저 찾아봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_178_r2_payload",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.surface_selection is not None
    r2_payload = adapter.payloads_by_node["R2"]
    assert "summary_candidate_records" not in r2_payload
    assert "entry_candidate_records" not in r2_payload
    assert "candidate_layer_surface_ref_records" in r2_payload
    assert "available_surface_refs" in r2_payload
    assert "candidate_records_by_surface_ref" in r2_payload
    grouped_json = json.dumps(
        r2_payload["candidate_records_by_surface_ref"],
        ensure_ascii=False,
    )
    assert "summary_text" not in grouped_json
    assert "source_leaf_summary" not in grouped_json
    assert "token_budget_bundle_summary" not in grouped_json
    assert "source_ingest_bundle" in grouped_json or "time_bundle" in grouped_json
    surface_record = data_store.require_record(result.surface_selection.frame_id)
    assert surface_record.data_type == R_LOOP_VESSEL_SURFACE_SELECTION_DATA_TYPE


def test_r2_selection_must_stay_inside_selected_surface() -> None:
    trace_store, data_store, packet_event_id, packet = _record_multi_surface_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_178",
        user_question="선택 범위 밖 후보를 고르면 실패해야 한다",
        read_packet=packet,
        adapter=CrossSurfaceR2Adapter(),
        frame_label="order_178_cross_surface_fail",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R2"
    assert result.result_frame.failure_type == "schema_failed"
    assert "selected_graph_node_id" in (result.result_frame.failure_reason or "")


def _record_multi_surface_packet():
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_178",
        batch_id="order_178_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=[
                _active_summary_row(
                    suffix="source_leaf",
                    data_kind="source_leaf_summary",
                    summary_depth=1,
                ),
                _active_summary_row(
                    suffix="token_bundle",
                    data_kind="token_budget_bundle_summary",
                    summary_depth=2,
                ),
            ],
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


def _active_summary_row(
    *,
    suffix: str,
    data_kind: str,
    summary_depth: int,
) -> dict[str, object]:
    summary_node_id = f"graph:summary:{suffix}"
    target_graph_node_id = f"graph:target:{suffix}"
    return {
        "summary_node_id": summary_node_id,
        "summary_display_name": f"Summary: {suffix}",
        "data_kind": data_kind,
        "info_class": "mixed" if summary_depth > 1 else "relative",
        "generated_by": "LLM:fake:night_summary",
        "payload_json": json.dumps(
            {
                "data_kind": data_kind,
                "summary_depth": summary_depth,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": target_graph_node_id,
                "target_node_kind": "summary_target",
                "source_leaf_count": 1 if summary_depth == 1 else 4,
                "source_summary_count": 0 if summary_depth == 1 else 4,
                "source_graph_node_ids": [target_graph_node_id],
                "source_data_ids": [target_graph_node_id],
                "source_trace_ids": [f"trace:summary:{suffix}"],
                "info_class": "mixed" if summary_depth > 1 else "relative",
                "generated_by": "LLM:fake:night_summary",
                "summary_text": f"{data_kind} active summary text for {suffix}.",
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": target_graph_node_id,
        "target_display_name": f"Target: {suffix}",
        "target_node_kind": "summary_target",
    }


class CapturingSurfaceAdapter:
    model_id = "capturing-surface-adapter"

    def __init__(self) -> None:
        self.payloads_by_node: dict[str, dict[str, object]] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.payloads_by_node["R1"] = request.input_payload
            payload = {
                "graph_search_goal": "Inspect source summary and token layer summary connection.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 2,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.payloads_by_node["R2"] = request.input_payload
            surface_id, graph_node_id = _first_surface_and_node(request.input_payload)
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_id,
                "selected_node_ref": graph_node_id,
                "selection_reason": "Select the first node inside the first supplied surface.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "summary",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            self.payloads_by_node["R3"] = request.input_payload
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "The selected candidate is sufficient for the surface test.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class CrossSurfaceR2Adapter(CapturingSurfaceAdapter):
    model_id = "cross-surface-r2-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)

        self.payloads_by_node["R2"] = request.input_payload
        available_surfaces = request.input_payload.get("available_surface_refs")
        records_by_surface = request.input_payload.get("candidate_records_by_surface_ref")
        selected_surface_id = None
        cross_surface_node_id = None
        if isinstance(available_surfaces, list) and len(available_surfaces) >= 2:
            selected_surface_id = available_surfaces[0]
            if isinstance(records_by_surface, dict):
                other_records = records_by_surface.get(available_surfaces[1])
                if isinstance(other_records, list) and other_records:
                    first = other_records[0]
                    if isinstance(first, dict):
                        cross_surface_node_id = first.get("node_ref")
        payload = {
            "selection_status": "selected",
            "selected_surface_ref": selected_surface_id,
            "selected_node_ref": cross_surface_node_id,
            "selection_reason": "Intentionally select a node from a different surface.",
            "expected_information_granularity": "low_summary",
            "expected_source_kind": "summary",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_surface_and_node(payload: dict[str, object]) -> tuple[str | None, str | None]:
    available_surfaces = payload.get("available_surface_refs")
    selected_surface_id = (
        available_surfaces[0]
        if isinstance(available_surfaces, list) and available_surfaces
        else None
    )
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if isinstance(records_by_surface, dict) and selected_surface_id:
        records = records_by_surface.get(selected_surface_id)
        if isinstance(records, list) and records:
            first = records[0]
            if isinstance(first, dict):
                node_ref = first.get("node_ref")
                if isinstance(node_ref, str):
                    return selected_surface_id, node_ref
    return selected_surface_id, None
