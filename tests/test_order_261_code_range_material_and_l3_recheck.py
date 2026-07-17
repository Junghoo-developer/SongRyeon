from __future__ import annotations

import json
import sys

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    Node2EvidenceRole,
    Node3BriefDocument,
    Node3CodeReadBoundary,
    Node3InputBriefFrame,
    validate_node3_input_brief_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.qwen_adapter import (
    DEFAULT_QWEN_NUM_CTX,
    QwenLocalHTTPAdapter,
)
from songryeon_core.nodes.l3_result_keeper import (
    l3_revision_achievement_frame_data_id,
    run_l3_revision_result_keeper,
)
from songryeon_core.nodes.node_2_metainfo_boundary import (
    _answer_material_record_metadata,
    run_node2_answer_basis_selection,
)
from songryeon_core.nodes.node_2_handoff import (
    _build_source_code_outline,
    node3_brief_llm_payload,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block


TURN_ID = "turn_order_261"
SOURCE_PATH = "songryeon_core/nodes/sample_large.py"
FIRST_CODE_ID = "tool_result:read_code_file:order_261:first"
SECOND_CODE_ID = "tool_result:read_code_file:order_261:second"


def test_qwen_direct_ollama_call_uses_explicit_long_context(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeOllamaModule:
        @staticmethod
        def chat(**kwargs):
            captured.update(kwargs)
            return {"message": {"content": "{}"}}

    monkeypatch.setitem(sys.modules, "ollama", FakeOllamaModule())
    adapter = QwenLocalHTTPAdapter()
    adapter.complete(
        LLMRequest(
            prompt="test prompt",
            input_payload={"long_material": "x" * 33000},
            response_format="json",
        )
    )

    assert captured["options"] == {
        "temperature": 0,
        "num_ctx": DEFAULT_QWEN_NUM_CTX,
    }


class RecordingSemanticAdapter:
    model_id = "order-261-semantic-adapter"

    def __init__(self, *, status: str) -> None:
        self.status = status
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        semantic_evidence_bindings: list[dict[str, str]] = []
        if self.status == "matched":
            preview = request.input_payload["read_code_file_previews"][0]
            semantic_evidence_bindings.append(
                {
                    "material_ref": preview["material_ref"],
                    "evidence_excerpt": preview["text_preview"][:40],
                }
            )
        payload = {
            "semantic_goal_match_status": self.status,
            "semantic_goal_match_reason": (
                "두 코드 구간을 함께 보면 사용자가 요청한 함수 본문을 확인할 수 있다."
                if self.status == "matched"
                else "현재 코드 구간만으로는 요청한 함수 설명이 충분하지 않다."
            ),
            "semantic_evidence_bindings": semantic_evidence_bindings,
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class RepairingRequiredCodeEvidenceAdapter:
    model_id = "order-261-answer-basis-repair-adapter"

    def __init__(self, *, drift_task_on_repair: bool = False) -> None:
        self.requests: list[LLMRequest] = []
        self.drift_task_on_repair = drift_task_on_repair

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        available = request.input_payload["available_evidence_sources"]
        catalog = request.input_payload["answer_material_catalog"]
        assert isinstance(available, list)
        assert isinstance(catalog, list)
        code_row = next(
            item
            for item in catalog
            if isinstance(item, dict) and item.get("source_kind") == "read_code_file"
        )
        generic_row = next(
            item
            for item in available
            if isinstance(item, dict) and item.get("material_channel") == "generic"
        )
        selected_ref = (
            generic_row["evidence_ref"]
            if len(self.requests) == 1
            else code_row["evidence_ref"]
        )
        payload = {
            "answer_basis_mode": "absolute_first",
            "basis_reason_codes": ["code_verified_fact_required"],
            "mode_selection_reason": "사용자가 지정한 코드 원문을 직접 확인해야 한다.",
            "mode_selection_reason_info_class": "relative",
            "user_task_summary": "지정한 함수의 코드 구조를 설명한다.",
            "fulfillment_requirements": ["읽은 코드 원문을 근거로 설명한다."],
            "evidence_requirement": "required",
            "evidence_roles": [
                {
                    "evidence_ref": selected_ref,
                    "evidence_role": "supporting_context",
                    "role_reason": "현재 선택한 자료를 설명 근거로 사용한다.",
                    "role_reason_info_class": "relative",
                }
            ],
        }
        if len(self.requests) == 2 and self.drift_task_on_repair:
            payload["user_task_summary"] = "JSON 오류를 설명하는 다른 과업으로 바꾼다."
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_partial_python_range_is_not_reported_as_a_parse_failure() -> None:
    outline = _build_source_code_outline(
        file_path=SOURCE_PATH,
        text="    return target_value\n",
        source_data_id=SECOND_CODE_ID,
        range_start_char=12000,
        range_end_char_exclusive=12024,
        total_char_count=25000,
    )

    assert outline.analysis_scope == "partial_range"
    assert outline.parse_status == "not_run_partial_range"
    assert outline.parse_error_type == ""
    assert outline.top_level_symbols == []


def test_complete_python_file_with_utf8_bom_is_parsed_from_an_analysis_copy() -> None:
    source_text = "\ufeffdef visible_function():\n    return 1\n"
    outline = _build_source_code_outline(
        file_path="complete_sample.py",
        text=source_text,
        source_data_id="tool_result:read_code_file:order_261:complete",
        range_start_char=0,
        range_end_char_exclusive=len(source_text),
        total_char_count=len(source_text),
    )

    assert outline.analysis_scope == "complete_file"
    assert outline.parse_status == "parsed"
    assert outline.utf8_bom_present is True
    assert outline.public_function_names == ["visible_function"]


def test_node2_code_catalog_exposes_exact_range_without_copying_source_text() -> None:
    target_text = "def target_function():\n    return 'visible to node_2'\n"
    source_text = "x" * 829 + target_text
    metadata = _answer_material_record_metadata(
        data_id=SECOND_CODE_ID,
        data_type="tool_result:read_code_file",
        payload={
            "file_path": SOURCE_PATH,
            "text": source_text,
            "range_start_char": 12000,
            "range_end_char_exclusive": 12000 + len(source_text),
            "total_char_count": 25000,
            "truncated_before": True,
            "truncated_after": True,
        },
    )

    assert metadata is not None
    preview = str(metadata["material_preview"])
    assert "range=[12000," in preview
    assert "truncated_before=True" in preview
    assert f"returned_text_chars={len(source_text)}" in preview
    assert "exact_text_delivery=node_3_after_evidence_selection" in preview
    assert target_text not in preview


def test_node2_repairs_required_contract_that_selected_no_answer_ready_material() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id=TURN_ID,
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:boundary", "source:handoff", SECOND_CODE_ID],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=event.event_id,
            payload={"turn_id": TURN_ID},
        )
    target_text = "def target_function():\n    return 'selected after schema repair'\n"
    _record_code_result(
        data_store=data_store,
        data_id=SECOND_CODE_ID,
        trace_id=event.event_id,
        text="x" * 829 + target_text,
        start=12000,
        total=25000,
    )
    adapter = RepairingRequiredCodeEvidenceAdapter()

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        user_question="target_function의 구조를 코드 원문으로 설명해줘.",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=adapter,
        input_ref=[event.event_id],
        source_data_ids=["source:runtime"],
    )

    assert len(adapter.requests) == 2
    first_input = adapter.requests[0].input_payload
    assert all(
        "material_preview" not in item
        for item in first_input["available_evidence_sources"]
    )
    serialized_first_input = json.dumps(first_input, ensure_ascii=False)
    assert target_text not in serialized_first_input
    assert first_input["answer_material_catalog"][0]["source_kind"] == "read_code_file"
    assert first_input["answer_ready_evidence_refs"]
    repair_request = adapter.requests[1].input_payload["schema_repair_request"]
    assert "must select at least one answer_ready" in repair_request["validation_error"]
    assert repair_request["answer_ready_evidence_refs"]
    assert frame.generated_by == f"LLM:{adapter.model_id}"
    assert frame.evidence_requirement == "required"
    assert frame.evidence_roles[0].source_data_id == SECOND_CODE_ID
    assert frame.evidence_roles[0].material_channel == "answer_ready"


def test_node2_rejects_schema_repair_that_changes_the_locked_user_task() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id=TURN_ID,
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:boundary", "source:handoff", SECOND_CODE_ID],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=event.event_id,
            payload={"turn_id": TURN_ID},
        )
    _record_code_result(
        data_store=data_store,
        data_id=SECOND_CODE_ID,
        trace_id=event.event_id,
        text="def target_function():\n    return 1\n",
        start=12000,
        total=25000,
    )

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        user_question="target_function의 구조를 코드 원문으로 설명해줘.",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=RepairingRequiredCodeEvidenceAdapter(drift_task_on_repair=True),
        input_ref=[event.event_id],
        source_data_ids=["source:runtime"],
    )

    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.answer_basis_failure_type == "schema_failed"
    assert "must preserve locked field: user_task_summary" in (
        frame.answer_basis_validation_error
    )


def test_task_focused_payload_joins_code_text_to_ranges_without_legacy_duplication() -> None:
    first_text = "first-range-only-marker"
    second_text = "second-range-target-marker"
    total_char_count = 100
    first_boundary = _boundary(
        source_data_id=FIRST_CODE_ID,
        text=first_text,
        start=0,
        total=total_char_count,
    )
    second_boundary = _boundary(
        source_data_id=SECOND_CODE_ID,
        text=second_text,
        start=len(first_text),
        total=total_char_count,
    )
    frame = Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id=TURN_ID,
        user_question=f"{SOURCE_PATH}의 target 함수를 설명해줘.",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        read_documents=[
            Node3BriefDocument(
                document_name=SOURCE_PATH,
                char_count=len(first_text),
                text=first_text,
                source_data_id=FIRST_CODE_ID,
            ),
            Node3BriefDocument(
                document_name=SOURCE_PATH,
                char_count=len(second_text),
                text=second_text,
                source_data_id=SECOND_CODE_ID,
            ),
        ],
        actual_tool_read_code_file_count=1,
        actual_tool_read_code_file_paths=[SOURCE_PATH],
        code_read_boundaries=[first_boundary, second_boundary],
        max_read_code_file_calls=5,
        remaining_read_code_file_calls=3,
        supplied_document_context_count=2,
        supplied_source_code_context_count=2,
        source_code_outlines=[
            _outline_for_boundary(first_boundary, first_text),
            _outline_for_boundary(second_boundary, second_text),
        ],
        llm_raw_document_text_count=2,
        answer_task_contract_status="recorded",
        user_task_summary="두 코드 구간을 이어서 target 함수를 설명한다.",
        fulfillment_requirements=["두 코드 구간의 범위를 보존한다."],
        evidence_requirement="required",
        answer_basis_mode="absolute_first",
        basis_reason_codes=["code_verified_fact_required"],
        mode_selection_reason="코드 원문과 문자 구간을 직접 확인해야 한다.",
        mode_selection_reason_info_class="relative",
            evidence_roles=[
                Node2EvidenceRole(
                    source_data_id="L3:achievement_frame",
                    evidence_role="primary_answer_basis",
                role_reason="현재 L 결과가 읽은 코드 구간을 묶는다.",
                role_reason_info_class="relative",
                source_label="L3 코드 근거 결과",
                    source_kind="l3_result",
                    material_channel="answer_ready",
                ),
                Node2EvidenceRole(
                    source_data_id=FIRST_CODE_ID,
                    evidence_role="supporting_context",
                    role_reason="첫 번째 코드 구간 원문을 직접 사용한다.",
                    role_reason_info_class="relative",
                    source_label="첫 번째 코드 구간",
                    source_kind="read_code_file",
                    material_channel="answer_ready",
                ),
                Node2EvidenceRole(
                    source_data_id=SECOND_CODE_ID,
                    evidence_role="supporting_context",
                    role_reason="두 번째 코드 구간 원문을 직접 사용한다.",
                    role_reason_info_class="relative",
                    source_label="두 번째 코드 구간",
                    source_kind="read_code_file",
                    material_channel="answer_ready",
                ),
            ],
        answer_basis_generated_by="LLM:test",
        answer_basis_info_class="relative",
        answer_basis_semantic_judgement_status="ran",
        source_trace_ids=["trace_order_261"],
        source_data_ids=[
            "node_2:handoff_frame",
            "L3:achievement_frame",
            FIRST_CODE_ID,
            SECOND_CODE_ID,
        ],
    )
    validate_node3_input_brief_frame(frame)

    payload = node3_brief_llm_payload(frame)
    materials = payload["source_code_range_materials"]
    assert isinstance(materials, dict)
    assert materials["count"] == 2
    assert materials["raw_text_count"] == 2
    assert payload["supplied_document_contexts"] == []
    assert payload["read_documents"] == []
    assert payload["absolute_grounding_facts"]["llm_raw_document_text_count"] == 0
    assert payload["absolute_grounding_facts"]["llm_raw_code_range_text_count"] == 2
    assert [item["range_start_char"] for item in materials["items"]] == [
        0,
        len(first_text),
    ]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert serialized.count(first_text) == 1
    assert serialized.count(second_text) == 1

    grounding = build_node3_grounding_block(frame, llm_payload=payload)
    assert "node_3 LLM 원문 text: 2개" in grounding
    assert "node_3 LLM 코드 구간 text: 2개" in grounding


@pytest.mark.parametrize(
    ("semantic_status", "expected_achievement"),
    [("matched", "achieved"), ("partial", "partial")],
)
def test_revision_l3_rechecks_all_current_code_ranges_before_closing(
    semantic_status: str,
    expected_achievement: str,
) -> None:
    trace_store, data_store, trace_id = _revision_stores()
    adapter = RecordingSemanticAdapter(status=semantic_status)

    run_l3_revision_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=TURN_ID,
        attempt_index=1,
        revision_query_frame_data_id="L2:revision_query_frame:0001",
        revision_tool_source_trace_ids=[trace_id],
        revision_tool_source_data_ids=[SECOND_CODE_ID],
        semantic_material_source_data_ids=[FIRST_CODE_ID, SECOND_CODE_ID],
        user_query=f"{SOURCE_PATH}의 target 함수를 설명해줘.",
        adapter=adapter,
    )

    achievement = data_store.require_record(
        l3_revision_achievement_frame_data_id(1)
    ).payload
    assert isinstance(achievement, dict)
    assert achievement["llm_semantic_judgement_status"] == "ran"
    assert achievement["semantic_goal_match_status"] == semantic_status
    assert achievement["achievement_status"] == expected_achievement
    assert achievement["actual_read_code_file_count"] == 1
    assert achievement["read_code_file_paths"] == [SOURCE_PATH]
    if semantic_status == "matched":
        assert "CODE:REVISION_SEMANTIC_MATCH_COMPLETION_POLICY" in achievement[
            "achievement_generation_source"
        ]

    assert len(adapter.requests) == 1
    previews = adapter.requests[0].input_payload["read_code_file_previews"]
    assert isinstance(previews, list)
    assert {item["range_start_char"] for item in previews} == {0, 12000}
    assert all(item["analysis_scope"] == "partial_range" for item in previews)
    assert any("target_function" in item["text_preview"] for item in previews)


def _boundary(
    *,
    source_data_id: str,
    text: str,
    start: int,
    total: int,
) -> Node3CodeReadBoundary:
    end = start + len(text)
    return Node3CodeReadBoundary(
        file_path=SOURCE_PATH,
        requested_start_char=start,
        range_start_char=start,
        range_end_char_exclusive=end,
        returned_char_count=len(text),
        total_char_count=total,
        truncated=True,
        truncated_before=start > 0,
        truncated_after=end < total,
        read_status="ok",
        source_data_id=source_data_id,
    )


def _outline_for_boundary(
    boundary: Node3CodeReadBoundary,
    text: str,
):
    return _build_source_code_outline(
        file_path=boundary.file_path,
        text=text,
        source_data_id=boundary.source_data_id,
        range_start_char=boundary.range_start_char,
        range_end_char_exclusive=boundary.range_end_char_exclusive,
        total_char_count=boundary.total_char_count,
    )


def _revision_stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id=TURN_ID,
        actor="test",
        event_type="node_output",
        output_ref=[FIRST_CODE_ID, SECOND_CODE_ID],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=event.event_id,
        payload={
            "macro_goal": "요청한 코드 파일의 target 함수를 설명한다.",
            "micro_goal": "연속 코드 구간에서 target 함수 본문을 확보한다.",
            "evidence_requirement_kind": "exact_artifact_lookup",
            "minimum_read_documents": 1,
            "required_materials": ["source_code_file"],
            "l_loop_success_condition": "target function source is available",
        },
    )
    data_store.create_record(
        data_id="L2:revision_query_frame:0001",
        data_type="node_output:L2_revision_query_frame",
        source_trace_id=event.event_id,
        payload={
            "query_text": SOURCE_PATH,
            "target_tool_name": "read_code_file",
            "read_code_file_start_char": 12000,
        },
    )
    _record_code_result(
        data_store=data_store,
        data_id=FIRST_CODE_ID,
        trace_id=event.event_id,
        text="prefix material before the requested function",
        start=0,
        total=24040,
    )
    _record_code_result(
        data_store=data_store,
        data_id=SECOND_CODE_ID,
        trace_id=event.event_id,
        text="def target_function():\n    return 'found in revision'\n",
        start=12000,
        total=24040,
    )
    return trace_store, data_store, event.event_id


def _record_code_result(
    *,
    data_store: DataStore,
    data_id: str,
    trace_id: str,
    text: str,
    start: int,
    total: int,
) -> None:
    end = start + len(text)
    data_store.create_record(
        data_id=data_id,
        data_type="tool_result:read_code_file",
        source_trace_id=trace_id,
        payload={
            "file_path": SOURCE_PATH,
            "read_status": "ok",
            "text": text,
            "requested_start_char": start,
            "range_start_char": start,
            "range_end_char_exclusive": end,
            "returned_char_count": len(text),
            "total_char_count": total,
            "char_count": total,
            "truncated": True,
            "truncated_before": start > 0,
            "truncated_after": end < total,
        },
    )
