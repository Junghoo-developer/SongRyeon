from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.l2_query_setter import run_l2_query_planner
from songryeon_core.nodes.l_tool_scope import (
    filter_available_tools_for_scope,
    record_l_tool_budget_partition,
    run_l_tool_scope_planner,
)


class PayloadAdapter:
    model_id = "order-134-payload-adapter"

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


def test_l_tool_scope_llm_selects_document_and_code_and_budget_splits() -> None:
    trace_store, data_store, l1_event = _seed_l_scope_stores()
    scope_adapter = PayloadAdapter(_scope_payload("document_and_code"))

    scope_trace_id, scope_data_id, scope_frame = run_l_tool_scope_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_134",
        l1_event=l1_event,
        user_query="ORDER_133과 실제 source code를 둘 다 확인해줘",
        goal_data_id="L1:goal_frame",
        budget_plan_data_id="L:budget_plan_frame",
        tool_catalog_data_id="tool_catalog:turn_order_134",
        available_tools=_all_tool_catalog_items(),
        adapter=scope_adapter,
    )

    assert scope_data_id == "L:tool_scope_frame"
    assert scope_frame.generated_by == "LLM:order-134-payload-adapter"
    assert scope_frame.info_class == "mixed"
    assert scope_frame.tool_scope_mode == "document_and_code"
    assert scope_frame.allowed_tool_groups == ["document_tools", "code_inspection_tools"]

    _, _, partition = record_l_tool_budget_partition(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_134",
        tool_scope_frame=scope_frame,
        tool_scope_trace_id=scope_trace_id,
        budget_plan_data_id="L:budget_plan_frame",
        budget_plan_trace_id=l1_event.event_id,
    )

    assert partition.document_tool_call_budget > 0
    assert partition.code_tool_call_budget > 0
    assert partition.document_query_budget > 0
    assert partition.code_query_budget > 0
    assert partition.document_read_budget > 0
    assert partition.code_read_budget > 0
    assert partition.generated_by == "CODE:L_TOOL_BUDGET_PARTITION_POLICY"
    assert partition.semantic_judgement_status == "not_run"


def test_l_tool_scope_fallback_is_explicit_failed_document_only() -> None:
    trace_store, data_store, l1_event = _seed_l_scope_stores()

    _, _, frame = run_l_tool_scope_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_134",
        l1_event=l1_event,
        user_query="anything",
        goal_data_id="L1:goal_frame",
        budget_plan_data_id="L:budget_plan_frame",
        tool_catalog_data_id="tool_catalog:turn_order_134",
        available_tools=_all_tool_catalog_items(),
        adapter=None,
    )

    assert frame.tool_scope_mode == "document_only"
    assert frame.allowed_tool_groups == ["document_tools"]
    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.info_class == "absolute_status"
    assert frame.semantic_judgement_status == "failed"
    assert frame.scope_failure_type == "adapter_missing"


def test_tool_catalog_is_filtered_by_scope_groups() -> None:
    scope = _scope_frame_dict(
        mode="code_only",
        groups=["code_inspection_tools"],
        materials=["source_code_file"],
    )
    trace_store, data_store, l1_event = _seed_l_scope_stores()
    adapter = PayloadAdapter(scope)
    _, _, frame = run_l_tool_scope_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_134",
        l1_event=l1_event,
        user_query="actual code only",
        goal_data_id="L1:goal_frame",
        budget_plan_data_id="L:budget_plan_frame",
        tool_catalog_data_id="tool_catalog:turn_order_134",
        available_tools=_all_tool_catalog_items(),
        adapter=adapter,
    )

    filtered = filter_available_tools_for_scope(_all_tool_catalog_items(), frame)
    filtered_names = {str(item["tool_name"]) for item in filtered}

    assert filtered_names == {"list_code_files", "search_code", "read_code_file"}


def test_l2_receives_filtered_tools_and_scope_payload() -> None:
    trace_store, data_store, l1_event = _seed_l_scope_stores()
    planner_adapter = PayloadAdapter(
        {
            "planner_mode": "llm",
            "selected_candidate_id": "L2:query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:query_candidate_0001",
                    "query_text": "songryeon_core/tools/code_tools.py",
                    "purpose": "scope가 허용한 code inspection tool로 source file을 읽는다.",
                    "expected_signal": "read_code_file source text",
                    "priority": 1,
                    "target_tool_name": "read_code_file",
                    "source_data_ids": ["L1:goal_frame"],
                }
            ],
        }
    )
    available_tools = [
        item for item in _all_tool_catalog_items() if item["tool_name"] in {"read_code_file"}
    ]

    run_l2_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_134",
        l1_event=l1_event,
        user_input="source file 읽기",
        adapter=planner_adapter,
        source_data_ids=["L1:goal_frame", "L:tool_scope_frame", "L:tool_budget_partition_frame"],
        available_tools=available_tools,
        l_tool_scope=_scope_frame_dict(
            mode="code_only",
            groups=["code_inspection_tools"],
            materials=["source_code_file"],
        ),
        budget_partition={"code_read_budget": 1},
    )

    assert planner_adapter.last_input_payload is not None
    assert planner_adapter.last_input_payload["l_tool_scope"]["tool_scope_mode"] == "code_only"
    available_names = {
        str(item["tool_name"])
        for item in planner_adapter.last_input_payload["available_tools"]
        if isinstance(item, dict)
    }
    assert available_names == {"read_code_file"}
    plan_payload = data_store.require_record("L2:query_plan_frame").payload
    assert isinstance(plan_payload, dict)
    assert plan_payload["candidates"][0]["target_tool_name"] == "read_code_file"


def test_l2_rejects_candidate_outside_filtered_scope() -> None:
    trace_store, data_store, l1_event = _seed_l_scope_stores()
    planner_adapter = PayloadAdapter(
        {
            "planner_mode": "llm",
            "selected_candidate_id": "L2:query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:query_candidate_0001",
                    "query_text": "문서 검색",
                    "purpose": "허용되지 않은 document tool을 고른 잘못된 후보.",
                    "expected_signal": "search docs result",
                    "priority": 1,
                    "target_tool_name": "search_docs",
                    "source_data_ids": ["L1:goal_frame"],
                }
            ],
        }
    )
    available_tools = [
        item for item in _all_tool_catalog_items() if item["tool_name"] == "read_code_file"
    ]

    with pytest.raises(ValueError, match="schema_failed"):
        run_l2_query_planner(
            trace_store=trace_store,
            data_store=data_store,
            turn_id="turn_order_134",
            l1_event=l1_event,
            user_input="source file 읽기",
            adapter=planner_adapter,
            source_data_ids=["L1:goal_frame", "L:tool_scope_frame"],
            available_tools=available_tools,
            l_tool_scope=_scope_frame_dict(
                mode="code_only",
                groups=["code_inspection_tools"],
                materials=["source_code_file"],
            ),
            budget_partition={"code_read_budget": 1},
        )


def _seed_l_scope_stores() -> tuple[TraceStore, DataStore, object]:
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_134",
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
            "frame_id": "L1:goal_frame",
            "turn_id": "turn_order_134",
            "macro_goal": "read order and source code",
            "macro_goal_reason": "LLM selected mixed source bundle.",
            "micro_goal": "prepare tool scope",
            "micro_goal_reason": "tool groups must be explicit before L2",
            "goal_source": "llm_l_route",
            "target_loop": "L",
            "evidence_requirement_kind": "multi_doc_relationship",
            "minimum_read_documents": 2,
            "requires_cross_document_analysis": True,
            "randomness_mode": "not_random",
            "l_loop_success_condition": "order and source materials are available",
        },
    )
    data_store.create_record(
        data_id="L:budget_plan_frame",
        data_type="node_output:l_loop_budget_plan_frame",
        source_trace_id=l1_event.event_id,
        payload={
            "frame_id": "L:budget_plan_frame",
            "turn_id": "turn_order_134",
            "approved_max_tool_calls": 6,
            "approved_max_query_attempts": 4,
            "approved_max_read_doc_calls": 2,
        },
    )
    data_store.create_record(
        data_id="tool_catalog:turn_order_134",
        data_type="tool_catalog",
        source_trace_id=l1_event.event_id,
        payload={"tools": _all_tool_catalog_items()},
    )
    return trace_store, data_store, l1_event


def _scope_payload(mode: str) -> dict[str, object]:
    if mode == "document_and_code":
        return _scope_frame_dict(
            mode="document_and_code",
            groups=["document_tools", "code_inspection_tools"],
            materials=["order_document", "source_code_file", "code_search_result"],
        )
    raise ValueError(f"unsupported test mode: {mode}")


def _scope_frame_dict(
    *,
    mode: str,
    groups: list[str],
    materials: list[str],
) -> dict[str, object]:
    return {
        "tool_scope_mode": mode,
        "allowed_tool_groups": groups,
        "required_materials": materials,
        "scope_reason": "test adapter supplied explicit scope payload.",
        "scope_reason_info_class": "mixed",
    }


def _all_tool_catalog_items() -> list[dict[str, object]]:
    return [
        {"tool_name": "list_docs", "read_only": True},
        {"tool_name": "read_doc", "read_only": True},
        {"tool_name": "read_artifact", "read_only": True},
        {"tool_name": "search_docs", "read_only": True},
        {"tool_name": "list_code_files", "read_only": True},
        {"tool_name": "search_code", "read_only": True},
        {"tool_name": "read_code_file", "read_only": True},
    ]
