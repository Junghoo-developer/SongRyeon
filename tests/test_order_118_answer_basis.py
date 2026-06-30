from __future__ import annotations

import json
from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.fake import BrokenJSONFakeLLMAdapter
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_2_metainfo_boundary import (
    run_node2_answer_basis_selection,
)
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_pretty_turn


class AnswerBasisPayloadFakeAdapter:
    model_id = "answer-basis-payload-fake-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        _ = request
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_node2_answer_basis_absolute_first_fixture() -> None:
    frame = _run_answer_basis_fixture(
        {
            "answer_basis_mode": "absolute_first",
            "basis_reason_codes": [
                "code_verified_fact_required",
                "runtime_state_basis_present",
            ],
            "mode_selection_reason": "runtime count 확인 요청이므로 코드/trace 값 중심으로 답해야 한다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [_role("source:runtime", "primary_answer_basis")],
        },
        user_question="몇 개 읽었어?",
    )

    assert frame.answer_basis_mode == "absolute_first"
    assert frame.generated_by == "LLM:answer-basis-payload-fake-adapter"
    assert frame.info_class == "mixed"
    assert frame.mode_selection_reason


def test_node2_answer_basis_relative_allowed_fixture() -> None:
    frame = _run_answer_basis_fixture(
        {
            "answer_basis_mode": "relative_allowed",
            "basis_reason_codes": ["user_asked_for_interpretation"],
            "mode_selection_reason": "사용자가 구조 의견을 요청했으므로 해석과 조언이 허용된다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [_role("source:runtime", "supporting_context")],
        },
        user_question="이 구조 어때?",
    )

    assert frame.answer_basis_mode == "relative_allowed"
    assert frame.basis_reason_codes == ["user_asked_for_interpretation"]
    assert frame.semantic_judgement_status == "ran"


def test_node2_answer_basis_mixed_or_uncertain_fixture() -> None:
    frame = _run_answer_basis_fixture(
        {
            "answer_basis_mode": "mixed_or_uncertain",
            "basis_reason_codes": ["multi_source_bundle", "partial_evidence_only"],
            "mode_selection_reason": "최근 대화와 실행 기록 source bundle을 함께 봐야 하므로 한계를 표시해야 한다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [
                _role("source:runtime", "supporting_context"),
                _role("source:memory", "primary_answer_basis"),
            ],
        },
        user_question="오늘 전체 흐름 정리해줘.",
    )

    assert frame.answer_basis_mode == "mixed_or_uncertain"
    assert "multi_source_bundle" in frame.basis_reason_codes
    assert "partial_evidence_only" in frame.basis_reason_codes
    assert len(frame.evidence_roles) == 2


def test_node2_answer_basis_llm_failure_uses_code_fallback() -> None:
    trace_store, data_store, input_trace_id = _stores()

    _, frame_id, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_118",
        user_question="몇 개 읽었어?",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=BrokenJSONFakeLLMAdapter(),
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime", "source:memory"],
    )

    assert frame_id == "node_2:answer_basis_frame"
    assert frame.answer_basis_mode == "mixed_or_uncertain"
    assert frame.basis_reason_codes == ["llm_mode_selection_failed"]
    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.info_class == "absolute_status"
    assert frame.semantic_judgement_status == "failed"


def test_node3_brief_receives_answer_basis_without_raw_id_leak_in_llm_payload() -> None:
    answer_basis_frame = _run_answer_basis_fixture(
        {
            "answer_basis_mode": "absolute_first",
            "basis_reason_codes": ["code_verified_fact_required"],
            "mode_selection_reason": "확인 가능한 실행 값 중심으로 답해야 한다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [_role("source:runtime", "primary_answer_basis")],
        },
        user_question="route가 뭐야?",
    )
    trace_store, data_store, input_trace_id = _stores()
    data_store.create_record(
        data_id=answer_basis_frame.frame_id,
        data_type="node_output:node2_answer_basis_frame",
        payload=asdict(answer_basis_frame),
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_118",
        user_question="route가 뭐야?",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[input_trace_id],
        source_data_ids=[
            "source:handoff",
            "source:runtime",
            answer_basis_frame.frame_id,
        ],
        answer_basis_frame=answer_basis_frame,
    )
    payload = node3_brief_llm_payload(brief)
    answer_basis_payload = payload["answer_basis"]

    assert brief.answer_basis_mode == "absolute_first"
    assert brief.answer_basis_frame_id == "node_2:answer_basis_frame"
    assert isinstance(answer_basis_payload, dict)
    assert answer_basis_payload["answer_basis_mode"] == "absolute_first"
    assert "source:runtime" not in json.dumps(answer_basis_payload, ensure_ascii=False)
    assert answer_basis_payload["evidence_roles"][0]["source_label"] == "공급된 근거 자료"


def test_runtime_view_displays_answer_basis_fallback() -> None:
    result = run_dry_turn(user_input="몇 개 읽었어?")
    rendered = render_pretty_turn(result, user_input="몇 개 읽었어?")

    assert result["node2_answer_basis_mode"] == "mixed_or_uncertain"
    assert result["node2_answer_basis_reason_codes"] == ["llm_mode_selection_failed"]
    assert "node_2 answer basis" in rendered
    assert "reason_codes" in rendered
    assert "CODE:FALLBACK" in rendered


def _run_answer_basis_fixture(
    payload: dict[str, object],
    *,
    user_question: str,
):
    trace_store, data_store, input_trace_id = _stores()
    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_118",
        user_question=user_question,
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=AnswerBasisPayloadFakeAdapter(payload),
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime", "source:memory"],
    )
    return frame


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    seed_event = trace_store.create_event(
        turn_id="turn_order_118",
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:memory", "source:boundary", "source:handoff"],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:memory", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=seed_event.event_id,
            payload={"data_id": data_id},
        )
    return trace_store, data_store, seed_event.event_id


def _role(source_data_id: str, evidence_role: str) -> dict[str, object]:
    return {
        "source_data_id": source_data_id,
        "evidence_role": evidence_role,
        "role_reason": "테스트 fixture가 지정한 역할이다.",
        "role_reason_info_class": "mixed",
    }
