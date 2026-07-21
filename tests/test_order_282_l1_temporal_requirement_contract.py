from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MemoryPacketFrom0
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.nodes.l1_goal_setter import (
    _validate_l1_goal_payload,
    run_l1_goal_setter,
)
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.runtime.dry_run import run_dry_turn


class _TemporalPayloadAdapter:
    model_id = "order-282-temporal-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_l1_records_llm_temporal_judgement_with_code_copied_basis() -> None:
    user_query = "가장 최근에 바뀐 발주서 원문을 확인해줘"
    payload = _valid_l1_payload()
    payload["temporal_requirement_basis_text"] = "LLM이 위조한 기준 문자열"
    trace_store = TraceStore()
    data_store = DataStore()

    run_l1_goal_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_282_success",
        memory_packet=MemoryPacketFrom0(target="L"),
        user_query=user_query,
        adapter=_TemporalPayloadAdapter(payload),
    )

    goal = data_store.require_record("L1:goal_frame").payload
    assert isinstance(goal, dict)
    assert goal["temporal_requirement_status"] == "required"
    assert goal["temporal_requirement_basis_text"] == user_query
    assert goal["temporal_requirement_info_class"] == "relative"
    assert goal["temporal_requirement_semantic_judgement_status"] == "ran"


def test_missing_temporal_output_closes_as_honest_code_status() -> None:
    payload = _valid_l1_payload()
    payload.pop("temporal_requirement_reason")
    user_query = "최근 변경 여부를 확인해줘"
    trace_store = TraceStore()
    data_store = DataStore()

    run_l1_goal_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_282_fallback",
        memory_packet=MemoryPacketFrom0(target="L"),
        user_query=user_query,
        adapter=_TemporalPayloadAdapter(payload),
    )

    goal = data_store.require_record("L1:goal_frame").payload
    assert isinstance(goal, dict)
    assert goal["goal_generation_source"] == "RULE_STUB"
    assert goal["temporal_requirement_status"] == "uncertain"
    assert goal["temporal_evidence_goal"] == (
        "CODE_STATUS:temporal_evidence_goal_not_set"
    )
    assert goal["temporal_requirement_reason"] == (
        "CODE_STATUS:l1_temporal_requirement_judgement_not_run"
    )
    assert goal["temporal_requirement_basis_text"] == user_query
    assert goal["temporal_requirement_info_class"] == "absolute_status"
    assert goal["temporal_requirement_semantic_judgement_status"] == "failed"


def test_temporal_requirement_enum_is_closed() -> None:
    payload = _valid_l1_payload()
    payload["temporal_requirement_status"] = "latest_by_code"

    with pytest.raises(ValueError, match="temporal_requirement_status"):
        _validate_l1_goal_payload(payload)


def test_runtime_view_displays_temporal_requirement_boundary() -> None:
    payload = _valid_l1_payload()
    payload.update(
        {
            "goal_generation_source": "LLM:test",
            "llm_goal_judgement_status": "ran",
            "temporal_requirement_basis_text": "최근 문서를 확인해줘",
            "temporal_requirement_info_class": "relative",
            "temporal_requirement_semantic_judgement_status": "ran",
        }
    )
    rendered = render_runtime_view(
        {
            "status": "ok",
            "data_records": [
                {
                    "data_id": "L1:goal_frame",
                    "data_type": "node_output:L1_goal_frame",
                    "payload": payload,
                }
            ],
        },
        user_input="최근 문서를 확인해줘",
    )

    assert "시간 근거 요구: status=required" in rendered
    assert "basis=current_user_query_copy" in rendered
    assert "info_class=relative / semantic=ran" in rendered
    assert "시간 근거 목표:" in rendered
    assert "판단 이유:" in rendered


def test_dry_run_summary_exposes_temporal_requirement_contract() -> None:
    result = run_dry_turn(
        "시간 계약 요약 필드 확인",
        force_l_route=True,
        l1_goal_adapter=SongRyeonAllNodesFakeLLMAdapter(),
        max_tool_calls=1,
        search_top_k=1,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    assert result["l1_temporal_requirement_status"] == "not_required"
    assert result["l1_temporal_requirement_info_class"] == "relative"
    assert (
        result["l1_temporal_requirement_semantic_judgement_status"] == "ran"
    )


def _valid_l1_payload() -> dict[str, object]:
    return {
        "macro_goal": "시간 근거가 있는 문서 원문을 확보한다.",
        "macro_goal_reason": "사용자가 최근 변경 자료를 요구했다.",
        "micro_goal": "시간 근거 후보를 찾을 준비를 한다.",
        "micro_goal_reason": "원문을 읽기 전에 후보가 필요하다.",
        "evidence_requirement_kind": "single_doc_lookup",
        "minimum_read_documents": 1,
        "requires_cross_document_analysis": False,
        "randomness_mode": "not_random",
        "l_loop_success_condition": "시간 근거와 원문이 함께 확보된다.",
        "temporal_requirement_status": "required",
        "temporal_evidence_goal": "자료의 관측 또는 수정 시각 근거를 확보한다.",
        "temporal_requirement_reason": "현재 질문이 최근 자료를 요구한다.",
        "artifact_requirement_mode": "not_applicable",
        "artifact_reference_occurrence_indices": [],
        "artifact_requirement_reason": "명시 artifact가 없다.",
        "requested_search_top_k": 3,
        "requested_max_tool_calls": 2,
        "requested_max_read_doc_calls": 1,
        "requested_max_query_attempts": 1,
        "budget_request_reason": "후보 검색과 원문 열람이 필요하다.",
    }
