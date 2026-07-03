from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import graph_vessel_neo4j_config_from_env
from songryeon_core.core.r_loop_vessel_read_packet import (
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.r_loop_vessel_start_handoff import (
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselOneStepFakeLLMAdapter,
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_one_step,
    run_r_loop_vessel_traverse,
)
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    record_r_loop_vessel_activity_ledger,
)


def run_local_r_loop_vessel_one_step(
    *,
    user_question: str,
    batch_id: str = "manual_r_loop_vessel_one_step",
    turn_id: str = "turn_r_loop_vessel_one_step_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
    llm_mode: str = "fake",
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, object]:
    """Read a Vessel packet and run one guarded R traversal step."""

    now = _now_iso()
    trace_store = TraceStore()
    data_store = DataStore()
    config = graph_vessel_neo4j_config_from_env(
        uri=uri,
        user=user,
        password=password,
        database=database,
        allow_no_auth=allow_no_auth,
    )
    read_packet = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:read_packet",
        config=config,
        created_at=now,
        limit=limit,
    )
    runtime_config = build_llm_runtime_config(
        mode=llm_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    if runtime_config.mode == "fake":
        adapter = RLoopVesselOneStepFakeLLMAdapter()
    else:
        adapter = build_llm_adapter(runtime_config, endpoint=endpoint)

    run = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        read_packet=read_packet.packet,
        adapter=adapter,
        frame_label=batch_id,
        input_ref=[read_packet.trace_event_id],
    )

    return {
        "status": "R_LOOP_VESSEL_ONE_STEP_OK"
        if run.result_frame.one_step_status == "completed"
        else "R_LOOP_VESSEL_ONE_STEP_NOT_PASSED",
        "one_step_status": run.result_frame.one_step_status,
        "failure_stage": run.result_frame.failure_stage,
        "failure_type": run.result_frame.failure_type,
        "failure_reason": run.result_frame.failure_reason,
        "failure_payload_summary": run.result_frame.failure_payload_summary,
        "read_packet_status": read_packet.packet.read_status,
        "packet_id": read_packet.packet.packet_id,
        "entry_candidate_count": read_packet.packet.entry_candidate_count,
        "summary_candidate_count": read_packet.packet.summary_candidate_count,
        "selected_graph_node_id": run.result_frame.selected_graph_node_id,
        "inspected_graph_node_id": run.result_frame.inspected_graph_node_id,
        "sufficiency_status": run.result_frame.sufficiency_status,
        "continuation_status": run.result_frame.continuation_status,
        "r_loop_task_status": run.return_summary.r_loop_task_status if run.return_summary else None,
        "hierarchy_child_candidate_count": (
            run.graph_traversal_candidate_surface.candidate_count
            if run.graph_traversal_candidate_surface is not None
            else None
        ),
        "hierarchy_child_candidate_node_ids": (
            run.graph_traversal_candidate_surface.candidate_graph_node_ids
            if run.graph_traversal_candidate_surface is not None
            else []
        ),
        "llm_runtime": llm_runtime_status(runtime_config),
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "result_frame": asdict(run.result_frame),
        "r1_goal_frame": asdict(run.r1_goal) if run.r1_goal is not None else None,
        "r2_selection_frame": asdict(run.r2_selection)
        if run.r2_selection is not None
        else None,
        "r3_inspection_frame": asdict(run.r3_inspection)
        if run.r3_inspection is not None
        else None,
        "continuation_frame": asdict(run.continuation)
        if run.continuation is not None
        else None,
        "return_summary_frame": asdict(run.return_summary)
        if run.return_summary is not None
        else None,
        "graph_traversal_candidate_surface_frame": (
            asdict(run.graph_traversal_candidate_surface)
            if run.graph_traversal_candidate_surface is not None
            else None
        ),
    }


def run_local_r_loop_vessel_traverse(
    *,
    user_question: str,
    batch_id: str = "manual_r_loop_vessel_traverse",
    turn_id: str = "turn_r_loop_vessel_traverse_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
    llm_mode: str = "fake",
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    driver_factory_for_test: object | None = None,
) -> dict[str, object]:
    """Read a Vessel packet and run a guarded multi-step R traversal."""

    now = _now_iso()
    trace_store = TraceStore()
    data_store = DataStore()
    config = graph_vessel_neo4j_config_from_env(
        uri=uri,
        user=user,
        password=password,
        database=database,
        allow_no_auth=allow_no_auth,
    )
    read_packet = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:read_packet",
        config=config,
        created_at=now,
        limit=limit,
        driver_factory=driver_factory_for_test,
    )
    start_handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:start_handoff",
        read_packet=read_packet.packet,
        source_read_packet_trace_event_id=read_packet.trace_event_id,
    )
    runtime_config = build_llm_runtime_config(
        mode=llm_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    if runtime_config.mode == "fake":
        adapter = RLoopVesselTraverseFakeLLMAdapter()
    else:
        adapter = build_llm_adapter(runtime_config, endpoint=endpoint)

    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        read_packet=read_packet.packet,
        adapter=adapter,
        frame_label=batch_id,
        input_ref=[read_packet.trace_event_id, start_handoff.trace_event_id],
        start_handoff_packet_id=start_handoff.packet.packet_id,
    )
    (
        activity_ledger_trace_event_id,
        activity_ledger_frame_id,
        activity_ledger,
    ) = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        traverse_run=run,
        frame_label=batch_id,
        source_start_handoff_packet_id=start_handoff.packet.packet_id,
    )

    return {
        "status": "R_LOOP_VESSEL_TRAVERSE_OK"
        if run.result_frame.traverse_status == "completed"
        else "R_LOOP_VESSEL_TRAVERSE_NOT_PASSED",
        "traverse_status": run.result_frame.traverse_status,
        "failure_stage": run.result_frame.failure_stage,
        "failure_type": run.result_frame.failure_type,
        "failure_reason": run.result_frame.failure_reason,
        "failure_payload_summary": run.result_frame.failure_payload_summary,
        "read_packet_status": read_packet.packet.read_status,
        "packet_id": read_packet.packet.packet_id,
        "start_handoff_packet_status": start_handoff.packet.packet_status,
        "start_handoff_packet_id": start_handoff.packet.packet_id,
        "start_handoff_trace_event_id": start_handoff.trace_event_id,
        "entry_candidate_count": read_packet.packet.entry_candidate_count,
        "summary_candidate_count": read_packet.packet.summary_candidate_count,
        "step_count": run.result_frame.step_count,
        "selected_graph_node_ids": run.result_frame.selected_graph_node_ids,
        "inspected_graph_node_ids": run.result_frame.inspected_graph_node_ids,
        "final_graph_node_id": run.result_frame.final_graph_node_id,
        "final_sufficiency_status": run.result_frame.final_sufficiency_status,
        "final_continuation_status": run.result_frame.final_continuation_status,
        "r_loop_task_status": run.result_frame.r_loop_task_status,
        "activity_ledger_frame_id": activity_ledger_frame_id,
        "activity_ledger_trace_event_id": activity_ledger_trace_event_id,
        "activity_ledger_task_status": activity_ledger.r_loop_task_status,
        "activity_ledger_selected_count": len(activity_ledger.selected_graph_node_ids),
        "activity_ledger_inspected_count": len(activity_ledger.inspected_graph_node_ids),
        "activity_ledger_candidate_count": len(activity_ledger.candidate_graph_node_ids),
        "terminal_material_seen_count": run.result_frame.terminal_material_seen_count,
        "min_terminal_material_count": run.result_frame.min_terminal_material_count,
        "raw_original_material_seen_count": (
            run.result_frame.raw_original_material_seen_count
        ),
        "max_raw_original_material_count": (
            run.result_frame.max_raw_original_material_count
        ),
        "raw_original_read_cap_reached": run.result_frame.raw_original_read_cap_reached,
        "early_stop_guard_trigger_count": run.result_frame.early_stop_guard_trigger_count,
        "candidate_surface_frame_ids": run.result_frame.candidate_surface_frame_ids,
        "graph_traversal_candidate_surface_frame_ids": (
            run.result_frame.graph_traversal_candidate_surface_frame_ids
        ),
        "llm_runtime": llm_runtime_status(runtime_config),
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "start_handoff_packet_frame": asdict(start_handoff.packet),
        "activity_ledger_frame": asdict(activity_ledger),
        "result_frame": asdict(run.result_frame),
        "r1_goal_frame": asdict(run.r1_goal) if run.r1_goal is not None else None,
        "r2_selection_frames": [asdict(frame) for frame in run.r2_selections],
        "r3_inspection_frames": [asdict(frame) for frame in run.r3_inspections],
        "continuation_frames": [asdict(frame) for frame in run.continuations],
        "return_summary_frame": asdict(run.return_summary)
        if run.return_summary is not None
        else None,
    }


def render_r_loop_vessel_one_step_text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result.get('status')}",
        f"one_step_status: {result.get('one_step_status')}",
        f"read_packet_status: {result.get('read_packet_status')}",
        f"entry_candidate_count: {result.get('entry_candidate_count')}",
        f"summary_candidate_count: {result.get('summary_candidate_count')}",
        f"selected_graph_node_id: {result.get('selected_graph_node_id')}",
        f"inspected_graph_node_id: {result.get('inspected_graph_node_id')}",
        f"sufficiency_status: {result.get('sufficiency_status')}",
        f"continuation_status: {result.get('continuation_status')}",
        f"r_loop_task_status: {result.get('r_loop_task_status')}",
        f"hierarchy_child_candidate_count: {result.get('hierarchy_child_candidate_count')}",
    ]
    child_ids = result.get("hierarchy_child_candidate_node_ids")
    if isinstance(child_ids, list) and child_ids:
        lines.append("hierarchy_child_candidate_node_ids:")
        for child_id in child_ids[:20]:
            lines.append(f"  - {child_id}")
        if len(child_ids) > 20:
            lines.append(f"  ... +{len(child_ids) - 20} more")
    failure_stage = result.get("failure_stage")
    failure_type = result.get("failure_type")
    failure_reason = result.get("failure_reason")
    if failure_stage or failure_type or failure_reason:
        lines.append(f"failure_stage: {failure_stage}")
        lines.append(f"failure_type: {failure_type}")
        lines.append(f"failure_reason: {failure_reason}")
    failure_payload_summary = result.get("failure_payload_summary")
    if isinstance(failure_payload_summary, dict) and failure_payload_summary:
        lines.append(f"failure_payload_summary: {failure_payload_summary}")
    r1 = result.get("r1_goal_frame")
    if isinstance(r1, dict):
        lines.append("")
        lines.append(f"R1 goal: {r1.get('graph_search_goal')}")
        lines.append(f"R1 granularity: {r1.get('required_information_granularity')}")
    r2 = result.get("r2_selection_frame")
    if isinstance(r2, dict):
        lines.append("")
        lines.append(f"R2 selection_reason: {r2.get('selection_reason')}")
    r3 = result.get("r3_inspection_frame")
    if isinstance(r3, dict):
        lines.append("")
        lines.append(f"R3 inspection_reason: {r3.get('inspection_reason')}")
    return "\n".join(lines)


def render_r_loop_vessel_traverse_text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result.get('status')}",
        f"traverse_status: {result.get('traverse_status')}",
        f"read_packet_status: {result.get('read_packet_status')}",
        "node_0 Vessel R start handoff: "
        f"status={result.get('start_handoff_packet_status')} / "
        f"packet={result.get('start_handoff_packet_id')}",
        f"entry_candidate_count: {result.get('entry_candidate_count')}",
        f"summary_candidate_count: {result.get('summary_candidate_count')}",
        f"step_count: {result.get('step_count')}",
        f"final_graph_node_id: {result.get('final_graph_node_id')}",
        f"final_sufficiency_status: {result.get('final_sufficiency_status')}",
        f"final_continuation_status: {result.get('final_continuation_status')}",
        f"r_loop_task_status: {result.get('r_loop_task_status')}",
        "R Vessel activity ledger: "
        f"status={result.get('activity_ledger_task_status')} / "
        f"selected={result.get('activity_ledger_selected_count')} / "
        f"inspected={result.get('activity_ledger_inspected_count')} / "
        f"candidates={result.get('activity_ledger_candidate_count')}",
        f"terminal_material_seen_count: {result.get('terminal_material_seen_count')}",
        f"min_terminal_material_count: {result.get('min_terminal_material_count')}",
        f"raw_original_material_seen_count: {result.get('raw_original_material_seen_count')}",
        f"max_raw_original_material_count: {result.get('max_raw_original_material_count')}",
        f"raw_original_read_cap_reached: {result.get('raw_original_read_cap_reached')}",
        f"early_stop_guard_trigger_count: {result.get('early_stop_guard_trigger_count')}",
    ]
    failure_stage = result.get("failure_stage")
    failure_type = result.get("failure_type")
    failure_reason = result.get("failure_reason")
    if failure_stage or failure_type or failure_reason:
        lines.append(f"failure_stage: {failure_stage}")
        lines.append(f"failure_type: {failure_type}")
        lines.append(f"failure_reason: {failure_reason}")
    failure_payload_summary = result.get("failure_payload_summary")
    if isinstance(failure_payload_summary, dict) and failure_payload_summary:
        lines.append(f"failure_payload_summary: {failure_payload_summary}")
    r1 = result.get("r1_goal_frame")
    if isinstance(r1, dict):
        lines.append("")
        lines.append(f"R1 goal: {r1.get('graph_search_goal')}")
        lines.append(f"R1 granularity: {r1.get('required_information_granularity')}")
    r2_frames = result.get("r2_selection_frames")
    r3_frames = result.get("r3_inspection_frames")
    if isinstance(r2_frames, list) or isinstance(r3_frames, list):
        lines.append("")
        lines.append("Traversal path:")
        max_len = max(
            len(r2_frames) if isinstance(r2_frames, list) else 0,
            len(r3_frames) if isinstance(r3_frames, list) else 0,
        )
        for index in range(max_len):
            r2 = r2_frames[index] if isinstance(r2_frames, list) and index < len(r2_frames) else None
            r3 = r3_frames[index] if isinstance(r3_frames, list) and index < len(r3_frames) else None
            selected = r2.get("selected_graph_node_id") if isinstance(r2, dict) else None
            inspected = r3.get("inspected_graph_node_id") if isinstance(r3, dict) else None
            sufficiency = r3.get("sufficiency_status") if isinstance(r3, dict) else None
            action = r3.get("recommended_next_action") if isinstance(r3, dict) else None
            lines.append(
                f"  step {index + 1}: selected={selected} inspected={inspected} "
                f"sufficiency={sufficiency} action={action}"
            )
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "render_r_loop_vessel_one_step_text",
    "render_r_loop_vessel_traverse_text",
    "run_local_r_loop_vessel_one_step",
    "run_local_r_loop_vessel_traverse",
]
