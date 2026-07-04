from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import graph_vessel_neo4j_config_from_env
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.r_loop_vessel_return_packet import (
    record_r_loop_vessel_return_packet,
)
from songryeon_core.core.r_loop_vessel_start_handoff import (
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.core.turn_activity_graph_links import (
    record_turn_activity_graph_links,
)
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    record_r_loop_vessel_activity_ledger,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseRun,
    run_r_loop_vessel_traverse,
)


@dataclass(frozen=True)
class VesselRLiveRouteRun:
    read_packet_trace_id: str
    read_packet_id: str
    read_packet_status: str
    start_handoff_trace_id: str
    start_handoff_packet_id: str
    traverse_run: RLoopVesselTraverseRun
    activity_ledger_trace_id: str
    activity_ledger_id: str
    return_packet_trace_id: str
    return_packet_id: str
    return_packet_status: str
    return_packet_node3_material_ready: bool
    turn_activity_graph_link_trace_id: str
    turn_activity_graph_link_id: str
    trace_event_ids: list[str]
    output_data_ids: list[str]


def record_vessel_r_live_route(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_question: str,
    batch_id: str,
    adapter: LLMAdapter | None,
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    limit: int = 50,
    max_node_reads: int = 6,
    max_raw_original_material_reads: int = 5,
    input_ref: list[str] | None = None,
    driver_factory_for_test: Any | None = None,
) -> VesselRLiveRouteRun:
    """Record the Vessel-backed R path for a live turn.

    This function only records existing absolute runtime frames. It does not
    write new graph memory nodes and it does not decide answer semantics.
    """

    source_trace_ids = list(input_ref or [])
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
    traverse_run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        read_packet=read_packet.packet,
        adapter=adapter,
        frame_label=batch_id,
        input_ref=[
            *source_trace_ids,
            read_packet.trace_event_id,
            start_handoff.trace_event_id,
        ],
        max_node_reads=max_node_reads,
        max_raw_original_material_reads=max_raw_original_material_reads,
        start_handoff_packet_id=start_handoff.packet.packet_id,
    )
    activity_ledger_trace_id, activity_ledger_id, _ = (
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
    turn_activity_link_trace_id, turn_activity_link_id, _ = (
        record_turn_activity_graph_links(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            l_loop_activity_ledger_data_ids=[],
            r_graph_access_ledger_data_ids=[],
            r_vessel_activity_ledger_data_ids=[activity_ledger_id],
        )
    )

    trace_event_ids = _unique_strings(
        [
            read_packet.trace_event_id,
            start_handoff.trace_event_id,
            *traverse_run.trace_event_ids,
            activity_ledger_trace_id,
            return_packet.trace_event_id,
            turn_activity_link_trace_id,
        ]
    )
    output_data_ids = _unique_strings(
        [
            read_packet.packet.packet_id,
            start_handoff.packet.packet_id,
            *traverse_run.output_data_ids,
            activity_ledger_id,
            return_packet.packet.packet_id,
            turn_activity_link_id,
        ]
    )
    return VesselRLiveRouteRun(
        read_packet_trace_id=read_packet.trace_event_id,
        read_packet_id=read_packet.packet.packet_id,
        read_packet_status=read_packet.packet.read_status,
        start_handoff_trace_id=start_handoff.trace_event_id,
        start_handoff_packet_id=start_handoff.packet.packet_id,
        traverse_run=traverse_run,
        activity_ledger_trace_id=activity_ledger_trace_id,
        activity_ledger_id=activity_ledger_id,
        return_packet_trace_id=return_packet.trace_event_id,
        return_packet_id=return_packet.packet.packet_id,
        return_packet_status=return_packet.packet.return_status,
        return_packet_node3_material_ready=return_packet.packet.node3_material_ready,
        turn_activity_graph_link_trace_id=turn_activity_link_trace_id,
        turn_activity_graph_link_id=turn_activity_link_id,
        trace_event_ids=trace_event_ids,
        output_data_ids=output_data_ids,
    )


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
