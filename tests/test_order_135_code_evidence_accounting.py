from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MemoryPacketFrom0, MetainfoBoundary, ZeroState
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.nodes.node_0_memory_supplier import record_l_loop_return_summary_for_node1
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block


class CodeExactL1Adapter:
    model_id = "order-135-code-l1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "macro_goal": "songryeon_core/tools/code_tools.py source file을 읽어 node_3가 답할 수 있게 한다.",
            "macro_goal_reason": "사용자가 실제 코드 원문 기준 답변을 요구했다.",
            "micro_goal": "songryeon_core/tools/code_tools.py를 read_code_file로 읽는다.",
            "micro_goal_reason": "정확한 source path가 주어졌다.",
            "evidence_requirement_kind": "exact_artifact_lookup",
            "minimum_read_documents": 1,
            "requires_cross_document_analysis": False,
            "randomness_mode": "not_random",
            "l_loop_success_condition": "requested source file text is read",
            "requested_search_top_k": 1,
            "requested_max_tool_calls": 1,
            "requested_max_read_doc_calls": 1,
            "requested_max_query_attempts": 1,
            "budget_request_reason": "one exact source read is enough",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class CodeOnlyScopeAdapter:
    model_id = "order-135-code-scope"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "tool_scope_mode": "code_only",
            "allowed_tool_groups": ["code_inspection_tools"],
            "required_materials": ["source_code_file"],
            "scope_reason": "source-code file evidence is required.",
            "scope_reason_info_class": "mixed",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class ReadCodeFileL2Adapter:
    model_id = "order-135-code-l2"

    def complete(self, request: LLMRequest) -> LLMResponse:
        source_data_ids = request.input_payload.get("attribution_source_data_ids")
        if not isinstance(source_data_ids, list) or not source_data_ids:
            source_data_ids = ["L1:goal_frame"]
        payload = {
            "planner_mode": "llm",
            "selected_candidate_id": "L2:query_candidate_0001",
            "candidates": [
                {
                    "candidate_id": "L2:query_candidate_0001",
                    "query_text": "songryeon_core/tools/code_tools.py",
                    "purpose": "read the exact source file requested by the user.",
                    "expected_signal": "read_code_file returns source text.",
                    "priority": 1,
                    "target_tool_name": "read_code_file",
                    "source_data_ids": source_data_ids,
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_read_code_file_counts_as_source_code_evidence_without_becoming_read_doc() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    memory_packet = MemoryPacketFrom0(target="L", trace_evidence_ids=[])
    user_query = (
        "songryeon_core/tools/code_tools.py 파일을 직접 읽고 read-only code inspection 기능을 정리해줘."
    )

    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_135",
        memory_packet=memory_packet,
        search_query=user_query,
        l1_goal_adapter=CodeExactL1Adapter(),
        l_tool_scope_adapter=CodeOnlyScopeAdapter(),
        l2_query_planner_adapter=ReadCodeFileL2Adapter(),
        max_tool_calls=3,
        max_query_attempts=2,
        max_read_doc_calls=1,
    )

    achievement_payload = data_store.require_record("L3:achievement_frame").payload
    assert isinstance(achievement_payload, dict)
    assert achievement_payload["achievement_status"] == "achieved"
    assert achievement_payload["goal_match_status"] == "matched"
    assert achievement_payload["goal_match_reason"] == (
        "CODE_STATUS:requested_source_code_file_read_code_file_matched"
    )
    assert achievement_payload["read_doc_ids"] == []
    assert achievement_payload["read_code_file_paths"] == ["songryeon_core/tools/code_tools.py"]
    assert achievement_payload["actual_read_code_file_count"] == 1

    _, _, return_summary_id, _ = record_l_loop_return_summary_for_node1(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_135",
        zero_state=ZeroState(),
        input_ref=result.source_trace_ids,
        source_data_ids=result.output_data_ids,
    )
    return_summary = data_store.require_record(return_summary_id).payload
    assert isinstance(return_summary, dict)
    assert return_summary["actual_read_doc_count"] == 0
    assert return_summary["actual_read_code_file_count"] == 1
    assert return_summary["read_code_file_paths"] == ["songryeon_core/tools/code_tools.py"]
    assert return_summary["failure_level"] == "none"

    seed = trace_store.create_event(
        turn_id="turn_order_135",
        actor="test",
        event_type="node_output",
        output_ref=["node_2:handoff_frame"],
        schema_status="passed",
    )
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_135",
        user_question=user_query,
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[seed.event_id, *result.source_trace_ids],
        source_data_ids=["node_2:handoff_frame", return_summary_id, *result.output_data_ids],
    )

    assert brief.actual_tool_read_doc_count == 0
    assert brief.actual_tool_read_code_file_count == 1
    assert brief.actual_tool_read_code_file_paths == ["songryeon_core/tools/code_tools.py"]
    assert brief.supplied_source_code_context_count == 1
    assert len(brief.source_code_outlines) == 1
    outline = brief.source_code_outlines[0]
    assert outline.file_path == "songryeon_core/tools/code_tools.py"
    assert outline.parse_status == "parsed"
    assert {
        "list_code_files",
        "search_code",
        "read_code_file",
    }.issubset(set(outline.public_function_names))
    top_level_symbols = {symbol.name for symbol in outline.top_level_symbols}
    assert "DEFAULT_CODE_FILE_EXTENSIONS" in top_level_symbols
    assert "DEFAULT_IGNORED_DIR_NAMES" in top_level_symbols
    assert any(
        document.document_name == "songryeon_core/tools/code_tools.py"
        and "def read_code_file" in document.text
        for document in brief.read_documents
    )

    payload = node3_brief_llm_payload(brief)
    outline_payload = payload["source_code_outlines"]
    assert outline_payload["count"] == 1
    assert outline_payload["items"][0]["public_function_names"] == outline.public_function_names
    assert "source_data_id" not in outline_payload["items"][0]

    grounding = build_node3_grounding_block(brief)
    assert "실제 read_doc 도구 원문 읽기: 0개" in grounding
    assert "실제 read_code_file 도구 원문 읽기: 1개" in grounding
    assert "node_3 공급 source-code context: 1개" in grounding
    assert "source-code 구조 목록: 1개" in grounding
