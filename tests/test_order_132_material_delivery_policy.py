from __future__ import annotations

from dataclasses import asdict
import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L3PerDocumentSummaryFrame,
    MetainfoBoundary,
    Node2AnswerBasisFrame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block


def test_relative_allowed_replaces_raw_text_with_l3_summary_payload() -> None:
    trace_store, data_store, trace_id = _stores_with_raw_document()
    _record_l3_summary(data_store, trace_id)
    answer_basis = _answer_basis_frame("relative_allowed")

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_132",
        user_question="요약 기준으로 설명해줘",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["source:handoff"],
        answer_basis_frame=answer_basis,
    )
    payload = node3_brief_llm_payload(brief)
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert brief.material_delivery_mode == "l3_summary_replaces_raw_context"
    assert brief.raw_document_policy == "omit_raw_text_from_llm_payload"
    assert brief.llm_raw_document_text_count == 0
    assert brief.llm_l3_summary_context_count == 1
    assert brief.raw_context_replaced_by_summary_count == 1
    assert payload["supplied_document_contexts"] == []
    assert payload["read_documents"] == []
    assert len(payload["omitted_supplied_document_contexts"]) == 1
    assert "원문 전체 텍스트 payload" not in payload_text
    assert "L3 task 요약" in payload_text

    raw_record = data_store.require_record("tool_result:read_doc:001")
    assert isinstance(raw_record.payload, dict)
    assert raw_record.payload["text"] == "원문 전체 텍스트 payload"


def test_absolute_first_preserves_raw_text_even_when_l3_summary_exists() -> None:
    trace_store, data_store, trace_id = _stores_with_raw_document()
    _record_l3_summary(data_store, trace_id)

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_132",
        user_question="원문 기준으로 확인해줘",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["source:handoff"],
        answer_basis_frame=_answer_basis_frame("absolute_first"),
    )
    payload = node3_brief_llm_payload(brief)

    assert brief.material_delivery_mode == "raw_document_primary"
    assert brief.llm_raw_document_text_count == 1
    assert brief.raw_context_replaced_by_summary_count == 0
    assert payload["supplied_document_contexts"][0]["text"] == "원문 전체 텍스트 payload"
    assert payload["material_delivery_policy"]["l3_summary_policy"] == "auxiliary_only"


def test_mixed_mode_without_l3_summary_falls_back_to_raw_text() -> None:
    trace_store, data_store, trace_id = _stores_with_raw_document()

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_132",
        user_question="불확실성을 드러내줘",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["source:handoff"],
        answer_basis_frame=_answer_basis_frame("mixed_or_uncertain"),
    )
    payload = node3_brief_llm_payload(brief)

    assert brief.material_delivery_mode == "raw_document_fallback_no_l3_summary"
    assert brief.raw_document_policy == "preserve_raw_context_because_l3_summary_missing"
    assert brief.llm_raw_document_text_count == 1
    assert payload["supplied_document_contexts"][0]["text"] == "원문 전체 텍스트 payload"


def test_grounding_reports_llm_raw_text_and_l3_summary_counts() -> None:
    trace_store, data_store, trace_id = _stores_with_raw_document()
    _record_l3_summary(data_store, trace_id)

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_132",
        user_question="요약 기준으로 설명해줘",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["source:handoff"],
        answer_basis_frame=_answer_basis_frame("relative_allowed"),
    )
    grounding = build_node3_grounding_block(brief)

    assert "- node_3 공급 문서 context: 1개" in grounding
    assert "- node_3 LLM 원문 text: 0개" in grounding
    assert "- L3 문서별 요약 재료: 1개" in grounding
    assert "L3 요약이 원문 text 대체" in grounding


def _stores_with_raw_document() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_132",
        actor="test",
        event_type="node_output",
        output_ref=["source:handoff", "tool_result:read_doc:001"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="source:handoff",
        data_type="test:handoff",
        source_trace_id=event.event_id,
        payload={"frame_id": "source:handoff"},
    )
    data_store.create_record(
        data_id="tool_result:read_doc:001",
        data_type="tool_result:read_doc",
        source_trace_id=event.event_id,
        payload={
            "doc_id": "Administrative_Reform_1/04_Orders/ORDER_132_TEST.md",
            "text": "원문 전체 텍스트 payload",
            "char_count": 14,
        },
    )
    return trace_store, data_store, event.event_id


def _record_l3_summary(data_store: DataStore, trace_id: str) -> None:
    frame = L3PerDocumentSummaryFrame(
        frame_id="L3:per_document_summary:0001",
        turn_id="turn_order_132",
        source_document_data_id="tool_result:read_doc:001",
        source_doc_id="Administrative_Reform_1/04_Orders/ORDER_132_TEST.md",
        source_document_name="ORDER_132_TEST.md",
        source_char_count=14,
        summary_status="ran",
        plain_document_summary="L3 plain 요약",
        plain_summary_source_data_id="tool_result:read_doc:001",
        task_relevant_summary="L3 task 요약",
        task_relevant_summary_source_data_ids=[
            "tool_result:read_doc:001",
            "L1:goal_frame",
            "L3:preserved_info_frame",
        ],
        generated_by="LLM:test",
        semantic_judgement_status="ran",
        summary_failure_type="none",
        llm_call_data_id="llm_call:L3_document_summary:trace_000010",
        prompt_ref="songryeon_core/prompts/l3_per_document_summary_v0.md",
        source_trace_ids=[trace_id],
        source_data_ids=[
            "tool_result:read_doc:001",
            "L1:goal_frame",
            "L3:preserved_info_frame",
            "llm_call:L3_document_summary:trace_000010",
        ],
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:L3_per_document_summary_frame",
        source_trace_id=trace_id,
        payload=asdict(frame),
    )


def _answer_basis_frame(mode: str) -> Node2AnswerBasisFrame:
    return Node2AnswerBasisFrame(
        frame_id="node_2:answer_basis_frame",
        turn_id="turn_order_132",
        answer_basis_mode=mode,
        basis_reason_codes=["document_basis_present"],
        mode_selection_reason="테스트용 answer_basis_mode",
        mode_selection_reason_info_class="mixed",
        generated_by="LLM:test",
        info_class="mixed",
        semantic_judgement_status="ran",
        source_trace_ids=["trace_answer_basis"],
        source_data_ids=["node_2:answer_basis_frame"],
    )
