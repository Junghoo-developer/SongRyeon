from __future__ import annotations

import json
from pathlib import Path

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import LToolScopeFrame, MemoryPacketFrom0
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop import (
    _fallback_l2_tool_for_available_tools,
    run_l_loop,
)
from songryeon_core.nodes.l2_query_setter import run_l2_query_planner
from songryeon_core.nodes.l_tool_scope import filter_available_tools_for_scope
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools.source_time_tools import (
    explicit_source_time_paths_from_text,
)


class _PayloadAdapter:
    model_id = "order-284-payload-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_input_payload = request.input_payload
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_temporal_capability_survives_l_tool_scope_group_filter() -> None:
    scope = LToolScopeFrame(
        frame_id="L:tool_scope_frame",
        turn_id="turn_order_284_scope",
        tool_scope_mode="document_only",
        allowed_tool_groups=["document_tools"],
        required_materials=["project_document"],
        scope_reason="문서 범위를 선택했다.",
        scope_reason_info_class="mixed",
    )
    available_tools = [
        {"tool_name": "search_docs", "capabilities": ["document_search"]},
        {"tool_name": "read_code_file", "capabilities": ["code_original_read"]},
        {
            "tool_name": "inspect_source_time_metadata",
            "capabilities": ["temporal_metadata", "exact_source_path"],
        },
    ]

    filtered = filter_available_tools_for_scope(available_tools, scope)

    assert [item["tool_name"] for item in filtered] == [
        "search_docs",
        "inspect_source_time_metadata",
    ]


def test_exact_temporal_paths_are_code_owned_literal_coordinates(tmp_path: Path) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    (document_root / "guide.md").write_text("guide", encoding="utf-8")
    (code_root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    paths = explicit_source_time_paths_from_text(
        document_root=document_root,
        code_root=code_root,
        text="docs/guide.md와 module.py의 시각을 확인해줘",
    )

    assert paths == [
        {"source_scope": "document", "source_path": "guide.md"},
        {"source_scope": "code", "source_path": "module.py"},
    ]


def test_l2_accepts_only_required_temporal_candidate_from_available_pair() -> None:
    trace_store, data_store, l1_event = _seed_l1_goal(
        temporal_requirement_status="required"
    )
    adapter = _PayloadAdapter(_temporal_l2_payload(path="guide.md", scope="document"))

    run_l2_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_284_plan",
        l1_event=l1_event,
        user_input="guide.md 수정 시각 확인",
        adapter=adapter,
        source_data_ids=["L1:goal_frame"],
        available_tools=[
            {"tool_name": "inspect_source_time_metadata", "read_only": True}
        ],
        available_temporal_source_paths=[
            {"source_scope": "document", "source_path": "guide.md"}
        ],
    )

    plan = data_store.require_record("L2:query_plan_frame").payload
    assert isinstance(plan, dict)
    candidate = plan["candidates"][0]
    assert candidate["target_tool_name"] == "inspect_source_time_metadata"
    assert candidate["source_scope"] == "document"
    assert adapter.last_input_payload is not None
    assert adapter.last_input_payload["available_temporal_source_paths"] == [
        {"source_scope": "document", "source_path": "guide.md"}
    ]


@pytest.mark.parametrize(
    ("temporal_status", "path", "scope"),
    [
        ("required", "invented.md", "document"),
        ("required", "guide.md", "code"),
        ("not_required", "guide.md", "document"),
    ],
)
def test_l2_rejects_temporal_candidate_outside_l1_and_code_boundaries(
    temporal_status: str,
    path: str,
    scope: str,
) -> None:
    trace_store, data_store, l1_event = _seed_l1_goal(
        temporal_requirement_status=temporal_status
    )

    with pytest.raises(ValueError, match="schema_failed"):
        run_l2_query_planner(
            trace_store=trace_store,
            data_store=data_store,
            turn_id="turn_order_284_reject",
            l1_event=l1_event,
            user_input="guide.md 수정 시각 확인",
            adapter=_PayloadAdapter(_temporal_l2_payload(path=path, scope=scope)),
            source_data_ids=["L1:goal_frame"],
            available_tools=[
                {"tool_name": "inspect_source_time_metadata", "read_only": True}
            ],
            available_temporal_source_paths=[
                {"source_scope": "document", "source_path": "guide.md"}
            ],
        )


def test_temporal_tool_executes_without_becoming_original_material(
    tmp_path: Path,
) -> None:
    document_root = tmp_path / "docs"
    code_root = tmp_path / "code"
    document_root.mkdir()
    code_root.mkdir()
    (document_root / "guide.md").write_text("time metadata target", encoding="utf-8")
    trace_store = TraceStore()
    data_store = DataStore()

    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_284_execute",
        memory_packet=MemoryPacketFrom0(target="L"),
        search_query="guide.md 파일의 수정 시각 근거를 확인해줘",
        document_root=document_root,
        code_root=code_root,
        l1_goal_adapter=_PayloadAdapter(_l1_payload("required")),
        l_tool_scope_adapter=_PayloadAdapter(_scope_payload()),
        l2_query_planner_adapter=_PayloadAdapter(
            _temporal_l2_payload(path="guide.md", scope="document")
        ),
        max_tool_calls=1,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    assert result.final_control_decision == "stop_success"
    assert len(result.temporal_metadata_result_data_ids) == 1
    temporal_id = result.temporal_metadata_result_data_ids[0]
    temporal_record = data_store.require_record(temporal_id)
    assert temporal_record.data_type == "tool_result:inspect_source_time_metadata"
    assert temporal_record.payload["inspection_status"] == "ok"
    assert not any(
        record.data_type.startswith(
            ("tool_result:read_doc", "tool_result:read_artifact", "tool_result:read_code_file")
        )
        for record in data_store.list_records()
    )
    achievement = _latest_payload(data_store, "node_output:L3_achievement_frame")
    assert achievement["actual_read_doc_count"] == 0
    assert achievement["actual_read_code_file_count"] == 0
    assert achievement["original_material_count"] == 0
    rendered = render_runtime_view(
        {"data_records": data_store.to_records()},
        user_input="guide.md 파일의 수정 시각 근거를 확인해줘",
    )
    assert "시간 메타데이터 [CODE 절대정보" in rendered
    assert "원문 읽기와 분리" in rendered


def test_code_fallback_never_auto_selects_temporal_tool() -> None:
    selected = _fallback_l2_tool_for_available_tools(
        [
            {
                "tool_name": "inspect_source_time_metadata",
                "capabilities": ["temporal_metadata"],
            },
            {"tool_name": "search_docs", "capabilities": ["document_search"]},
        ]
    )

    assert selected == "search_docs"


def _seed_l1_goal(
    *,
    temporal_requirement_status: str,
) -> tuple[TraceStore, DataStore, object]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_284_plan",
        actor="L1",
        event_type="node_output",
        output_ref=["L1:goal_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=event.event_id,
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": "turn_order_284_plan",
            **_l1_payload(temporal_requirement_status),
        },
    )
    return trace_store, data_store, event


def _l1_payload(temporal_requirement_status: str) -> dict[str, object]:
    return {
        "macro_goal": "시간 근거를 확보한다.",
        "macro_goal_reason": "사용자가 지정 파일의 시각을 요구했다.",
        "micro_goal": "정확한 파일의 시간 메타데이터를 검사한다.",
        "micro_goal_reason": "파일 좌표가 사용자 입력에 있다.",
        "evidence_requirement_kind": "single_doc_lookup",
        "minimum_read_documents": 1,
        "requires_cross_document_analysis": False,
        "randomness_mode": "not_random",
        "l_loop_success_condition": "지정 파일의 시간 메타데이터가 기록된다.",
        "temporal_requirement_status": temporal_requirement_status,
        "temporal_evidence_goal": "지정 파일의 관측·수정 시각을 확보한다.",
        "temporal_requirement_reason": "사용자가 시간 근거를 요구했다.",
        "artifact_requirement_mode": "not_applicable",
        "artifact_reference_occurrence_indices": [],
        "artifact_requirement_reason": "문서 원문 artifact 요구가 아니다.",
        "requested_search_top_k": 1,
        "requested_max_tool_calls": 1,
        "requested_max_read_doc_calls": 1,
        "requested_max_query_attempts": 1,
        "budget_request_reason": "정확한 시간 도구 1회가 필요하다.",
    }


def _scope_payload() -> dict[str, object]:
    return {
        "tool_scope_mode": "document_only",
        "allowed_tool_groups": ["document_tools"],
        "required_materials": ["project_document"],
        "scope_reason": "지정된 문서 좌표의 메타데이터가 필요하다.",
        "scope_reason_info_class": "mixed",
    }


def _temporal_l2_payload(*, path: str, scope: str) -> dict[str, object]:
    return {
        "planner_mode": "llm",
        "selected_candidate_id": "L2:query_candidate_0001",
        "candidates": [
            {
                "candidate_id": "L2:query_candidate_0001",
                "query_text": path,
                "purpose": "L1이 요구한 시간 근거를 정확한 파일 좌표에서 읽는다.",
                "expected_signal": "수정 시각, 관측 시각, hash 절대정보",
                "priority": 1,
                "target_tool_name": "inspect_source_time_metadata",
                "source_scope": scope,
                "read_code_file_start_char": 0,
                "source_data_ids": ["L1:goal_frame"],
            }
        ],
    }


def _latest_payload(data_store: DataStore, data_type: str) -> dict[str, object]:
    matches = [
        record for record in data_store.list_records() if record.data_type == data_type
    ]
    assert matches
    payload = matches[-1].payload
    assert isinstance(payload, dict)
    return payload
