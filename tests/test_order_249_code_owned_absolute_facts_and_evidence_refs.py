from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import DataRef, MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.l3_result_keeper import run_l3_result_keeper
from songryeon_core.nodes.node_2_metainfo_boundary import (
    run_node2_answer_basis_selection,
)


class WrongOperationalFactsL3Adapter:
    model_id = "order-249-wrong-operational-facts"

    def __init__(self) -> None:
        self.l3_input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "L3 Result Keeper v0" in request.prompt:
            self.l3_input_payload = request.input_payload
            payload: dict[str, object] = {
                # 이전 L3 출력 형식을 일부러 섞어도 authoritative 운영 frame에는
                # 복사되지 않아야 한다.
                "achievement_status": "achieved",
                "reason": "후보 3개 중 5개를 찾고 문서 3개와 코드 2개를 읽었다.",
                "macro_achievement_status": "achieved",
                "macro_achievement_reason": "잘못 센 운영 숫자다.",
                "micro_achievement_status": "achieved",
                "micro_achievement_reason": "잘못 센 운영 숫자다.",
                "semantic_goal_match_status": "matched",
                "semantic_goal_match_reason": "읽은 문서가 질문의 요약 경계를 직접 다룬다.",
            }
        else:
            payload = {
                "plain_document_summary": "테스트 문서는 L3의 운영 사실 경계를 설명한다.",
                "task_relevant_summary": "현재 질문에서는 코드 소유 count 경계가 핵심이다.",
                "summary_limit_note": "",
            }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class InspectingAnswerBasisAdapter:
    model_id = "order-249-evidence-ref-inspector"

    def __init__(self, *, selected_ref: str) -> None:
        self.selected_ref = selected_ref
        self.input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.input_payload = request.input_payload
        payload = {
            "answer_basis_mode": "relative_allowed",
            "basis_reason_codes": ["user_asked_for_interpretation"],
            "mode_selection_reason": "한 근거의 의미를 해석해도 되는 질문이다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [
                {
                    "evidence_ref": self.selected_ref,
                    "evidence_role": "primary_answer_basis",
                    "role_reason": "선택한 근거가 질문의 중심 자료다.",
                    "role_reason_info_class": "relative",
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_l3_ignores_llm_operational_counts_and_preserves_code_facts() -> None:
    trace_store, data_store, l1_event, l2_event, tool_trace_id = _l3_stores()
    adapter = WrongOperationalFactsL3Adapter()

    run_l3_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_249_l3",
        l1_event=l1_event,
        l2_event=l2_event,
        extra_input_trace_ids=[tool_trace_id],
        extra_input_data_ids=[
            "L1:goal_frame",
            "L2:query_frame",
            "tool_result:search_docs:001",
            "tool_result:read_doc:001",
        ],
        user_query="L3의 운영 사실 경계를 설명해줘",
        adapter=adapter,
    )

    record = data_store.get_record("L3:achievement_frame")
    assert record is not None
    payload = record.payload
    assert isinstance(payload, dict)
    assert payload["candidate_count"] == 1
    assert payload["read_doc_ids"] == ["ORDER_249_TEST.md"]
    assert payload["actual_read_code_file_count"] == 0
    assert str(payload["reason"]).startswith("CODE_STATUS:")
    assert "후보 3개" not in str(payload["reason"])
    assert payload["semantic_goal_match_status"] == "matched"
    assert payload["semantic_goal_match_reason"] == "읽은 문서가 질문의 요약 경계를 직접 다룬다."
    assert "CODE:OPERATION_CHECK" in str(payload["achievement_generation_source"])
    assert "SEMANTIC_GOAL_MATCH" in str(payload["achievement_generation_source"])

    assert adapter.l3_input_payload is not None
    serialized_input = json.dumps(adapter.l3_input_payload, ensure_ascii=False)
    assert "evidence_counts" not in adapter.l3_input_payload
    assert "minimum_read_documents" not in serialized_input
    assert "source_data_ids" not in serialized_input


def test_node2_evidence_ref_input_hides_raw_ids_and_code_restores_source_id() -> None:
    trace_store, data_store, input_trace_id, boundary = _node2_stores()
    adapter = InspectingAnswerBasisAdapter(selected_ref="E004")

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_249_node2",
        user_question="이 근거가 답변 중심으로 적절한지 해석해줘",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=adapter,
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime"],
    )

    assert frame.generated_by == f"LLM:{adapter.model_id}"
    assert frame.evidence_roles[0].source_data_id == "source:sample_boundary_record"
    assert adapter.input_payload is not None
    table = adapter.input_payload["available_evidence_sources"]
    assert isinstance(table, list)
    assert [row["evidence_ref"] for row in table] == ["E001", "E002", "E003", "E004"]
    serialized_input = json.dumps(adapter.input_payload, ensure_ascii=False)
    assert '"source_data_id"' not in serialized_input
    assert '"info_id"' not in serialized_input
    assert "source:sample_boundary_record" not in serialized_input


def test_node2_unknown_evidence_ref_remains_schema_failed_fallback() -> None:
    trace_store, data_store, input_trace_id, boundary = _node2_stores()

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_249_node2_invalid",
        user_question="이 근거를 해석해줘",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=InspectingAnswerBasisAdapter(selected_ref="E999"),
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime"],
    )

    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.answer_basis_mode == "mixed_or_uncertain"
    assert frame.answer_basis_failure_type == "schema_failed"
    assert "evidence_ref must exist" in frame.answer_basis_validation_error


def _l3_stores() -> tuple[TraceStore, DataStore, object, object, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_249_l3",
        actor="L1",
        event_type="node_output",
        output_ref=["L1:goal_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=l1_event.event_id,
        payload={
            "macro_goal": "읽은 근거가 질문에 맞는지 확인한다.",
            "micro_goal": "문서 원문 한 개를 확보한다.",
            "minimum_read_documents": 1,
            "evidence_requirement_kind": "single_doc",
            "l_loop_success_condition": "문서 원문 한 개가 있어야 한다.",
        },
    )
    l2_event = trace_store.create_event(
        turn_id="turn_order_249_l3",
        actor="L2",
        event_type="node_output",
        output_ref=["L2:query_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        source_trace_id=l2_event.event_id,
        payload={"query_text": "ORDER_249 L3 운영 사실 경계"},
    )
    tool_event = trace_store.create_event(
        turn_id="turn_order_249_l3",
        actor="tool:read_doc",
        event_type="tool_result",
        output_ref=["tool_result:read_doc:001"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="tool_result:search_docs:001",
        data_type="tool_result:search_docs",
        source_trace_id=tool_event.event_id,
        payload={
            "results": [
                {
                    "result_id": "result_001",
                    "doc_id": "ORDER_249_TEST.md",
                    "chunk_id": "ORDER_249_TEST.md#chunk_001",
                    "score": 0.95,
                    "embedding_model_id": "test-embedding",
                    "text_preview": "L3 운영 사실 경계",
                }
            ]
        },
    )
    data_store.create_record(
        data_id="tool_result:read_doc:001",
        data_type="tool_result:read_doc",
        source_trace_id=tool_event.event_id,
        payload={
            "doc_id": "ORDER_249_TEST.md",
            "text": "L3 운영 count와 상태는 코드가 기록하고 LLM은 의미 적합성만 판단한다.",
            "char_count": 42,
        },
    )
    return trace_store, data_store, l1_event, l2_event, tool_event.event_id


def _node2_stores() -> tuple[TraceStore, DataStore, str, MetainfoBoundary]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_249_node2",
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
