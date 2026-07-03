from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory_store import (
    SONGRYEON_GRAPH_NAMESPACE,
    SONGRYEON_VESSEL_SERVICE_NAME,
)
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.trace_store import TraceStore


R_LOOP_VESSEL_READ_PACKET_DATA_TYPE = "r_loop:vessel_read_packet"
R_LOOP_VESSEL_READ_PACKET_GENERATOR = "CODE:R_LOOP_VESSEL_READ_PACKET_BUILDER"
R_LOOP_VESSEL_READ_PACKET_POLICY_ID = "R_LOOP_VESSEL_READ_PACKET_V0"
R_LOOP_VESSEL_READ_PACKET_SCHEMA_NAME = "RLoopVesselReadPacketFrame"
R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_POLICY_ID = (
    "R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_V0"
)
R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_MAX_DEPTH = 2
R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_POLICY_ID = (
    "R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_V0"
)
R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_MAX_DEPTH = 2
R_LOOP_VESSEL_READ_PACKET_STATUSES = {
    "passed",
    "empty",
    "adapter_unavailable",
    "read_failed",
}

Neo4jDriverFactory = Callable[..., Any]


@dataclass(frozen=True)
class RLoopVesselEntryCandidateRecord:
    candidate_node_id: str
    candidate_kind: str
    display_name: str
    node_kind: str | None
    data_kind: str | None
    created_at: str | None
    written_at: str | None
    source_trace_id: str | None
    summary_depth: int | None
    source_leaf_count: int | None
    source_summary_count: int | None
    source_graph_node_ids: list[str]
    parent_graph_node_ids: list[str]


@dataclass(frozen=True)
class RLoopVesselSummaryCandidateRecord:
    summary_node_id: str
    summary_display_name: str
    data_kind: str | None
    summary_depth: int | None
    summary_status: str | None
    validity_status: str | None
    review_status: str | None
    info_class: str | None
    generated_by: str | None
    target_graph_node_id: str | None
    target_display_name: str | None
    target_node_kind: str | None
    source_leaf_count: int | None
    source_summary_count: int | None
    source_graph_node_ids: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    summary_text_char_count: int
    summary_text: str
    summary_text_preview: str


@dataclass(frozen=True)
class RLoopVesselReadPacketFrame:
    packet_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    target_consumer: str
    read_status: str
    failure_type: str | None
    failure_reason: str | None
    entry_candidate_count: int
    summary_candidate_count: int
    total_summary_scanned_count: int | None
    active_summary_candidate_count: int | None
    skipped_summary_count: int | None
    summary_child_expansion_policy_id: str
    base_summary_candidate_count: int
    summary_child_expanded_count: int
    summary_child_expanded_node_ids: list[str]
    summary_child_expansion_truncated: bool
    exact_child_expansion_policy_id: str
    base_entry_candidate_count: int
    exact_child_expanded_entry_count: int
    exact_child_expanded_node_ids: list[str]
    exact_child_expansion_truncated: bool
    summary_count_by_data_kind: dict[str, int]
    summary_count_by_depth: dict[str, int]
    entry_candidate_records: list[dict[str, object]]
    summary_candidate_records: list[dict[str, object]]
    packet_lines: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = R_LOOP_VESSEL_READ_PACKET_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_READ_PACKET_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedRLoopVesselReadPacket:
    packet: RLoopVesselReadPacketFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def r_loop_vessel_read_packet_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"r_loop:vessel_read_packet:{_stable_suffix(batch_id)}"


def build_r_loop_vessel_read_packet_from_neo4j(
    *,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_r_loop_vessel_read_packet",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RLoopVesselReadPacketFrame:
    timestamp = created_at or _now_iso()
    safe_limit = max(1, min(limit, 500))
    base = _PacketBase(
        packet_id=r_loop_vessel_read_packet_id(batch_id),
        created_at=timestamp,
        target_adapter_name=SONGRYEON_VESSEL_SERVICE_NAME,
        vessel_database_name=config.database,
        graph_namespace=SONGRYEON_GRAPH_NAMESPACE,
    )

    config_failure = _config_failure(config)
    if config_failure is not None:
        failure_type, failure_reason = config_failure
        return _make_packet(
            base=base,
            read_status="adapter_unavailable",
            failure_type=failure_type,
            failure_reason=failure_reason,
            entry_candidates=[],
            active_summary_candidates=[],
            total_summary_scanned_count=None,
        )

    driver_factory = driver_factory or _load_neo4j_driver_factory()
    if driver_factory is None:
        return _make_packet(
            base=base,
            read_status="adapter_unavailable",
            failure_type="neo4j_driver_missing",
            failure_reason="Python neo4j package is not installed.",
            entry_candidates=[],
            active_summary_candidates=[],
            total_summary_scanned_count=None,
        )

    try:
        auth = None if config.allow_no_auth and config.password is None else (config.user, config.password)
        driver = driver_factory(config.uri, auth=auth)
        try:
            with driver.session(database=config.database) as session:
                (
                    entry_candidates,
                    active_summary_candidates,
                    total_summary_scanned_count,
                    expanded_entry_records,
                    expanded_summary_records,
                ) = session.execute_read(
                    _execute_read_packet,
                    SONGRYEON_GRAPH_NAMESPACE,
                    safe_limit,
                )
        finally:
            close = getattr(driver, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        return _make_packet(
            base=base,
            read_status="read_failed",
            failure_type="neo4j_read_failed",
            failure_reason=f"{type(exc).__name__}: {exc}",
            entry_candidates=[],
            active_summary_candidates=[],
            total_summary_scanned_count=None,
        )

    read_status = "passed" if entry_candidates or active_summary_candidates else "empty"
    return _make_packet(
        base=base,
        read_status=read_status,
        failure_type=None if read_status == "passed" else "no_r_loop_vessel_candidates",
        failure_reason=None
        if read_status == "passed"
        else "No R loop Vessel entry or active summary candidates were found.",
        entry_candidates=entry_candidates,
        active_summary_candidates=active_summary_candidates,
        total_summary_scanned_count=total_summary_scanned_count,
        base_entry_candidate_count=expanded_entry_records.base_entry_candidate_count,
        exact_child_expanded_node_ids=expanded_entry_records.exact_child_expanded_node_ids,
        exact_child_expansion_truncated=(
            expanded_entry_records.exact_child_expansion_truncated
        ),
        base_summary_candidate_count=(
            expanded_summary_records.base_summary_candidate_count
        ),
        summary_child_expanded_node_ids=(
            expanded_summary_records.summary_child_expanded_node_ids
        ),
        summary_child_expansion_truncated=(
            expanded_summary_records.summary_child_expansion_truncated
        ),
    )


def record_r_loop_vessel_read_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_r_loop_vessel_read_packet",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RecordedRLoopVesselReadPacket:
    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=config,
        batch_id=batch_id,
        limit=limit,
        created_at=created_at,
        driver_factory=driver_factory,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="r_loop_vessel_read_packet_builder",
        event_type="node_output",
        timestamp=packet.created_at,
        input_ref=[],
        output_ref=[packet.packet_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=packet.packet_id,
        data_type=R_LOOP_VESSEL_READ_PACKET_DATA_TYPE,
        payload=asdict(packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedRLoopVesselReadPacket(
        packet=packet,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


@dataclass(frozen=True)
class _PacketBase:
    packet_id: str
    created_at: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str


@dataclass(frozen=True)
class _EntryExpansion:
    records: list[object]
    base_entry_candidate_count: int
    exact_child_expanded_node_ids: list[str]
    exact_child_expansion_truncated: bool


@dataclass(frozen=True)
class _SummaryExpansion:
    candidates: list[RLoopVesselSummaryCandidateRecord]
    base_summary_candidate_count: int
    summary_child_expanded_node_ids: list[str]
    summary_child_expansion_truncated: bool


def _make_packet(
    *,
    base: _PacketBase,
    read_status: str,
    failure_type: str | None,
    failure_reason: str | None,
    entry_candidates: list[RLoopVesselEntryCandidateRecord],
    active_summary_candidates: list[RLoopVesselSummaryCandidateRecord],
    total_summary_scanned_count: int | None,
    base_entry_candidate_count: int | None = None,
    exact_child_expanded_node_ids: list[str] | None = None,
    exact_child_expansion_truncated: bool = False,
    base_summary_candidate_count: int | None = None,
    summary_child_expanded_node_ids: list[str] | None = None,
    summary_child_expansion_truncated: bool = False,
) -> RLoopVesselReadPacketFrame:
    entry_payloads = [asdict(candidate) for candidate in entry_candidates]
    summary_payloads = [asdict(candidate) for candidate in active_summary_candidates]
    active_summary_count = len(active_summary_candidates)
    expanded_node_ids = exact_child_expanded_node_ids or []
    expanded_summary_node_ids = summary_child_expanded_node_ids or []
    skipped_summary_count = (
        None
        if total_summary_scanned_count is None
        else max(0, total_summary_scanned_count - active_summary_count)
    )
    source_data_ids = _unique_strings(
        [candidate.candidate_node_id for candidate in entry_candidates]
        + [
            source_id
            for candidate in entry_candidates
            for source_id in candidate.source_graph_node_ids
        ]
        + [
            parent_id
            for candidate in entry_candidates
            for parent_id in candidate.parent_graph_node_ids
        ]
        + [candidate.summary_node_id for candidate in active_summary_candidates]
        + [candidate.target_graph_node_id for candidate in active_summary_candidates]
        + [
            source_id
            for candidate in active_summary_candidates
            for source_id in candidate.source_data_ids
        ]
    )
    source_trace_ids = _unique_strings(
        [candidate.source_trace_id for candidate in entry_candidates]
        + [
            source_trace_id
            for candidate in active_summary_candidates
            for source_trace_id in candidate.source_trace_ids
        ]
    )
    packet = RLoopVesselReadPacketFrame(
        packet_id=base.packet_id,
        created_at=base.created_at,
        policy_id=R_LOOP_VESSEL_READ_PACKET_POLICY_ID,
        target_adapter_name=base.target_adapter_name,
        vessel_database_name=base.vessel_database_name,
        graph_namespace=base.graph_namespace,
        target_consumer="R_LOOP",
        read_status=read_status,
        failure_type=failure_type,
        failure_reason=failure_reason,
        entry_candidate_count=len(entry_candidates),
        summary_candidate_count=active_summary_count,
        total_summary_scanned_count=total_summary_scanned_count,
        active_summary_candidate_count=active_summary_count
        if total_summary_scanned_count is not None
        else None,
        skipped_summary_count=skipped_summary_count,
        summary_child_expansion_policy_id=(
            R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_POLICY_ID
        ),
        base_summary_candidate_count=(
            active_summary_count
            if base_summary_candidate_count is None
            else base_summary_candidate_count
        ),
        summary_child_expanded_count=len(expanded_summary_node_ids),
        summary_child_expanded_node_ids=expanded_summary_node_ids,
        summary_child_expansion_truncated=summary_child_expansion_truncated,
        exact_child_expansion_policy_id=R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_POLICY_ID,
        base_entry_candidate_count=(
            len(entry_candidates)
            if base_entry_candidate_count is None
            else base_entry_candidate_count
        ),
        exact_child_expanded_entry_count=len(expanded_node_ids),
        exact_child_expanded_node_ids=expanded_node_ids,
        exact_child_expansion_truncated=exact_child_expansion_truncated,
        summary_count_by_data_kind=_count_summaries_by_data_kind(active_summary_candidates),
        summary_count_by_depth=_count_summaries_by_depth(active_summary_candidates),
        entry_candidate_records=entry_payloads,
        summary_candidate_records=summary_payloads,
        packet_lines=_build_packet_lines(
            entry_candidates,
            active_summary_candidates,
            base_entry_candidate_count=(
                len(entry_candidates)
                if base_entry_candidate_count is None
                else base_entry_candidate_count
            ),
            exact_child_expanded_node_ids=expanded_node_ids,
            exact_child_expansion_truncated=exact_child_expansion_truncated,
            base_summary_candidate_count=(
                active_summary_count
                if base_summary_candidate_count is None
                else base_summary_candidate_count
            ),
            summary_child_expanded_node_ids=expanded_summary_node_ids,
            summary_child_expansion_truncated=summary_child_expansion_truncated,
        ),
        source_data_ids=source_data_ids,
        source_trace_ids=source_trace_ids,
    )
    _validate_packet(packet)
    return packet


def _execute_read_packet(
    tx: object,
    graph_namespace: str,
    limit: int,
) -> tuple[
    list[RLoopVesselEntryCandidateRecord],
    list[RLoopVesselSummaryCandidateRecord],
    int,
    _EntryExpansion,
    _SummaryExpansion,
]:
    entry_records = _read_entry_records(tx, graph_namespace)
    summary_records = _read_summary_records(tx, graph_namespace)
    expanded_entry_records = _expand_entry_records_by_exact_children(
        entry_records=entry_records,
        limit=limit,
    )
    entry_candidates = [
        _entry_candidate_from_record(record)
        for record in expanded_entry_records.records
    ]
    active_summary_candidates_all = [
        _summary_candidate_from_record(record)
        for record in summary_records
        if _is_active_r_loop_summary(record)
    ]
    base_active_summary_candidates = _balanced_summary_candidate_limit(
        active_summary_candidates_all,
        limit,
    )
    summary_expansion = _expand_summary_candidates_by_source_summary_children(
        base_candidates=base_active_summary_candidates,
        all_candidates=active_summary_candidates_all,
        limit=limit,
    )
    return (
        entry_candidates,
        summary_expansion.candidates,
        len(summary_records),
        expanded_entry_records,
        summary_expansion,
    )


def _expand_entry_records_by_exact_children(
    *,
    entry_records: list[object],
    limit: int,
) -> _EntryExpansion:
    base_records = list(entry_records[:limit])
    if not base_records:
        return _EntryExpansion(
            records=[],
            base_entry_candidate_count=0,
            exact_child_expanded_node_ids=[],
            exact_child_expansion_truncated=False,
        )

    records_by_id: dict[str, object] = {}
    record_index_by_id: dict[str, int] = {}
    parent_index: dict[str, list[str]] = {}
    for index, record in enumerate(entry_records):
        candidate_id = _optional_record_str(record, "candidate_node_id")
        if not candidate_id:
            continue
        records_by_id[candidate_id] = record
        record_index_by_id[candidate_id] = index
        for parent_id in _record_list_strings(record, "parent_graph_node_ids"):
            parent_index.setdefault(parent_id, []).append(candidate_id)

    selected_ids = {
        candidate_id
        for record in base_records
        for candidate_id in [_optional_record_str(record, "candidate_node_id")]
        if candidate_id
    }
    expanded_records = list(base_records)
    expanded_node_ids: list[str] = []
    frontier = list(base_records)
    expansion_budget = limit
    truncated = False

    for _depth in range(R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_MAX_DEPTH):
        child_ids = _ordered_exact_child_ids(
            frontier=frontier,
            parent_index=parent_index,
            record_index_by_id=record_index_by_id,
        )
        next_frontier: list[object] = []
        for child_id in child_ids:
            if child_id in selected_ids:
                continue
            child_record = records_by_id.get(child_id)
            if child_record is None:
                continue
            if expansion_budget <= 0:
                truncated = True
                break
            expanded_records.append(child_record)
            expanded_node_ids.append(child_id)
            selected_ids.add(child_id)
            next_frontier.append(child_record)
            expansion_budget -= 1
        if truncated or not next_frontier:
            break
        frontier = next_frontier

    return _EntryExpansion(
        records=expanded_records,
        base_entry_candidate_count=len(base_records),
        exact_child_expanded_node_ids=expanded_node_ids,
        exact_child_expansion_truncated=truncated,
    )


def _ordered_exact_child_ids(
    *,
    frontier: list[object],
    parent_index: dict[str, list[str]],
    record_index_by_id: dict[str, int],
) -> list[str]:
    child_ids: list[str] = []
    for record in frontier:
        payload = _payload(record)
        child_ids.extend(_list_strings(payload.get("source_graph_node_ids")))
        candidate_id = _optional_record_str(record, "candidate_node_id")
        if candidate_id:
            child_ids.extend(parent_index.get(candidate_id, []))
    return sorted(
        _unique_strings(child_ids),
        key=lambda item: (record_index_by_id.get(item, 1_000_000), item),
    )


def _read_entry_records(tx: object, graph_namespace: str) -> list[object]:
    result = tx.run(
        """
        MATCH (core:CoreEgo {graph_namespace: $graph_namespace})
          -[:HAS_AXIS {graph_namespace: $graph_namespace}]->
          (axis:TimeAxis {graph_namespace: $graph_namespace})
        RETURN
          axis.data_id AS candidate_node_id,
          coalesce(axis.display_name, axis.data_id) AS display_name,
          axis.node_kind AS node_kind,
          axis.data_kind AS data_kind,
          axis.created_at AS created_at,
          axis.written_at AS written_at,
          axis.source_trace_id AS source_trace_id,
          axis.payload_json AS payload_json,
          labels(axis) AS labels,
          [] AS parent_graph_node_ids,
          0 AS traversal_level
        UNION
        MATCH (core:CoreEgo {graph_namespace: $graph_namespace})
          -[:HAS_AXIS {graph_namespace: $graph_namespace}]->
          (axis:TimeAxis {graph_namespace: $graph_namespace})
        MATCH (axis)-[:HAS_BUNDLE {graph_namespace: $graph_namespace}]->
          (entry:VesselRecord {graph_namespace: $graph_namespace})
        WHERE entry:TimeBundle OR entry:SourceIngestBundle
        RETURN
          entry.data_id AS candidate_node_id,
          coalesce(entry.display_name, entry.data_id) AS display_name,
          entry.node_kind AS node_kind,
          entry.data_kind AS data_kind,
          entry.created_at AS created_at,
          entry.written_at AS written_at,
          entry.source_trace_id AS source_trace_id,
          entry.payload_json AS payload_json,
          labels(entry) AS labels,
          [axis.data_id] AS parent_graph_node_ids,
          1 AS traversal_level
        UNION
        MATCH (entry:VesselRecord {graph_namespace: $graph_namespace})
        WHERE entry:SourceKindBundle
          OR entry:RawSource
          OR entry.node_kind = "source_kind_bundle"
          OR entry.node_kind = "raw_source"
          OR entry.node_kind = "token_budget_summary_bundle"
        OPTIONAL MATCH (parent:VesselRecord {graph_namespace: $graph_namespace})-[rel]->(entry)
        WHERE type(rel) IN ["HAS_SOURCE_KIND", "CONTAINS_SOURCE", "CONTAINS"]
        WITH entry, collect(parent.data_id) AS parent_graph_node_ids
        RETURN
          entry.data_id AS candidate_node_id,
          coalesce(entry.display_name, entry.data_id) AS display_name,
          entry.node_kind AS node_kind,
          entry.data_kind AS data_kind,
          entry.created_at AS created_at,
          entry.written_at AS written_at,
          entry.source_trace_id AS source_trace_id,
          entry.payload_json AS payload_json,
          labels(entry) AS labels,
          [id IN parent_graph_node_ids WHERE id IS NOT NULL] AS parent_graph_node_ids,
          2 AS traversal_level
        ORDER BY traversal_level, created_at, candidate_node_id
        LIMIT 10000
        """,
        graph_namespace=graph_namespace,
    )
    return _records(result)


def _read_summary_records(tx: object, graph_namespace: str) -> list[object]:
    result = tx.run(
        """
        MATCH (summary:SummaryGraphNode {graph_namespace: $graph_namespace})
        OPTIONAL MATCH (summary)-[:SUMMARY_OF {graph_namespace: $graph_namespace}]->
          (target:VesselRecord {graph_namespace: $graph_namespace})
        RETURN
          summary.data_id AS summary_node_id,
          coalesce(summary.display_name, summary.data_id) AS summary_display_name,
          summary.data_kind AS data_kind,
          summary.info_class AS info_class,
          summary.generated_by AS generated_by,
          summary.payload_json AS payload_json,
          target.data_id AS target_graph_node_id,
          coalesce(target.display_name, target.data_id) AS target_display_name,
          target.node_kind AS target_node_kind
        ORDER BY summary.data_kind, summary.data_id
        LIMIT 10000
        """,
        graph_namespace=graph_namespace,
    )
    return _records(result)


def _entry_candidate_from_record(record: object) -> RLoopVesselEntryCandidateRecord:
    payload = _payload(record)
    candidate_id = _require_record_str(record, "candidate_node_id")
    return RLoopVesselEntryCandidateRecord(
        candidate_node_id=candidate_id,
        candidate_kind=_entry_candidate_kind(record, payload),
        display_name=_require_record_str(record, "display_name"),
        node_kind=_optional_record_str(record, "node_kind")
        or _text(payload.get("node_kind"))
        or None,
        data_kind=_optional_record_str(record, "data_kind")
        or _text(payload.get("data_kind"))
        or None,
        created_at=_optional_record_str(record, "created_at")
        or _text(payload.get("created_at"))
        or None,
        written_at=_optional_record_str(record, "written_at")
        or _text(payload.get("written_at"))
        or None,
        source_trace_id=_optional_record_str(record, "source_trace_id")
        or _first_string(_list_strings(payload.get("source_trace_ids"))),
        summary_depth=_optional_int(payload.get("summary_depth")),
        source_leaf_count=_optional_int(payload.get("source_leaf_count")),
        source_summary_count=_optional_int(payload.get("source_summary_count")),
        source_graph_node_ids=_list_strings(payload.get("source_graph_node_ids")),
        parent_graph_node_ids=_record_list_strings(record, "parent_graph_node_ids"),
    )


def _summary_candidate_from_record(record: object) -> RLoopVesselSummaryCandidateRecord:
    payload = _payload(record)
    summary_text = _text(payload.get("summary_text"))
    source_data_ids = _list_strings(payload.get("source_data_ids"))
    target_graph_node_id = (
        _optional_record_str(record, "target_graph_node_id")
        or _text(payload.get("target_graph_node_id"))
        or None
    )
    return RLoopVesselSummaryCandidateRecord(
        summary_node_id=_require_record_str(record, "summary_node_id"),
        summary_display_name=_require_record_str(record, "summary_display_name"),
        data_kind=_optional_record_str(record, "data_kind")
        or _text(payload.get("data_kind"))
        or None,
        summary_depth=_optional_int(payload.get("summary_depth")),
        summary_status=_text(payload.get("summary_status")) or None,
        validity_status=_text(payload.get("validity_status")) or None,
        review_status=_text(payload.get("review_status")) or None,
        info_class=_optional_record_str(record, "info_class")
        or _text(payload.get("info_class"))
        or None,
        generated_by=_optional_record_str(record, "generated_by")
        or _text(payload.get("generated_by"))
        or None,
        target_graph_node_id=target_graph_node_id,
        target_display_name=_optional_record_str(record, "target_display_name"),
        target_node_kind=_optional_record_str(record, "target_node_kind")
        or _text(payload.get("target_node_kind"))
        or None,
        source_leaf_count=_optional_int(payload.get("source_leaf_count")),
        source_summary_count=_optional_int(payload.get("source_summary_count")),
        source_graph_node_ids=_list_strings(payload.get("source_graph_node_ids")),
        source_data_ids=_unique_strings(source_data_ids + [target_graph_node_id]),
        source_trace_ids=_list_strings(payload.get("source_trace_ids")),
        summary_text_char_count=len(summary_text),
        summary_text=summary_text,
        summary_text_preview=_preview(summary_text),
    )


def _entry_candidate_kind(record: object, payload: dict[str, object]) -> str:
    labels = _record_value(record, "labels")
    if isinstance(labels, list):
        if "TimeAxis" in labels:
            return "time_axis"
        if "SourceIngestBundle" in labels:
            return "source_ingest_bundle"
        if "SourceKindBundle" in labels:
            return "source_kind_bundle"
        if "RawSource" in labels:
            return "raw_source"
        if "TimeBundle" in labels:
            return "time_bundle"
    node_kind = _optional_record_str(record, "node_kind") or _text(payload.get("node_kind"))
    if node_kind == "time_axis":
        return "time_axis"
    if node_kind in {
        "time_bundle",
        "source_ingest_time_bundle",
        "source_kind_bundle",
        "raw_source",
        "token_budget_summary_bundle",
    }:
        return node_kind
    return "entry_bundle"


def _is_active_r_loop_summary(record: object) -> bool:
    payload = _payload(record)
    return (
        _text(payload.get("summary_status")) == "ran"
        and _text(payload.get("validity_status")) == "active"
    )


def _balanced_summary_candidate_limit(
    candidates: list[RLoopVesselSummaryCandidateRecord],
    limit: int,
) -> list[RLoopVesselSummaryCandidateRecord]:
    if len(candidates) <= limit:
        return list(candidates)

    groups: dict[tuple[str, str, str], list[RLoopVesselSummaryCandidateRecord]] = {}
    for candidate in candidates:
        key = _summary_candidate_balance_key(candidate)
        groups.setdefault(key, []).append(candidate)

    ordered_keys = sorted(groups)
    selected: list[RLoopVesselSummaryCandidateRecord] = []
    while len(selected) < limit and ordered_keys:
        next_keys: list[tuple[str, str, str]] = []
        for key in ordered_keys:
            group = groups[key]
            if group and len(selected) < limit:
                selected.append(group.pop(0))
            if group:
                next_keys.append(key)
        ordered_keys = next_keys
    return selected


def _expand_summary_candidates_by_source_summary_children(
    *,
    base_candidates: list[RLoopVesselSummaryCandidateRecord],
    all_candidates: list[RLoopVesselSummaryCandidateRecord],
    limit: int,
) -> _SummaryExpansion:
    """Copy source summary children needed for hierarchical R traversal.

    This is not a relevance decision. The code only follows summary->source IDs
    that already point at active summary records loaded from Neo4j.
    """

    selected = list(base_candidates)
    selected_ids = {candidate.summary_node_id for candidate in selected}
    candidates_by_id = {
        candidate.summary_node_id: candidate for candidate in all_candidates
    }
    expanded_node_ids: list[str] = []
    expansion_budget = max(0, limit)
    frontier = list(base_candidates)
    truncated = False

    for _depth in range(R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_MAX_DEPTH):
        next_frontier: list[RLoopVesselSummaryCandidateRecord] = []
        for source_id in _summary_source_summary_ids(frontier):
            if source_id in selected_ids:
                continue
            child = candidates_by_id.get(source_id)
            if child is None:
                continue
            if expansion_budget <= 0:
                truncated = True
                break
            selected.append(child)
            selected_ids.add(child.summary_node_id)
            expanded_node_ids.append(child.summary_node_id)
            next_frontier.append(child)
            expansion_budget -= 1
        if truncated or not next_frontier:
            break
        frontier = next_frontier

    return _SummaryExpansion(
        candidates=selected,
        base_summary_candidate_count=len(base_candidates),
        summary_child_expanded_node_ids=expanded_node_ids,
        summary_child_expansion_truncated=truncated,
    )


def _summary_source_summary_ids(
    candidates: list[RLoopVesselSummaryCandidateRecord],
) -> list[str]:
    values: list[str] = []
    for candidate in candidates:
        values.extend(
            source_id
            for source_id in candidate.source_graph_node_ids
            if source_id.startswith("graph:summary:")
        )
        values.extend(
            source_id
            for source_id in candidate.source_data_ids
            if source_id.startswith("graph:summary:")
        )
    return _unique_strings(values)


def _summary_candidate_balance_key(
    candidate: RLoopVesselSummaryCandidateRecord,
) -> tuple[int, int, str, str]:
    depth = candidate.summary_depth if candidate.summary_depth is not None else -1
    return (
        _summary_candidate_data_kind_rank(candidate.data_kind),
        -depth,
        candidate.data_kind or "unknown",
        candidate.info_class or "unknown",
    )


def _summary_candidate_data_kind_rank(data_kind: str | None) -> int:
    if data_kind == "token_budget_bundle_summary":
        return 0
    if data_kind == "source_kind_summary":
        return 1
    if data_kind == "source_leaf_summary":
        return 2
    return 3


def _count_summaries_by_data_kind(
    candidates: list[RLoopVesselSummaryCandidateRecord],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        key = candidate.data_kind or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_summaries_by_depth(
    candidates: list[RLoopVesselSummaryCandidateRecord],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        key = str(candidate.summary_depth) if candidate.summary_depth is not None else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _build_packet_lines(
    entry_candidates: list[RLoopVesselEntryCandidateRecord],
    active_summary_candidates: list[RLoopVesselSummaryCandidateRecord],
    *,
    base_entry_candidate_count: int,
    exact_child_expanded_node_ids: list[str],
    exact_child_expansion_truncated: bool,
    base_summary_candidate_count: int,
    summary_child_expanded_node_ids: list[str],
    summary_child_expansion_truncated: bool,
) -> list[str]:
    lines = [
        f"R loop Vessel entry candidates: {len(entry_candidates)}",
        f"R loop Vessel base entry candidates: {base_entry_candidate_count}",
        "R loop Vessel exact child expansion: "
        f"{len(exact_child_expanded_node_ids)}"
        f" / truncated={str(exact_child_expansion_truncated).lower()}",
        f"R loop active summary candidates: {len(active_summary_candidates)}",
        f"R loop base active summary candidates: {base_summary_candidate_count}",
        "R loop summary child expansion: "
        f"{len(summary_child_expanded_node_ids)}"
        f" / truncated={str(summary_child_expansion_truncated).lower()}",
    ]
    if entry_candidates:
        lines.append("Entry candidates")
        for candidate in entry_candidates:
            lines.append(
                "  "
                f"{candidate.candidate_kind} "
                f"[{candidate.candidate_node_id}] "
                f"{candidate.display_name}"
            )
    if active_summary_candidates:
        lines.append("Active summary candidates")
        for candidate in active_summary_candidates:
            lines.append(
                "  "
                f"{candidate.data_kind or 'unknown'}"
                f"(depth={candidate.summary_depth if candidate.summary_depth is not None else 'unknown'}, "
                f"info={candidate.info_class or 'unknown'}) "
                f"[{candidate.summary_node_id}]"
            )
            if candidate.target_graph_node_id:
                target_name = candidate.target_display_name or candidate.target_graph_node_id
                lines.append(f"    SUMMARY_OF -> {target_name} [{candidate.target_graph_node_id}]")
            if candidate.summary_text_preview:
                lines.append(f"    preview: {candidate.summary_text_preview}")
    return lines


def _config_failure(config: GraphVesselNeo4jConfig) -> tuple[str, str] | None:
    if not config.uri or not config.user or not config.database:
        return (
            "neo4j_config_missing",
            "Neo4j uri/user/database config is incomplete.",
        )
    if config.password is None and not config.allow_no_auth:
        return (
            "neo4j_config_missing",
            "Neo4j password is not configured. Set SONGRYEON_NEO4J_PASSWORD or pass --password.",
        )
    return None


def _validate_packet(packet: RLoopVesselReadPacketFrame) -> None:
    if packet.generated_by != R_LOOP_VESSEL_READ_PACKET_GENERATOR:
        raise ValueError("RLoopVesselReadPacketFrame.generated_by must be packet builder")
    if packet.info_class != "absolute":
        raise ValueError("RLoopVesselReadPacketFrame.info_class must be absolute")
    if packet.semantic_judgement_status != "not_run":
        raise ValueError("RLoopVesselReadPacketFrame.semantic_judgement_status must be not_run")
    if packet.read_status not in R_LOOP_VESSEL_READ_PACKET_STATUSES:
        raise ValueError("RLoopVesselReadPacketFrame.read_status is invalid")
    if packet.target_consumer != "R_LOOP":
        raise ValueError("RLoopVesselReadPacketFrame.target_consumer must be R_LOOP")
    if (
        packet.summary_child_expansion_policy_id
        != R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_POLICY_ID
    ):
        raise ValueError("RLoopVesselReadPacketFrame summary child expansion policy is invalid")
    if packet.base_summary_candidate_count < 0:
        raise ValueError("RLoopVesselReadPacketFrame base_summary_candidate_count is invalid")
    if packet.summary_candidate_count < packet.base_summary_candidate_count:
        raise ValueError("RLoopVesselReadPacketFrame summary count is below base count")
    if packet.summary_child_expanded_count != len(packet.summary_child_expanded_node_ids):
        raise ValueError("RLoopVesselReadPacketFrame summary child expansion count mismatch")
    if packet.exact_child_expansion_policy_id != R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_POLICY_ID:
        raise ValueError("RLoopVesselReadPacketFrame exact child expansion policy is invalid")
    if packet.base_entry_candidate_count < 0:
        raise ValueError("RLoopVesselReadPacketFrame base_entry_candidate_count is invalid")
    if packet.exact_child_expanded_entry_count != len(packet.exact_child_expanded_node_ids):
        raise ValueError("RLoopVesselReadPacketFrame exact child expansion count mismatch")
    if packet.entry_candidate_count < packet.base_entry_candidate_count:
        raise ValueError("RLoopVesselReadPacketFrame entry count is below base count")
    if packet.read_status == "passed":
        if packet.entry_candidate_count + packet.summary_candidate_count < 1:
            raise ValueError("passed RLoopVesselReadPacketFrame must include candidates")


def _record_payload_if_missing(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
    created_at: str,
    source_trace_id: str,
    created_data_ids: list[str],
    existing_data_ids: list[str],
) -> None:
    existing = data_store.get_record(data_id)
    if existing is not None:
        if existing.data_type != data_type:
            raise ValueError(f"R loop Vessel read packet data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"R loop Vessel read packet data_id collision with different payload: {data_id}")
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


def _load_neo4j_driver_factory() -> Neo4jDriverFactory | None:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return None
    return GraphDatabase.driver


def _records(result: object) -> list[object]:
    return list(result)


def _require_record_str(record: object, field_name: str) -> str:
    value = _record_value(record, field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"R loop Vessel record field is missing: {field_name}")
    return value


def _optional_record_str(record: object, field_name: str) -> str | None:
    value = _record_value(record, field_name)
    return value if isinstance(value, str) and value else None


def _record_list_strings(record: object, field_name: str) -> list[str]:
    return _list_strings(_record_value(record, field_name))


def _record_value(record: object, field_name: str) -> object:
    try:
        return record[field_name]  # type: ignore[index]
    except (KeyError, TypeError):
        data = getattr(record, "data", None)
        if callable(data):
            payload = data()
            if isinstance(payload, dict):
                return payload.get(field_name)
    return None


def _payload(record: object) -> dict[str, object]:
    payload_json = _optional_record_str(record, "payload_json")
    if not payload_json:
        return {}
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _list_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _first_string(values: list[str]) -> str | None:
    return values[0] if values else None


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _preview(text: str, *, max_chars: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _stable_suffix(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "R_LOOP_VESSEL_READ_PACKET_DATA_TYPE",
    "R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_POLICY_ID",
    "R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_POLICY_ID",
    "R_LOOP_VESSEL_READ_PACKET_GENERATOR",
    "R_LOOP_VESSEL_READ_PACKET_POLICY_ID",
    "R_LOOP_VESSEL_READ_PACKET_SCHEMA_NAME",
    "R_LOOP_VESSEL_READ_PACKET_STATUSES",
    "RLoopVesselEntryCandidateRecord",
    "RLoopVesselReadPacketFrame",
    "RLoopVesselSummaryCandidateRecord",
    "RecordedRLoopVesselReadPacket",
    "build_r_loop_vessel_read_packet_from_neo4j",
    "r_loop_vessel_read_packet_id",
    "record_r_loop_vessel_read_packet",
]
