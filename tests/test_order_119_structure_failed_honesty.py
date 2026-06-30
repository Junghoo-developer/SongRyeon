from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    Node3InputBriefFrame,
    Node3SelectedRecentMemoryContext,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.fake import BrokenJSONFakeLLMAdapter
from songryeon_core.nodes.node_2_handoff import node3_brief_llm_payload
from songryeon_core.nodes.node_2_metainfo_boundary import run_node2_answer_basis_selection
from songryeon_core.nodes.node_3_reporter import assemble_node3_report_markdown
from songryeon_core.runtime.terminal_view import render_chat_answer, render_pretty_turn


def test_structure_failed_fallback_no_fake_search() -> None:
    result = {
        "status": "structure_failed",
        "trace_count": 0,
        "data_record_count": 0,
        "structure_failure_stage": "node_3:run",
        "structure_failure_exception_type": "ValueError",
        "structure_failure_reason": "node_3 LLM reporter failed: parse_failed",
    }

    rendered = render_chat_answer(result, user_input="이 구조 어때?")

    assert "node_3 최종 보고도 실행되지 않았고" in rendered
    assert "의미 답변은 만들지 않고" in rendered
    assert "확인 가능한 search_docs/read_doc payload도 없어" in rendered
    assert "내부 문서를 찾았어" not in rendered
    assert "검색 결과 payload를 찾지 못해서" not in rendered


def test_structure_failed_mentions_actual_search_payload_only_when_present() -> None:
    result = {
        "status": "structure_failed",
        "trace_count": 3,
        "data_record_count": 2,
        "data_records": [
            _record(
                data_id="tool:search:001",
                data_type="tool_result:search_docs",
                payload={
                    "result_count": 1,
                    "results": [{"doc_id": "Administrative_Reform_1/04_Orders/ORDER_119.md"}],
                },
            ),
            _record(
                data_id="tool:read:001",
                data_type="tool_result:read_doc",
                payload={
                    "doc_id": "Administrative_Reform_1/04_Orders/ORDER_119.md",
                    "char_count": 119,
                    "text": "# ORDER 119",
                },
            ),
        ],
    }

    rendered = render_chat_answer(result, user_input="방금 읽은 거야?")

    assert "DataStore에 검색/문서 payload가 남아 있어" in rendered
    assert "search_docs payload: 후보 1개" in rendered
    assert "read_doc payload: `ORDER_119.md`" in rendered
    assert "내부 문서를 찾았어" not in rendered
    assert "검색 결과 payload를 찾지 못해서" not in rendered


def test_answer_basis_failure_diagnostics_are_recorded_and_rendered() -> None:
    trace_store, data_store, input_trace_id = _stores()

    _, _, frame = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_119",
        user_question="몇 개 읽었어?",
        boundary_id="source:boundary",
        boundary=MetainfoBoundary(),
        handoff_frame_id="source:handoff",
        adapter=BrokenJSONFakeLLMAdapter(),
        input_ref=[input_trace_id],
        source_data_ids=["source:runtime", "source:memory"],
    )
    result = {
        "status": "ok",
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "data_records": data_store.to_records(),
    }
    rendered = render_pretty_turn(result, user_input="몇 개 읽었어?")

    assert frame.answer_basis_mode == "mixed_or_uncertain"
    assert frame.basis_reason_codes == ["llm_mode_selection_failed"]
    assert frame.generated_by == "CODE:FALLBACK"
    assert frame.answer_basis_failure_type == "parse_failed"
    assert frame.answer_basis_llm_call_data_id
    assert frame.answer_basis_trace_event_id
    assert frame.answer_basis_payload_parse_status == "failed"
    assert frame.answer_basis_raw_text_present is True
    assert frame.answer_basis_prompt_ref.endswith("node_2_answer_basis_selector_v0.md")
    assert "failure_type: parse_failed" in rendered
    assert "payload_parse_status: failed" in rendered
    assert "llm_call: llm_call:node_2:" in rendered


def test_selected_recent_memory_payload_boundary_is_not_document() -> None:
    brief = Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_119",
        user_question="그건 실행기록 문서를 읽은 거야?",
        brief_status="ready",
        handoff_frame_id="source:handoff",
        selected_recent_memory_contexts=[
            Node3SelectedRecentMemoryContext(
                source_turn_id="turn_previous",
                raw_user_text="아까 실행기록 문서를 봤냐고 물었어",
                raw_assistant_text="그때는 최근 대화 원문만 봤다고 답했어",
                raw_user_text_chars=len("아까 실행기록 문서를 봤냐고 물었어"),
                raw_assistant_text_chars=len("그때는 최근 대화 원문만 봤다고 답했어"),
                raw_user_text_truncated=False,
                raw_assistant_text_truncated=False,
                selection_status="selected",
                selection_info_class="mixed",
                selection_reason="테스트 fixture가 선택한 최근 대화다.",
                selection_reason_generated_by="LLM:test",
                copied_from="recent_raw_conversation",
            )
        ],
        reporting_rules=[
            "선택된 최근 기억 context는 과거 대화 원문을 code가 복사한 context이며, 실행기록 문서나 새로 읽은 문서가 아니다.",
        ],
        source_data_ids=["source:handoff"],
    )

    payload = node3_brief_llm_payload(brief)

    assert payload["available_document_extract_count"] == 0
    assert "not a read document" in payload["selected_recent_memory_source_boundary"]
    assert "not an execution-record document" in payload["selected_recent_memory_source_boundary"]
    assert any("실행기록 문서나 새로 읽은 문서가 아니다" in rule for rule in brief.reporting_rules)


def test_bold_duplicate_grounding_block_is_stripped() -> None:
    brief = Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_119",
        user_question="요약해줘",
        brief_status="ready",
        handoff_frame_id="source:handoff",
        source_data_ids=["source:handoff"],
    )

    rendered = assemble_node3_report_markdown(
        brief_frame=brief,
        body_markdown=(
            "**근거 기준:**\n"
            "- 실제 read_doc 도구 원문 읽기: 99개\n\n"
            "본문만 남아야 한다."
        ),
    )

    assert rendered.startswith("근거 기준:")
    assert rendered.count("근거 기준:") == 1
    assert "99개" not in rendered
    assert "본문만 남아야 한다." in rendered


def _record(*, data_id: str, data_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "data_id": data_id,
        "data_type": data_type,
        "exists": True,
        "created_at": None,
        "source_trace_id": None,
        "payload": payload,
    }


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    seed_event = trace_store.create_event(
        turn_id="turn_order_119",
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:memory", "source:boundary", "source:handoff"],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:memory", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=seed_event.event_id,
            payload={"data_id": data_id},
        )
    return trace_store, data_store, seed_event.event_id
