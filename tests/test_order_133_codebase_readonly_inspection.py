from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MemoryPacketFrom0
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.nodes.l2_query_setter import run_l2_query_setter
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.tools.code_tools import list_code_files, read_code_file, search_code
from songryeon_core.tools.tool_runner import build_document_tool_registry


class CodeReadQueryPlannerAdapter:
    model_id = "order-133-code-read-query-planner"

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
                    "purpose": "사용자가 코드 구조 읽기 MVP를 요청했으므로 실제 source file을 읽는다.",
                    "expected_signal": "read_code_file로 source text가 복사된다.",
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


class CodeInspectionScopeAdapter:
    model_id = "order-133-code-inspection-scope-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "tool_scope_mode": "code_only",
            "allowed_tool_groups": ["code_inspection_tools"],
            "required_materials": ["source_code_file"],
            "scope_reason": "test adapter explicitly opens code inspection tools.",
            "scope_reason_info_class": "mixed",
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_code_tools_list_search_read_and_block_path_escape(tmp_path) -> None:
    source_dir = tmp_path / "pkg"
    source_dir.mkdir()
    source_file = source_dir / "sample.py"
    source_file.write_text("class Sample:\n    pass\n", encoding="utf-8")
    ignored_dir = tmp_path / "__pycache__"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("SHOULD_NOT_APPEAR = True\n", encoding="utf-8")

    listed = list_code_files(root=tmp_path)
    listed_paths = [item["file_path"] for item in listed["files"]]
    assert "pkg/sample.py" in listed_paths
    assert "__pycache__/hidden.py" not in listed_paths

    searched = search_code(root=tmp_path, query="class Sample")
    assert searched["match_count"] == 1
    assert searched["results"][0]["file_path"] == "pkg/sample.py"
    assert searched["results"][0]["line_number"] == 1

    read = read_code_file(root=tmp_path, file_path="pkg/sample.py")
    assert read["read_status"] == "ok"
    assert read["line_count"] == 2
    assert "class Sample" in read["text"]

    escaped = read_code_file(root=tmp_path, file_path="../outside.py")
    assert escaped["read_status"] == "path_outside_workspace_rejected"
    assert escaped["text"] == ""


def test_tool_registry_exposes_code_tools_as_read_only(tmp_path) -> None:
    registry = build_document_tool_registry(tmp_path, code_root=tmp_path)

    for tool_name in ("list_code_files", "search_code", "read_code_file"):
        spec = registry.get(tool_name)
        assert spec.read_only is True
        assert spec.output_data_type == f"tool_result:{tool_name}"


def test_l2_query_setter_accepts_code_tool_modes() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    l1_event = trace_store.create_event(
        turn_id="turn_order_133",
        actor="L1",
        event_type="node_output",
        output_ref=["L1:goal_frame"],
        schema_status="passed",
    )

    run_l2_query_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_133",
        l1_event=l1_event,
        query_text="songryeon_core/tools/code_tools.py",
        query_source="llm_query_plan",
        target_tool_name="read_code_file",
        source_data_ids=["L1:goal_frame"],
    )

    payload = data_store.require_record("L2:query_frame").payload
    assert isinstance(payload, dict)
    assert payload["target_tool_name"] == "read_code_file"
    assert payload["query_mode"] == "code_file_read"


def test_l_loop_runs_read_code_file_and_node3_brief_receives_source_context() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    memory_packet = MemoryPacketFrom0(target="L", trace_evidence_ids=[])

    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_133",
        memory_packet=memory_packet,
        search_query="코드 구조 읽기 MVP source file을 읽어줘",
        l_tool_scope_adapter=CodeInspectionScopeAdapter(),
        l2_query_planner_adapter=CodeReadQueryPlannerAdapter(),
        max_tool_calls=3,
        max_query_attempts=2,
        max_read_doc_calls=1,
    )

    code_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "tool_result:read_code_file"
    ]
    assert len(code_records) == 1
    code_payload = code_records[0].payload
    assert isinstance(code_payload, dict)
    assert code_payload["read_status"] == "ok"
    assert code_payload["file_path"] == "songryeon_core/tools/code_tools.py"

    seed = trace_store.create_event(
        turn_id="turn_order_133",
        actor="test",
        event_type="node_output",
        output_ref=["node_2:handoff_frame"],
        schema_status="passed",
    )
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_133",
        user_question="코드 구조 읽기 MVP source file을 읽어줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[seed.event_id, *result.source_trace_ids],
        source_data_ids=["node_2:handoff_frame", *result.output_data_ids],
    )

    source_contexts = [
        document
        for document in brief.read_documents
        if document.document_name == "songryeon_core/tools/code_tools.py"
    ]
    assert len(source_contexts) == 1
    assert "def read_code_file" in source_contexts[0].text
