from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import RLoopVesselReadPacketFrame
from songryeon_core.core.trace_store import TraceStore


R_LOOP_VESSEL_START_HANDOFF_DATA_TYPE = "r_loop:vessel_start_handoff_packet"
R_LOOP_VESSEL_START_HANDOFF_GENERATOR = "CODE:NODE_0_R_VESSEL_START_HANDOFF"
R_LOOP_VESSEL_START_HANDOFF_SCHEMA_NAME = "RLoopVesselStartHandoffPacketFrame"
R_LOOP_VESSEL_START_HANDOFF_SCHEMA_VERSION = "0.1"
R_LOOP_VESSEL_START_HANDOFF_STATUSES = {
    "available",
    "empty",
    "adapter_unavailable",
    "read_failed",
}


@dataclass(frozen=True)
class RLoopVesselStartHandoffPacketFrame:
    """node_0 copies absolute Vessel read-packet coordinates before R starts."""

    packet_id: str
    turn_id: str
    target: str
    mode: str
    packet_status: str
    source_vessel_read_packet_id: str
    source_graph_guide_packet_id: str | None
    source_graph_snapshot_id: str | None
    entry_candidate_count: int
    summary_candidate_count: int
    available_entry_node_ids: list[str]
    summary_count_by_data_kind: dict[str, int]
    summary_count_by_depth: dict[str, int]
    recent_turn_capsule_count: int
    recent_raw_conversation_count: int
    source_trace_ids: list[str]
    source_data_ids: list[str]
    generated_by: str = R_LOOP_VESSEL_START_HANDOFF_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_START_HANDOFF_SCHEMA_NAME
    schema_version: str = R_LOOP_VESSEL_START_HANDOFF_SCHEMA_VERSION


@dataclass(frozen=True)
class RecordedRLoopVesselStartHandoffPacket:
    packet: RLoopVesselStartHandoffPacketFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def r_loop_vessel_start_handoff_packet_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"r_loop:vessel_start_handoff:{_stable_suffix(batch_id)}"


def build_r_loop_vessel_start_handoff_packet(
    *,
    read_packet: RLoopVesselReadPacketFrame,
    turn_id: str,
    batch_id: str = "manual_r_loop_vessel_start_handoff",
    source_read_packet_trace_event_id: str | None = None,
    recent_turn_capsule_count: int = 0,
    recent_raw_conversation_count: int = 0,
) -> RLoopVesselStartHandoffPacketFrame:
    status = "available" if read_packet.read_status == "passed" else read_packet.read_status
    graph_guide_packet_id = _first_prefixed(read_packet.source_data_ids, "rloop:graph_guide:")
    graph_snapshot_id = _first_prefixed(read_packet.source_data_ids, "graph:snapshot:")
    available_entry_node_ids = (
        _entry_candidate_node_ids(read_packet)
        if status == "available"
        else []
    )
    frame = RLoopVesselStartHandoffPacketFrame(
        packet_id=r_loop_vessel_start_handoff_packet_id(batch_id),
        turn_id=turn_id,
        target="R_LOOP",
        mode="vessel_r_start_handoff",
        packet_status=status,
        source_vessel_read_packet_id=read_packet.packet_id,
        source_graph_guide_packet_id=graph_guide_packet_id,
        source_graph_snapshot_id=graph_snapshot_id,
        entry_candidate_count=read_packet.entry_candidate_count,
        summary_candidate_count=read_packet.summary_candidate_count,
        available_entry_node_ids=available_entry_node_ids,
        summary_count_by_data_kind=dict(read_packet.summary_count_by_data_kind),
        summary_count_by_depth=dict(read_packet.summary_count_by_depth),
        recent_turn_capsule_count=recent_turn_capsule_count,
        recent_raw_conversation_count=recent_raw_conversation_count,
        source_trace_ids=_unique_strings(
            [source_read_packet_trace_event_id, *read_packet.source_trace_ids]
        ),
        source_data_ids=_unique_strings(
            [
                read_packet.packet_id,
                graph_guide_packet_id,
                graph_snapshot_id,
                *read_packet.source_data_ids,
            ]
        ),
    )
    validate_r_loop_vessel_start_handoff_packet_frame(frame)
    return frame


def record_r_loop_vessel_start_handoff_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    read_packet: RLoopVesselReadPacketFrame,
    batch_id: str = "manual_r_loop_vessel_start_handoff",
    source_read_packet_trace_event_id: str | None = None,
    recent_turn_capsule_count: int = 0,
    recent_raw_conversation_count: int = 0,
) -> RecordedRLoopVesselStartHandoffPacket:
    packet = build_r_loop_vessel_start_handoff_packet(
        read_packet=read_packet,
        turn_id=turn_id,
        batch_id=batch_id,
        source_read_packet_trace_event_id=source_read_packet_trace_event_id,
        recent_turn_capsule_count=recent_turn_capsule_count,
        recent_raw_conversation_count=recent_raw_conversation_count,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="memory_packet",
        timestamp=_now_iso(),
        input_ref=_unique_strings(
            [source_read_packet_trace_event_id, read_packet.packet_id]
        ),
        output_ref=[packet.packet_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=packet.packet_id,
        data_type=R_LOOP_VESSEL_START_HANDOFF_DATA_TYPE,
        payload=asdict(packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedRLoopVesselStartHandoffPacket(
        packet=packet,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def validate_r_loop_vessel_start_handoff_packet_frame(
    frame: RLoopVesselStartHandoffPacketFrame,
) -> None:
    _require_text_fields(
        "RLoopVesselStartHandoffPacketFrame",
        {
            "packet_id": frame.packet_id,
            "turn_id": frame.turn_id,
            "target": frame.target,
            "mode": frame.mode,
            "packet_status": frame.packet_status,
            "source_vessel_read_packet_id": frame.source_vessel_read_packet_id,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.target != "R_LOOP":
        raise ValueError("RLoopVesselStartHandoffPacketFrame.target must be R_LOOP")
    if frame.mode != "vessel_r_start_handoff":
        raise ValueError("RLoopVesselStartHandoffPacketFrame.mode is invalid")
    if frame.packet_status not in R_LOOP_VESSEL_START_HANDOFF_STATUSES:
        raise ValueError(
            f"unknown RLoopVesselStartHandoffPacketFrame.packet_status: {frame.packet_status}"
        )
    if frame.generated_by != R_LOOP_VESSEL_START_HANDOFF_GENERATOR:
        raise ValueError("RLoopVesselStartHandoffPacketFrame.generated_by must be node_0 code")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselStartHandoffPacketFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "RLoopVesselStartHandoffPacketFrame.semantic_judgement_status must be not_run"
        )
    if frame.schema_name != R_LOOP_VESSEL_START_HANDOFF_SCHEMA_NAME:
        raise ValueError(
            f"unknown RLoopVesselStartHandoffPacketFrame.schema_name: {frame.schema_name}"
        )
    if frame.schema_version != R_LOOP_VESSEL_START_HANDOFF_SCHEMA_VERSION:
        raise ValueError(
            f"unknown RLoopVesselStartHandoffPacketFrame.schema_version: {frame.schema_version}"
        )
    _validate_non_negative_ints(
        "RLoopVesselStartHandoffPacketFrame",
        {
            "entry_candidate_count": frame.entry_candidate_count,
            "summary_candidate_count": frame.summary_candidate_count,
            "recent_turn_capsule_count": frame.recent_turn_capsule_count,
            "recent_raw_conversation_count": frame.recent_raw_conversation_count,
        },
    )
    _validate_string_list(
        "RLoopVesselStartHandoffPacketFrame.available_entry_node_ids",
        frame.available_entry_node_ids,
    )
    _validate_string_list(
        "RLoopVesselStartHandoffPacketFrame.source_trace_ids",
        frame.source_trace_ids,
    )
    _validate_string_list(
        "RLoopVesselStartHandoffPacketFrame.source_data_ids",
        frame.source_data_ids,
    )
    _validate_no_duplicates(
        "RLoopVesselStartHandoffPacketFrame.available_entry_node_ids",
        frame.available_entry_node_ids,
    )
    _validate_no_duplicates(
        "RLoopVesselStartHandoffPacketFrame.source_trace_ids",
        frame.source_trace_ids,
    )
    _validate_no_duplicates(
        "RLoopVesselStartHandoffPacketFrame.source_data_ids",
        frame.source_data_ids,
    )
    _validate_counts(
        "RLoopVesselStartHandoffPacketFrame.summary_count_by_data_kind",
        frame.summary_count_by_data_kind,
    )
    _validate_counts(
        "RLoopVesselStartHandoffPacketFrame.summary_count_by_depth",
        frame.summary_count_by_depth,
    )
    if frame.source_vessel_read_packet_id not in frame.source_data_ids:
        raise ValueError(
            "RLoopVesselStartHandoffPacketFrame.source_data_ids must include read packet"
        )
    if frame.packet_status == "available":
        if frame.entry_candidate_count + frame.summary_candidate_count < 1:
            raise ValueError("available R Vessel start handoff requires candidates")
    elif frame.available_entry_node_ids:
        raise ValueError("non-available R Vessel start handoff must not expose entry IDs")


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
            raise ValueError(f"R loop Vessel start handoff data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(
                f"R loop Vessel start handoff payload collision: {data_id}"
            )
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


def _entry_candidate_node_ids(read_packet: RLoopVesselReadPacketFrame) -> list[str]:
    values: list[str] = []
    for record in read_packet.entry_candidate_records:
        value = record.get("candidate_node_id")
        if isinstance(value, str) and value:
            values.append(value)
    return _unique_strings(values)


def _first_prefixed(values: list[str], prefix: str) -> str | None:
    for value in values:
        if value.startswith(prefix):
            return value
    return None


def _validate_counts(field_name: str, counts: dict[str, int]) -> None:
    if not isinstance(counts, dict):
        raise TypeError(f"{field_name} must be a dict")
    for key, value in counts.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name}.{key} must be a non-negative integer")


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
    "R_LOOP_VESSEL_START_HANDOFF_DATA_TYPE",
    "R_LOOP_VESSEL_START_HANDOFF_GENERATOR",
    "R_LOOP_VESSEL_START_HANDOFF_SCHEMA_NAME",
    "R_LOOP_VESSEL_START_HANDOFF_SCHEMA_VERSION",
    "R_LOOP_VESSEL_START_HANDOFF_STATUSES",
    "RLoopVesselStartHandoffPacketFrame",
    "RecordedRLoopVesselStartHandoffPacket",
    "build_r_loop_vessel_start_handoff_packet",
    "r_loop_vessel_start_handoff_packet_id",
    "record_r_loop_vessel_start_handoff_packet",
    "validate_r_loop_vessel_start_handoff_packet_frame",
]
