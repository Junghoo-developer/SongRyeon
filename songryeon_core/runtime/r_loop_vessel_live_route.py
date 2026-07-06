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

# 학습용 큰 그림:
# 이 파일은 qwen-turn 같은 "현장 턴"에서 route=R이 실제로 선택되었을 때,
# Vessel 그래프 기억을 읽고 R1/R2/R3 탐색을 실행한 뒤 다시 node_2/node_3 쪽으로
# 넘길 수 있는 기록들을 만드는 좁은 통합 경로다.
#
# 여기서 중요한 점:
# - Neo4j에 새 기억을 쓰지 않는다.
# - 그래프 의미를 코드가 대신 판단하지 않는다.
# - 이미 존재하는 Vessel graph를 읽고, R 루프가 남긴 trace/data를 정리한다.
# - 마지막에 node_0이 "R이 무엇을 했는지"를 return packet으로 감싼다.


@dataclass(frozen=True)
class VesselRLiveRouteRun:
    # live route 한 번이 만든 핵심 좌표 묶음.
    # 실제 내용 전체를 복사해 들고 다니기보다, trace/data id를 통해
    # "어디에 무엇이 기록되었는지"를 후속 단계가 다시 찾을 수 있게 한다.
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

    # input_ref는 이 R 경로가 어떤 이전 trace에서 이어졌는지 알려주는 연결 고리다.
    # 예를 들어 node_1 route=R trace가 있으면 여기서 같이 보존된다.
    source_trace_ids = list(input_ref or [])

    # Neo4j 접속 정보는 env/CLI에서 가져온다.
    # 이 단계는 "어디에 있는 Vessel을 읽을 것인가"를 정할 뿐,
    # 아직 실제 그래프를 읽지는 않는다.
    config = graph_vessel_neo4j_config_from_env(
        uri=uri,
        user=user,
        password=password,
        database=database,
        allow_no_auth=allow_no_auth,
    )

    # 1단계: node_0이 Vessel에서 R이 볼 수 있는 시작 후보 묶음을 읽는다.
    # 이 read packet은 R1/R2/R3가 세상을 보는 첫 창이다.
    read_packet = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:read_packet",
        config=config,
        limit=limit,
        driver_factory=driver_factory_for_test,
    )

    # 2단계: node_0이 "이 read packet을 R 루프에게 넘긴다"는 handoff를 기록한다.
    # 이것이 없으면 나중에 R이 어디서 출발했는지 추적하기 어렵다.
    start_handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:start_handoff",
        read_packet=read_packet.packet,
        source_read_packet_trace_event_id=read_packet.trace_event_id,
    )

    # 3단계: 실제 R 탐색.
    # R1은 목표/예산을 잡고, R2는 후보를 고르고, R3는 고른 node를 검사한다.
    # max_node_reads와 max_raw_original_material_reads는 그래프 탐색 폭주를 막는 예산이다.
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

    # 4단계: R이 실제로 어떤 node들을 골랐고 읽었는지 장부로 남긴다.
    # 이 장부가 있어야 턴 캡슐/그래프에서 "이번 턴의 R 활동"을 나중에 백업하거나 연결할 수 있다.
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

    # 5단계: node_0이 R 활동 장부를 downstream용 return packet으로 바꾼다.
    # R 내부 기록을 그대로 node_3에게 던지는 게 아니라, "node_3에게 줄 수 있는 재료가 있는가"를
    # code가 절대정보로 정리하는 단계다.
    return_packet = record_r_loop_vessel_return_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        activity_ledger_frame_id=activity_ledger_id,
        frame_label=batch_id,
    )

    # 6단계: 이번 턴의 raw capsule과 R 활동 장부를 연결한다.
    # 이렇게 해야 "이 대화 턴에서 어떤 그래프 기억을 건드렸는가"를 나중에 역추적할 수 있다.
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

    # 마지막으로 이 live route 전체가 만든 trace/data 좌표를 중복 없이 모은다.
    # 여기서도 내용 해석은 하지 않고, 후속 감사/렌더러가 따라갈 좌표만 정리한다.
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
