from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.l3_result_keeper import (
    L3_SEMANTIC_EVIDENCE_EXCERPT_MAX_CHARS,
    _L3SemanticMaterial,
    _l3_semantic_evidence_bindings_from_payload,
    _l3_semantic_evidence_candidates,
    _validate_l3_semantic_payload,
    run_l3_result_keeper,
)
from songryeon_core.nodes.node_0_memory_supplier import (
    build_l_loop_return_summary_frame,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)


class UnknownExcerptRefL3Adapter:
    model_id = "order-272-unknown-excerpt-ref"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "L3 Result Keeper v0" in request.prompt:
            preview = request.input_payload["read_document_previews"][0]
            payload = {
                "semantic_goal_match_status": "matched",
                "semantic_goal_match_reason": "문서가 사용자 질문과 맞는다.",
                "semantic_evidence_bindings": [
                    {
                        "material_ref": preview["material_ref"],
                        "evidence_excerpt_ref": "DOC_MATERIAL_0001:EXCERPT_9999",
                    }
                ],
            }
        else:
            payload = {
                "plain_document_summary": "L3 실패 전파 테스트 문서다.",
                "task_relevant_summary": "원문 확보와 의미 검사 실패를 분리한다.",
                "summary_limit_note": "",
            }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_fixed_excerpt_candidates_are_stable_bounded_and_lossless() -> None:
    text = "가" * 401 + "\n" + "나" * 403
    material = _L3SemanticMaterial(
        material_ref="DOC_MATERIAL_0001",
        source_data_id="tool_result:read_doc:001",
        text=text,
    )

    first = _l3_semantic_evidence_candidates([material])
    second = _l3_semantic_evidence_candidates([material])

    assert first == second
    assert "".join(candidate.text for candidate in first) == text
    assert all(
        0 < len(candidate.text) <= L3_SEMANTIC_EVIDENCE_EXCERPT_MAX_CHARS
        for candidate in first
    )
    assert [candidate.evidence_excerpt_ref for candidate in first] == [
        "DOC_MATERIAL_0001:EXCERPT_0001",
        "DOC_MATERIAL_0001:EXCERPT_0002",
        "DOC_MATERIAL_0001:EXCERPT_0003",
    ]


def test_selected_excerpt_ref_is_resolved_to_exact_code_owned_text() -> None:
    material = _L3SemanticMaterial(
        material_ref="CODE_MATERIAL_0001",
        source_data_id="tool_result:read_code_file:001",
        text="def visible():\n    return 1\n",
    )
    materials = {material.material_ref: material}
    candidates = _l3_semantic_evidence_candidates([material])
    candidate_map = {
        candidate.evidence_excerpt_ref: candidate for candidate in candidates
    }
    payload = {
        "semantic_goal_match_status": "matched",
        "semantic_goal_match_reason": "함수 원문이 질문에 맞는다.",
        "semantic_evidence_bindings": [
            {
                "material_ref": material.material_ref,
                "evidence_excerpt_ref": candidates[0].evidence_excerpt_ref,
            }
        ],
    }

    _validate_l3_semantic_payload(
        payload,
        semantic_material_by_ref=materials,
        semantic_evidence_candidate_by_ref=candidate_map,
    )
    bindings = _l3_semantic_evidence_bindings_from_payload(
        payload=payload,
        semantic_material_by_ref=materials,
        semantic_evidence_candidate_by_ref=candidate_map,
    )

    assert len(bindings) == 1
    assert bindings[0].evidence_excerpt_ref == candidates[0].evidence_excerpt_ref
    assert bindings[0].evidence_excerpt == material.text
    assert bindings[0].source_data_id == material.source_data_id


def test_multiple_distinct_excerpt_refs_from_one_material_are_allowed() -> None:
    material = _L3SemanticMaterial(
        material_ref="DOC_MATERIAL_0001",
        source_data_id="tool_result:read_doc:001",
        text="가" * 450,
    )
    materials = {material.material_ref: material}
    candidates = _l3_semantic_evidence_candidates([material])
    candidate_map = {
        candidate.evidence_excerpt_ref: candidate for candidate in candidates
    }
    payload = {
        "semantic_goal_match_status": "matched",
        "semantic_goal_match_reason": "한 문서의 두 구간이 함께 질문을 뒷받침한다.",
        "semantic_evidence_bindings": [
            {
                "material_ref": material.material_ref,
                "evidence_excerpt_ref": candidate.evidence_excerpt_ref,
            }
            for candidate in candidates
        ],
    }

    _validate_l3_semantic_payload(
        payload,
        semantic_material_by_ref=materials,
        semantic_evidence_candidate_by_ref=candidate_map,
    )
    bindings = _l3_semantic_evidence_bindings_from_payload(
        payload=payload,
        semantic_material_by_ref=materials,
        semantic_evidence_candidate_by_ref=candidate_map,
    )

    assert len(bindings) == 2
    assert "".join(binding.evidence_excerpt for binding in bindings) == material.text


def test_l3_schema_failure_reaches_return_summary_and_node3_brief() -> None:
    trace_store, data_store, l1_event, l2_event, tool_trace_id = _l3_stores()
    source_data_ids = [
        "L1:goal_frame",
        "L2:query_frame",
        "tool_result:read_doc:001",
        "tool_use_budget:L",
        "L:control:final",
    ]

    run_l3_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_272",
        l1_event=l1_event,
        l2_event=l2_event,
        extra_input_trace_ids=[tool_trace_id],
        extra_input_data_ids=source_data_ids,
        final_control_data_id="L:control:final",
        user_query="L3 의미 실패가 숨지 않는지 확인해줘",
        adapter=UnknownExcerptRefL3Adapter(),
    )

    achievement = data_store.require_record("L3:achievement_frame").payload
    assert isinstance(achievement, dict)
    assert achievement["llm_semantic_judgement_status"] == "not_run"
    assert achievement["llm_semantic_execution_status"] == "failed"
    assert achievement["llm_semantic_failure_type"] == "schema_failed"
    assert "evidence_excerpt_ref was not supplied" in achievement[
        "llm_semantic_failure_reason"
    ]
    assert achievement["evidence_acquisition_status"] == "original_material_acquired"

    return_frame = build_l_loop_return_summary_frame(
        data_store=data_store,
        turn_id="turn_order_272",
        source_trace_ids=[l1_event.event_id, l2_event.event_id, tool_trace_id],
        source_data_ids=[
            *source_data_ids,
            *achievement["source_data_ids"],
            "L3:achievement_frame",
        ],
    )
    assert return_frame.failure_level == "l3_semantic_failed"
    assert return_frame.recommended_next_route_for_node1 == "2"
    assert return_frame.l3_semantic_execution_status == "failed"
    assert return_frame.l3_semantic_failure_type == "schema_failed"

    return_event = trace_store.create_event(
        turn_id="turn_order_272",
        actor="node_0",
        event_type="node_output",
        output_ref=[return_frame.frame_id, "source:handoff"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=return_frame.frame_id,
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=return_event.event_id,
        payload=asdict(return_frame),
    )
    data_store.create_record(
        data_id="source:handoff",
        data_type="node_output:node_2_handoff_frame",
        source_trace_id=return_event.event_id,
        payload={"frame_id": "source:handoff"},
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_272",
        user_question="L3 의미 실패가 숨지 않는지 확인해줘",
        handoff_frame_id="source:handoff",
        boundary=MetainfoBoundary(),
        input_trace_ids=[return_event.event_id],
        source_data_ids=["source:handoff", return_frame.frame_id],
    )
    payload = node3_brief_llm_payload(brief)

    assert brief.l3_semantic_execution_status == "failed"
    assert brief.l3_semantic_failure_type == "schema_failed"
    assert (
        brief.l_loop_result_attitude_hint
        == "l_loop_original_material_acquired_l3_semantic_failed"
    )
    assert payload["l_loop_result"]["l3_semantic_execution_status"] == "failed"
    assert payload["l_loop_result"]["l3_semantic_failure_type"] == "schema_failed"


def test_l3_prompt_uses_only_valid_status_and_excerpt_ref_selection() -> None:
    prompt = Path("songryeon_core/prompts/l3_result_keeper_v0.md").read_text(
        encoding="utf-8"
    )

    assert '"evidence_excerpt_ref"' in prompt
    assert '"evidence_excerpt"' not in prompt
    assert "use `partial` and `failed`" not in prompt


def _l3_stores() -> tuple[TraceStore, DataStore, object, object, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_272",
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
            "macro_goal": "읽은 문서가 질문에 맞는지 확인한다.",
            "micro_goal": "문서 원문 한 개를 확보한다.",
            "minimum_read_documents": 1,
            "evidence_requirement_kind": "single_doc",
            "l_loop_success_condition": "문서 원문 한 개가 있어야 한다.",
        },
    )
    l2_event = trace_store.create_event(
        turn_id="turn_order_272",
        actor="L2",
        event_type="node_output",
        output_ref=["L2:query_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        source_trace_id=l2_event.event_id,
        payload={"query_text": "ORDER_272 L3 실패 전파"},
    )
    tool_event = trace_store.create_event(
        turn_id="turn_order_272",
        actor="tool:read_doc",
        event_type="tool_result",
        output_ref=["tool_result:read_doc:001"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="tool_result:read_doc:001",
        data_type="tool_result:read_doc",
        source_trace_id=tool_event.event_id,
        payload={
            "doc_id": "ORDER_272_TEST.md",
            "text": "L3 의미 검사가 실패해도 실제 읽은 원문은 보존한다.",
            "char_count": 31,
        },
    )
    data_store.create_record(
        data_id="tool_use_budget:L",
        data_type="tool_use_budget",
        source_trace_id=tool_event.event_id,
        payload={
            "max_tool_calls": 2,
            "tool_call_count": 1,
            "max_read_doc_calls": 1,
            "read_doc_count": 1,
            "max_query_attempts": 1,
            "query_count": 0,
            "max_read_code_file_calls": 0,
            "stop_reason": "completed",
        },
    )
    data_store.create_record(
        data_id="L:control:final",
        data_type="node_output:L_loop_control_frame",
        source_trace_id=tool_event.event_id,
        payload={"decision": "stop_success"},
    )
    return trace_store, data_store, l1_event, l2_event, tool_event.event_id
