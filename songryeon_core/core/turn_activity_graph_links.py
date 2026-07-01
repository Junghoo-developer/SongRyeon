from __future__ import annotations

import json
from dataclasses import asdict

from songryeon_core.core.data_store import DataRecord, DataStore
from songryeon_core.core.graph_memory import raw_capsule_graph_node_id
from songryeon_core.core.schemas import (
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    TurnActivityGraphLinkFrame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
    validate_turn_activity_graph_link_frame,
)
from songryeon_core.core.trace_store import TraceStore


L_LOOP_ACTIVITY_LEDGER_DATA_TYPE = "loop_activity:l_loop_activity_ledger_frame"
R_GRAPH_ACCESS_LEDGER_DATA_TYPE = "graph_memory:turn_access_ledger_frame"
TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE = "graph_memory:turn_activity_graph_link_frame"


def turn_activity_graph_link_frame_id(turn_id: str) -> str:
    if not turn_id:
        raise ValueError("turn_id must not be empty")
    return f"graph:turn_activity_graph_link:{turn_id}"


def activity_ledger_graph_node_id(ledger_data_id: str) -> str:
    if not ledger_data_id:
        raise ValueError("ledger_data_id must not be empty")
    return f"graph:activity_ledger:{ledger_data_id}"


def activity_ledger_graph_edge_id(*, raw_capsule_node_id: str, activity_node_id: str) -> str:
    if not raw_capsule_node_id:
        raise ValueError("raw_capsule_node_id must not be empty")
    if not activity_node_id:
        raise ValueError("activity_node_id must not be empty")
    return f"graph:edge:has_activity_ledger:{raw_capsule_node_id}:{activity_node_id}"


def record_turn_activity_graph_links(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    l_loop_activity_ledger_data_ids: list[str] | None = None,
    r_graph_access_ledger_data_ids: list[str] | None = None,
    frame_id: str | None = None,
) -> tuple[str, str, TurnActivityGraphLinkFrame]:
    """Create graph nodes/edges connecting a raw capsule to L/R activity ledgers."""

    raw_node_id = raw_capsule_graph_node_id(turn_id)
    l_ledger_records = _ledger_records(
        data_store=data_store,
        turn_id=turn_id,
        data_type=L_LOOP_ACTIVITY_LEDGER_DATA_TYPE,
        explicit_data_ids=l_loop_activity_ledger_data_ids,
    )
    r_ledger_records = _ledger_records(
        data_store=data_store,
        turn_id=turn_id,
        data_type=R_GRAPH_ACCESS_LEDGER_DATA_TYPE,
        explicit_data_ids=r_graph_access_ledger_data_ids,
    )
    activity_nodes: list[GraphMemoryNodeFrame] = []
    activity_edges: list[GraphMemoryEdgeFrame] = []
    link_records: list[dict[str, str]] = []

    for activity_kind, records, source_field in [
        ("l_loop_activity_ledger", l_ledger_records, "l_loop_activity_ledger_data_ids"),
        ("r_graph_access_ledger", r_ledger_records, "r_graph_access_ledger_data_ids"),
    ]:
        for record in records:
            node = _build_activity_ledger_node(
                turn_id=turn_id,
                raw_node_id=raw_node_id,
                ledger_record=record,
                activity_kind=activity_kind,
            )
            edge = _build_activity_ledger_edge(
                raw_node_id=raw_node_id,
                activity_node=node,
                ledger_data_id=record.data_id,
            )
            activity_nodes.append(node)
            activity_edges.append(edge)
            link_records.append(
                {
                    "activity_kind": activity_kind,
                    "ledger_data_id": record.data_id,
                    "graph_node_id": node.node_id,
                    "edge_id": edge.edge_id,
                    "source_field": source_field,
                }
            )

    source_trace_ids = _unique_strings(
        [
            trace_id
            for node in activity_nodes
            for trace_id in node.source_trace_ids
        ]
    )
    source_data_ids = _unique_strings(
        [
            raw_node_id,
            *[record.data_id for record in l_ledger_records],
            *[record.data_id for record in r_ledger_records],
            *[node.node_id for node in activity_nodes],
            *[edge.edge_id for edge in activity_edges],
        ]
    )
    frame = TurnActivityGraphLinkFrame(
        frame_id=frame_id or turn_activity_graph_link_frame_id(turn_id),
        turn_id=turn_id,
        turn_capsule_graph_node_id=raw_node_id,
        l_loop_activity_ledger_data_ids=[record.data_id for record in l_ledger_records],
        r_graph_access_ledger_data_ids=[record.data_id for record in r_ledger_records],
        activity_ledger_graph_node_ids=[node.node_id for node in activity_nodes],
        activity_ledger_graph_edge_ids=[edge.edge_id for edge in activity_edges],
        link_records=link_records,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_turn_activity_graph_link_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_activity_link_builder",
        event_type="node_output",
        input_ref=source_trace_ids,
        output_ref=[
            frame.frame_id,
            *[node.node_id for node in activity_nodes],
            *[edge.edge_id for edge in activity_edges],
        ],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    for node in activity_nodes:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=node.node_id,
            data_type=f"graph_memory:node:{node.node_kind}",
            payload=asdict(node),
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
    for edge in activity_edges:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=edge.edge_id,
            data_type=f"graph_memory:edge:{edge.edge_kind}",
            payload=asdict(edge),
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame.frame_id,
        data_type=TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE,
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return event.event_id, frame.frame_id, frame


def _build_activity_ledger_node(
    *,
    turn_id: str,
    raw_node_id: str,
    ledger_record: DataRecord,
    activity_kind: str,
) -> GraphMemoryNodeFrame:
    payload = ledger_record.payload if isinstance(ledger_record.payload, dict) else {}
    source_trace_ids = _unique_strings(_string_list(payload.get("source_trace_ids")))
    node = GraphMemoryNodeFrame(
        node_id=activity_ledger_graph_node_id(ledger_record.data_id),
        node_kind="activity_ledger",
        data_kind=activity_kind,
        source_turn_id=turn_id,
        trace_count=len(source_trace_ids),
        movement_count=0,
        summary_depth=0,
        source_depth_min=0,
        source_depth_max=0,
        source_leaf_count=1,
        source_summary_count=0,
        source_bundle_kind="activity_ledger",
        bundle_policy_id="turn_activity_graph_link_v0",
        source_char_count=_payload_char_count(ledger_record.payload),
        source_graph_node_ids=[raw_node_id],
        source_trace_ids=source_trace_ids,
        source_data_ids=[ledger_record.data_id],
    )
    validate_graph_memory_node_frame(node)
    return node


def _build_activity_ledger_edge(
    *,
    raw_node_id: str,
    activity_node: GraphMemoryNodeFrame,
    ledger_data_id: str,
) -> GraphMemoryEdgeFrame:
    edge = GraphMemoryEdgeFrame(
        edge_id=activity_ledger_graph_edge_id(
            raw_capsule_node_id=raw_node_id,
            activity_node_id=activity_node.node_id,
        ),
        edge_kind="HAS_ACTIVITY_LEDGER",
        from_node_id=raw_node_id,
        to_node_id=activity_node.node_id,
        source_graph_node_ids=[raw_node_id, activity_node.node_id],
        source_trace_ids=list(activity_node.source_trace_ids),
        source_data_ids=[raw_node_id, activity_node.node_id, ledger_data_id],
    )
    validate_graph_memory_edge_frame(edge)
    return edge


def _ledger_records(
    *,
    data_store: DataStore,
    turn_id: str,
    data_type: str,
    explicit_data_ids: list[str] | None,
) -> list[DataRecord]:
    if explicit_data_ids is not None:
        records = [data_store.require_record(data_id) for data_id in explicit_data_ids]
    else:
        records = [
            record
            for record in data_store.list_records()
            if record.data_type == data_type
        ]
    filtered: list[DataRecord] = []
    seen: set[str] = set()
    for record in records:
        if record.data_type != data_type:
            raise ValueError(f"unexpected ledger data_type for {record.data_id}: {record.data_type}")
        payload = record.payload if isinstance(record.payload, dict) else {}
        if payload.get("turn_id") != turn_id:
            continue
        if record.data_id in seen:
            continue
        seen.add(record.data_id)
        filtered.append(record)
    return filtered


def _record_payload_if_missing(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: object,
    created_at: str,
    source_trace_id: str,
    created_data_ids: list[str],
    existing_data_ids: list[str],
) -> None:
    existing = data_store.get_record(data_id)
    if existing is not None:
        if existing.data_type != data_type or existing.payload != payload:
            raise ValueError(f"data_id collision with different payload: {data_id}")
        existing_data_ids.append(data_id)
        return
    data_store.create_record(
        data_id=data_id,
        data_type=data_type,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )
    created_data_ids.append(data_id)


def _payload_char_count(payload: object) -> int:
    return len(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = [
    "L_LOOP_ACTIVITY_LEDGER_DATA_TYPE",
    "R_GRAPH_ACCESS_LEDGER_DATA_TYPE",
    "TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE",
    "activity_ledger_graph_edge_id",
    "activity_ledger_graph_node_id",
    "record_turn_activity_graph_links",
    "turn_activity_graph_link_frame_id",
]
