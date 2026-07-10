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


def test_r3_enum_failure_gets_one_repair_attempt_in_one_step() -> None:
    trace_store, data_store, packet_event_id, packet = _record_one_step_packet()
    adapter = RepairingOneStepR3Adapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_214_one_step",
        user_question="R3 enum 실패는 한 번만 수리해",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_214_one_step_repair",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r3_inspection is not None
    assert result.r3_inspection.current_information_granularity == "low_summary"
    assert adapter.r3_call_count == 2
    assert adapter.repair_payload_seen is True
    r3_call_ids = [
        call_id
        for call_id in result.result_frame.llm_call_data_ids
        if "R3_vessel_inspector" in call_id
    ]
    assert len(r3_call_ids) == 2


def test_r3_enum_failure_gets_one_repair_attempt_in_traverse() -> None:
    trace_store, data_store, packet_event_id, packet = _record_traverse_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=["graph:summary:source_kind:code_bundle"]),
        ],
        summary_rows=[_summary_row()],
    )
    adapter = RepairingTraverseR3Adapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_214_traverse",
        user_question="R3 enum 실패를 고친 뒤 계속 내려가",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_214_traverse_repair",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.r_loop_task_status == "sufficient"
    assert adapter.r3_call_count >= 2
    assert adapter.repair_payload_seen is True
    r3_call_ids = [
        call_id
        for call_id in result.result_frame.llm_call_data_ids
        if "R3_vessel_inspector" in call_id
    ]
    assert len(r3_call_ids) == len(result.r3_inspections) + 1


class RepairingOneStepR3Adapter(RLoopVesselOneStepFakeLLMAdapter):
    model_id = "repairing-one-step-r3-adapter"

    def __init__(self) -> None:
        self.r3_call_count = 0
        self.repair_payload_seen = False

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R3 Vessel Inspector" not in request.prompt:
            return super().complete(request)
        self.r3_call_count += 1
        if "schema_repair_request" not in request.input_payload:
            payload = _invalid_r3_payload()
        else:
            self.repair_payload_seen = True
            payload = _valid_r3_payload()
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class RepairingTraverseR3Adapter(RLoopVesselTraverseFakeLLMAdapter):
    model_id = "repairing-traverse-r3-adapter"

    def __init__(self) -> None:
        self.r3_call_count = 0
        self.repair_payload_seen = False
        self._first_r3_failed = False

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R3 Vessel Inspector" not in request.prompt:
            return super().complete(request)
        self.r3_call_count += 1
        if not self._first_r3_failed and "schema_repair_request" not in request.input_payload:
            self._first_r3_failed = True
            payload = _invalid_r3_payload()
            return LLMResponse(
                text=json.dumps(payload, ensure_ascii=False),
                model_id=self.model_id,
                raw=payload,
            )
        if "schema_repair_request" in request.input_payload:
            self.repair_payload_seen = True
        return super().complete(request)


def _invalid_r3_payload() -> dict[str, object]:
    return {
        "current_information_granularity": "낮은 요약",
        "sufficiency_status": "충분",
        "granularity_problem_status": "없음",
        "branch_problem_status": "없음",
        "recommended_next_action": "멈춤",
        "inspection_reason": "Intentionally return enum labels outside the allowed table.",
    }


def _valid_r3_payload() -> dict[str, object]:
    return {
        "current_information_granularity": "low_summary",
        "sufficiency_status": "sufficient",
        "granularity_problem_status": "none",
        "branch_problem_status": "none",
        "recommended_next_action": "stop",
        "inspection_reason": "Repair copied allowed enum/status values.",
    }
