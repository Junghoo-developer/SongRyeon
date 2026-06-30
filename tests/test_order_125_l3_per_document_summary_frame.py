from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L3PerDocumentSummaryFrame,
    MetainfoBoundary,
    validate_l3_per_document_summary_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.l3_result_keeper import (
    run_l3_result_keeper,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)


class SequencePayloadAdapter:
    model_id = "order-125-sequence-fake"

    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = list(payloads)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.payloads:
            raise RuntimeError("no fake payload left")
        payload = self.payloads.pop(0)
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_l3_per_document_summary_schema_separates_relative_and_mixed() -> None:
    frame = _valid_summary_frame()
    validate_l3_per_document_summary_frame(frame)

    frame.plain_summary_info_class = "mixed"
    with pytest.raises(ValueError, match="plain_document_summary must be marked relative"):
        validate_l3_per_document_summary_frame(frame)


def test_l3_result_keeper_records_per_document_summary_frame() -> None:
    trace_store, data_store, l1_event, l2_event, source_trace_id = _stores_with_l_inputs()
    data_store.create_record(
        data_id="tool_result:read_doc:001",
        data_type="tool_result:read_doc",
        source_trace_id=source_trace_id,
        payload={
            "doc_id": "Administrative_Reform_1/04_Orders/ORDER_125_TEST.md",
            "text": "ORDER_125는 L3가 읽은 문서마다 두 종류의 요약을 남기는 구조다.",
            "char_count": 37,
        },
    )

    run_l3_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_125",
        l1_event=l1_event,
        l2_event=l2_event,
        extra_input_trace_ids=[source_trace_id],
        extra_input_data_ids=["L1:goal_frame", "tool_result:read_doc:001"],
        user_query="ORDER_125 요약 흐름을 알려줘",
        adapter=SequencePayloadAdapter(
            [
                _achievement_payload(),
                {
                    "plain_document_summary": "ORDER_125가 문서별 두 종류 요약을 다룬다고 설명한다.",
                    "task_relevant_summary": "현재 질문 기준으로 L3 문서별 요약 frame의 용도와 경계가 핵심이다.",
                    "summary_limit_note": "",
                },
            ]
        ),
    )

    summary_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "node_output:L3_per_document_summary_frame"
    ]
    assert len(summary_records) == 1
    payload = summary_records[0].payload
    assert isinstance(payload, dict)
    assert payload["summary_status"] == "ran"
    assert payload["plain_summary_info_class"] == "relative"
    assert payload["plain_summary_source_mode"] == "direct_record"
    assert payload["plain_summary_claim_alignment"] == "one_document_to_one_summary"
    assert payload["task_relevant_summary_info_class"] == "mixed"
    assert payload["task_relevant_summary_source_mode"] == "source_bundle"
    assert payload["task_relevant_summary_claim_alignment"] == "one_document_plus_task_context"
    assert payload["source_document_data_id"] in payload["source_data_ids"]
    assert payload["llm_call_data_id"] in payload["source_data_ids"]


def test_node3_brief_receives_l3_summary_material_without_raw_payload_ids() -> None:
    trace_store, data_store, _, _, source_trace_id = _stores_with_l_inputs()
    summary_frame = _valid_summary_frame()
    data_store.create_record(
        data_id=summary_frame.frame_id,
        data_type="node_output:L3_per_document_summary_frame",
        source_trace_id=source_trace_id,
        payload=asdict(summary_frame),
    )
    data_store.create_record(
        data_id="source:handoff",
        data_type="test:handoff",
        source_trace_id=source_trace_id,
        payload={"frame_id": "source:handoff"},
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_125",
        user_question="L3 요약은 어떻게 전달돼?",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[source_trace_id],
        source_data_ids=["source:handoff"],
    )
    payload = node3_brief_llm_payload(brief)

    assert brief.brief_status == "ready"
    assert len(brief.l3_document_summaries) == 1
    assert summary_frame.frame_id in brief.source_data_ids
    l3_summary_payload = payload["l3_document_summaries"]
    assert isinstance(l3_summary_payload, dict)
    assert l3_summary_payload["count"] == 1
    item = l3_summary_payload["items"][0]
    assert "source_data_id" not in item
    assert item["plain_summary_info_class"] == "relative"
    assert item["task_relevant_summary_info_class"] == "mixed"
    assert item["plain_document_summary"] == summary_frame.plain_document_summary
    assert item["task_relevant_summary"] == summary_frame.task_relevant_summary


def _stores_with_l_inputs() -> tuple[TraceStore, DataStore, object, object, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_125",
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
            "macro_goal": "문서별 요약 경계를 확인한다.",
            "micro_goal": "L3 요약 frame이 node_3로 전달되는지 본다.",
            "minimum_read_documents": 1,
        },
    )
    l2_event = trace_store.create_event(
        turn_id="turn_order_125",
        actor="L2",
        event_type="node_output",
        output_ref=["L2:query_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        source_trace_id=l2_event.event_id,
        payload={"query_text": "ORDER_125"},
    )
    source_event = trace_store.create_event(
        turn_id="turn_order_125",
        actor="tool:read_doc",
        event_type="tool_result",
        output_ref=["tool_result:read_doc:001"],
        schema_status="passed",
    )
    return trace_store, data_store, l1_event, l2_event, source_event.event_id


def _achievement_payload() -> dict[str, object]:
    return {
        "achievement_status": "partial",
        "reason": "읽은 문서 하나를 기준으로 부분 판단한다.",
        "macro_achievement_status": "partial",
        "macro_achievement_reason": "문서 요약 경계 확인에는 일부 근거가 있다.",
        "micro_achievement_status": "partial",
        "micro_achievement_reason": "read_doc 문서가 하나 있다.",
        "goal_match_status": "not_applicable",
        "goal_match_reason": "CODE_STATUS:no_specific_doc_hint_detected",
        "semantic_goal_match_status": "partial",
        "semantic_goal_match_reason": "읽은 문서 하나만 있으므로 부분 근거다.",
    }


def _valid_summary_frame() -> L3PerDocumentSummaryFrame:
    return L3PerDocumentSummaryFrame(
        frame_id="L3:per_document_summary:0001",
        turn_id="turn_order_125",
        source_document_data_id="tool_result:read_doc:001",
        source_doc_id="Administrative_Reform_1/04_Orders/ORDER_125_TEST.md",
        source_document_name="ORDER_125_TEST.md",
        source_char_count=37,
        summary_status="ran",
        plain_document_summary="ORDER_125가 L3 문서별 요약 frame을 설명한다.",
        plain_summary_source_data_id="tool_result:read_doc:001",
        task_relevant_summary="현재 질문 기준으로 L3 요약 전달 경계가 중요하다.",
        task_relevant_summary_source_data_ids=[
            "tool_result:read_doc:001",
            "L1:goal_frame",
            "L3:preserved_info_frame",
        ],
        generated_by="LLM:order-125-sequence-fake",
        semantic_judgement_status="ran",
        summary_failure_type="none",
        llm_call_data_id="llm_call:L3_document_summary:trace_000010",
        prompt_ref="songryeon_core/prompts/l3_per_document_summary_v0.md",
        source_trace_ids=["trace_000001"],
        source_data_ids=[
            "tool_result:read_doc:001",
            "L1:goal_frame",
            "L3:preserved_info_frame",
            "llm_call:L3_document_summary:trace_000010",
        ],
    )
