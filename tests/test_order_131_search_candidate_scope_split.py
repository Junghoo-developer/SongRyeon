from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_0_memory_supplier import (
    NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
    record_node0_document_material_packet,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block


def test_node3_brief_splits_final_and_accumulated_search_candidate_scopes() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_l_return_summary(
        data_store,
        trace_id,
        search_result_doc_ids=["docs/final/A.md", "docs/final/B.md"],
    )
    _record_l3_preserved_frame(
        data_store,
        trace_id,
        data_id="L3:preserved_info_frame",
        doc_ids=["docs/a/README.md", "docs/b/README.md"],
    )
    _record_l3_preserved_frame(
        data_store,
        trace_id,
        data_id="L3:revision_preserved_info_frame:0001",
        doc_ids=["docs/final/A.md", "docs/c/C.md"],
    )
    _, material_id, _ = record_node0_document_material_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_131",
        frame_id=NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID,
        source_trace_ids=[trace_id],
        source_data_ids=["L:return_summary_frame"],
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_131",
        user_question="검색 후보 count를 구분해줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=[
            "node_2:handoff_frame",
            "L:return_summary_frame",
            "L3:preserved_info_frame",
            "L3:revision_preserved_info_frame:0001",
            material_id,
        ],
    )
    payload = node3_brief_llm_payload(brief)
    grounding = build_node3_grounding_block(brief)

    assert brief.final_search_candidate_count == 2
    assert brief.final_search_candidate_documents == ["A.md", "B.md"]
    assert brief.search_candidate_count == brief.final_search_candidate_count
    assert brief.search_candidate_documents == brief.final_search_candidate_documents
    assert brief.accumulated_search_candidate_count == 4
    assert brief.accumulated_search_candidate_documents == [
        "docs/a/README.md",
        "docs/b/README.md",
        "A.md",
        "C.md",
    ]
    assert payload["search_candidate_scope"]["final_search_candidate"]["count"] == 2
    assert payload["search_candidate_scope"]["accumulated_search_candidate"]["count"] == 4
    assert "- 검색 후보 문서(최종): 2개" in grounding
    assert "- 검색 후보 문서(누적): 4개" in grounding


def test_node3_brief_final_search_candidates_fallback_to_return_summary_without_material_packet() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_l_return_summary(
        data_store,
        trace_id,
        search_result_doc_ids=["docs/final/A.md", "docs/final/B.md"],
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_131",
        user_question="material packet이 없어도 최종 후보를 세어줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=["node_2:handoff_frame", "L:return_summary_frame"],
    )

    assert brief.final_search_candidate_count == 2
    assert brief.final_search_candidate_documents == ["A.md", "B.md"]
    assert brief.accumulated_search_candidate_count == 0


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_131",
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


def _record_l_return_summary(
    data_store: DataStore,
    trace_id: str,
    *,
    search_result_doc_ids: list[str],
) -> None:
    data_store.create_record(
        data_id="L:return_summary_frame",
        data_type="node_output:l_loop_return_summary_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": "L:return_summary_frame",
            "turn_id": "turn_order_131",
            "search_result_doc_ids": search_result_doc_ids,
            "search_candidate_count": len(search_result_doc_ids),
        },
    )


def _record_l3_preserved_frame(
    data_store: DataStore,
    trace_id: str,
    *,
    data_id: str,
    doc_ids: list[str],
) -> None:
    data_store.create_record(
        data_id=data_id,
        data_type="node_output:L3_preserved_info_frame",
        source_trace_id=trace_id,
        payload={
            "frame_id": data_id,
            "turn_id": "turn_order_131",
            "candidates": [
                {
                    "candidate_id": f"candidate:{index}",
                    "doc_id": doc_id,
                }
                for index, doc_id in enumerate(doc_ids, start=1)
            ],
        },
    )
