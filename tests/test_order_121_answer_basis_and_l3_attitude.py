from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import DataRef, MetainfoBoundary, Node3InputBriefFrame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_2_metainfo_boundary import run_node2_answer_basis_selection
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


class AnswerBasisPayloadFakeAdapter:
    model_id = "order-121-answer-basis-fake"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_node2_answer_basis_accepts_available_evidence_source_from_boundary_sample() -> None:
    trace_store, data_store, trace_id = _stores()
    boundary = MetainfoBoundary(
        absolute_info=[
            DataRef(
                data_id="source:sample_boundary_record",
                data_type="test:boundary_sample",
                source_trace_id=trace_id,
            )
        ]
    )

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_121",
        user_question="이 구조 어때?",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=AnswerBasisPayloadFakeAdapter(
            {
                "answer_basis_mode": "relative_allowed",
                "basis_reason_codes": ["user_asked_for_interpretation"],
                "mode_selection_reason": "boundary sample을 근거로 해석 답변이 가능하다.",
                "mode_selection_reason_info_class": "mixed",
                "evidence_roles": [
                    {
                        "source_data_id": "source:sample_boundary_record",
                        "evidence_role": "supporting_context",
                        "role_reason": "available_evidence_sources 안에 있는 sample 근거다.",
                        "role_reason_info_class": "mixed",
                    }
                ],
            }
        ),
        input_ref=[trace_id],
        source_data_ids=["source:runtime"],
    )

    assert frame.semantic_judgement_status == "ran"
    assert frame.generated_by == "LLM:order-121-answer-basis-fake"
    assert frame.evidence_roles[0].source_data_id == "source:sample_boundary_record"
    assert "source:sample_boundary_record" in frame.source_data_ids


def test_node2_answer_basis_rejects_source_outside_available_evidence_sources() -> None:
    trace_store, data_store, trace_id = _stores()

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_121",
        user_question="이 구조 어때?",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=AnswerBasisPayloadFakeAdapter(
            {
                "answer_basis_mode": "relative_allowed",
                "basis_reason_codes": ["user_asked_for_interpretation"],
                "mode_selection_reason": "허용되지 않은 근거 ID를 일부러 쓴다.",
                "mode_selection_reason_info_class": "mixed",
                "evidence_roles": [
                    {
                        "source_data_id": "source:not_in_available_table",
                        "evidence_role": "supporting_context",
                        "role_reason": "validator가 막아야 한다.",
                        "role_reason_info_class": "mixed",
                    }
                ],
            }
        ),
        input_ref=[trace_id],
        source_data_ids=["source:runtime"],
    )

    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.answer_basis_mode == "mixed_or_uncertain"
    assert frame.answer_basis_failure_type == "schema_failed"
    assert "source_data_id must exist" in frame.answer_basis_validation_error


def test_node3_brief_preserves_l_loop_failure_attitude() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_l_loop_return_summary(data_store, trace_id)

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_121",
        user_question="말하기 모드 설계 어때?",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["source:handoff"],
    )
    payload = node3_brief_llm_payload(brief)
    grounding = build_node3_grounding_block(brief)

    assert brief.l_loop_task_status == "failed"
    assert brief.l_loop_failure_level == "budget_exhausted"
    assert brief.l_loop_result_attitude_hint == "l_loop_budget_exhausted"
    assert payload["l_loop_result"]["attitude_hint"] == "l_loop_budget_exhausted"
    assert "L 검색 목표 상태: failed / budget_exhausted" in grounding
    assert "검색 성공으로 단정하지 않는다" in grounding


def test_node4_flags_l_loop_failure_hidden_as_success() -> None:
    trace_store, data_store, trace_id = _stores()
    brief = Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_121",
        user_question="말하기 모드 설계 어때?",
        brief_status="ready",
        handoff_frame_id="source:handoff",
        l_loop_return_summary_frame_id="L:return_summary_frame",
        l_loop_task_status="failed",
        l_loop_failure_level="budget_exhausted",
        l3_goal_match_status="missing",
        l3_semantic_goal_match_status="missing",
        remaining_query_attempts=0,
        remaining_read_doc_calls=8,
        l_loop_result_attitude_hint="l_loop_budget_exhausted",
        source_trace_ids=[trace_id],
        source_data_ids=["source:handoff", "L:return_summary_frame"],
    )
    rendered_markdown = (
        build_node3_grounding_block(brief)
        + "\n\nL 검색 목표가 성공했으므로 설계 평가는 충분히 확정됐다."
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_121",
        report_id="report:test",
        boundary_id="boundary:test",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=SongRyeonAllNodesFakeLLMAdapter(),
        input_ref=[trace_id],
        source_data_ids=["report:test", brief.frame_id, "boundary:test"],
    )
    gate = data_store.require_record("node_4:gatekeeper_frame").payload

    assert gate["gate_status"] == "needs_revision"
    assert "l_loop_failure_hidden_as_success" in gate["contradictions"]


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_121",
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:boundary", "source:handoff"],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=event.event_id,
            payload={"data_id": data_id},
        )
    return trace_store, data_store, event.event_id


def _record_l_loop_return_summary(data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L:return_summary_frame",
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L:return_summary_frame",
            "turn_id": "turn_order_121",
            "loop_id": "L",
            "l_loop_task_status": "failed",
            "failure_level": "budget_exhausted",
            "l3_goal_match_status": "missing",
            "l3_semantic_goal_match_status": "missing",
            "remaining_query_attempts": 0,
            "remaining_read_doc_calls": 8,
        },
    )
