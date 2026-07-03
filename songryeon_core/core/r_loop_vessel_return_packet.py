from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore


R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE = "r_loop:vessel_return_packet"
R_LOOP_VESSEL_RETURN_PACKET_GENERATOR = "CODE:NODE_0_R_VESSEL_RETURN_PACKET"
R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME = "RLoopVesselReturnPacketFrame"
R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION = "0.1"
R_LOOP_VESSEL_RETURN_STATUSES = {"available", "failed"}


@dataclass(frozen=True)
class RLoopVesselReturnPacketFrame:
    """node_0 labels the finished Vessel R traversal for downstream nodes."""

    packet_id: str
    turn_id: str
    target: str
    mode: str
    return_status: str
    source_start_handoff_packet_id: str | None
    source_activity_ledger_frame_id: str
    source_traverse_result_frame_id: str
    source_return_summary_frame_id: str | None
    source_read_packet_id: str
    r_loop_task_status: str
    traverse_status: str
    failure_stage: str | None
    failure_type: str | None
    failure_reason: str | None
    selected_graph_node_count: int
    inspected_graph_node_count: int
    summary_material_count: int
    raw_original_material_count: int
    node3_material_ready: bool
    node3_material_source_data_ids: list[str]
    source_trace_ids: list[str]
    source_data_ids: list[str]
    generated_by: str = R_LOOP_VESSEL_RETURN_PACKET_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME
    schema_version: str = R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION


@dataclass(frozen=True)
class RecordedRLoopVesselReturnPacket:
    packet: RLoopVesselReturnPacketFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def r_loop_vessel_return_packet_id(frame_label: str) -> str:
    if not frame_label:
        raise ValueError("frame_label must not be empty")
    return f"r_loop:vessel_return_packet:{_stable_suffix(frame_label)}"


def build_r_loop_vessel_return_packet(
    *,
    data_store: DataStore,
    turn_id: str,
    activity_ledger_payload: dict[str, object],
    frame_label: str,
) -> RLoopVesselReturnPacketFrame:
    activity_ledger_id = _required_text(activity_ledger_payload, "frame_id")
    traverse_result_id = _required_text(activity_ledger_payload, "traverse_result_frame_id")
    read_packet_id = _required_text(activity_ledger_payload, "source_read_packet_id")
    traverse_payload = _payload_by_id(data_store, traverse_result_id)
    return_summary_id = _optional_text(
        activity_ledger_payload.get("return_summary_frame_id")
    )
    traverse_status = _text(
        traverse_payload,
        "traverse_status",
        fallback=_text(activity_ledger_payload, "traverse_status", fallback="failed"),
    )
    r_loop_task_status = _text(
        traverse_payload,
        "r_loop_task_status",
        fallback=_optional_text(activity_ledger_payload.get("r_loop_task_status"))
        or "failed",
    )
    selected_ids = _string_list(
        traverse_payload.get("selected_graph_node_ids")
        if traverse_payload
        else activity_ledger_payload.get("selected_graph_node_ids")
    )
    inspected_ids = _string_list(
        traverse_payload.get("inspected_graph_node_ids")
        if traverse_payload
        else activity_ledger_payload.get("inspected_graph_node_ids")
    )
    return_status = "available" if traverse_status == "completed" else "failed"
    material_source_ids = _unique_strings(
        [
            traverse_result_id,
            read_packet_id,
            return_summary_id,
            *selected_ids,
            *inspected_ids,
        ]
    )
    frame = RLoopVesselReturnPacketFrame(
        packet_id=r_loop_vessel_return_packet_id(frame_label),
        turn_id=turn_id,
        target="node_1_or_node_2",
        mode="vessel_r_return_packet",
        return_status=return_status,
        source_start_handoff_packet_id=_optional_text(
            activity_ledger_payload.get("source_start_handoff_packet_id")
        ),
        source_activity_ledger_frame_id=activity_ledger_id,
        source_traverse_result_frame_id=traverse_result_id,
        source_return_summary_frame_id=return_summary_id,
        source_read_packet_id=read_packet_id,
        r_loop_task_status=r_loop_task_status,
        traverse_status=traverse_status,
        failure_stage=_optional_text(
            traverse_payload.get("failure_stage")
            if traverse_payload
            else activity_ledger_payload.get("failure_stage")
        ),
        failure_type=_optional_text(
            traverse_payload.get("failure_type")
            if traverse_payload
            else activity_ledger_payload.get("failure_type")
        ),
        failure_reason=_optional_text(
            traverse_payload.get("failure_reason")
            if traverse_payload
            else activity_ledger_payload.get("failure_reason")
        ),
        selected_graph_node_count=len(selected_ids),
        inspected_graph_node_count=len(inspected_ids),
        summary_material_count=sum(1 for value in _unique_strings([*selected_ids, *inspected_ids]) if value.startswith("graph:summary:")),
        raw_original_material_count=_int(
            traverse_payload,
            "raw_original_material_seen_count",
            fallback=_int(activity_ledger_payload, "raw_original_material_seen_count"),
        ),
        node3_material_ready=return_status == "available",
        node3_material_source_data_ids=material_source_ids,
        source_trace_ids=_unique_strings(
            [
                *_string_list(activity_ledger_payload.get("source_trace_ids")),
                *_string_list(traverse_payload.get("source_trace_ids")),
            ]
        ),
        source_data_ids=_unique_strings(
            [
                activity_ledger_id,
                traverse_result_id,
                read_packet_id,
                return_summary_id,
                _optional_text(activity_ledger_payload.get("source_start_handoff_packet_id")),
                *_string_list(activity_ledger_payload.get("source_data_ids")),
                *_string_list(traverse_payload.get("source_data_ids")),
                *material_source_ids,
            ]
        ),
    )
    validate_r_loop_vessel_return_packet_frame(frame)
    return frame


def record_r_loop_vessel_return_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    activity_ledger_frame_id: str,
    frame_label: str = "manual_vessel_r_traverse",
) -> RecordedRLoopVesselReturnPacket:
    activity_record = data_store.require_record(activity_ledger_frame_id)
    if not isinstance(activity_record.payload, dict):
        raise ValueError("R Vessel return packet requires activity ledger payload")
    packet = build_r_loop_vessel_return_packet(
        data_store=data_store,
        turn_id=turn_id,
        activity_ledger_payload=activity_record.payload,
        frame_label=frame_label,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="memory_packet",
        timestamp=_now_iso(),
        input_ref=packet.source_trace_ids,
        output_ref=[packet.packet_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=packet.packet_id,
        data_type=R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE,
        payload=asdict(packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedRLoopVesselReturnPacket(
        packet=packet,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def validate_r_loop_vessel_return_packet_frame(
    frame: RLoopVesselReturnPacketFrame,
) -> None:
    _require_text_fields(
        "RLoopVesselReturnPacketFrame",
        {
            "packet_id": frame.packet_id,
            "turn_id": frame.turn_id,
            "target": frame.target,
            "mode": frame.mode,
            "return_status": frame.return_status,
            "source_activity_ledger_frame_id": frame.source_activity_ledger_frame_id,
            "source_traverse_result_frame_id": frame.source_traverse_result_frame_id,
            "source_read_packet_id": frame.source_read_packet_id,
            "r_loop_task_status": frame.r_loop_task_status,
            "traverse_status": frame.traverse_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.target != "node_1_or_node_2":
        raise ValueError("RLoopVesselReturnPacketFrame.target is invalid")
    if frame.mode != "vessel_r_return_packet":
        raise ValueError("RLoopVesselReturnPacketFrame.mode is invalid")
    if frame.return_status not in R_LOOP_VESSEL_RETURN_STATUSES:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.return_status: {frame.return_status}")
    if frame.traverse_status not in {"completed", "failed", "not_run"}:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.traverse_status: {frame.traverse_status}")
    if frame.r_loop_task_status not in {"not_run", "sufficient", "partial", "failed"}:
        raise ValueError(
            f"unknown RLoopVesselReturnPacketFrame.r_loop_task_status: {frame.r_loop_task_status}"
        )
    if frame.generated_by != R_LOOP_VESSEL_RETURN_PACKET_GENERATOR:
        raise ValueError("RLoopVesselReturnPacketFrame.generated_by must be node_0 code")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselReturnPacketFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "RLoopVesselReturnPacketFrame.semantic_judgement_status must be not_run"
        )
    if frame.schema_name != R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.schema_version: {frame.schema_version}")
    _validate_non_negative_ints(
        "RLoopVesselReturnPacketFrame",
        {
            "selected_graph_node_count": frame.selected_graph_node_count,
            "inspected_graph_node_count": frame.inspected_graph_node_count,
            "summary_material_count": frame.summary_material_count,
            "raw_original_material_count": frame.raw_original_material_count,
        },
    )
    if not isinstance(frame.node3_material_ready, bool):
        raise TypeError("RLoopVesselReturnPacketFrame.node3_material_ready must be bool")
    if frame.return_status == "failed" and frame.node3_material_ready:
        raise ValueError("failed RLoopVesselReturnPacketFrame cannot be node3-ready")
    for field_name, values in {
        "node3_material_source_data_ids": frame.node3_material_source_data_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }.items():
        _validate_string_list(f"RLoopVesselReturnPacketFrame.{field_name}", values)
        _validate_no_duplicates(f"RLoopVesselReturnPacketFrame.{field_name}", values)
    required_source_ids = _unique_strings(
        [
            frame.source_start_handoff_packet_id,
            frame.source_activity_ledger_frame_id,
            frame.source_traverse_result_frame_id,
            frame.source_return_summary_frame_id,
            frame.source_read_packet_id,
            *frame.node3_material_source_data_ids,
        ]
    )
    missing = sorted(set(required_source_ids) - set(frame.source_data_ids))
    if missing:
        raise ValueError(
            "RLoopVesselReturnPacketFrame.source_data_ids missing required IDs: "
            f"{missing}"
        )


def _payload_by_id(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return {}
    return record.payload


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
            raise ValueError(f"R Vessel return packet data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"R Vessel return packet payload collision: {data_id}")
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


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _text(payload: dict[str, object], field_name: str, *, fallback: str = "") -> str:
    value = payload.get(field_name)
    return value if isinstance(value, str) and value else fallback


def _int(payload: dict[str, object], field_name: str, *, fallback: int = 0) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    return fallback


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _validate_non_negative_ints(class_name: str, values: dict[str, int]) -> None:
    for field_name, value in values.items():
        if not isinstance(value, int):
            raise TypeError(f"{class_name}.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{class_name}.{field_name} must not be negative")


def _validate_string_list(field_name: str, values: list[str]) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field_name} must contain only non-empty strings")


def _validate_no_duplicates(field_name: str, values: list[str]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


def _require_text_fields(class_name: str, values: dict[str, str]) -> None:
    for field_name, value in values.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{class_name}.{field_name} must not be empty")


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
    "R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE",
    "R_LOOP_VESSEL_RETURN_PACKET_GENERATOR",
    "R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME",
    "R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION",
    "R_LOOP_VESSEL_RETURN_STATUSES",
    "RLoopVesselReturnPacketFrame",
    "RecordedRLoopVesselReturnPacket",
    "build_r_loop_vessel_return_packet",
    "r_loop_vessel_return_packet_id",
    "record_r_loop_vessel_return_packet",
    "validate_r_loop_vessel_return_packet_frame",
]
