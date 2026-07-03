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


GRAPH_VESSEL_NEO4J_INSPECT_RESULT_DATA_TYPE = "graph_vessel:neo4j_inspect_result"
GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR = "CODE:GRAPH_VESSEL_NEO4J_INSPECTOR"
GRAPH_VESSEL_NEO4J_INSPECT_POLICY_ID = "VESSEL_INSPECT_MANUAL_WALK_V0"
GRAPH_VESSEL_NEO4J_INSPECT_SCHEMA_NAME = "GraphVesselNeo4jInspectResultFrame"
GRAPH_VESSEL_NEO4J_INSPECT_STATUSES = {
    "passed",
    "empty",
    "adapter_unavailable",
    "read_failed",
}

Neo4jDriverFactory = Callable[..., Any]


@dataclass(frozen=True)
class GraphVesselNeo4jInspectPathItem:
    core_data_id: str
    core_display_name: str
    axis_data_id: str
    axis_display_name: str
    bundle_data_id: str | None
    bundle_display_name: str | None
    bundle_created_at: str | None
    bundle_written_at: str | None
    raw_capsule_data_id: str | None
    raw_capsule_display_name: str | None
    raw_capsule_created_at: str | None
    raw_capsule_written_at: str | None
    raw_capsule_source_trace_id: str | None


@dataclass(frozen=True)
class GraphVesselNeo4jInspectSummarySampleItem:
    summary_data_id: str
    summary_display_name: str
    data_kind: str | None
    summary_depth: int | None
    summary_status: str | None
    validity_status: str | None
    review_status: str | None
    target_graph_node_id: str | None
    target_display_name: str | None
    target_node_kind: str | None
    source_leaf_count: int | None
    source_summary_count: int | None
    info_class: str | None
    generated_by: str | None
    summary_text_preview: str


@dataclass(frozen=True)
class GraphVesselNeo4jInspectResultFrame:
    result_id: str
    created_at: str
    policy_id: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str
    inspect_status: str
    failure_type: str | None
    failure_reason: str | None
    inspected_path_count: int
    core_count: int | None
    time_axis_count: int | None
    time_bundle_count: int | None
    raw_capsule_count: int | None
    summary_count: int | None
    active_summary_count: int | None
    invalidated_summary_count: int | None
    summary_count_by_data_kind: dict[str, int]
    summary_count_by_depth: dict[str, int]
    summary_sample_items: list[dict[str, object]]
    summary_lines: list[str]
    path_items: list[dict[str, object]]
    tree_lines: list[str]
    source_data_ids: list[str]
    source_trace_ids: list[str]
    generated_by: str = GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = GRAPH_VESSEL_NEO4J_INSPECT_SCHEMA_NAME


@dataclass(frozen=True)
class RecordedGraphVesselNeo4jInspectResult:
    result: GraphVesselNeo4jInspectResultFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def graph_vessel_neo4j_inspect_result_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_vessel:neo4j_inspect_result:{_stable_suffix(batch_id)}"


def inspect_graph_vessel_from_neo4j(
    *,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_inspect",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> GraphVesselNeo4jInspectResultFrame:
    timestamp = created_at or _now_iso()
    safe_limit = max(1, min(limit, 500))
    base = _InspectBase(
        result_id=graph_vessel_neo4j_inspect_result_id(batch_id),
        created_at=timestamp,
        target_adapter_name=SONGRYEON_VESSEL_SERVICE_NAME,
        vessel_database_name=config.database,
        graph_namespace=SONGRYEON_GRAPH_NAMESPACE,
    )

    config_failure = _config_failure(config)
    if config_failure is not None:
        failure_type, failure_reason = config_failure
        return _make_result(
            base=base,
            inspect_status="adapter_unavailable",
            failure_type=failure_type,
            failure_reason=failure_reason,
            counts=_empty_counts(),
            path_items=[],
        )

    driver_factory = driver_factory or _load_neo4j_driver_factory()
    if driver_factory is None:
        return _make_result(
            base=base,
            inspect_status="adapter_unavailable",
            failure_type="neo4j_driver_missing",
            failure_reason="Python neo4j package is not installed.",
            counts=_empty_counts(),
            path_items=[],
        )

    try:
        auth = None if config.allow_no_auth and config.password is None else (config.user, config.password)
        driver = driver_factory(config.uri, auth=auth)
        try:
            with driver.session(database=config.database) as session:
                (
                    counts,
                    path_items,
                    summary_items,
                    summary_count_by_data_kind,
                    summary_count_by_depth,
                ) = session.execute_read(
                    _execute_inspect,
                    SONGRYEON_GRAPH_NAMESPACE,
                    safe_limit,
                )
        finally:
            close = getattr(driver, "close", None)
            if callable(close):
                close()
    except Exception as exc:
        return _make_result(
            base=base,
            inspect_status="read_failed",
            failure_type="neo4j_read_failed",
            failure_reason=f"{type(exc).__name__}: {exc}",
            counts=_empty_counts(),
            path_items=[],
        )

    return _make_result(
        base=base,
        inspect_status="passed" if path_items else "empty",
        failure_type=None if path_items else "no_inspectable_path",
        failure_reason=None if path_items else "No CoreEgo -> TimeAxis path was found.",
        counts=counts,
        path_items=path_items,
        summary_items=summary_items,
        summary_count_by_data_kind=summary_count_by_data_kind,
        summary_count_by_depth=summary_count_by_depth,
    )


def record_graph_vessel_neo4j_inspect_result(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    config: GraphVesselNeo4jConfig,
    batch_id: str = "manual_vessel_inspect",
    limit: int = 50,
    created_at: str | None = None,
    driver_factory: Neo4jDriverFactory | None = None,
) -> RecordedGraphVesselNeo4jInspectResult:
    result = inspect_graph_vessel_from_neo4j(
        config=config,
        batch_id=batch_id,
        limit=limit,
        created_at=created_at,
        driver_factory=driver_factory,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="graph_vessel_neo4j_inspector",
        event_type="node_output",
        timestamp=result.created_at,
        input_ref=[],
        output_ref=[result.result_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=result.result_id,
        data_type=GRAPH_VESSEL_NEO4J_INSPECT_RESULT_DATA_TYPE,
        payload=asdict(result),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedGraphVesselNeo4jInspectResult(
        result=result,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


@dataclass(frozen=True)
class _InspectBase:
    result_id: str
    created_at: str
    target_adapter_name: str
    vessel_database_name: str
    graph_namespace: str


@dataclass(frozen=True)
class _InspectCounts:
    core_count: int | None
    time_axis_count: int | None
    time_bundle_count: int | None
    raw_capsule_count: int | None
    summary_count: int | None
    active_summary_count: int | None
    invalidated_summary_count: int | None


def _make_result(
    *,
    base: _InspectBase,
    inspect_status: str,
    failure_type: str | None,
    failure_reason: str | None,
    counts: _InspectCounts,
    path_items: list[GraphVesselNeo4jInspectPathItem],
    summary_items: list[GraphVesselNeo4jInspectSummarySampleItem] | None = None,
    summary_count_by_data_kind: dict[str, int] | None = None,
    summary_count_by_depth: dict[str, int] | None = None,
) -> GraphVesselNeo4jInspectResultFrame:
    path_item_payloads = [asdict(item) for item in path_items]
    summary_items = summary_items or []
    summary_item_payloads = [asdict(item) for item in summary_items]
    source_data_ids = _unique_strings(
        [
            value
            for item in path_items
            for value in (
                item.core_data_id,
                item.axis_data_id,
                item.bundle_data_id,
                item.raw_capsule_data_id,
            )
        ]
        + [item.summary_data_id for item in summary_items]
        + [item.target_graph_node_id for item in summary_items]
    )
    source_trace_ids = _unique_strings(
        [item.raw_capsule_source_trace_id for item in path_items]
    )
    result = GraphVesselNeo4jInspectResultFrame(
        result_id=base.result_id,
        created_at=base.created_at,
        policy_id=GRAPH_VESSEL_NEO4J_INSPECT_POLICY_ID,
        target_adapter_name=base.target_adapter_name,
        vessel_database_name=base.vessel_database_name,
        graph_namespace=base.graph_namespace,
        inspect_status=inspect_status,
        failure_type=failure_type,
        failure_reason=failure_reason,
        inspected_path_count=len(path_items),
        core_count=counts.core_count,
        time_axis_count=counts.time_axis_count,
        time_bundle_count=counts.time_bundle_count,
        raw_capsule_count=counts.raw_capsule_count,
        summary_count=counts.summary_count,
        active_summary_count=counts.active_summary_count,
        invalidated_summary_count=counts.invalidated_summary_count,
        summary_count_by_data_kind=summary_count_by_data_kind or {},
        summary_count_by_depth=summary_count_by_depth or {},
        summary_sample_items=summary_item_payloads,
        summary_lines=_build_summary_lines(summary_items),
        path_items=path_item_payloads,
        tree_lines=_build_tree_lines(path_items),
        source_data_ids=source_data_ids,
        source_trace_ids=source_trace_ids,
    )
    _validate_inspect_result(result)
    return result


def _execute_inspect(
    tx: object,
    graph_namespace: str,
    limit: int,
) -> tuple[
    _InspectCounts,
    list[GraphVesselNeo4jInspectPathItem],
    list[GraphVesselNeo4jInspectSummarySampleItem],
    dict[str, int],
    dict[str, int],
]:
    counts = _InspectCounts(
        core_count=_count_label(tx, graph_namespace, "CoreEgo"),
        time_axis_count=_count_label(tx, graph_namespace, "TimeAxis"),
        time_bundle_count=_count_label(tx, graph_namespace, "TimeBundle"),
        raw_capsule_count=_count_label(tx, graph_namespace, "RawCapsule"),
        summary_count=_count_label(tx, graph_namespace, "SummaryGraphNode"),
        active_summary_count=None,
        invalidated_summary_count=None,
    )
    summary_records = _read_summary_records(tx, graph_namespace)
    summary_items = [
        _summary_item_from_record(record)
        for record in summary_records[:limit]
    ]
    summary_count_by_data_kind = _count_summary_items_by_data_kind(summary_records)
    summary_count_by_depth = _count_summary_items_by_depth(summary_records)
    active_summary_count = sum(
        1
        for record in summary_records
        if _summary_payload(record).get("validity_status") == "active"
    )
    invalidated_summary_count = sum(
        1
        for record in summary_records
        if _text(_summary_payload(record).get("validity_status")).startswith("invalidated")
    )
    counts = _InspectCounts(
        core_count=counts.core_count,
        time_axis_count=counts.time_axis_count,
        time_bundle_count=counts.time_bundle_count,
        raw_capsule_count=counts.raw_capsule_count,
        summary_count=counts.summary_count,
        active_summary_count=active_summary_count,
        invalidated_summary_count=invalidated_summary_count,
    )
    result = tx.run(
        """
        MATCH (core:CoreEgo {graph_namespace: $graph_namespace})
          -[:HAS_AXIS {graph_namespace: $graph_namespace}]->
          (axis:TimeAxis {graph_namespace: $graph_namespace})
        OPTIONAL MATCH (axis)-[:HAS_BUNDLE {graph_namespace: $graph_namespace}]->
          (bundle:TimeBundle {graph_namespace: $graph_namespace})
        OPTIONAL MATCH (bundle)-[:CONTAINS_MEMORY {graph_namespace: $graph_namespace}]->
          (capsule:RawCapsule {graph_namespace: $graph_namespace})
        RETURN
          core.data_id AS core_data_id,
          coalesce(core.display_name, core.data_id) AS core_display_name,
          axis.data_id AS axis_data_id,
          coalesce(axis.display_name, axis.data_id) AS axis_display_name,
          bundle.data_id AS bundle_data_id,
          coalesce(bundle.display_name, bundle.data_id) AS bundle_display_name,
          bundle.created_at AS bundle_created_at,
          bundle.written_at AS bundle_written_at,
          capsule.data_id AS raw_capsule_data_id,
          coalesce(capsule.display_name, capsule.data_id) AS raw_capsule_display_name,
          capsule.created_at AS raw_capsule_created_at,
          capsule.written_at AS raw_capsule_written_at,
          capsule.source_trace_id AS raw_capsule_source_trace_id
        ORDER BY bundle.created_at, bundle.data_id, capsule.created_at, capsule.data_id
        LIMIT $limit
        """,
        graph_namespace=graph_namespace,
        limit=limit,
    )
    return (
        counts,
        [_path_item_from_record(record) for record in _records(result)],
        summary_items,
        summary_count_by_data_kind,
        summary_count_by_depth,
    )


def _path_item_from_record(record: object) -> GraphVesselNeo4jInspectPathItem:
    return GraphVesselNeo4jInspectPathItem(
        core_data_id=_require_record_str(record, "core_data_id"),
        core_display_name=_require_record_str(record, "core_display_name"),
        axis_data_id=_require_record_str(record, "axis_data_id"),
        axis_display_name=_require_record_str(record, "axis_display_name"),
        bundle_data_id=_optional_record_str(record, "bundle_data_id"),
        bundle_display_name=_optional_record_str(record, "bundle_display_name"),
        bundle_created_at=_optional_record_str(record, "bundle_created_at"),
        bundle_written_at=_optional_record_str(record, "bundle_written_at"),
        raw_capsule_data_id=_optional_record_str(record, "raw_capsule_data_id"),
        raw_capsule_display_name=_optional_record_str(record, "raw_capsule_display_name"),
        raw_capsule_created_at=_optional_record_str(record, "raw_capsule_created_at"),
        raw_capsule_written_at=_optional_record_str(record, "raw_capsule_written_at"),
        raw_capsule_source_trace_id=_optional_record_str(record, "raw_capsule_source_trace_id"),
    )


def _build_tree_lines(path_items: list[GraphVesselNeo4jInspectPathItem]) -> list[str]:
    if not path_items:
        return []
    lines: list[str] = []
    seen_core: set[str] = set()
    seen_axis: set[tuple[str, str]] = set()
    seen_bundle: set[tuple[str, str, str]] = set()
    for item in path_items:
        if item.core_data_id not in seen_core:
            lines.append(f"{item.core_display_name} [{item.core_data_id}]")
            seen_core.add(item.core_data_id)
        axis_key = (item.core_data_id, item.axis_data_id)
        if axis_key not in seen_axis:
            lines.append(f"  HAS_AXIS -> {item.axis_display_name} [{item.axis_data_id}]")
            seen_axis.add(axis_key)
        if item.bundle_data_id is None:
            continue
        bundle_key = (item.core_data_id, item.axis_data_id, item.bundle_data_id)
        if bundle_key not in seen_bundle:
            lines.append(
                f"    HAS_BUNDLE -> {item.bundle_display_name or item.bundle_data_id} "
                f"[{item.bundle_data_id}]"
            )
            seen_bundle.add(bundle_key)
        if item.raw_capsule_data_id is not None:
            lines.append(
                f"      CONTAINS_MEMORY -> "
                f"{item.raw_capsule_display_name or item.raw_capsule_data_id} "
                f"[{item.raw_capsule_data_id}]"
            )
    return lines


def _read_summary_records(tx: object, graph_namespace: str) -> list[object]:
    result = tx.run(
        """
        MATCH (summary:SummaryGraphNode {graph_namespace: $graph_namespace})
        OPTIONAL MATCH (summary)-[:SUMMARY_OF {graph_namespace: $graph_namespace}]->
          (target:VesselRecord {graph_namespace: $graph_namespace})
        RETURN
          summary.data_id AS summary_data_id,
          coalesce(summary.display_name, summary.data_id) AS summary_display_name,
          summary.data_kind AS summary_data_kind,
          summary.info_class AS summary_info_class,
          summary.generated_by AS summary_generated_by,
          summary.payload_json AS summary_payload_json,
          target.data_id AS target_graph_node_id,
          coalesce(target.display_name, target.data_id) AS target_display_name,
          target.node_kind AS target_node_kind
        ORDER BY summary.data_kind, summary.data_id
        LIMIT 10000
        """,
        graph_namespace=graph_namespace,
    )
    return _records(result)


def _summary_item_from_record(record: object) -> GraphVesselNeo4jInspectSummarySampleItem:
    payload = _summary_payload(record)
    summary_text = _text(payload.get("summary_text"))
    target_graph_node_id = (
        _optional_record_str(record, "target_graph_node_id")
        or _text(payload.get("target_graph_node_id"))
        or None
    )
    return GraphVesselNeo4jInspectSummarySampleItem(
        summary_data_id=_require_record_str(record, "summary_data_id"),
        summary_display_name=_require_record_str(record, "summary_display_name"),
        data_kind=_optional_record_str(record, "summary_data_kind")
        or _text(payload.get("data_kind"))
        or None,
        summary_depth=_optional_int(payload.get("summary_depth")),
        summary_status=_text(payload.get("summary_status")) or None,
        validity_status=_text(payload.get("validity_status")) or None,
        review_status=_text(payload.get("review_status")) or None,
        target_graph_node_id=target_graph_node_id,
        target_display_name=_optional_record_str(record, "target_display_name"),
        target_node_kind=_optional_record_str(record, "target_node_kind")
        or _text(payload.get("target_node_kind"))
        or None,
        source_leaf_count=_optional_int(payload.get("source_leaf_count")),
        source_summary_count=_optional_int(payload.get("source_summary_count")),
        info_class=_optional_record_str(record, "summary_info_class")
        or _text(payload.get("info_class"))
        or None,
        generated_by=_optional_record_str(record, "summary_generated_by")
        or _text(payload.get("generated_by"))
        or None,
        summary_text_preview=_preview(summary_text),
    )


def _count_summary_items_by_data_kind(records: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        payload = _summary_payload(record)
        data_kind = (
            _optional_record_str(record, "summary_data_kind")
            or _text(payload.get("data_kind"))
            or "unknown"
        )
        counts[data_kind] = counts.get(data_kind, 0) + 1
    return dict(sorted(counts.items()))


def _count_summary_items_by_depth(records: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        depth = _optional_int(_summary_payload(record).get("summary_depth"))
        key = str(depth) if depth is not None else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _build_summary_lines(
    summary_items: list[GraphVesselNeo4jInspectSummarySampleItem],
) -> list[str]:
    if not summary_items:
        return []
    lines = ["Summary samples"]
    for item in summary_items:
        lines.append(
            "  "
            f"{item.data_kind or 'unknown'}"
            f"(depth={item.summary_depth if item.summary_depth is not None else 'unknown'}, "
            f"info={item.info_class or 'unknown'}) "
            f"[{item.summary_data_id}]"
        )
        if item.target_graph_node_id:
            target_name = item.target_display_name or item.target_graph_node_id
            lines.append(f"    SUMMARY_OF -> {target_name} [{item.target_graph_node_id}]")
        if item.summary_text_preview:
            lines.append(f"    preview: {item.summary_text_preview}")
    return lines


def _count_label(tx: object, graph_namespace: str, label: str) -> int:
    _validate_cypher_token(label)
    result = tx.run(
        f"""
        MATCH (n:{label} {{graph_namespace: $graph_namespace}})
        RETURN count(n) AS count
        """,
        graph_namespace=graph_namespace,
    )
    return _single_count(result)


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


def _empty_counts() -> _InspectCounts:
    return _InspectCounts(
        core_count=None,
        time_axis_count=None,
        time_bundle_count=None,
        raw_capsule_count=None,
        summary_count=None,
        active_summary_count=None,
        invalidated_summary_count=None,
    )


def _validate_inspect_result(result: GraphVesselNeo4jInspectResultFrame) -> None:
    if result.generated_by != GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR:
        raise ValueError("GraphVesselNeo4jInspectResultFrame.generated_by must be inspector")
    if result.info_class != "absolute":
        raise ValueError("GraphVesselNeo4jInspectResultFrame.info_class must be absolute")
    if result.semantic_judgement_status != "not_run":
        raise ValueError("GraphVesselNeo4jInspectResultFrame.semantic_judgement_status must be not_run")
    if result.inspect_status not in GRAPH_VESSEL_NEO4J_INSPECT_STATUSES:
        raise ValueError("GraphVesselNeo4jInspectResultFrame.inspect_status is invalid")
    if result.inspect_status == "passed" and result.inspected_path_count < 1:
        raise ValueError("passed inspect result must include at least one path item")


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
            raise ValueError(f"Neo4j inspect result data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"Neo4j inspect result data_id collision with different payload: {data_id}")
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
        raise ValueError(f"Neo4j inspect record field is missing: {field_name}")
    return value


def _optional_record_str(record: object, field_name: str) -> str | None:
    value = _record_value(record, field_name)
    return value if isinstance(value, str) and value else None


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


def _summary_payload(record: object) -> dict[str, object]:
    payload_json = _optional_record_str(record, "summary_payload_json")
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


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _preview(text: str, *, max_chars: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _single_count(result: object) -> int:
    single = getattr(result, "single", None)
    if callable(single):
        record = single()
        if record is None:
            return 0
        try:
            return int(record["count"])
        except (KeyError, TypeError, ValueError):
            return 0
    try:
        first = next(iter(result))
        return int(first["count"])
    except (KeyError, TypeError, ValueError, StopIteration):
        return 0


def _validate_cypher_token(value: str) -> None:
    if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise ValueError(f"unsafe Neo4j token: {value}")


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
    "GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR",
    "GRAPH_VESSEL_NEO4J_INSPECT_POLICY_ID",
    "GRAPH_VESSEL_NEO4J_INSPECT_RESULT_DATA_TYPE",
    "GRAPH_VESSEL_NEO4J_INSPECT_STATUSES",
    "GraphVesselNeo4jInspectPathItem",
    "GraphVesselNeo4jInspectResultFrame",
    "GraphVesselNeo4jInspectSummarySampleItem",
    "RecordedGraphVesselNeo4jInspectResult",
    "graph_vessel_neo4j_inspect_result_id",
    "inspect_graph_vessel_from_neo4j",
    "record_graph_vessel_neo4j_inspect_result",
]
