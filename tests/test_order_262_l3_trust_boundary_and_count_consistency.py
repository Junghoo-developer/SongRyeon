from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    Node2EvidenceRole,
    Node3BriefDocument,
    Node3CodeReadBoundary,
    Node3InputBriefFrame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.l3_result_keeper import (
    _L3SemanticMaterial,
    _validate_l3_semantic_payload,
    run_l3_result_keeper,
)
from songryeon_core.nodes.node_0_memory_supplier import (
    build_l_loop_return_summary_frame,
)
from songryeon_core.nodes.node_2_handoff import (
    NODE3_CODE_RANGE_RAW_TEXT_BUDGET_CHARS,
    _node3_code_range_material_bundle,
    node3_brief_llm_payload,
)
from songryeon_core.nodes.node_2_metainfo_boundary import (
    _answer_basis_repair_locked_fields,
    _validate_answer_basis_repair_locked_fields,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block


class RecordingPartialL3Adapter:
    model_id = "order-262-recording-l3"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        payload = {
            "semantic_goal_match_status": "partial",
            "semantic_goal_match_reason": "현재 실행이 공급한 코드 구간만으로는 충분하지 않다.",
            "semantic_evidence_bindings": [],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_l3_matched_rejects_unknown_ref_and_non_verbatim_excerpt() -> None:
    materials = {
        "CODE_MATERIAL_0001": _L3SemanticMaterial(
            material_ref="CODE_MATERIAL_0001",
            source_data_id="L:run:0002:tool_result:read_code_file:001",
            text="def visible_function():\n    return 1\n",
        )
    }

    with pytest.raises(ValueError, match="material_ref was not supplied"):
        _validate_l3_semantic_payload(
            {
                "semantic_goal_match_status": "matched",
                "semantic_goal_match_reason": "보이는 함수가 요청에 맞는다.",
                "semantic_evidence_bindings": [
                    {
                        "material_ref": "CODE_MATERIAL_9999",
                        "evidence_excerpt": "def visible_function",
                    }
                ],
            },
            semantic_material_by_ref=materials,
        )

    with pytest.raises(ValueError, match="copied exactly"):
        _validate_l3_semantic_payload(
            {
                "semantic_goal_match_status": "matched",
                "semantic_goal_match_reason": "보이는 함수가 요청에 맞는다.",
                "semantic_evidence_bindings": [
                    {
                        "material_ref": "CODE_MATERIAL_0001",
                        "evidence_excerpt": "원문에는 없는 요약 문장",
                    }
                ],
            },
            semantic_material_by_ref=materials,
        )


def test_l3_only_sees_current_input_data_ids() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_262_scope",
        actor="L1",
        event_type="node_output",
        output_ref=["L:run:0002:L1:goal_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L:run:0002:L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=l1_event.event_id,
        payload={
            "macro_goal": "현재 실행의 코드 원문을 확인한다.",
            "micro_goal": "current.py를 읽는다.",
            "minimum_read_documents": 1,
            "evidence_requirement_kind": "exact_artifact_lookup",
            "l_loop_success_condition": "current.py 원문이 있어야 한다.",
        },
    )
    l2_event = trace_store.create_event(
        turn_id="turn_order_262_scope",
        actor="L2",
        event_type="node_output",
        output_ref=["L:run:0002:L2:query_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L:run:0002:L2:query_frame",
        data_type="node_output:L2_query_frame",
        source_trace_id=l2_event.event_id,
        payload={"query_text": "current.py"},
    )
    tool_event = trace_store.create_event(
        turn_id="turn_order_262_scope",
        actor="tool:read_code_file",
        event_type="tool_result",
        output_ref=[
            "L:run:0001:tool_result:read_code_file:001",
            "L:run:0002:tool_result:read_code_file:001",
        ],
        schema_status="passed",
    )
    for data_id, file_path, marker in (
        (
            "L:run:0001:tool_result:read_code_file:001",
            "old.py",
            "OLD_RUN_MUST_NOT_APPEAR",
        ),
        (
            "L:run:0002:tool_result:read_code_file:001",
            "current.py",
            "CURRENT_RUN_VISIBLE",
        ),
    ):
        text = f"# {marker}\n"
        data_store.create_record(
            data_id=data_id,
            data_type="tool_result:read_code_file",
            source_trace_id=tool_event.event_id,
            payload={
                "read_status": "ok",
                "file_path": file_path,
                "text": text,
                "char_count": len(text),
                "line_count": 1,
                "range_start_char": 0,
                "range_end_char_exclusive": len(text),
                "total_char_count": len(text),
            },
        )

    adapter = RecordingPartialL3Adapter()
    run_l3_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_262_scope",
        l1_event=l1_event,
        l2_event=l2_event,
        extra_input_trace_ids=[tool_event.event_id],
        extra_input_data_ids=[
            "L:run:0002:L1:goal_frame",
            "L:run:0002:L2:query_frame",
            "L:run:0002:tool_result:read_code_file:001",
        ],
        user_query="current.py 원문을 확인해줘",
        adapter=adapter,
        preserved_frame_data_id="L:run:0002:L3:preserved_info_frame",
        achievement_frame_data_id="L:run:0002:L3:achievement_frame",
        target_goal_data_id="L:run:0002:L1:goal_frame",
    )

    previews = adapter.requests[0].input_payload["read_code_file_previews"]
    assert [item["file_path"] for item in previews] == ["current.py"]
    assert "OLD_RUN_MUST_NOT_APPEAR" not in json.dumps(previews)
    achievement = data_store.require_record(
        "L:run:0002:L3:achievement_frame"
    ).payload
    assert achievement["read_code_file_paths"] == ["current.py"]


def test_node3_code_budget_keeps_whole_ranges_and_records_exclusions() -> None:
    materials = [
        {
            "material_ref": f"CODE_RANGE_{index:04d}",
            "file_path": f"file_{index}.py",
            "range_start_char": (index - 1) * 10000,
            "range_end_char_exclusive": index * 10000,
            "returned_char_count": 10000,
            "text_payload_status": "included",
            "text_char_count": 10000,
            "text": str(index) * 10000,
        }
        for index in range(1, 4)
    ]

    bundle = _node3_code_range_material_bundle(materials)

    assert bundle["raw_text_budget_chars"] == NODE3_CODE_RANGE_RAW_TEXT_BUDGET_CHARS
    assert bundle["raw_text_chars"] == 20000
    assert [item["material_ref"] for item in bundle["items"]] == [
        "CODE_RANGE_0001",
        "CODE_RANGE_0002",
    ]
    assert bundle["excluded_count"] == 1
    excluded = bundle["excluded_items"][0]
    assert excluded["material_ref"] == "CODE_RANGE_0003"
    assert excluded["range_start_char"] == 20000
    assert excluded["range_end_char_exclusive"] == 30000
    assert "text" not in excluded
    assert excluded["text_char_count"] == 10000


def test_l3_status_selection_alone_does_not_inject_code_text() -> None:
    frame = _minimal_code_brief(
        evidence_roles=[
            Node2EvidenceRole(
                source_data_id="L3:achievement_frame",
                evidence_role="primary_answer_basis",
                role_reason="L3 상태를 답변 근거로 선택한다.",
                role_reason_info_class="relative",
                source_label="L3 결과",
                source_kind="l3_result",
                material_channel="answer_ready",
            )
        ]
    )

    payload = node3_brief_llm_payload(frame)

    assert payload["source_code_range_materials"]["count"] == 0
    assert payload["source_code_range_materials"]["raw_text_count"] == 0


def test_latest_revision_achievement_drives_l_return_summary() -> None:
    data_store = DataStore()
    trace_id = "trace_order_262_revision"
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L1:goal_frame",
            "minimum_read_documents": 1,
            "evidence_requirement_kind": "exact_artifact_lookup",
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L3:achievement_frame",
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "partial",
            "read_doc_ids": [],
            "search_result_doc_ids": ["docs/target.md"],
        },
    )
    data_store.create_record(
        data_id="L3:revision_achievement_frame:0001",
        data_type="node_output:L3_revision_achievement_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L3:revision_achievement_frame:0001",
            "achievement_status": "achieved",
            "goal_match_status": "matched",
            "semantic_goal_match_status": "matched",
            "read_doc_ids": ["docs/target.md"],
            "search_result_doc_ids": ["docs/target.md"],
        },
    )
    data_store.create_record(
        data_id="L:budget:latest",
        data_type="tool_use_budget",
        source_trace_id=trace_id,
        payload={
            "max_tool_calls": 3,
            "tool_call_count": 2,
            "max_read_doc_calls": 2,
            "read_doc_count": 1,
            "max_query_attempts": 2,
            "query_count": 1,
            "stop_reason": "completed",
        },
    )

    frame = build_l_loop_return_summary_frame(
        data_store=data_store,
        turn_id="turn_order_262_revision",
        source_trace_ids=[trace_id],
        source_data_ids=[
            "L1:goal_frame",
            "L3:achievement_frame",
            "L3:revision_achievement_frame:0001",
            "L:budget:latest",
        ],
    )

    assert frame.l_loop_task_status == "achieved"
    assert frame.l3_goal_match_status == "matched"
    assert frame.l3_semantic_goal_match_status == "matched"
    assert frame.read_doc_ids == ["docs/target.md"]


def test_node2_repair_locks_valid_task_contract_for_any_schema_error() -> None:
    failed_payload = {
        "answer_basis_mode": "absolute_first",
        "basis_reason_codes": ["code_verified_fact_required"],
        "mode_selection_reason": "코드 원문이 필요하다.",
        "mode_selection_reason_info_class": "relative",
        "user_task_summary": "지정한 함수의 실제 동작을 설명한다.",
        "fulfillment_requirements": ["코드 원문을 근거로 설명한다."],
        "evidence_requirement": "required",
        "evidence_roles": [{"evidence_ref": "UNKNOWN_REF"}],
    }
    locked = _answer_basis_repair_locked_fields(
        failed_payload=failed_payload,
        failure_reason="Node2 evidence_ref must exist in available_evidence_sources",
    )

    assert locked == {
        "user_task_summary": "지정한 함수의 실제 동작을 설명한다.",
        "fulfillment_requirements": ["코드 원문을 근거로 설명한다."],
        "evidence_requirement": "required",
    }
    repaired_payload = dict(failed_payload)
    repaired_payload["user_task_summary"] = "다른 과업으로 바꾼다."
    with pytest.raises(ValueError, match="must preserve locked field"):
        _validate_answer_basis_repair_locked_fields(
            payload=repaired_payload,
            locked_fields=locked,
        )


def test_grounding_splits_unique_code_files_from_call_ranges() -> None:
    frame = _minimal_code_brief(
        evidence_roles=[],
        duplicate_boundary=True,
        task_contract_status="not_recorded",
    )

    grounding = build_node3_grounding_block(frame)

    assert "실제 read_code_file 고유 파일: 1개" in grounding
    assert "실제 read_code_file 호출/구간: 2개" in grounding


def _minimal_code_brief(
    *,
    evidence_roles: list[Node2EvidenceRole],
    duplicate_boundary: bool = False,
    task_contract_status: str = "recorded",
) -> Node3InputBriefFrame:
    text = "def visible_function():\n    return 1\n"
    source_data_id = "tool_result:read_code_file:001"
    boundary = Node3CodeReadBoundary(
        source_data_id=source_data_id,
        file_path="sample.py",
        requested_start_char=0,
        range_start_char=0,
        range_end_char_exclusive=len(text),
        returned_char_count=len(text),
        total_char_count=len(text),
        truncated=False,
        truncated_before=False,
        truncated_after=False,
        read_status="ok",
    )
    boundaries = [boundary]
    if duplicate_boundary:
        boundaries.append(
            Node3CodeReadBoundary(
                source_data_id="tool_result:read_code_file:002",
                file_path="sample.py",
                requested_start_char=len(text),
                range_start_char=len(text),
                range_end_char_exclusive=len(text) * 2,
                returned_char_count=len(text),
                total_char_count=len(text) * 2,
                truncated=True,
                truncated_before=True,
                truncated_after=False,
                read_status="ok",
            )
        )
    source_data_ids = [
        "node_2:handoff_frame",
        "L3:achievement_frame",
        source_data_id,
        *( ["tool_result:read_code_file:002"] if duplicate_boundary else [] ),
    ]
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_262_brief",
        user_question="sample.py의 함수를 설명해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        read_documents=[
            Node3BriefDocument(
                document_name="sample.py",
                char_count=len(text),
                text=text,
                source_data_id=source_data_id,
            )
        ],
        actual_tool_read_code_file_count=1,
        actual_tool_read_code_file_paths=["sample.py"],
        code_read_boundaries=boundaries,
        supplied_document_context_count=1,
        supplied_source_code_context_count=1,
        answer_task_contract_status=task_contract_status,
        user_task_summary=(
            "sample.py의 함수를 설명한다."
            if task_contract_status == "recorded"
            else ""
        ),
        fulfillment_requirements=(
            ["코드 원문을 사용한다."]
            if task_contract_status == "recorded"
            else []
        ),
        evidence_requirement=(
            "required" if task_contract_status == "recorded" else "not_recorded"
        ),
        answer_basis_mode="absolute_first",
        basis_reason_codes=["code_verified_fact_required"],
        mode_selection_reason="코드 원문 확인이 필요하다.",
        mode_selection_reason_info_class="relative",
        evidence_roles=evidence_roles,
        answer_basis_generated_by="LLM:test",
        answer_basis_info_class="relative",
        answer_basis_semantic_judgement_status="ran",
        source_trace_ids=["trace_order_262_brief"],
        source_data_ids=source_data_ids,
    )
