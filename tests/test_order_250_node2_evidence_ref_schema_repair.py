from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import DataRef, MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_2_metainfo_boundary import (
    run_node2_answer_basis_selection,
)


class RepairingAnswerBasisAdapter:
    model_id = "order-250-repairing-answer-basis"

    def __init__(self) -> None:
        self.input_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.input_payloads.append(request.input_payload)
        evidence_role = {
            "evidence_role": "primary_answer_basis",
            "role_reason": "질문의 중심 근거다.",
            "role_reason_info_class": "relative",
        }
        if "schema_repair_request" in request.input_payload:
            evidence_role["evidence_ref"] = "E004"
        payload = _answer_basis_payload(evidence_role=evidence_role)
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class FixedRefAnswerBasisAdapter:
    model_id = "order-250-fixed-ref-answer-basis"

    def __init__(self, *, evidence_ref: str) -> None:
        self.evidence_ref = evidence_ref
        self.call_count = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        payload = _answer_basis_payload(
            evidence_role={
                "evidence_ref": self.evidence_ref,
                "evidence_role": "primary_answer_basis",
                "role_reason": "질문의 중심 근거다.",
                "role_reason_info_class": "relative",
            }
        )
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_schema_failed_evidence_role_is_repaired_once_by_same_llm() -> None:
    trace_store, data_store, input_trace_id, boundary = _node2_stores()
    adapter = RepairingAnswerBasisAdapter()

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_250_repair",
        user_question="이 근거를 바탕으로 답변 태도를 정해줘",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=adapter,
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime"],
    )

    assert len(adapter.input_payloads) == 2
    assert "schema_repair_request" not in adapter.input_payloads[0]
    assert adapter.input_payloads[1]["schema_repair_request"]["repair_attempt_index"] == 1
    assert frame.generated_by == f"LLM:{adapter.model_id}"
    assert frame.answer_basis_failure_type == "none"
    assert frame.evidence_roles[0].source_data_id == "source:sample_boundary_record"
    llm_call_ids = [
        source_data_id
        for source_data_id in frame.source_data_ids
        if source_data_id.startswith("llm_call:node_2:")
    ]
    assert len(llm_call_ids) == 2


def test_unknown_ref_remains_fallback_after_single_repair_attempt() -> None:
    trace_store, data_store, input_trace_id, boundary = _node2_stores()
    adapter = FixedRefAnswerBasisAdapter(evidence_ref="E999")

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_250_invalid",
        user_question="이 근거를 바탕으로 답변 태도를 정해줘",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=adapter,
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime"],
    )

    assert adapter.call_count == 2
    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.answer_basis_failure_type == "schema_failed"
    assert "evidence_ref must exist" in frame.answer_basis_validation_error


def test_valid_first_payload_does_not_run_schema_repair() -> None:
    trace_store, data_store, input_trace_id, boundary = _node2_stores()
    adapter = FixedRefAnswerBasisAdapter(evidence_ref="E004")

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_250_first_pass",
        user_question="이 근거를 바탕으로 답변 태도를 정해줘",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=adapter,
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime"],
    )

    assert adapter.call_count == 1
    assert frame.generated_by == f"LLM:{adapter.model_id}"


def _answer_basis_payload(*, evidence_role: dict[str, str]) -> dict[str, object]:
    return {
        "answer_basis_mode": "relative_allowed",
        "basis_reason_codes": ["user_asked_for_interpretation"],
        "mode_selection_reason": "한 근거의 의미를 해석해도 되는 질문이다.",
        "mode_selection_reason_info_class": "mixed",
        "evidence_roles": [evidence_role],
    }


def _node2_stores() -> tuple[TraceStore, DataStore, str, MetainfoBoundary]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_250",
        actor="test",
        event_type="node_output",
        output_ref=[
            "source:runtime",
            "source:boundary",
            "source:handoff",
            "source:sample_boundary_record",
        ],
        schema_status="passed",
    )
    for data_id in (
        "source:runtime",
        "source:boundary",
        "source:handoff",
        "source:sample_boundary_record",
    ):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=event.event_id,
            payload={"data_id": data_id},
        )
    boundary = MetainfoBoundary(
        absolute_info=[
            DataRef(
                data_id="source:sample_boundary_record",
                data_type="test:boundary_sample",
                source_trace_id=event.event_id,
            )
        ]
    )
    return trace_store, data_store, event.event_id, boundary
