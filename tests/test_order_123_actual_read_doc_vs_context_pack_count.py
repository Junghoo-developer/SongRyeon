from __future__ import annotations

from dataclasses import asdict

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DocumentContextPackFrame,
    DocumentContextPackIncludedDocument,
    MetainfoBoundary,
    Node3BriefDocument,
    Node3InputBriefFrame,
    validate_node3_input_brief_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper
from songryeon_core.tools.document_context_pack import DOCUMENT_CONTEXT_PACK_DATA_TYPE


def test_node3_grounding_separates_actual_read_doc_from_supplied_context() -> None:
    brief = _brief(actual_read_doc_count=2, supplied_context_count=10)

    grounding = build_node3_grounding_block(brief)

    assert "- 실제 read_doc 도구 원문 읽기: 2개" in grounding
    assert "- node_3 공급 문서 context: 10개" in grounding
    assert "- 읽은 문서: 10개" not in grounding


def test_node3_llm_payload_exposes_structured_count_boundary() -> None:
    brief = _brief(actual_read_doc_count=2, supplied_context_count=10)

    payload = node3_brief_llm_payload(brief)

    assert payload["actual_tool_read_doc"]["count"] == 2
    assert payload["actual_tool_read_doc"]["document_names"] == ["ACTUAL_A.md", "ACTUAL_B.md"]
    assert payload["supplied_document_context"]["count"] == 10
    assert len(payload["supplied_document_contexts"]) == 10
    assert len(payload["read_documents"]) == 10
    assert payload["read_documents"][0]["legacy_alias"] == "supplied_document_context"


def test_node3_input_brief_rejects_context_count_mismatch() -> None:
    brief = _brief(actual_read_doc_count=2, supplied_context_count=10)
    brief.supplied_document_context_count = 9

    with pytest.raises(ValueError, match="supplied_document_context_count"):
        validate_node3_input_brief_frame(brief)


def test_record_node3_input_brief_keeps_l_tool_count_and_context_pack_count_separate() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_l_loop_return_summary(data_store=data_store, trace_id=trace_id)
    _record_document_context_pack(data_store=data_store, trace_id=trace_id)

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_123",
        user_question="read_doc 수와 공급 context 수를 구분해줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["node_2:handoff_frame", "L:document_context_pack_frame"],
    )

    assert brief.actual_tool_read_doc_count == 2
    assert brief.actual_tool_read_doc_documents == ["ACTUAL_A.md", "ACTUAL_B.md"]
    assert brief.supplied_document_context_count == 3
    assert len(brief.read_documents) == 3
    assert [document.document_name for document in brief.read_documents] == [
        "PACKED_1.md",
        "PACKED_2.md",
        "PACKED_3.md",
    ]


def test_node4_count_guard_uses_actual_read_doc_count_not_context_count() -> None:
    trace_store, data_store, trace_id = _stores()
    brief = _brief(actual_read_doc_count=2, supplied_context_count=10)
    rendered_markdown = "\n".join(
        [
            "근거 기준:",
            "- 실제 read_doc 도구 원문 읽기: 10개",
            "- node_3 공급 문서 context: 10개",
            "- 검색 후보 문서(최종): 0개",
            "- 검색 후보 문서(누적): 0개",
            "- 현재 턴 실행 순서 자료: 0개",
            "- 답변 한계: 일부러 actual read_doc count를 context count와 섞은 보고문이다.",
            "",
            "본문",
        ]
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_123",
        report_id="report:order_123",
        boundary_id="boundary:order_123",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=SongRyeonAllNodesFakeLLMAdapter(),
        input_ref=[trace_id],
        source_data_ids=["report:order_123", brief.frame_id, "boundary:order_123"],
    )

    gate = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate["gate_status"] == "needs_revision"
    assert "grounding_count_mismatch" in gate["reason"]
    assert "실제 read_doc 도구 원문 읽기:actual_10_expected_2" in gate["contradictions"]


def _brief(*, actual_read_doc_count: int, supplied_context_count: int) -> Node3InputBriefFrame:
    read_documents = [
        Node3BriefDocument(
            document_name=f"PACKED_{index}.md",
            char_count=len("context"),
            text="context",
            source_data_id="L:document_context_pack_frame",
        )
        for index in range(1, supplied_context_count + 1)
    ]
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_123",
        user_question="read_doc 수와 공급 context 수를 구분해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        read_documents=read_documents,
        actual_tool_read_doc_count=actual_read_doc_count,
        actual_tool_read_doc_documents=["ACTUAL_A.md", "ACTUAL_B.md"][:actual_read_doc_count],
        supplied_document_context_count=supplied_context_count,
        source_data_ids=["node_2:handoff_frame"],
    )


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_123",
        actor="test",
        event_type="node_output",
        output_ref=["node_2:handoff_frame"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="node_2:handoff_frame",
        data_type="test:handoff",
        source_trace_id=event.event_id,
        payload={"frame_id": "node_2:handoff_frame"},
    )
    return trace_store, data_store, event.event_id


def _record_l_loop_return_summary(*, data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L:return_summary_frame",
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L:return_summary_frame",
            "turn_id": "turn_order_123",
            "l_loop_task_status": "achieved",
            "failure_level": "none",
            "l3_goal_match_status": "matched",
            "l3_semantic_goal_match_status": "matched",
            "remaining_query_attempts": 0,
            "remaining_read_doc_calls": 8,
            "actual_read_doc_count": 2,
            "read_doc_ids": ["docs/ACTUAL_A.md", "docs/ACTUAL_B.md"],
        },
    )


def _record_document_context_pack(*, data_store: DataStore, trace_id: str) -> None:
    documents = [
        DocumentContextPackIncludedDocument(
            doc_id=f"docs/PACKED_{index}.md",
            document_name=f"PACKED_{index}.md",
            char_count=len(f"packed context {index}"),
            rank_index=index,
            selection_basis="test_pack",
            text=f"packed context {index}",
            source_data_id=f"source:{index}",
        )
        for index in range(1, 4)
    ]
    frame = DocumentContextPackFrame(
        frame_id="L:document_context_pack_frame",
        turn_id="turn_order_123",
        max_document_context_chars=100000,
        budget_unit="chars",
        whole_document_only=True,
        strict_rank_order=True,
        included_documents=documents,
        included_document_count=len(documents),
        included_total_chars=sum(document.char_count for document in documents),
        source_trace_ids=[trace_id],
        source_data_ids=["L:return_summary_frame"],
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=DOCUMENT_CONTEXT_PACK_DATA_TYPE,
        source_trace_id=trace_id,
        payload=asdict(frame),
    )
