from __future__ import annotations

from dataclasses import asdict, dataclass, field

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.r_loop_vessel_one_step import RLoopVesselTraverseRun


R_LOOP_VESSEL_ACTIVITY_LEDGER_DATA_TYPE = "r_loop:vessel_activity_ledger_frame"
R_LOOP_VESSEL_ACTIVITY_LEDGER_GENERATOR = "CODE:R_LOOP_VESSEL_ACTIVITY_LEDGER"
R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_NAME = "RLoopVesselActivityLedgerFrame"
R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_VERSION = "0.1"
R_LOOP_VESSEL_ACTIVITY_STAGES = {
    "start_handoff",
    "read_packet",
    "traverse_result",
    "r1_goal",
    "candidate_layer_surface",
    "surface_selection",
    "r2_selection",
    "r3_inspection",
    "graph_traversal_candidate_surface",
    "budget",
    "continuation",
    "continuation_checkpoint",
    "step_memory",
    "return_summary",
}


@dataclass(frozen=True)
class RLoopVesselActivityLedgerFrame:
    """Absolute ledger of frames and graph node IDs touched by one Vessel R traverse."""

    frame_id: str
    turn_id: str
    source_start_handoff_packet_id: str | None
    source_read_packet_id: str
    traverse_result_frame_id: str
    traverse_status: str
    r1_goal_frame_id: str | None
    candidate_layer_surface_frame_ids: list[str] = field(default_factory=list)
    surface_selection_frame_ids: list[str] = field(default_factory=list)
    r2_selection_frame_ids: list[str] = field(default_factory=list)
    r3_inspection_frame_ids: list[str] = field(default_factory=list)
    graph_traversal_candidate_surface_frame_ids: list[str] = field(default_factory=list)
    budget_frame_ids: list[str] = field(default_factory=list)
    continuation_frame_ids: list[str] = field(default_factory=list)
    continuation_checkpoint_packet_ids: list[str] = field(default_factory=list)
    step_memory_packet_ids: list[str] = field(default_factory=list)
    return_summary_frame_id: str | None = None
    selected_graph_node_ids: list[str] = field(default_factory=list)
    inspected_graph_node_ids: list[str] = field(default_factory=list)
    candidate_graph_node_ids: list[str] = field(default_factory=list)
    terminal_material_seen_count: int = 0
    raw_original_material_seen_count: int = 0
    r_loop_task_status: str | None = None
    final_continuation_status: str | None = None
    failure_stage: str | None = None
    failure_type: str | None = None
    failure_reason: str | None = None
    activity_records: list[dict[str, str]] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = R_LOOP_VESSEL_ACTIVITY_LEDGER_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_NAME
    schema_version: str = R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_VERSION


def r_loop_vessel_activity_ledger_frame_id(frame_label: str) -> str:
    if not frame_label:
        raise ValueError("frame_label must not be empty")
    return f"R:{_stable_suffix(frame_label)}:vessel_activity_ledger_frame"


def record_r_loop_vessel_activity_ledger(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    traverse_run: RLoopVesselTraverseRun,
    frame_label: str = "manual_vessel_r_traverse",
    source_start_handoff_packet_id: str | None = None,
) -> tuple[str, str, RLoopVesselActivityLedgerFrame]:
    """Record one absolute ledger for a completed or failed Vessel R traversal."""

    frame = build_r_loop_vessel_activity_ledger_frame(
        data_store=data_store,
        turn_id=turn_id,
        traverse_run=traverse_run,
        frame_label=frame_label,
        source_start_handoff_packet_id=source_start_handoff_packet_id,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=R_LOOP_VESSEL_ACTIVITY_LEDGER_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def build_r_loop_vessel_activity_ledger_frame(
    *,
    data_store: DataStore,
    turn_id: str,
    traverse_run: RLoopVesselTraverseRun,
    frame_label: str = "manual_vessel_r_traverse",
    source_start_handoff_packet_id: str | None = None,
) -> RLoopVesselActivityLedgerFrame:
    result = traverse_run.result_frame
    start_handoff_id = source_start_handoff_packet_id or _first_prefixed(
        result.source_data_ids,
        "r_loop:vessel_start_handoff:",
    )
    budget_frame_ids = _data_ids_by_type(
        data_store=data_store,
        data_ids=traverse_run.output_data_ids,
        data_type="node_output:R_loop_budget_frame",
    )
    if traverse_run.final_budget is not None:
        budget_frame_ids = _unique_strings(
            [*budget_frame_ids, traverse_run.final_budget.frame_id]
        )

    activity_sources = {
        "start_handoff": [start_handoff_id] if start_handoff_id else [],
        "read_packet": [result.source_packet_id],
        "traverse_result": [result.frame_id],
        "r1_goal": [result.r1_goal_frame_id] if result.r1_goal_frame_id else [],
        "candidate_layer_surface": [
            frame.frame_id for frame in traverse_run.candidate_layer_surfaces
        ],
        "surface_selection": [
            frame.frame_id for frame in traverse_run.surface_selections
        ],
        "r2_selection": [frame.frame_id for frame in traverse_run.r2_selections],
        "r3_inspection": [frame.frame_id for frame in traverse_run.r3_inspections],
        "graph_traversal_candidate_surface": [
            frame.frame_id for frame in traverse_run.graph_traversal_candidate_surfaces
        ],
        "budget": budget_frame_ids,
        "continuation": [frame.frame_id for frame in traverse_run.continuations],
        "continuation_checkpoint": [
            frame.packet_id for frame in traverse_run.continuation_checkpoints
        ],
        "step_memory": [
            frame.packet_id for frame in traverse_run.step_memory_packets
        ],
        "return_summary": (
            [traverse_run.return_summary.frame_id]
            if traverse_run.return_summary is not None
            else []
        ),
    }
    activity_records = _build_activity_records(activity_sources)
    source_data_ids = _unique_strings(
        [
            *result.source_data_ids,
            *traverse_run.output_data_ids,
            result.frame_id,
            start_handoff_id,
            *[data_id for values in activity_sources.values() for data_id in values],
        ]
    )
    source_trace_ids = _unique_strings(
        [*result.source_trace_ids, *traverse_run.trace_event_ids]
    )
    frame = RLoopVesselActivityLedgerFrame(
        frame_id=r_loop_vessel_activity_ledger_frame_id(frame_label),
        turn_id=turn_id,
        source_start_handoff_packet_id=start_handoff_id,
        source_read_packet_id=result.source_packet_id,
        traverse_result_frame_id=result.frame_id,
        traverse_status=result.traverse_status,
        r1_goal_frame_id=result.r1_goal_frame_id,
        candidate_layer_surface_frame_ids=activity_sources["candidate_layer_surface"],
        surface_selection_frame_ids=activity_sources["surface_selection"],
        r2_selection_frame_ids=activity_sources["r2_selection"],
        r3_inspection_frame_ids=activity_sources["r3_inspection"],
        graph_traversal_candidate_surface_frame_ids=activity_sources[
            "graph_traversal_candidate_surface"
        ],
        budget_frame_ids=budget_frame_ids,
        continuation_frame_ids=activity_sources["continuation"],
        continuation_checkpoint_packet_ids=activity_sources[
            "continuation_checkpoint"
        ],
        step_memory_packet_ids=activity_sources["step_memory"],
        return_summary_frame_id=(
            traverse_run.return_summary.frame_id
            if traverse_run.return_summary is not None
            else None
        ),
        selected_graph_node_ids=list(result.selected_graph_node_ids),
        inspected_graph_node_ids=list(result.inspected_graph_node_ids),
        candidate_graph_node_ids=_candidate_graph_node_ids(traverse_run),
        terminal_material_seen_count=result.terminal_material_seen_count,
        raw_original_material_seen_count=result.raw_original_material_seen_count,
        r_loop_task_status=result.r_loop_task_status,
        final_continuation_status=result.final_continuation_status,
        failure_stage=result.failure_stage,
        failure_type=result.failure_type,
        failure_reason=result.failure_reason,
        activity_records=activity_records,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_r_loop_vessel_activity_ledger_frame(frame)
    return frame


def validate_r_loop_vessel_activity_ledger_frame(
    frame: RLoopVesselActivityLedgerFrame,
) -> None:
    _require_text_fields(
        "RLoopVesselActivityLedgerFrame",
        {
            "frame_id": frame.frame_id,
            "turn_id": frame.turn_id,
            "source_read_packet_id": frame.source_read_packet_id,
            "traverse_result_frame_id": frame.traverse_result_frame_id,
            "traverse_status": frame.traverse_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.generated_by != R_LOOP_VESSEL_ACTIVITY_LEDGER_GENERATOR:
        raise ValueError("RLoopVesselActivityLedgerFrame.generated_by must be code ledger")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselActivityLedgerFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "RLoopVesselActivityLedgerFrame.semantic_judgement_status must be not_run"
        )
    if frame.schema_name != R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_NAME:
        raise ValueError(
            f"unknown RLoopVesselActivityLedgerFrame.schema_name: {frame.schema_name}"
        )
    if frame.schema_version != R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_VERSION:
        raise ValueError(
            f"unknown RLoopVesselActivityLedgerFrame.schema_version: {frame.schema_version}"
        )
    _validate_non_negative_ints(
        "RLoopVesselActivityLedgerFrame",
        {
            "terminal_material_seen_count": frame.terminal_material_seen_count,
            "raw_original_material_seen_count": frame.raw_original_material_seen_count,
        },
    )
    list_fields = {
        "candidate_layer_surface_frame_ids": frame.candidate_layer_surface_frame_ids,
        "surface_selection_frame_ids": frame.surface_selection_frame_ids,
        "r2_selection_frame_ids": frame.r2_selection_frame_ids,
        "r3_inspection_frame_ids": frame.r3_inspection_frame_ids,
        "graph_traversal_candidate_surface_frame_ids": (
            frame.graph_traversal_candidate_surface_frame_ids
        ),
        "budget_frame_ids": frame.budget_frame_ids,
        "continuation_frame_ids": frame.continuation_frame_ids,
        "continuation_checkpoint_packet_ids": frame.continuation_checkpoint_packet_ids,
        "step_memory_packet_ids": frame.step_memory_packet_ids,
        "selected_graph_node_ids": frame.selected_graph_node_ids,
        "inspected_graph_node_ids": frame.inspected_graph_node_ids,
        "candidate_graph_node_ids": frame.candidate_graph_node_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }
    for field_name, values in list_fields.items():
        _validate_string_list(f"RLoopVesselActivityLedgerFrame.{field_name}", values)
        _validate_no_duplicates(f"RLoopVesselActivityLedgerFrame.{field_name}", values)

    required_source_ids = _unique_strings(
        [
            frame.source_start_handoff_packet_id,
            frame.source_read_packet_id,
            frame.traverse_result_frame_id,
            frame.r1_goal_frame_id,
            frame.return_summary_frame_id,
            *frame.candidate_layer_surface_frame_ids,
            *frame.surface_selection_frame_ids,
            *frame.r2_selection_frame_ids,
            *frame.r3_inspection_frame_ids,
            *frame.graph_traversal_candidate_surface_frame_ids,
            *frame.budget_frame_ids,
            *frame.continuation_frame_ids,
            *frame.continuation_checkpoint_packet_ids,
            *frame.step_memory_packet_ids,
        ]
    )
    missing = sorted(set(required_source_ids) - set(frame.source_data_ids))
    if missing:
        raise ValueError(
            "RLoopVesselActivityLedgerFrame.source_data_ids missing required IDs: "
            f"{missing}"
        )

    if not frame.activity_records:
        raise ValueError("RLoopVesselActivityLedgerFrame.activity_records must not be empty")
    for index, record in enumerate(frame.activity_records, start=1):
        if not isinstance(record, dict):
            raise ValueError("RLoopVesselActivityLedgerFrame.activity_records must be dicts")
        stage = record.get("stage")
        data_id = record.get("data_id")
        source_field = record.get("source_field")
        if not stage or not data_id or not source_field:
            raise ValueError(
                "RLoopVesselActivityLedgerFrame.activity_records entries require "
                "stage, data_id, source_field"
            )
        if stage not in R_LOOP_VESSEL_ACTIVITY_STAGES:
            raise ValueError(f"unknown R Vessel activity stage at {index}: {stage}")
        if data_id not in frame.source_data_ids:
            raise ValueError(
                "RLoopVesselActivityLedgerFrame.source_data_ids must include "
                f"activity record data_id at {index}"
            )


def _build_activity_records(
    activity_sources: dict[str, list[str]],
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for stage, data_ids in activity_sources.items():
        for data_id in data_ids:
            records.append(
                {
                    "stage": stage,
                    "data_id": data_id,
                    "source_field": _source_field_for_stage(stage),
                }
            )
    return records


def _source_field_for_stage(stage: str) -> str:
    if stage == "start_handoff":
        return "source_start_handoff_packet_id"
    if stage == "read_packet":
        return "source_read_packet_id"
    if stage == "traverse_result":
        return "traverse_result_frame_id"
    if stage == "r1_goal":
        return "r1_goal_frame_id"
    if stage == "return_summary":
        return "return_summary_frame_id"
    if stage == "continuation_checkpoint":
        return "continuation_checkpoint_packet_ids"
    if stage == "step_memory":
        return "step_memory_packet_ids"
    return f"{stage}_frame_ids"


def _candidate_graph_node_ids(traverse_run: RLoopVesselTraverseRun) -> list[str]:
    values: list[str] = []
    for surface in traverse_run.candidate_layer_surfaces:
        for record in surface.surface_records:
            items = record.get("candidate_graph_node_ids")
            if isinstance(items, list):
                values.extend(item for item in items if isinstance(item, str) and item)
    for surface in traverse_run.graph_traversal_candidate_surfaces:
        values.extend(surface.candidate_graph_node_ids)
    values.extend(traverse_run.result_frame.selected_graph_node_ids)
    values.extend(traverse_run.result_frame.inspected_graph_node_ids)
    return _unique_strings(values)


def _data_ids_by_type(
    *,
    data_store: DataStore,
    data_ids: list[str],
    data_type: str,
) -> list[str]:
    result: list[str] = []
    for data_id in data_ids:
        record = data_store.get_record(data_id)
        if record is not None and record.data_type == data_type:
            result.append(data_id)
    return _unique_strings(result)


def _first_prefixed(values: list[str], prefix: str) -> str | None:
    for value in values:
        if value.startswith(prefix):
            return value
    return None


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


__all__ = [
    "R_LOOP_VESSEL_ACTIVITY_LEDGER_DATA_TYPE",
    "R_LOOP_VESSEL_ACTIVITY_LEDGER_GENERATOR",
    "R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_NAME",
    "R_LOOP_VESSEL_ACTIVITY_LEDGER_SCHEMA_VERSION",
    "R_LOOP_VESSEL_ACTIVITY_STAGES",
    "RLoopVesselActivityLedgerFrame",
    "build_r_loop_vessel_activity_ledger_frame",
    "r_loop_vessel_activity_ledger_frame_id",
    "record_r_loop_vessel_activity_ledger",
    "validate_r_loop_vessel_activity_ledger_frame",
]
