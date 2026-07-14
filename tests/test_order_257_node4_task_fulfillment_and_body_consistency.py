from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import Node3InputBriefFrame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


class GatePayloadAdapter:
    model_id = "order-257-gate-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        _ = request
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_node4_blocks_llm_pass_when_user_task_is_not_fulfilled() -> None:
    brief = _brief(evidence_requirement="not_required")
    gate = _run_gate(
        brief=brief,
        rendered_markdown="문서 근거가 없어 답할 수 없습니다.",
        payload=_gate_payload(
            task_fulfillment_status="not_fulfilled",
            grounding_consistency_status="consistent",
            task_failure_reasons=["근거 비의존 인사 요청을 문서 부족으로 거절했다."],
        ),
    )

    assert gate["gate_status"] == "needs_revision"
    assert gate["task_fulfillment_status"] == "not_fulfilled"
    assert "CODE_STATUS:node4_task_not_fulfilled" in gate["reason"]


def test_node4_blocks_body_contradiction_even_when_llm_gate_says_pass() -> None:
    brief = _brief(evidence_requirement="required")
    brief.actual_tool_read_doc_count = 7
    report = (
        f"{build_node3_grounding_block(brief)}\n\n"
        "실제 문서 원문 읽기는 발생하지 않았습니다."
    )
    gate = _run_gate(
        brief=brief,
        rendered_markdown=report,
        payload=_gate_payload(
            task_fulfillment_status="fulfilled",
            grounding_consistency_status="contradiction",
            task_failure_reasons=["read_doc 절대 count와 본문이 충돌한다."],
        ),
    )

    assert gate["gate_status"] == "needs_revision"
    assert gate["grounding_consistency_status"] == "contradiction"
    assert "CODE_STATUS:node4_body_grounding_contradiction" in gate["reason"]


def test_node4_passes_fulfilled_not_required_task_without_grounding_block() -> None:
    brief = _brief(evidence_requirement="not_required")
    gate = _run_gate(
        brief=brief,
        rendered_markdown="안녕, 오늘도 잘 부탁해.",
        payload=_gate_payload(
            task_fulfillment_status="fulfilled",
            grounding_consistency_status="consistent",
            task_failure_reasons=[],
        ),
    )

    assert gate["gate_status"] == "pass"
    assert gate["task_fulfillment_status"] == "fulfilled"
    assert gate["grounding_consistency_status"] == "consistent"


def test_node4_does_not_silently_pass_missing_task_checks_for_recorded_contract() -> None:
    brief = _brief(evidence_requirement="not_required")
    payload = {
        "gate_status": "pass",
        "reason": "기존 근거 guard는 통과했다.",
        "checked_claims": [],
        "unsupported_claims": [],
        "contradictions": [],
        "revision_targets": [],
    }
    gate = _run_gate(
        brief=brief,
        rendered_markdown="안녕, 오늘도 잘 부탁해.",
        payload=payload,
    )

    assert gate["gate_status"] == "needs_revision"
    assert gate["task_fulfillment_status"] == "not_checkable"
    assert "CODE_STATUS:node4_task_check_not_available" in gate["reason"]


def _gate_payload(
    *,
    task_fulfillment_status: str,
    grounding_consistency_status: str,
    task_failure_reasons: list[str],
) -> dict[str, object]:
    return {
        "gate_status": "pass",
        "reason": "기존 근거 경계는 통과했다.",
        "checked_claims": ["user_task_fulfillment", "body_grounding_consistency"],
        "unsupported_claims": [],
        "contradictions": [],
        "revision_targets": [],
        "task_fulfillment_status": task_fulfillment_status,
        "grounding_consistency_status": grounding_consistency_status,
        "task_failure_reasons": task_failure_reasons,
    }


def _brief(*, evidence_requirement: str) -> Node3InputBriefFrame:
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_257",
        user_question="안녕이라고 한 문장으로 답해줘.",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        answer_task_contract_status="recorded",
        user_task_summary="한 문장으로 인사한다.",
        fulfillment_requirements=["인사 한 문장을 출력한다."],
        evidence_requirement=evidence_requirement,
        answer_basis_mode="relative_allowed",
        basis_reason_codes=["user_asked_for_interpretation"],
        mode_selection_reason="근거 비의존 인사 요청이다.",
        mode_selection_reason_info_class="relative",
        answer_basis_generated_by="LLM:test",
        answer_basis_info_class="relative",
        answer_basis_semantic_judgement_status="ran",
        source_trace_ids=["trace_001"],
        source_data_ids=["node_2:handoff_frame"],
    )


def _run_gate(
    *,
    brief: Node3InputBriefFrame,
    rendered_markdown: str,
    payload: dict[str, object],
) -> dict[str, object]:
    trace_store = TraceStore()
    data_store = DataStore()
    seed = trace_store.create_event(
        turn_id=brief.turn_id,
        actor="test",
        event_type="node_output",
        output_ref=["report:1", brief.frame_id, "boundary:1"],
        schema_status="passed",
    )
    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=brief.turn_id,
        report_id="report:1",
        boundary_id="boundary:1",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=GatePayloadAdapter(payload),
        input_ref=[seed.event_id],
        source_data_ids=["report:1", brief.frame_id, "boundary:1"],
    )
    record = data_store.require_record("node_4:gatekeeper_frame")
    assert isinstance(record.payload, dict)
    return record.payload
