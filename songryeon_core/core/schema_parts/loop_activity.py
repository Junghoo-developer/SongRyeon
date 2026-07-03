from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schema_parts.base import (
    _validate_no_duplicates,
    _validate_string_list,
)


L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_NAME = "LLoopActivityLedgerFrame"
L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_VERSION = "0.1"
L_LOOP_ACTIVITY_LEDGER_GENERATOR = "CODE:L_LOOP_ACTIVITY_LEDGER"
L_LOOP_ACTIVITY_LEDGER_DATA_TYPE = "loop_activity:l_loop_activity_ledger_frame"

L_LOOP_ACTIVITY_STAGES = {
    "run_frame",
    "goal",
    "budget_plan",
    "tool_scope",
    "tool_budget_partition",
    "tool_catalog",
    "tool_choice",
    "query_plan",
    "query",
    "control",
    "tool_result",
    "tool_distillation",
    "tool_budget",
    "continuation",
    "revision_input",
    "revision_query_plan",
    "revision_query",
    "failure_signal",
    "explicit_artifact_reference",
    "document_context_pack",
    "l3_preserved",
    "l3_achievement",
    "return_summary",
    "document_material_packet",
}


@dataclass
class LLoopActivityLedgerFrame:
    """An absolute per-turn index of records produced or used by one L loop run."""

    frame_id: str
    turn_id: str
    run_index: int
    turn_capsule_graph_node_id: str
    loop_id: str = "L"
    run_frame_data_ids: list[str] = field(default_factory=list)
    goal_data_ids: list[str] = field(default_factory=list)
    budget_plan_data_ids: list[str] = field(default_factory=list)
    tool_scope_data_ids: list[str] = field(default_factory=list)
    tool_budget_partition_data_ids: list[str] = field(default_factory=list)
    tool_catalog_data_ids: list[str] = field(default_factory=list)
    tool_choice_data_ids: list[str] = field(default_factory=list)
    query_plan_data_ids: list[str] = field(default_factory=list)
    query_data_ids: list[str] = field(default_factory=list)
    control_data_ids: list[str] = field(default_factory=list)
    tool_result_data_ids: list[str] = field(default_factory=list)
    tool_distillation_data_ids: list[str] = field(default_factory=list)
    tool_budget_data_ids: list[str] = field(default_factory=list)
    continuation_data_ids: list[str] = field(default_factory=list)
    revision_input_data_ids: list[str] = field(default_factory=list)
    revision_query_plan_data_ids: list[str] = field(default_factory=list)
    revision_query_data_ids: list[str] = field(default_factory=list)
    failure_signal_data_ids: list[str] = field(default_factory=list)
    explicit_artifact_reference_data_ids: list[str] = field(default_factory=list)
    document_context_pack_data_ids: list[str] = field(default_factory=list)
    preserved_data_ids: list[str] = field(default_factory=list)
    achievement_data_ids: list[str] = field(default_factory=list)
    return_summary_frame_id: str | None = None
    document_material_packet_frame_id: str | None = None
    output_data_ids: list[str] = field(default_factory=list)
    search_candidate_doc_ids: list[str] = field(default_factory=list)
    read_doc_ids: list[str] = field(default_factory=list)
    read_code_file_paths: list[str] = field(default_factory=list)
    output_data_id_count: int = 0
    tool_result_count: int = 0
    search_candidate_doc_count: int = 0
    actual_read_doc_count: int = 0
    actual_read_code_file_count: int = 0
    document_material_item_count: int = 0
    activity_records: list[dict[str, str]] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = L_LOOP_ACTIVITY_LEDGER_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_NAME
    schema_version: str = L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_VERSION


def validate_l_loop_activity_ledger_frame(frame: LLoopActivityLedgerFrame) -> None:
    """Validate that an L loop ledger only indexes existing absolute coordinates."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "turn_capsule_graph_node_id": frame.turn_capsule_graph_node_id,
        "loop_id": frame.loop_id,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"LLoopActivityLedgerFrame.{field_name} must not be empty")
    if frame.schema_name != L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown LLoopActivityLedgerFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown LLoopActivityLedgerFrame.schema_version: {frame.schema_version}"
        )
    if frame.loop_id != "L":
        raise ValueError("LLoopActivityLedgerFrame.loop_id must be L")
    if frame.run_index < 1:
        raise ValueError("LLoopActivityLedgerFrame.run_index must be positive")
    if frame.generated_by != L_LOOP_ACTIVITY_LEDGER_GENERATOR:
        raise ValueError("LLoopActivityLedgerFrame.generated_by must reveal code ledger")
    if frame.info_class != "absolute":
        raise ValueError("LLoopActivityLedgerFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("LLoopActivityLedgerFrame.semantic_judgement_status must be not_run")

    list_fields = {
        "run_frame_data_ids": frame.run_frame_data_ids,
        "goal_data_ids": frame.goal_data_ids,
        "budget_plan_data_ids": frame.budget_plan_data_ids,
        "tool_scope_data_ids": frame.tool_scope_data_ids,
        "tool_budget_partition_data_ids": frame.tool_budget_partition_data_ids,
        "tool_catalog_data_ids": frame.tool_catalog_data_ids,
        "tool_choice_data_ids": frame.tool_choice_data_ids,
        "query_plan_data_ids": frame.query_plan_data_ids,
        "query_data_ids": frame.query_data_ids,
        "control_data_ids": frame.control_data_ids,
        "tool_result_data_ids": frame.tool_result_data_ids,
        "tool_distillation_data_ids": frame.tool_distillation_data_ids,
        "tool_budget_data_ids": frame.tool_budget_data_ids,
        "continuation_data_ids": frame.continuation_data_ids,
        "revision_input_data_ids": frame.revision_input_data_ids,
        "revision_query_plan_data_ids": frame.revision_query_plan_data_ids,
        "revision_query_data_ids": frame.revision_query_data_ids,
        "failure_signal_data_ids": frame.failure_signal_data_ids,
        "explicit_artifact_reference_data_ids": frame.explicit_artifact_reference_data_ids,
        "document_context_pack_data_ids": frame.document_context_pack_data_ids,
        "preserved_data_ids": frame.preserved_data_ids,
        "achievement_data_ids": frame.achievement_data_ids,
        "output_data_ids": frame.output_data_ids,
        "search_candidate_doc_ids": frame.search_candidate_doc_ids,
        "read_doc_ids": frame.read_doc_ids,
        "read_code_file_paths": frame.read_code_file_paths,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }
    for field_name, values in list_fields.items():
        _validate_string_list(f"LLoopActivityLedgerFrame.{field_name}", values)
        _validate_no_duplicates(f"LLoopActivityLedgerFrame.{field_name}", values)

    expected_counts = {
        "output_data_id_count": len(frame.output_data_ids),
        "tool_result_count": len(frame.tool_result_data_ids),
        "search_candidate_doc_count": len(frame.search_candidate_doc_ids),
        "actual_read_doc_count": len(frame.read_doc_ids),
        "actual_read_code_file_count": len(frame.read_code_file_paths),
    }
    actual_counts = {
        "output_data_id_count": frame.output_data_id_count,
        "tool_result_count": frame.tool_result_count,
        "search_candidate_doc_count": frame.search_candidate_doc_count,
        "actual_read_doc_count": frame.actual_read_doc_count,
        "actual_read_code_file_count": frame.actual_read_code_file_count,
    }
    for field_name, value in actual_counts.items():
        if not isinstance(value, int):
            raise TypeError(f"LLoopActivityLedgerFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"LLoopActivityLedgerFrame.{field_name} must not be negative")
        if value != expected_counts[field_name]:
            raise ValueError(f"LLoopActivityLedgerFrame.{field_name} must mirror source list")
    if not isinstance(frame.document_material_item_count, int):
        raise TypeError("LLoopActivityLedgerFrame.document_material_item_count must be an integer")
    if frame.document_material_item_count < 0:
        raise ValueError("LLoopActivityLedgerFrame.document_material_item_count must not be negative")

    if frame.return_summary_frame_id is not None:
        if not frame.return_summary_frame_id:
            raise ValueError("LLoopActivityLedgerFrame.return_summary_frame_id must not be empty")
        if frame.return_summary_frame_id not in frame.source_data_ids:
            raise ValueError(
                "LLoopActivityLedgerFrame.source_data_ids must include return_summary_frame_id"
            )
    if frame.document_material_packet_frame_id is not None:
        if not frame.document_material_packet_frame_id:
            raise ValueError(
                "LLoopActivityLedgerFrame.document_material_packet_frame_id must not be empty"
            )
        if frame.document_material_packet_frame_id not in frame.source_data_ids:
            raise ValueError(
                "LLoopActivityLedgerFrame.source_data_ids must include "
                "document_material_packet_frame_id"
            )

    activity_data_ids = {
        data_id
        for values in _activity_source_lists(frame)
        for data_id in values
    }
    missing_source_ids = sorted(activity_data_ids - set(frame.source_data_ids))
    if missing_source_ids:
        raise ValueError(
            "LLoopActivityLedgerFrame.source_data_ids must include activity data ids: "
            f"{missing_source_ids}"
        )
    if not frame.activity_records:
        raise ValueError("LLoopActivityLedgerFrame.activity_records must not be empty")
    for record in frame.activity_records:
        if not isinstance(record, dict):
            raise ValueError("LLoopActivityLedgerFrame.activity_records must contain dict records")
        stage = record.get("stage")
        data_id = record.get("data_id")
        source_field = record.get("source_field")
        if not stage or not data_id or not source_field:
            raise ValueError(
                "LLoopActivityLedgerFrame.activity_records entries require "
                "stage, data_id, source_field"
            )
        if stage not in L_LOOP_ACTIVITY_STAGES:
            raise ValueError(f"unknown L loop activity stage: {stage}")
        if data_id not in frame.source_data_ids:
            raise ValueError(
                "LLoopActivityLedgerFrame.source_data_ids must include activity record data_id"
            )


def _activity_source_lists(frame: LLoopActivityLedgerFrame) -> list[list[str]]:
    result = [
        frame.run_frame_data_ids,
        frame.goal_data_ids,
        frame.budget_plan_data_ids,
        frame.tool_scope_data_ids,
        frame.tool_budget_partition_data_ids,
        frame.tool_catalog_data_ids,
        frame.tool_choice_data_ids,
        frame.query_plan_data_ids,
        frame.query_data_ids,
        frame.control_data_ids,
        frame.tool_result_data_ids,
        frame.tool_distillation_data_ids,
        frame.tool_budget_data_ids,
        frame.continuation_data_ids,
        frame.revision_input_data_ids,
        frame.revision_query_plan_data_ids,
        frame.revision_query_data_ids,
        frame.failure_signal_data_ids,
        frame.explicit_artifact_reference_data_ids,
        frame.document_context_pack_data_ids,
        frame.preserved_data_ids,
        frame.achievement_data_ids,
        frame.output_data_ids,
    ]
    optional_ids = [
        data_id
        for data_id in [
            frame.return_summary_frame_id,
            frame.document_material_packet_frame_id,
        ]
        if data_id is not None
    ]
    if optional_ids:
        result.append(optional_ids)
    return result


__all__ = [
    "L_LOOP_ACTIVITY_LEDGER_DATA_TYPE",
    "L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_NAME",
    "L_LOOP_ACTIVITY_LEDGER_FRAME_SCHEMA_VERSION",
    "L_LOOP_ACTIVITY_LEDGER_GENERATOR",
    "L_LOOP_ACTIVITY_STAGES",
    "LLoopActivityLedgerFrame",
    "validate_l_loop_activity_ledger_frame",
]
