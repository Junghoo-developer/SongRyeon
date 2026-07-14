from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    Node0DocumentMaterialItem,
    Node2AnswerBasisFrame,
    Node2EvidenceRole,
    Node3BriefRuntimeTask,
    Node3InputBriefFrame,
    Node3L3DocumentSummaryMaterial,
    validate_node2_answer_basis_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_2_handoff import node3_brief_llm_payload
from songryeon_core.nodes.node_2_metainfo_boundary import (
    run_node2_answer_basis_selection,
)
from songryeon_core.nodes.node_3_reporter import assemble_node3_report_markdown


class CatalogSelectingAdapter:
    model_id = "catalog-selecting-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        catalog = request.input_payload.get("answer_material_catalog")
        assert isinstance(catalog, list)
        summary = next(
            item
            for item in catalog
            if isinstance(item, dict)
            and item.get("source_kind") == "l3_document_summary"
        )
        payload = {
            "answer_basis_mode": "relative_allowed",
            "basis_reason_codes": ["document_basis_present"],
            "mode_selection_reason": "선택 가능한 L3 문서 요약이 사용자 설명 과업에 직접 대응한다.",
            "mode_selection_reason_info_class": "relative",
            "user_task_summary": "ORDER 256의 핵심을 설명한다.",
            "fulfillment_requirements": [
                "검색 과정이 아니라 ORDER 256의 핵심 내용을 설명한다."
            ],
            "evidence_requirement": "required",
            "evidence_roles": [
                {
                    "evidence_ref": summary["evidence_ref"],
                    "evidence_role": "primary_answer_basis",
                    "role_reason": "이 L3 요약이 문서 내용에 직접 대응한다.",
                    "role_reason_info_class": "relative",
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_node2_catalog_exposes_l3_summary_and_records_task_contract() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_256",
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:boundary", "source:handoff"],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            payload={"turn_id": "turn_order_256"},
            source_trace_id=event.event_id,
        )
    data_store.create_record(
        data_id="summary:order_256",
        data_type="node_output:L3_per_document_summary_frame",
        payload={
            "turn_id": "turn_order_256",
            "source_document_name": "ORDER_256.md",
            "plain_document_summary": "ORDER 256은 node_3 payload를 집중시킨다.",
            "task_relevant_summary": "사용자 과업과 선택된 재료를 먼저 공급한다.",
        },
        source_trace_id=event.event_id,
    )

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_256",
        user_question="ORDER 256을 설명해줘.",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=CatalogSelectingAdapter(),
        input_ref=[event.event_id],
        source_data_ids=["source:runtime"],
    )

    assert frame.task_contract_status == "recorded"
    assert frame.user_task_summary == "ORDER 256의 핵심을 설명한다."
    assert frame.evidence_requirement == "required"
    assert frame.evidence_roles[0].source_data_id == "summary:order_256"
    assert frame.evidence_roles[0].source_kind == "l3_document_summary"
    assert frame.evidence_roles[0].material_channel == "answer_ready"


def test_node2_task_contract_rejects_unknown_evidence_requirement() -> None:
    frame = Node2AnswerBasisFrame(
        frame_id="node_2:answer_basis_frame",
        turn_id="turn_order_256",
        answer_basis_mode="relative_allowed",
        basis_reason_codes=["user_asked_for_interpretation"],
        mode_selection_reason="사용자 설명 요청이다.",
        mode_selection_reason_info_class="relative",
        task_contract_status="recorded",
        user_task_summary="설명한다.",
        fulfillment_requirements=["직접 설명한다."],
        evidence_requirement="unknown",
        generated_by="LLM:test",
        info_class="relative",
        semantic_judgement_status="ran",
        source_trace_ids=["trace_001"],
        source_data_ids=["source:1"],
    )
    with pytest.raises(ValueError, match="evidence_requirement"):
        validate_node2_answer_basis_frame(frame)


def test_not_required_task_omits_empty_ledgers_and_runtime_sequence() -> None:
    frame = _focused_brief(
        evidence_requirement="not_required",
        evidence_roles=[],
    )
    frame.runtime_tasks = [_runtime_task()]
    frame.document_material_packet_frame_id = "material:ledger"
    frame.document_material_items = [
        Node0DocumentMaterialItem(
            doc_id="doc:1",
            document_name="unused.md",
            was_search_candidate=True,
            source_roles=["search_candidate"],
        )
    ]

    payload = node3_brief_llm_payload(frame)

    assert payload["focus_policy"]["payload_mode"] == "task_focused"
    assert payload["task_contract"]["evidence_requirement"] == "not_required"
    assert "runtime_task_sequence" not in payload
    assert "document_material_packet" not in payload
    assert "reporting_rules" not in payload
    assert payload["supplied_document_contexts"] == []


def test_selected_l3_summary_is_included_without_unselected_process_ledgers() -> None:
    summary_id = "summary:order_256"
    frame = _focused_brief(
        evidence_requirement="required",
        evidence_roles=[
            Node2EvidenceRole(
                source_data_id=summary_id,
                evidence_role="primary_answer_basis",
                role_reason="문서 내용에 직접 대응한다.",
                role_reason_info_class="relative",
                source_label="L3 문서 요약: ORDER_256.md",
                source_kind="l3_document_summary",
                material_channel="answer_ready",
            )
        ],
    )
    frame.source_data_ids.append(summary_id)
    frame.l3_document_summaries = [
        Node3L3DocumentSummaryMaterial(
            document_name="ORDER_256.md",
            source_char_count=100,
            summary_status="ran",
            plain_document_summary="담백 요약",
            task_relevant_summary="과업 맞춤 요약",
            generated_by="LLM:test",
            semantic_judgement_status="ran",
            source_data_id=summary_id,
        )
    ]
    frame.runtime_tasks = [_runtime_task()]
    frame.document_material_packet_frame_id = "material:ledger"

    payload = node3_brief_llm_payload(frame)

    assert payload["l3_document_summaries"]["count"] == 1
    assert (
        payload["l3_document_summaries"]["items"][0]["task_relevant_summary"]
        == "과업 맞춤 요약"
    )
    assert "runtime_task_sequence" not in payload
    assert "document_material_packet" not in payload


def test_runtime_sequence_is_included_only_when_node2_selects_it() -> None:
    frame = _focused_brief(
        evidence_requirement="required",
        evidence_roles=[
            Node2EvidenceRole(
                source_data_id="source:handoff",
                evidence_role="primary_answer_basis",
                role_reason="사용자가 실행 순서를 물었다.",
                role_reason_info_class="relative",
                source_label="현재 턴 실행 과정 장부",
                source_kind="runtime_task_sequence",
                material_channel="process",
            )
        ],
    )
    frame.runtime_tasks = [_runtime_task()]

    payload = node3_brief_llm_payload(frame)

    assert len(payload["runtime_task_sequence"]) == 1
    assert payload["focus_policy"]["runtime_task_sequence_selected"] is True


def test_not_required_task_omits_grounding_block_to_preserve_user_format() -> None:
    frame = _focused_brief(
        evidence_requirement="not_required",
        evidence_roles=[],
    )

    rendered = assemble_node3_report_markdown(
        brief_frame=frame,
        body_markdown="안녕, 오늘도 잘 부탁해.",
    )

    assert rendered == "안녕, 오늘도 잘 부탁해."


def _focused_brief(
    *,
    evidence_requirement: str,
    evidence_roles: list[Node2EvidenceRole],
) -> Node3InputBriefFrame:
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_256",
        user_question="테스트 질문",
        brief_status="ready",
        handoff_frame_id="source:handoff",
        answer_task_contract_status="recorded",
        user_task_summary="사용자 요청을 직접 수행한다.",
        fulfillment_requirements=["사용자 요청에 직접 답한다."],
        evidence_requirement=evidence_requirement,
        answer_basis_mode="relative_allowed",
        basis_reason_codes=["user_asked_for_interpretation"],
        mode_selection_reason="설명 요청이다.",
        mode_selection_reason_info_class="relative",
        evidence_roles=evidence_roles,
        answer_basis_generated_by="LLM:test",
        answer_basis_info_class="relative",
        answer_basis_semantic_judgement_status="ran",
        source_trace_ids=["trace_001"],
        source_data_ids=["source:handoff"],
    )


def _runtime_task() -> Node3BriefRuntimeTask:
    return Node3BriefRuntimeTask(
        step_index=1,
        node_label="node_1",
        mode="routing",
        status="completed",
        model_label="LLM:test",
    )
