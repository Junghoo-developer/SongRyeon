from __future__ import annotations

import json

from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselOneStepFakeLLMAdapter,
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_one_step,
    run_r_loop_vessel_traverse,
)

from tests.test_order_176_vessel_r_one_step_traversal import (
    _record_packet as _record_one_step_packet,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    _record_packet as _record_traverse_packet,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)


def test_r2_schema_copy_failure_gets_one_repair_attempt_in_one_step() -> None:
    trace_store, data_store, packet_event_id, packet = _record_one_step_packet()
    adapter = RepairingOneStepR2Adapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_213_one_step",
        user_question="R2 번호표 복사 실패는 한 번만 수리해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_213_one_step_repair",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r2_selection is not None
    assert adapter.r2_call_count == 2
    assert adapter.repair_payload_seen is True
    r2_call_ids = [
        call_id
        for call_id in result.result_frame.llm_call_data_ids
        if "R2_vessel_node_selector" in call_id
    ]
    assert len(r2_call_ids) == 2


def test_r2_schema_copy_failure_gets_one_repair_attempt_in_traverse() -> None:
    trace_store, data_store, packet_event_id, packet = _record_traverse_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=["graph:summary:source_kind:code_bundle"]),
        ],
        summary_rows=[_summary_row()],
    )
    adapter = RepairingTraverseR2Adapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_213_traverse",
        user_question="R2 번호표 복사 실패를 고친 뒤 계속 내려가",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_213_traverse_repair",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.r_loop_task_status == "sufficient"
    assert adapter.r2_call_count >= 2
    assert adapter.repair_payload_seen is True
    r2_call_ids = [
        call_id
        for call_id in result.result_frame.llm_call_data_ids
        if "R2_vessel_node_selector" in call_id
    ]
    assert len(r2_call_ids) == len(result.r2_selections) + 1


class RepairingOneStepR2Adapter(RLoopVesselOneStepFakeLLMAdapter):
    model_id = "repairing-one-step-r2-adapter"

    def __init__(self) -> None:
        self.r2_call_count = 0
        self.repair_payload_seen = False

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)
        self.r2_call_count += 1
        if "schema_repair_request" not in request.input_payload:
            payload = _invalid_r2_payload()
        else:
            self.repair_payload_seen = True
            payload = _valid_r2_payload_from_request(request)
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class RepairingTraverseR2Adapter(RLoopVesselTraverseFakeLLMAdapter):
    model_id = "repairing-traverse-r2-adapter"

    def __init__(self) -> None:
        self.r2_call_count = 0
        self.repair_payload_seen = False
        self._first_r2_failed = False

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)
        self.r2_call_count += 1
        if not self._first_r2_failed and "schema_repair_request" not in request.input_payload:
            self._first_r2_failed = True
            payload = _invalid_r2_payload()
            return LLMResponse(
                text=json.dumps(payload, ensure_ascii=False),
                model_id=self.model_id,
                raw=payload,
            )
        if "schema_repair_request" in request.input_payload:
            self.repair_payload_seen = True
        return super().complete(request)


def _invalid_r2_payload() -> dict[str, object]:
    return {
        "selection_status": "selected",
        "selected_surface_ref": "surface_missing",
        "selected_node_ref": "node_missing",
        "selection_reason": "Intentionally return refs outside the supplied copy table.",
        "expected_information_granularity": "요약",
        "expected_source_kind": "summary",
    }


def _valid_r2_payload_from_request(request: LLMRequest) -> dict[str, object]:
    surface_ref, node_ref = _first_visible_surface_and_node(request.input_payload)
    return {
        "selection_status": "selected" if node_ref else "none_selected",
        "selected_surface_ref": surface_ref if node_ref else None,
        "selected_node_ref": node_ref,
        "selection_reason": "Repair copied the official surface and node refs.",
        "expected_information_granularity": "low_summary",
        "expected_source_kind": "summary_or_entry_candidate",
    }


def _first_visible_surface_and_node(
    payload: dict[str, object],
) -> tuple[str | None, str | None]:
    available_surface_refs = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(available_surface_refs, list) or not isinstance(records_by_surface, dict):
        return None, None
    for surface_ref in available_surface_refs:
        if not isinstance(surface_ref, str):
            continue
        records = records_by_surface.get(surface_ref)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            node_ref = record.get("node_ref")
            if isinstance(node_ref, str) and node_ref:
                return surface_ref, node_ref
    return None, None
