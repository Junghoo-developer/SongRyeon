from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    Node2AnswerBasisFrame,
    Node2EvidenceRole,
    Node3InputBriefFrame,
    Node3VesselRMaterial,
    validate_node2_answer_basis_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_2_metainfo_boundary import run_node2_answer_basis_selection
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


def test_node2_exposes_role_reason_info_class_contract_to_llm() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    input_event = trace_store.create_event(
        turn_id="turn_order_232_answer_basis",
        actor="user",
        event_type="user_input",
        output_ref=["source:runtime"],
        schema_status="passed",
    )
    adapter = ContractCheckingAnswerBasisAdapter()

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_232_answer_basis",
        user_question="R 결과의 한계를 구분해 설명해줘.",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=adapter,
        input_ref=[input_event.event_id],
        source_data_ids=["source:runtime"],
    )

    assert adapter.seen_role_reason_info_class_values == ["relative", "mixed"]
    assert frame.semantic_judgement_status == "ran"
    assert frame.evidence_roles[0].role_reason_info_class == "relative"


@pytest.mark.parametrize("invalid_info_class", ["absolute", "absolute_status"])
def test_node2_rejects_absolute_evidence_role_reason(invalid_info_class: str) -> None:
    frame = Node2AnswerBasisFrame(
        frame_id="node_2:answer_basis_frame:order_232",
        turn_id="turn_order_232_schema",
        answer_basis_mode="mixed_or_uncertain",
        basis_reason_codes=["multi_source_bundle"],
        mode_selection_reason="여러 source를 함께 사용한다.",
        mode_selection_reason_info_class="mixed",
        evidence_roles=[
            Node2EvidenceRole(
                source_data_id="source:runtime",
                evidence_role="primary_answer_basis",
                role_reason="이 source를 주된 근거로 사용한다.",
                role_reason_info_class=invalid_info_class,
            )
        ],
        generated_by="LLM:test",
        info_class="mixed",
        semantic_judgement_status="ran",
        source_trace_ids=["trace:user"],
        source_data_ids=["source:runtime"],
    )

    with pytest.raises(ValueError, match="role_reason_info_class"):
        validate_node2_answer_basis_frame(frame)


def test_node4_does_not_treat_negated_status_word_as_status_assignment() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    brief = _partial_vessel_r_brief()
    rendered_markdown = "\n\n".join(
        [
            build_node3_grounding_block(brief),
            (
                "`vessel_r_material`은 5개 항목을 포함하지만, "
                "`task_status`가 `sufficient`가 아니므로 이 재료는 "
                "부분적/제한된 정보로 간주되어야 합니다."
            ),
        ]
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_232_negated_status",
        report_id="node_3:report:order_232_negated_status",
        boundary_id="node_2:boundary:order_232_negated_status",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=PassGatekeeperAdapter(),
        input_ref=["trace:user"],
        source_data_ids=[brief.frame_id],
    )

    gate_payload = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate_payload["gate_status"] == "pass"
    assert not any(
        contradiction.startswith("vessel_r_status_name_mismatch")
        for contradiction in gate_payload["contradictions"]
    )


class ContractCheckingAnswerBasisAdapter:
    model_id = "order-232-answer-basis-contract"

    def __init__(self) -> None:
        self.seen_role_reason_info_class_values: list[str] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        values = request.input_payload.get("role_reason_info_class_values")
        self.seen_role_reason_info_class_values = list(values) if isinstance(values, list) else []
        payload = {
            "answer_basis_mode": "mixed_or_uncertain",
            "basis_reason_codes": ["multi_source_bundle"],
            "mode_selection_reason": "여러 source를 함께 사용한다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [
                {
                    "evidence_ref": "E001",
                    "evidence_role": "primary_answer_basis",
                    "role_reason": "이 source를 주된 근거로 사용한다.",
                    "role_reason_info_class": "relative",
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class PassGatekeeperAdapter:
    model_id = "order-232-pass-gatekeeper"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "gate_status": "pass",
            "reason": "structured brief와 보고문이 일치한다.",
            "checked_claims": ["vessel_r_material.status"],
            "unsupported_claims": [],
            "contradictions": [],
            "revision_targets": [],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _partial_vessel_r_brief() -> Node3InputBriefFrame:
    vessel_material = Node3VesselRMaterial(
        source_data_id="r_loop:vessel_return_packet:order_232_partial",
        material_status="present",
        traverse_status="completed",
        r_loop_task_status="partial",
        failure_type=None,
        failure_reason=None,
        traversal_path_count=5,
        selected_graph_node_ids=[],
        inspected_graph_node_ids=[],
        summary_material_count=2,
        raw_original_material_count=0,
        source_data_ids=["r_loop:vessel_return_packet:order_232_partial"],
    )
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame:order_232_partial",
        turn_id="turn_order_232_partial",
        user_question="partial R 결과를 정직하게 설명해줘.",
        brief_status="ready",
        handoff_frame_id="node_2:handoff:order_232_partial",
        vessel_r_material_status="present",
        vessel_r_material_count=5,
        vessel_r_material_source_data_ids=["r_loop:vessel_return_packet:order_232_partial"],
        vessel_r_material=vessel_material,
        source_trace_ids=["trace:user"],
        source_data_ids=[
            "node_2:handoff:order_232_partial",
            "r_loop:vessel_return_packet:order_232_partial",
        ],
    )
