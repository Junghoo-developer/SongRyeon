from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MemoryPacketFrom0
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.nodes.l2_query_setter import run_l2_query_planner
from songryeon_core.tools.code_tools import explicit_code_file_paths_from_text


SOURCE_PATH = "songryeon_core/tools/code_tools.py"


class QueryPlanAdapter:
    model_id = "order-260-query-plan"

    def __init__(self, *, query_text: str) -> None:
        self.query_text = query_text

    def complete(self, request: LLMRequest) -> LLMResponse:
        source_data_ids = request.input_payload.get("attribution_source_data_ids")
        if not isinstance(source_data_ids, list) or not source_data_ids:
            source_data_ids = ["L1:goal_frame"]
        payload = {
            "planner_mode": "llm",
            "selected_candidate_id": "candidate_1",
            "candidates": [
                {
                    "candidate_id": "candidate_1",
                    "query_text": self.query_text,
                    "purpose": "Read the exact user-supplied source path.",
                    "expected_signal": "The source file returns an exact text range.",
                    "priority": 1,
                    "target_tool_name": "read_code_file",
                    "read_code_file_start_char": 0,
                    "source_data_ids": source_data_ids,
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload),
            model_id=self.model_id,
            raw=payload,
        )


class CodeOnlyScopeAdapter:
    model_id = "order-260-code-scope"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "tool_scope_mode": "code_only",
            "allowed_tool_groups": ["code_inspection_tools"],
            "required_materials": ["source_code_file"],
            "scope_reason": "The user supplied an exact source file path.",
            "scope_reason_info_class": "mixed",
        }
        return LLMResponse(
            text=json.dumps(payload),
            model_id=self.model_id,
            raw=payload,
        )


def test_code_extracts_only_literal_existing_workspace_paths(tmp_path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "sample.py").write_text("VALUE = 2\n", encoding="utf-8")

    paths = explicit_code_file_paths_from_text(
        root=tmp_path,
        text="pkg\\sample.py 파일을 읽어줘",
    )

    assert paths == ["pkg/sample.py"]


def test_initial_l2_accepts_exact_code_path_from_code_supplied_list() -> None:
    trace_store, data_store, l1_event = _planner_stores()

    run_l2_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_260",
        l1_event=l1_event,
        user_input=f"{SOURCE_PATH} 파일을 읽어줘",
        adapter=QueryPlanAdapter(query_text=SOURCE_PATH),
        source_data_ids=["L1:goal_frame"],
        available_tools=[{"tool_name": "read_code_file", "read_only": True}],
        available_explicit_code_file_paths=[SOURCE_PATH],
    )

    payload = data_store.require_record("L2:query_plan_frame").payload
    assert isinstance(payload, dict)
    assert payload["candidates"][0]["query_text"] == SOURCE_PATH


def test_initial_l2_rejects_descriptive_sentence_in_code_path_field() -> None:
    trace_store, data_store, l1_event = _planner_stores()

    with pytest.raises(ValueError, match="L2 query planner failed: schema_failed"):
        run_l2_query_planner(
            trace_store=trace_store,
            data_store=data_store,
            turn_id="turn_order_260",
            l1_event=l1_event,
            user_input=f"{SOURCE_PATH} 파일을 읽어줘",
            adapter=QueryPlanAdapter(
                query_text=f"{SOURCE_PATH} 파일의 처음부터 12,000자까지 읽기"
            ),
            source_data_ids=["L1:goal_frame"],
            available_tools=[{"tool_name": "read_code_file", "read_only": True}],
            available_explicit_code_file_paths=[SOURCE_PATH],
        )


def test_l_loop_copies_single_explicit_path_after_malformed_llm_plan() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_260_fallback",
        memory_packet=MemoryPacketFrom0(target="L", trace_evidence_ids=[]),
        search_query=f"{SOURCE_PATH} 파일을 직접 읽어줘",
        l_tool_scope_adapter=CodeOnlyScopeAdapter(),
        l2_query_planner_adapter=QueryPlanAdapter(
            query_text=f"{SOURCE_PATH} 파일의 처음부터 읽기"
        ),
        max_tool_calls=2,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    query_payload = data_store.require_record("L2:query_frame").payload
    assert isinstance(query_payload, dict)
    assert query_payload["query_text"] == SOURCE_PATH
    assert query_payload["query_source"] == "code_explicit_path_copy_fallback"
    assert query_payload["target_tool_name"] == "read_code_file"

    tool_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "tool_result:read_code_file"
    ]
    assert len(tool_records) == 1
    tool_payload = tool_records[0].payload
    assert isinstance(tool_payload, dict)
    assert tool_payload["read_status"] == "ok"
    assert tool_payload["file_path"] == SOURCE_PATH
    assert tool_payload["returned_char_count"] > 0


def _planner_stores():
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_260",
        actor="L1",
        event_type="node_output",
        output_ref=["L1:goal_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=l1_event.event_id,
        payload={"macro_goal": "read exact code", "micro_goal": "read exact code"},
    )
    return trace_store, data_store, l1_event
