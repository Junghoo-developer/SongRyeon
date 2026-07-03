from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief


def test_node3_actual_read_doc_count_uses_doc_identity_not_file_name() -> None:
    trace_store, data_store, trace_id = _stores()
    _record_handoff(data_store, trace_id)
    _record_return_summary(
        data_store,
        trace_id,
        read_doc_ids=[
            "04_Orders/README.md",
            "05_Execution_Records/README.md",
        ],
    )
    _record_read_doc(
        data_store,
        trace_id,
        "tool_result:read_doc:orders_readme",
        "04_Orders/README.md",
        "orders readme",
    )
    _record_read_doc(
        data_store,
        trace_id,
        "tool_result:read_doc:records_readme",
        "05_Execution_Records/README.md",
        "records readme",
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_128",
        user_question="README 두 개를 따로 세어줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[trace_id],
        source_data_ids=[
            "node_2:handoff_frame",
            "L:return_summary_frame",
            "tool_result:read_doc:orders_readme",
            "tool_result:read_doc:records_readme",
        ],
    )

    assert brief.actual_tool_read_doc_count == 2
    assert brief.actual_tool_read_doc_documents == [
        "04_Orders/README.md",
        "05_Execution_Records/README.md",
    ]


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_128",
        actor="test",
        event_type="node_output",
        output_ref=["seed"],
        schema_status="passed",
    )
    return trace_store, data_store, event.event_id


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


def _record_return_summary(
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
            "turn_id": "turn_order_128",
            "actual_read_doc_count": len(read_doc_ids),
            "read_doc_ids": read_doc_ids,
            "search_result_doc_ids": read_doc_ids,
        },
    )


def _record_read_doc(
    data_store: DataStore,
    trace_id: str,
    data_id: str,
    doc_id: str,
    text: str,
) -> None:
    data_store.create_record(
        data_id=data_id,
        data_type="tool_result:read_doc",
        source_trace_id=trace_id,
        payload={"doc_id": doc_id, "text": text, "char_count": len(text)},
    )
