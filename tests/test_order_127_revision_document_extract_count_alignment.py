from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_0_memory_supplier import (
    NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
    build_l_loop_return_summary_frame,
    build_node0_document_material_packet_frame,
)
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief


def test_l_loop_return_summary_merges_revision_document_extract_records() -> None:
    _, data_store, trace_id = _stores()
    _record_l1_goal(data_store, trace_id)
    _record_l3_achievement(data_store, trace_id, read_doc_ids=["docs/A.md", "docs/B.md"])
    _record_budget(data_store, trace_id)
    for name in ["A", "B", "C", "D"]:
        _record_read_doc(data_store, trace_id, f"docs/{name}.md", f"{name} 원문")

    frame = build_l_loop_return_summary_frame(
        data_store=data_store,
        turn_id="turn_order_127",
        source_trace_ids=[trace_id],
        source_data_ids=[
            "L1:goal_frame",
            "L3:achievement_frame",
            "L:budget:latest",
            "tool_result:read_doc:A",
            "tool_result:read_doc:B",
            "tool_result:read_doc:C",
            "tool_result:read_doc:D",
        ],
    )

    assert frame.actual_read_doc_count == 4
    assert frame.read_doc_ids == ["docs/A.md", "docs/B.md", "docs/C.md", "docs/D.md"]


def test_node0_material_packet_marks_revision_read_docs_as_actual_reads() -> None:
    _, data_store, trace_id = _stores()
    _record_stale_return_summary(data_store, trace_id, read_doc_ids=["docs/A.md", "docs/B.md"])
    for name in ["A", "B", "C", "D"]:
        _record_read_doc(data_store, trace_id, f"docs/{name}.md", f"{name} 원문")

    frame = build_node0_document_material_packet_frame(
        data_store=data_store,
        turn_id="turn_order_127",
        frame_id=NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
        source_trace_ids=[trace_id],
        source_data_ids=[
            "L:return_summary_frame",
            "tool_result:read_doc:A",
            "tool_result:read_doc:B",
            "tool_result:read_doc:C",
            "tool_result:read_doc:D",
        ],
    )

    assert frame.actual_tool_read_doc_count == 4
    by_name = {item.document_name: item for item in frame.items}
    assert by_name["C.md"].was_actual_tool_read_doc is True
    assert by_name["D.md"].was_actual_tool_read_doc is True


def test_node3_brief_uses_revision_document_extract_records_for_actual_read_count() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_handoff(data_store, trace_id)
    _record_stale_return_summary(data_store, trace_id, read_doc_ids=["docs/A.md", "docs/B.md"])
    for name in ["A", "B", "C", "D"]:
        _record_read_doc(data_store, trace_id, f"docs/{name}.md", f"{name} 원문")

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_127",
        user_question="revision read_doc count를 확인해줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=[
            "node_2:handoff_frame",
            "L:return_summary_frame",
            "tool_result:read_doc:A",
            "tool_result:read_doc:B",
            "tool_result:read_doc:C",
            "tool_result:read_doc:D",
        ],
    )

    assert brief.actual_tool_read_doc_count == 4
    assert brief.actual_tool_read_doc_documents == ["A.md", "B.md", "C.md", "D.md"]


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_127",
        actor="test",
        event_type="node_output",
        output_ref=["seed"],
        schema_status="passed",
    )
    return trace_store, data_store, event.event_id


def _record_l1_goal(data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L1:goal_frame",
            "minimum_read_documents": 1,
            "evidence_requirement_kind": "multi_doc_relationship",
        },
    )


def _record_l3_achievement(
    data_store: DataStore,
    trace_id: str,
    *,
    read_doc_ids: list[str],
) -> None:
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L3:achievement_frame",
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "partial",
            "read_doc_ids": read_doc_ids,
            "search_result_doc_ids": [
                "docs/A.md",
                "docs/B.md",
                "docs/C.md",
                "docs/D.md",
            ],
        },
    )


def _record_budget(data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L:budget:latest",
        data_type="tool_use_budget",
        source_trace_id=trace_id,
        payload={
            "max_tool_calls": 10,
            "tool_call_count": 4,
            "max_read_doc_calls": 10,
            "read_doc_count": 4,
            "max_query_attempts": 8,
            "query_count": 1,
            "stop_reason": "completed",
        },
    )


def _record_stale_return_summary(
    data_store: DataStore,
    trace_id: str,
    *,
    read_doc_ids: list[str],
) -> None:
    data_store.create_record(
        data_id="L:return_summary_frame",
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L:return_summary_frame",
            "turn_id": "turn_order_127",
            "actual_read_doc_count": len(read_doc_ids),
            "read_doc_ids": read_doc_ids,
            "search_result_doc_ids": [
                "docs/A.md",
                "docs/B.md",
                "docs/C.md",
                "docs/D.md",
            ],
        },
    )


def _record_read_doc(data_store: DataStore, trace_id: str, doc_id: str, text: str) -> None:
    data_store.create_record(
        data_id=f"tool_result:read_doc:{doc_id.rsplit('/', 1)[-1].removesuffix('.md')}",
        data_type="tool_result:read_doc",
        source_trace_id=trace_id,
        payload={"doc_id": doc_id, "text": text, "char_count": len(text)},
    )


def _record_handoff(data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="node_2:handoff_frame",
        data_type="node_output:node2_handoff_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "node_2:handoff_frame",
            "source_data_ids": ["L:return_summary_frame"],
        },
    )
