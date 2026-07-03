from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DocumentContextPackFrame,
    DocumentContextPackIncludedDocument,
    MetainfoBoundary,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_0_memory_supplier import (
    NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
    build_node0_document_material_packet_frame,
    record_node0_document_material_packet,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
    record_route2_handoff,
)
from songryeon_core.tools.document_context_pack import DOCUMENT_CONTEXT_PACK_DATA_TYPE


def test_node0_document_material_packet_marks_document_roles_without_summary() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_l_return_summary(data_store, trace_id)
    _record_context_pack(data_store, trace_id)
    _record_read_doc(data_store, trace_id, "docs/A.md", "A 원문")
    _record_read_doc(data_store, trace_id, "docs/B.md", "B 원문")

    frame = build_node0_document_material_packet_frame(
        data_store=data_store,
        turn_id="turn_order_124",
        frame_id=NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
        source_trace_ids=[trace_id],
        source_data_ids=[
            "L:return_summary_frame",
            "L:document_context_pack_frame",
            "tool_result:read_doc:A",
            "tool_result:read_doc:B",
        ],
    )

    assert frame.semantic_judgement_status == "not_run"
    assert frame.item_count == 3
    assert frame.search_candidate_count == 3
    assert frame.actual_tool_read_doc_count == 2
    assert frame.supplied_document_context_count == 3
    assert frame.unread_candidate_count == 1

    by_name = {item.document_name: item for item in frame.items}
    assert by_name["A.md"].was_search_candidate is True
    assert by_name["A.md"].was_actual_tool_read_doc is True
    assert by_name["A.md"].was_supplied_document_context is True
    assert by_name["C.md"].was_unread_candidate is True
    assert by_name["C.md"].was_actual_tool_read_doc is False


def test_route2_handoff_preserves_document_material_packet_counts() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_route2_minimum_records(data_store, trace_id)
    _record_l_return_summary(data_store, trace_id)
    _, material_id, _ = record_node0_document_material_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_124",
        frame_id=NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
        source_trace_ids=[trace_id],
        source_data_ids=["L:return_summary_frame"],
    )

    _, handoff_id = record_route2_handoff(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_124",
        user_question="문서 장부 확인",
        node2_input_frame_id="node2_input:turn_order_124",
        node2_input_trace_id=trace_id,
        final_memory_packet_id="memory_packet:node_2:final_trace_for_2",
        turn_outcome_id="turn_outcome:turn_order_124",
        route_ids=["route:2"],
        l_loop_output_ids=[],
    )

    payload = data_store.require_record(handoff_id).payload
    assert payload["document_material_packet_frame_id"] == material_id
    assert payload["document_material_item_count"] == 3
    assert payload["document_material_unread_candidate_count"] == 1
    assert material_id in payload["source_data_ids"]


def test_node3_brief_and_payload_receive_document_material_ledger() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_l_return_summary(data_store, trace_id)
    _record_context_pack(data_store, trace_id)
    _, material_id, _ = record_node0_document_material_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_124",
        frame_id=NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
        source_trace_ids=[trace_id],
        source_data_ids=["L:return_summary_frame", "L:document_context_pack_frame"],
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_124",
        user_question="읽은 문서와 안 읽은 후보를 구분해줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["node_2:handoff_frame", "L:return_summary_frame", "L:document_context_pack_frame", material_id],
    )
    payload = node3_brief_llm_payload(brief)

    assert brief.document_material_packet_frame_id == material_id
    assert len(brief.document_material_items) == 3
    assert any(item.was_unread_candidate for item in brief.document_material_items)
    assert payload["document_material_packet"]["status"] == "present"
    assert payload["document_material_packet"]["item_count"] == 3
    assert payload["document_material_packet"]["unread_candidate_count"] == 1
    assert "source_data_ids" not in payload["document_material_packet"]["items"][0]


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_124",
        actor="test",
        event_type="node_output",
        output_ref=["seed"],
        schema_status="passed",
    )
    return trace_store, data_store, event.event_id


def _record_l_return_summary(data_store: DataStore, trace_id: str) -> None:
    data_store.create_record(
        data_id="L:return_summary_frame",
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L:return_summary_frame",
            "turn_id": "turn_order_124",
            "read_doc_ids": ["docs/A.md", "docs/B.md"],
            "search_result_doc_ids": ["docs/A.md", "docs/B.md", "docs/C.md"],
        },
    )


def _record_context_pack(data_store: DataStore, trace_id: str) -> None:
    documents = [
        DocumentContextPackIncludedDocument(
            doc_id=f"docs/{name}.md",
            document_name=f"{name}.md",
            char_count=len(name),
            rank_index=index,
            selection_basis="test",
            text=f"{name} context",
            source_data_id=f"source:{name}",
        )
        for index, name in enumerate(["A", "B", "C"], start=1)
    ]
    frame = DocumentContextPackFrame(
        frame_id="L:document_context_pack_frame",
        turn_id="turn_order_124",
        max_document_context_chars=1000,
        budget_unit="chars",
        whole_document_only=True,
        strict_rank_order=True,
        included_documents=documents,
        included_document_count=len(documents),
        included_total_chars=sum(item.char_count for item in documents),
        source_trace_ids=[trace_id],
        source_data_ids=["L:return_summary_frame"],
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=DOCUMENT_CONTEXT_PACK_DATA_TYPE,
        source_trace_id=trace_id,
        payload=asdict(frame),
    )


def _record_read_doc(data_store: DataStore, trace_id: str, doc_id: str, text: str) -> None:
    data_store.create_record(
        data_id=f"tool_result:read_doc:{doc_id.rsplit('/', 1)[-1].removesuffix('.md')}",
        data_type="tool_result:read_doc",
        source_trace_id=trace_id,
        payload={"doc_id": doc_id, "text": text, "char_count": len(text)},
    )


def _record_route2_minimum_records(data_store: DataStore, trace_id: str) -> None:
    for data_id, data_type in {
        "node2_input:turn_order_124": "node_output:node2_input_frame",
        "memory_packet:node_2:final_trace_for_2": "memory_packet",
        "turn_outcome:turn_order_124": "node_output:turn_outcome",
        "route:2": "node_output:route_decision",
    }.items():
        data_store.create_record(
            data_id=data_id,
            data_type=data_type,
            source_trace_id=trace_id,
            payload={"data_id": data_id},
        )
