from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore


R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_DATA_TYPE = (
    "r_loop:vessel_continuation_checkpoint_packet"
)
R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_GENERATOR = (
    "CODE:NODE_0_R_VESSEL_CONTINUATION_CHECKPOINT"
)
R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_NAME = (
    "RLoopVesselContinuationCheckpointPacketFrame"
)
R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_VERSION = "0.1"


@dataclass(frozen=True)
class RLoopVesselContinuationCheckpointPacketFrame:
    """node_0 copies absolute R traversal state between Vessel R steps."""

    packet_id: str
    turn_id: str
    step_index: int
    target: str
    mode: str
    source_start_handoff_packet_id: str | None
    source_read_packet_id: str
    source_candidate_surface_frame_id: str
    source_r2_selection_frame_id: str
    source_r3_inspection_frame_id: str
    source_continuation_frame_id: str
    selected_graph_node_ids_so_far: list[str]
    inspected_graph_node_ids_so_far: list[str]
    next_candidate_graph_node_ids: list[str]
    next_candidate_count: int
    remaining_node_reads: int
    remaining_traversal_depth: int
    terminal_material_seen_count: int
    raw_original_material_seen_count: int
    raw_original_read_cap_reached: bool
    continuation_status: str
    next_target_node: str
    source_trace_ids: list[str]
    source_data_ids: list[str]
    generated_by: str = R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_NAME
    schema_version: str = R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_VERSION


@dataclass(frozen=True)
class RecordedRLoopVesselContinuationCheckpointPacket:
    packet: RLoopVesselContinuationCheckpointPacketFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def r_loop_vessel_continuation_checkpoint_packet_id(
    *, frame_label: str, step_index: int
) -> str:
    if not frame_label:
        raise ValueError("frame_label must not be empty")
    if step_index < 1:
        raise ValueError("step_index must be positive")
    return (
        "r_loop:vessel_continuation_checkpoint:"
        f"{_stable_suffix(frame_label)}:step_{step_index:04d}"
    )


def build_r_loop_vessel_continuation_checkpoint_packet(
    *,
    turn_id: str,
    frame_label: str,
    step_index: int,
    source_start_handoff_packet_id: str | None,
    source_read_packet_id: str,
    source_candidate_surface_frame_id: str,
    source_r2_selection_frame_id: str,
    source_r3_inspection_frame_id: str,
    source_continuation_frame_id: str,
    selected_graph_node_ids_so_far: list[str],
    inspected_graph_node_ids_so_far: list[str],
    next_candidate_graph_node_ids: list[str],
    remaining_node_reads: int,
    remaining_traversal_depth: int,
    terminal_material_seen_count: int,
    raw_original_material_seen_count: int,
    raw_original_read_cap_reached: bool,
    continuation_status: str,
    next_target_node: str,
    source_trace_ids: list[str] | None = None,
) -> RLoopVesselContinuationCheckpointPacketFrame:
    frame = RLoopVesselContinuationCheckpointPacketFrame(
        packet_id=r_loop_vessel_continuation_checkpoint_packet_id(
            frame_label=frame_label,
            step_index=step_index,
        ),
        turn_id=turn_id,
        step_index=step_index,
        target="R_LOOP",
        mode="vessel_r_continuation_checkpoint",
        source_start_handoff_packet_id=source_start_handoff_packet_id,
        source_read_packet_id=source_read_packet_id,
        source_candidate_surface_frame_id=source_candidate_surface_frame_id,
        source_r2_selection_frame_id=source_r2_selection_frame_id,
        source_r3_inspection_frame_id=source_r3_inspection_frame_id,
        source_continuation_frame_id=source_continuation_frame_id,
        selected_graph_node_ids_so_far=_unique_strings(selected_graph_node_ids_so_far),
        inspected_graph_node_ids_so_far=_unique_strings(inspected_graph_node_ids_so_far),
        next_candidate_graph_node_ids=_unique_strings(next_candidate_graph_node_ids),
        next_candidate_count=len(_unique_strings(next_candidate_graph_node_ids)),
        remaining_node_reads=remaining_node_reads,
        remaining_traversal_depth=remaining_traversal_depth,
        terminal_material_seen_count=terminal_material_seen_count,
        raw_original_material_seen_count=raw_original_material_seen_count,
        raw_original_read_cap_reached=raw_original_read_cap_reached,
        continuation_status=continuation_status,
        next_target_node=next_target_node,
        source_trace_ids=_unique_strings(source_trace_ids or []),
        source_data_ids=_unique_strings(
            [
                source_start_handoff_packet_id,
                source_read_packet_id,
                source_candidate_surface_frame_id,
                source_r2_selection_frame_id,
                source_r3_inspection_frame_id,
                source_continuation_frame_id,
                *selected_graph_node_ids_so_far,
                *inspected_graph_node_ids_so_far,
                *next_candidate_graph_node_ids,
            ]
        ),
    )
    validate_r_loop_vessel_continuation_checkpoint_packet_frame(frame)
    return frame


def record_r_loop_vessel_continuation_checkpoint_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame_label: str,
    step_index: int,
    source_start_handoff_packet_id: str | None,
    source_read_packet_id: str,
    source_candidate_surface_frame_id: str,
    source_r2_selection_frame_id: str,
    source_r3_inspection_frame_id: str,
    source_continuation_frame_id: str,
    selected_graph_node_ids_so_far: list[str],
    inspected_graph_node_ids_so_far: list[str],
    next_candidate_graph_node_ids: list[str],
    remaining_node_reads: int,
    remaining_traversal_depth: int,
    terminal_material_seen_count: int,
    raw_original_material_seen_count: int,
    raw_original_read_cap_reached: bool,
    continuation_status: str,
    next_target_node: str,
    source_trace_ids: list[str] | None = None,
) -> RecordedRLoopVesselContinuationCheckpointPacket:
    packet = build_r_loop_vessel_continuation_checkpoint_packet(
        turn_id=turn_id,
        frame_label=frame_label,
        step_index=step_index,
        source_start_handoff_packet_id=source_start_handoff_packet_id,
        source_read_packet_id=source_read_packet_id,
        source_candidate_surface_frame_id=source_candidate_surface_frame_id,
        source_r2_selection_frame_id=source_r2_selection_frame_id,
        source_r3_inspection_frame_id=source_r3_inspection_frame_id,
        source_continuation_frame_id=source_continuation_frame_id,
        selected_graph_node_ids_so_far=selected_graph_node_ids_so_far,
        inspected_graph_node_ids_so_far=inspected_graph_node_ids_so_far,
        next_candidate_graph_node_ids=next_candidate_graph_node_ids,
        remaining_node_reads=remaining_node_reads,
        remaining_traversal_depth=remaining_traversal_depth,
        terminal_material_seen_count=terminal_material_seen_count,
        raw_original_material_seen_count=raw_original_material_seen_count,
        raw_original_read_cap_reached=raw_original_read_cap_reached,
        continuation_status=continuation_status,
        next_target_node=next_target_node,
        source_trace_ids=source_trace_ids,
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
        data_type=R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_DATA_TYPE,
        payload=asdict(packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedRLoopVesselContinuationCheckpointPacket(
        packet=packet,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def validate_r_loop_vessel_continuation_checkpoint_packet_frame(
    frame: RLoopVesselContinuationCheckpointPacketFrame,
) -> None:
    _require_text_fields(
        "RLoopVesselContinuationCheckpointPacketFrame",
        {
            "packet_id": frame.packet_id,
            "turn_id": frame.turn_id,
            "target": frame.target,
            "mode": frame.mode,
            "source_read_packet_id": frame.source_read_packet_id,
            "source_candidate_surface_frame_id": frame.source_candidate_surface_frame_id,
            "source_r2_selection_frame_id": frame.source_r2_selection_frame_id,
            "source_r3_inspection_frame_id": frame.source_r3_inspection_frame_id,
            "source_continuation_frame_id": frame.source_continuation_frame_id,
            "continuation_status": frame.continuation_status,
            "next_target_node": frame.next_target_node,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.target != "R_LOOP":
        raise ValueError("RLoopVesselContinuationCheckpointPacketFrame.target must be R_LOOP")
    if frame.mode != "vessel_r_continuation_checkpoint":
        raise ValueError("RLoopVesselContinuationCheckpointPacketFrame.mode is invalid")
    if frame.continuation_status != "continue_deeper":
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame records continue_deeper only"
        )
    if frame.next_target_node != "R2":
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame.next_target_node must be R2"
        )
    if frame.generated_by != R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_GENERATOR:
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame.generated_by must be node_0 code"
        )
    if frame.info_class != "absolute":
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame.info_class must be absolute"
        )
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame.semantic_judgement_status must be not_run"
        )
    if frame.schema_name != R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_NAME:
        raise ValueError(
            "unknown RLoopVesselContinuationCheckpointPacketFrame.schema_name: "
            f"{frame.schema_name}"
        )
    if frame.schema_version != R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(
            "unknown RLoopVesselContinuationCheckpointPacketFrame.schema_version: "
            f"{frame.schema_version}"
        )
    _validate_non_negative_ints(
        "RLoopVesselContinuationCheckpointPacketFrame",
        {
            "step_index": frame.step_index,
            "next_candidate_count": frame.next_candidate_count,
            "remaining_node_reads": frame.remaining_node_reads,
            "remaining_traversal_depth": frame.remaining_traversal_depth,
            "terminal_material_seen_count": frame.terminal_material_seen_count,
            "raw_original_material_seen_count": frame.raw_original_material_seen_count,
        },
    )
    if frame.step_index < 1:
        raise ValueError("RLoopVesselContinuationCheckpointPacketFrame.step_index must be positive")
    if not isinstance(frame.raw_original_read_cap_reached, bool):
        raise TypeError(
            "RLoopVesselContinuationCheckpointPacketFrame.raw_original_read_cap_reached must be bool"
        )
    list_fields = {
        "selected_graph_node_ids_so_far": frame.selected_graph_node_ids_so_far,
        "inspected_graph_node_ids_so_far": frame.inspected_graph_node_ids_so_far,
        "next_candidate_graph_node_ids": frame.next_candidate_graph_node_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }
    for field_name, values in list_fields.items():
        _validate_string_list(
            f"RLoopVesselContinuationCheckpointPacketFrame.{field_name}",
            values,
        )
        _validate_no_duplicates(
            f"RLoopVesselContinuationCheckpointPacketFrame.{field_name}",
            values,
        )
    if frame.next_candidate_count != len(frame.next_candidate_graph_node_ids):
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame.next_candidate_count mismatch"
        )
    required_source_ids = _unique_strings(
        [
            frame.source_start_handoff_packet_id,
            frame.source_read_packet_id,
            frame.source_candidate_surface_frame_id,
            frame.source_r2_selection_frame_id,
            frame.source_r3_inspection_frame_id,
            frame.source_continuation_frame_id,
            *frame.selected_graph_node_ids_so_far,
            *frame.inspected_graph_node_ids_so_far,
            *frame.next_candidate_graph_node_ids,
        ]
    )
    missing = sorted(set(required_source_ids) - set(frame.source_data_ids))
    if missing:
        raise ValueError(
            "RLoopVesselContinuationCheckpointPacketFrame.source_data_ids missing "
            f"required IDs: {missing}"
        )


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
            raise ValueError(f"R Vessel checkpoint data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"R Vessel checkpoint payload collision: {data_id}")
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
    "R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_DATA_TYPE",
    "R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_GENERATOR",
    "R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_NAME",
    "R_LOOP_VESSEL_CONTINUATION_CHECKPOINT_SCHEMA_VERSION",
    "RLoopVesselContinuationCheckpointPacketFrame",
    "RecordedRLoopVesselContinuationCheckpointPacket",
    "build_r_loop_vessel_continuation_checkpoint_packet",
    "r_loop_vessel_continuation_checkpoint_packet_id",
    "record_r_loop_vessel_continuation_checkpoint_packet",
    "validate_r_loop_vessel_continuation_checkpoint_packet_frame",
]
