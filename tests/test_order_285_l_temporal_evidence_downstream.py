from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DocumentContextPackFrame,
    DocumentContextPackIncludedDocument,
    MemoryPacketFrom0,
    MetainfoBoundary,
    Node2AnswerBasisFrame,
    Node2EvidenceRole,
    Node3InputBriefFrame,
    Node3TemporalMetadataMaterial,
    validate_l_loop_return_summary_frame,
    validate_node3_input_brief_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.nodes.node_0_memory_supplier import (
    build_l_loop_return_summary_frame,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.tools.document_context_pack import DOCUMENT_CONTEXT_PACK_DATA_TYPE


class _PayloadAdapter:
    model_id = "order-285-payload-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_temporal_result_reaches_l3_without_becoming_original_material(
    tmp_path: Path,
) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    (document_root / "guide.md").write_text("metadata target", encoding="utf-8")
    trace_store = TraceStore()
    data_store = DataStore()

    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_285_l3",
        memory_packet=MemoryPacketFrom0(target="L"),
        search_query="guide.md 파일의 수정 시각만 확인해줘",
        document_root=document_root,
        code_root=code_root,
        l1_goal_adapter=_PayloadAdapter(_l1_metadata_only_payload()),
        l_tool_scope_adapter=_PayloadAdapter(_scope_payload()),
        l2_query_planner_adapter=_PayloadAdapter(_temporal_l2_payload()),
        l3_result_adapter=_PayloadAdapter(_l3_temporal_match_payload()),
        max_tool_calls=1,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    achievement_record = data_store.require_record(result.achievement_data_ids[-1])
    achievement = achievement_record.payload
    assert isinstance(achievement, dict)
    assert achievement["achievement_status"] == "achieved"
    assert achievement["temporal_requirement_status"] == "required"
    assert achievement["temporal_evidence_requirement_status"] == "satisfied"
    assert achievement["temporal_metadata_inspection_count"] == 1
    assert achievement["successful_temporal_metadata_count"] == 1
    assert achievement["original_material_count"] == 0
    assert achievement["actual_read_doc_count"] == 0
    assert achievement["schema_version"] == "0.7"

    return_summary = build_l_loop_return_summary_frame(
        data_store=data_store,
        turn_id="turn_order_285_l3",
        source_trace_ids=result.source_trace_ids,
        source_data_ids=result.output_data_ids,
    )
    validate_l_loop_return_summary_frame(return_summary)
    assert return_summary.temporal_evidence_requirement_status == "satisfied"
    assert return_summary.temporal_metadata_inspection_count == 1
    assert return_summary.original_material_count == 0


def test_node3_brief_separates_tool_read_context_and_temporal_inspection() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_temporal_result(data_store=data_store, trace_id=trace_id)
    _record_return_summary(data_store=data_store, trace_id=trace_id)
    _record_context_pack(data_store=data_store, trace_id=trace_id)

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_285_brief",
        user_question="guide.md 수정 시각과 원문 노출을 구분해줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["node_2:handoff_frame"],
    )

    assert brief.actual_tool_read_doc_count == 0
    assert brief.supplied_document_context_count == 1
    assert brief.temporal_metadata_inspection_count == 1
    assert brief.successful_temporal_metadata_count == 1
    assert brief.l_temporal_evidence_requirement_status == "satisfied"
    validate_node3_input_brief_frame(brief)

    payload = node3_brief_llm_payload(brief)
    assert payload["temporal_metadata"]["successful_inspection_count"] == 1
    assert (
        payload["temporal_metadata"]["items"][0]["modified_at_utc"]
        == "2026-07-23T00:00:00+00:00"
    )
    assert "tool_result:inspect_source_time_metadata" not in json.dumps(
        payload,
        ensure_ascii=False,
    )
    grounding = build_node3_grounding_block(brief, llm_payload=payload)
    assert "- 실제 read_doc 도구 원문 읽기: 0개" in grounding
    assert "- node_3 공급 문서 context: 1개" in grounding
    assert "- 파일 시간 메타데이터 검사: 1개 / 성공 1개" in grounding


def test_task_focused_payload_exposes_selected_temporal_material_only() -> None:
    material = _temporal_material()
    brief = Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_285_payload",
        user_question="guide.md 수정 시각을 확인해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        answer_task_contract_status="recorded",
        user_task_summary="지정 파일의 수정 시각을 보고한다.",
        fulfillment_requirements=["수정 시각을 정확히 쓴다."],
        evidence_requirement="required",
        evidence_roles=[
            Node2EvidenceRole(
                source_data_id=material.source_data_id,
                evidence_role="primary_answer_basis",
                role_reason="시간 질문에 직접 대응하는 절대근거다.",
                role_reason_info_class="relative",
                source_label="파일 시간 메타데이터: guide.md",
                source_kind="source_time_metadata",
                material_channel="answer_ready",
            )
        ],
        l_temporal_requirement_status="required",
        l_temporal_evidence_requirement_status="satisfied",
        temporal_metadata_inspection_count=1,
        successful_temporal_metadata_count=1,
        temporal_metadata_materials=[material],
        source_data_ids=["node_2:handoff_frame", material.source_data_id],
    )

    payload = node3_brief_llm_payload(brief)

    assert payload["temporal_metadata"]["inspection_count"] == 1
    assert payload["absolute_grounding_facts"][
        "selected_temporal_metadata_inspection_count"
    ] == 1
    assert material.source_data_id not in json.dumps(payload, ensure_ascii=False)


def _l1_metadata_only_payload() -> dict[str, object]:
    return {
        "macro_goal": "지정 파일의 시간 메타데이터 절대근거를 확보한다.",
        "macro_goal_reason": "사용자가 파일 내용이 아닌 수정 시각을 요구했다.",
        "micro_goal": "정확한 파일 좌표의 시간 메타데이터를 검사한다.",
        "micro_goal_reason": "시간 검사 도구에 정확한 좌표가 필요하다.",
        "evidence_requirement_kind": "exact_artifact_lookup",
        "minimum_read_documents": 0,
        "requires_cross_document_analysis": False,
        "randomness_mode": "not_random",
        "l_loop_success_condition": "지정 파일의 성공한 시간 검사 결과가 있다.",
        "temporal_requirement_status": "required",
        "temporal_evidence_goal": "수정 시각과 관측 시각을 확보한다.",
        "temporal_requirement_reason": "사용자가 수정 시각을 직접 요구했다.",
        "artifact_requirement_mode": "not_applicable",
        "artifact_reference_occurrence_indices": [],
        "artifact_requirement_reason": "경로는 시간 검사 좌표이며 원문 내용 계약이 아니다.",
        "requested_search_top_k": 1,
        "requested_max_tool_calls": 1,
        "requested_max_read_doc_calls": 0,
        "requested_max_query_attempts": 1,
        "budget_request_reason": "시간 도구 1회면 충분하다.",
    }


def _scope_payload() -> dict[str, object]:
    return {
        "tool_scope_mode": "document_only",
        "allowed_tool_groups": ["document_tools"],
        "required_materials": ["project_document"],
        "scope_reason": "문서 시간 메타데이터가 필요하다.",
        "scope_reason_info_class": "mixed",
    }


def _temporal_l2_payload() -> dict[str, object]:
    return {
        "planner_mode": "llm",
        "selected_candidate_id": "L2:query_candidate_0001",
        "candidates": [
            {
                "candidate_id": "L2:query_candidate_0001",
                "query_text": "guide.md",
                "purpose": "정확한 파일 좌표의 시간 메타데이터를 검사한다.",
                "expected_signal": "수정 시각과 관측 시각 절대정보",
                "priority": 1,
                "target_tool_name": "inspect_source_time_metadata",
                "source_scope": "document",
                "read_code_file_start_char": 0,
                "source_data_ids": ["L1:goal_frame"],
            }
        ],
    }


def _l3_temporal_match_payload() -> dict[str, object]:
    return {
        "semantic_goal_match_status": "matched",
        "semantic_goal_match_reason": "지정 파일의 시간 검사 결과가 질문에 대응한다.",
        "semantic_evidence_bindings": [
            {
                "material_ref": "TIME_MATERIAL_0001",
                "evidence_excerpt_ref": "TIME_MATERIAL_0001:EXCERPT_0001",
            }
        ],
    }


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_285_brief",
        actor="test",
        event_type="node_output",
        output_ref=["node_2:handoff_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="node_2:handoff_frame",
        data_type="test:handoff",
        source_trace_id=event.event_id,
        payload={"frame_id": "node_2:handoff_frame"},
    )
    return trace_store, data_store, event.event_id


def _record_temporal_result(*, data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="tool_result:inspect_source_time_metadata:001",
        data_type="tool_result:inspect_source_time_metadata",
        source_trace_id=trace_id,
        payload=asdict(_temporal_material()) | {"root_path": "C:/workspace"},
    )


def _temporal_material() -> Node3TemporalMetadataMaterial:
    return Node3TemporalMetadataMaterial(
        source_data_id="tool_result:inspect_source_time_metadata:001",
        source_scope="document",
        requested_source_path="guide.md",
        relative_path="guide.md",
        inspection_status="ok",
        exists=True,
        observed_at_utc="2026-07-23T01:00:00+00:00",
        modified_at_utc="2026-07-23T00:00:00+00:00",
        size_bytes=12,
        content_hash_sha256="a" * 64,
        source_kind="internal_document",
        generated_by="CODE:SOURCE_TIME_METADATA_INSPECTOR",
        info_class="absolute",
        semantic_judgement_status="not_run",
    )


def _record_return_summary(*, data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L:return_summary_frame",
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L:return_summary_frame",
            "turn_id": "turn_order_285_brief",
            "l_loop_task_status": "achieved",
            "failure_level": "none",
            "l3_goal_match_status": "matched",
            "l3_semantic_goal_match_status": "matched",
            "l3_semantic_execution_status": "ran",
            "l3_semantic_failure_type": "none",
            "l3_semantic_failure_reason": "CODE_STATUS:none",
            "evidence_acquisition_status": "none",
            "original_material_count": 0,
            "original_material_requirement_status": "not_required",
            "temporal_requirement_status": "required",
            "temporal_evidence_requirement_status": "satisfied",
            "temporal_metadata_inspection_count": 1,
            "successful_temporal_metadata_count": 1,
            "temporal_metadata_result_data_ids": [
                "tool_result:inspect_source_time_metadata:001"
            ],
            "remaining_query_attempts": 0,
            "remaining_read_doc_calls": 1,
            "actual_read_doc_count": 0,
            "read_doc_ids": [],
        },
    )


def _record_context_pack(*, data_store: DataStore, trace_id: str) -> None:
    included = DocumentContextPackIncludedDocument(
        doc_id="docs/guide.md",
        document_name="guide.md",
        char_count=len("metadata target"),
        rank_index=1,
        selection_basis="explicit_reference",
        text="metadata target",
        source_data_id="source:guide",
    )
    frame = DocumentContextPackFrame(
        frame_id="L:document_context_pack_frame",
        turn_id="turn_order_285_brief",
        max_document_context_chars=1000,
        budget_unit="chars",
        whole_document_only=True,
        strict_rank_order=True,
        included_documents=[included],
        included_document_count=1,
        included_total_chars=included.char_count,
        source_trace_ids=[trace_id],
        source_data_ids=["L:return_summary_frame"],
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=DOCUMENT_CONTEXT_PACK_DATA_TYPE,
        source_trace_id=trace_id,
        payload=asdict(frame),
    )
