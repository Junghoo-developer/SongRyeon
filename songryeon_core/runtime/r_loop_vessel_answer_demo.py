from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import graph_vessel_neo4j_config_from_env
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.r_loop_vessel_return_packet import (
    record_r_loop_vessel_return_packet,
)
from songryeon_core.core.r_loop_vessel_start_handoff import (
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.registry import build_default_schema_registry
from songryeon_core.core.schemas import (
    MemoryPacketFrom0,
    Node2InputFrame,
    RoutingDecision,
    TurnOutcomeFrame,
    validate_node2_input_frame,
    validate_turn_outcome_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.core.turn_activity_graph_links import (
    record_turn_activity_graph_links,
)
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    record_r_loop_vessel_activity_ledger,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)
from songryeon_core.nodes.node_0_memory_supplier import (
    memory_packet_data_id,
    record_memory_packet,
)
from songryeon_core.nodes.node_1_router import record_routing
from songryeon_core.nodes.node_2_handoff import (
    record_node3_input_brief,
    record_route2_handoff,
)
from songryeon_core.nodes.node_2_metainfo_boundary import (
    build_metainfo_boundary,
    record_boundary,
    run_node2_answer_basis_selection,
)
from songryeon_core.nodes.node_3_reporter import (
    assemble_node3_report_markdown,
    record_report,
    render_report_with_llm,
)
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


DEFAULT_R_VESSEL_ANSWER_DEMO_CACHE_DIR = (
    ".songryeon_core_cache/vessel_r_answer_demo"
)


def run_local_r_loop_vessel_answer_demo(
    *,
    user_question: str,
    batch_id: str = "manual_r_loop_vessel_answer_demo",
    turn_id: str = "turn_r_loop_vessel_answer_demo_0001",
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
    max_node_reads: int = 6,
    max_raw_original_material_reads: int = 5,
    llm_mode: str = "fake",
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    write_trace_cache: bool = False,
    trace_cache_dir: str = DEFAULT_R_VESSEL_ANSWER_DEMO_CACHE_DIR,
    driver_factory_for_test: object | None = None,
) -> dict[str, object]:
    """Run the narrow manual Vessel-R-to-answer demo route.

    This command is a manual demo path only. It does not enable default route=R
    in live chat and it does not write new Vessel graph memory nodes.
    """

    trace_store = TraceStore()
    data_store = DataStore()
    user_input_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref=user_question,
        schema_status="passed",
    )
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
        r_adapter = RLoopVesselTraverseFakeLLMAdapter()
        node_adapter = SongRyeonAllNodesFakeLLMAdapter()
    else:
        r_adapter = build_llm_adapter(runtime_config, endpoint=endpoint)
        node_adapter = r_adapter

    traverse_run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        read_packet=read_packet.packet,
        adapter=r_adapter,
        frame_label=batch_id,
        input_ref=[
            user_input_event.event_id,
            read_packet.trace_event_id,
            start_handoff.trace_event_id,
        ],
        max_node_reads=max_node_reads,
        max_raw_original_material_reads=max_raw_original_material_reads,
        start_handoff_packet_id=start_handoff.packet.packet_id,
    )
    activity_ledger_trace_id, activity_ledger_id, activity_ledger = (
        record_r_loop_vessel_activity_ledger(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            traverse_run=traverse_run,
            frame_label=batch_id,
            source_start_handoff_packet_id=start_handoff.packet.packet_id,
        )
    )
    return_packet = record_r_loop_vessel_return_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        activity_ledger_frame_id=activity_ledger_id,
        frame_label=batch_id,
    )
    turn_activity_link_trace_id, turn_activity_link_id, turn_activity_link = (
        record_turn_activity_graph_links(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            l_loop_activity_ledger_data_ids=[],
            r_graph_access_ledger_data_ids=[],
            r_vessel_activity_ledger_data_ids=[activity_ledger_id],
        )
    )

    route_trace_id, route_id, final_packet_trace_id, final_packet_id = (
        _record_manual_route2_final_packet(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            return_packet_trace_id=return_packet.trace_event_id,
            return_packet_id=return_packet.packet.packet_id,
        )
    )
    outcome_trace_id, outcome_id = _record_turn_outcome(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        final_packet_trace_id=final_packet_trace_id,
        final_packet_id=final_packet_id,
    )
    node2_input_trace_id, node2_input_id = _record_node2_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        final_packet_id=final_packet_id,
        outcome_id=outcome_id,
        route_id=route_id,
        source_data_ids=[
            read_packet.packet.packet_id,
            start_handoff.packet.packet_id,
            *traverse_run.output_data_ids,
            activity_ledger_id,
            return_packet.packet.packet_id,
            turn_activity_link_id,
            route_id,
            final_packet_id,
            outcome_id,
        ],
    )
    handoff_trace_id, handoff_id = record_route2_handoff(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        node2_input_frame_id=node2_input_id,
        node2_input_trace_id=node2_input_trace_id,
        final_memory_packet_id=final_packet_id,
        turn_outcome_id=outcome_id,
        route_ids=[route_id],
        l_loop_output_ids=[],
    )
    boundary = build_metainfo_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        node2_input_frame_id=node2_input_id,
    )
    boundary_id = f"node_2:boundary:{_safe_id_part(batch_id)}"
    boundary_trace_id = record_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        boundary_id=boundary_id,
        boundary=boundary,
        input_ref=[node2_input_trace_id],
    )
    answer_basis_trace_id, answer_basis_id, answer_basis_frame = (
        run_node2_answer_basis_selection(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            user_question=user_question,
            boundary_id=boundary_id,
            boundary=boundary,
            handoff_frame_id=handoff_id,
            adapter=node_adapter,
            input_ref=[handoff_trace_id, boundary_trace_id],
            source_data_ids=[node2_input_id, handoff_id, boundary_id],
        )
    )
    brief_trace_id, brief_id, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        handoff_frame_id=handoff_id,
        boundary=boundary,
        input_trace_ids=[handoff_trace_id, boundary_trace_id, answer_basis_trace_id],
        source_data_ids=[
            node2_input_id,
            handoff_id,
            boundary_id,
            answer_basis_id,
            return_packet.packet.packet_id,
        ],
        answer_basis_frame=answer_basis_frame,
    )

    report_id = f"node_3:report:{_safe_id_part(batch_id)}"
    report_draft = _render_node3_demo_report(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        brief_frame=brief,
        adapter=node_adapter,
        input_ref=[brief_trace_id],
        source_data_ids=[brief_id, handoff_id, boundary_id, answer_basis_id],
    )
    report_trace_id = record_report(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        report_id=report_id,
        rendered_markdown=report_draft["rendered_markdown"],
        allowed_info_ids=[data_ref.data_id for data_ref in boundary.absolute_info],
        allowed_relative_info_ids=[info_ref.info_id for info_ref in boundary.relative_info],
        allowed_mixed_info_ids=[info_ref.info_id for info_ref in boundary.mixed_info],
        input_ref=report_draft["source_trace_ids"],
        source_data_ids=report_draft["source_data_ids"],
        report_generation_source=str(report_draft["generation_source"]),
        llm_reporter_status=str(report_draft["llm_reporter_status"]),
    )
    gatekeeper_trace_id = run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        report_id=report_id,
        boundary_id=boundary_id,
        brief_frame=brief,
        rendered_markdown=str(report_draft["rendered_markdown"]),
        adapter=node_adapter,
        input_ref=[report_trace_id],
        source_data_ids=[report_id, brief_id, boundary_id, answer_basis_id],
    )
    gatekeeper_frame = data_store.require_record("node_4:gatekeeper_frame").payload
    gate_status = (
        str(gatekeeper_frame.get("gate_status") or "failed")
        if isinstance(gatekeeper_frame, dict)
        else "failed"
    )
    final_answer = (
        str(report_draft["rendered_markdown"])
        if gate_status == "pass"
        else _safe_blocking_answer(gatekeeper_frame)
    )
    trace_cache = _write_trace_cache(
        trace_store=trace_store,
        data_store=data_store,
        batch_id=batch_id,
        trace_cache_dir=trace_cache_dir,
    ) if write_trace_cache else {}

    status = (
        "R_LOOP_VESSEL_ANSWER_DEMO_OK"
        if gate_status == "pass"
        else "R_LOOP_VESSEL_ANSWER_DEMO_NOT_PASSED"
    )
    return {
        "status": status,
        "demo_status": "completed" if gate_status == "pass" else "blocked",
        "read_packet_status": read_packet.packet.read_status,
        "traverse_status": traverse_run.result_frame.traverse_status,
        "r_loop_task_status": traverse_run.result_frame.r_loop_task_status,
        "return_packet_status": return_packet.packet.return_status,
        "return_packet_node3_material_ready": return_packet.packet.node3_material_ready,
        "node2_handoff_status": _payload_text(data_store, handoff_id, "handoff_status"),
        "node3_brief_status": brief.brief_status,
        "node3_vessel_r_material_status": brief.vessel_r_material_status,
        "node3_vessel_r_material_count": brief.vessel_r_material_count,
        "node3_reporter_status": report_draft["llm_reporter_status"],
        "node4_gate_status": gate_status,
        "node4_reason": (
            gatekeeper_frame.get("reason")
            if isinstance(gatekeeper_frame, dict)
            else "node_4 gatekeeper frame missing"
        ),
        "final_answer": final_answer,
        "packet_id": read_packet.packet.packet_id,
        "start_handoff_packet_id": start_handoff.packet.packet_id,
        "traverse_result_frame_id": traverse_run.result_frame.frame_id,
        "activity_ledger_frame_id": activity_ledger_id,
        "return_packet_id": return_packet.packet.packet_id,
        "turn_activity_graph_link_frame_id": turn_activity_link_id,
        "route_id": route_id,
        "final_memory_packet_id": final_packet_id,
        "turn_outcome_id": outcome_id,
        "node2_input_id": node2_input_id,
        "node2_handoff_id": handoff_id,
        "boundary_id": boundary_id,
        "answer_basis_id": answer_basis_id,
        "node3_brief_id": brief_id,
        "node3_report_id": report_id,
        "node4_gatekeeper_id": "node_4:gatekeeper_frame",
        "source_trace_ids": _unique_strings(
            [
                user_input_event.event_id,
                read_packet.trace_event_id,
                start_handoff.trace_event_id,
                activity_ledger_trace_id,
                return_packet.trace_event_id,
                turn_activity_link_trace_id,
                route_trace_id,
                final_packet_trace_id,
                outcome_trace_id,
                node2_input_trace_id,
                handoff_trace_id,
                boundary_trace_id,
                answer_basis_trace_id,
                brief_trace_id,
                report_trace_id,
                gatekeeper_trace_id,
            ]
        ),
        "key_frame_ids": {
            "read_packet": read_packet.packet.packet_id,
            "start_handoff": start_handoff.packet.packet_id,
            "traverse_result": traverse_run.result_frame.frame_id,
            "activity_ledger": activity_ledger_id,
            "return_packet": return_packet.packet.packet_id,
            "node2_handoff": handoff_id,
            "node3_brief": brief_id,
            "node3_report": report_id,
            "node4_gatekeeper": "node_4:gatekeeper_frame",
        },
        "activity_ledger_frame": asdict(activity_ledger),
        "return_packet_frame": asdict(return_packet.packet),
        "turn_activity_graph_link_frame": asdict(turn_activity_link),
        "node3_brief_frame": asdict(brief),
        "node4_gatekeeper_frame": gatekeeper_frame,
        "trace_cache": trace_cache,
        "llm_runtime": llm_runtime_status(runtime_config),
        "neo4j_uri": config.uri,
        "neo4j_user": config.user,
        "neo4j_password_configured": config.password is not None,
        "neo4j_allow_no_auth": config.allow_no_auth,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
    }


def render_r_loop_vessel_answer_demo_text(result: dict[str, object]) -> str:
    lines = [
        f"status: {result.get('status')}",
        f"demo_status: {result.get('demo_status')}",
        f"read_packet_status: {result.get('read_packet_status')}",
        f"traverse_status: {result.get('traverse_status')}",
        f"r_loop_task_status: {result.get('r_loop_task_status')}",
        "node_0 Vessel R return packet: "
        f"status={result.get('return_packet_status')} / "
        f"node3_ready={result.get('return_packet_node3_material_ready')}",
        f"node_2 handoff: status={result.get('node2_handoff_status')}",
        "node_3 brief: "
        f"status={result.get('node3_brief_status')} / "
        f"vessel_r={result.get('node3_vessel_r_material_status')} / "
        f"materials={result.get('node3_vessel_r_material_count')}",
        f"node_3 reporter: status={result.get('node3_reporter_status')}",
        f"node_4 gatekeeper: status={result.get('node4_gate_status')}",
        f"node_4 reason: {result.get('node4_reason')}",
        "",
        "Key frames:",
    ]
    key_frame_ids = result.get("key_frame_ids")
    if isinstance(key_frame_ids, dict):
        for key, value in key_frame_ids.items():
            lines.append(f"  {key}: {value}")
    lines.extend(["", "Final answer:", str(result.get("final_answer") or "")])
    return "\n".join(lines)


def _record_manual_route2_final_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    return_packet_trace_id: str,
    return_packet_id: str,
) -> tuple[str, str, str, str]:
    decision = RoutingDecision(
        route="2",
        route_reason="CODE_STATUS:manual_vessel_r_answer_demo_to_node_2",
        route_source="CODE:MANUAL_DEMO_ROUTE",
        required_schema=build_default_schema_registry().binding_for("node_2"),
        expected_next_0_mode="final_trace_for_2",
        route_rule_id="manual_vessel_r_answer_demo_route",
    )
    route_trace_id = record_routing(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        decision=decision,
        input_ref=[return_packet_trace_id],
        source_data_ids=[return_packet_id],
    )
    route_id = "route:2"
    final_packet = MemoryPacketFrom0(
        target="node_2",
        trace_evidence_ids=[route_trace_id, return_packet_trace_id],
    )
    final_packet_trace_id = record_memory_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        packet=final_packet,
        mode="final_trace_for_2",
        input_ref=[route_trace_id, return_packet_trace_id],
        source_data_ids=[route_id, return_packet_id],
        operation_label="CODE_STATUS:vessel_r_answer_demo_trace_supplied",
    )
    return (
        route_trace_id,
        route_id,
        final_packet_trace_id,
        memory_packet_data_id("node_2", "final_trace_for_2"),
    )


def _record_turn_outcome(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    final_packet_trace_id: str,
    final_packet_id: str,
) -> tuple[str, str]:
    outcome_id = f"turn_outcome:{turn_id}"
    outcome = TurnOutcomeFrame(
        outcome_id=outcome_id,
        turn_id=turn_id,
        status="manual_vessel_r_answer_demo_completed",
        decided_by="node_0",
        source_trace_ids=[final_packet_trace_id],
        source_data_ids=[final_packet_id],
    )
    validate_turn_outcome_frame(outcome)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="turn_outcome",
        input_ref=[final_packet_trace_id],
        output_ref=[outcome_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=outcome_id,
        data_type="node_output:turn_outcome",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(outcome),
    )
    return event.event_id, outcome_id


def _record_node2_input_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    final_packet_id: str,
    outcome_id: str,
    route_id: str,
    source_data_ids: list[str],
) -> tuple[str, str]:
    frame_id = f"node2_input:{turn_id}"
    frame = Node2InputFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        final_memory_packet_id=final_packet_id,
        turn_outcome_id=outcome_id,
        route_ids=[route_id],
        l_loop_output_ids=[],
        source_trace_ids=[event.event_id for event in trace_store.events_for_turn(turn_id)],
        source_data_ids=_unique_strings([*source_data_ids, final_packet_id, outcome_id, route_id]),
    )
    validate_node2_input_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type="node_output:node2_input_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id


def _render_node3_demo_report(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    brief_frame,
    adapter,
    input_ref: list[str],
    source_data_ids: list[str],
) -> dict[str, object]:
    try:
        draft = render_report_with_llm(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            brief_frame=brief_frame,
            adapter=adapter,
            input_ref=input_ref,
            source_data_ids=source_data_ids,
        )
        return {
            "rendered_markdown": draft.rendered_markdown,
            "generation_source": draft.generation_source,
            "llm_reporter_status": draft.llm_reporter_status,
            "source_trace_ids": draft.source_trace_ids,
            "source_data_ids": draft.source_data_ids,
        }
    except Exception as exc:
        rendered_markdown = assemble_node3_report_markdown(
            brief_frame=brief_frame,
            body_markdown=(
                "node_3 LLM 보고문 생성이 실패해서 의미 답변은 만들지 않았어.\n\n"
                f"실패 유형: {type(exc).__name__}"
            ),
        )
        return {
            "rendered_markdown": rendered_markdown,
            "generation_source": "CODE/SAFE_RENDERER",
            "llm_reporter_status": "failed",
            "source_trace_ids": list(input_ref),
            "source_data_ids": _unique_strings([*source_data_ids, brief_frame.frame_id]),
        }


def _safe_blocking_answer(gatekeeper_frame: object) -> str:
    reason = "node_4 gatekeeper did not pass"
    if isinstance(gatekeeper_frame, dict):
        reason = str(gatekeeper_frame.get("reason") or reason)
    return (
        "node_4가 이번 데모 답변을 통과시키지 않았어.\n"
        "그래서 사용자-facing 의미 답변은 차단하고, 실패 상태만 보고할게.\n\n"
        f"차단 이유: {reason}"
    )


def _write_trace_cache(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    batch_id: str,
    trace_cache_dir: str,
) -> dict[str, str]:
    target_dir = Path(trace_cache_dir) / _safe_id_part(batch_id)
    trace_path = trace_store.save_json(target_dir / "trace_store.json")
    data_path = data_store.save_json(target_dir / "data_store.json")
    return {
        "trace_store_path": str(trace_path),
        "data_store_path": str(data_path),
    }


def _payload_text(data_store: DataStore, data_id: str, field_name: str) -> str:
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return ""
    value = record.payload.get(field_name)
    return str(value) if value is not None else ""


def _safe_id_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return cleaned or "manual"


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


__all__ = [
    "render_r_loop_vessel_answer_demo_text",
    "run_local_r_loop_vessel_answer_demo",
]
