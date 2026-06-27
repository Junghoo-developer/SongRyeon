from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schema_parts.base import NodeMovement, SchemaBinding


@dataclass
class TraceEvent:
    """일 하나가 벌어질 때마다 남기는 trace 기록 조각."""

    # trace 조각 하나를 나중에 다시 찾기 위한 고유 번호.
    event_id: str
    # 이 trace가 어느 사용자 턴에서 생겼는지 나타내는 번호.
    turn_id: str
    # 이 trace가 생긴 시간. 처음에는 문자열로 두고 나중에 datetime으로 바꿔도 된다.
    timestamp: str
    # 이 흔적을 만든 주체. 예: user, node_0, node_1, L2, tool_search.
    actor: str
    # 어떤 종류의 사건인지. 예: user_input, node_output, routing, tool_call.
    event_type: str
    # 이 사건이 참고한 입력 데이터 ID 목록.
    input_ref: list[str] = field(default_factory=list)
    # 이 사건이 만들어낸 출력 데이터 ID 목록.
    output_ref: list[str] = field(default_factory=list)
    # 원문이 길 때 원문이 저장된 위치나 ID.
    raw_content_ref: str | None = None
    # 이 사건의 출력이 스키마 검사를 통과했는지. 예: passed, failed, not_checked.
    schema_status: str = "not_checked"


@dataclass
class UnifiedState:
    """0번을 제외한 일반 노드와 루프가 함께 보는 현재 턴 상태."""

    # 이번 턴을 구분하는 ID.
    turn_id: str
    # 현재 턴을 시작한 사용자 입력 원문 또는 원문 ID.
    user_input: str
    # 1번 라우터가 실제로 선택한 대상. 예: "2", "L".
    current_route: str | None = None
    # 이번 턴에서 지금까지 쌓인 trace 이벤트 ID 목록.
    trace_event_ids: list[str] = field(default_factory=list)
    # 현재 노드에 강제되는 스키마 정보.
    active_schema: SchemaBinding | None = None
    # 2번 메타정보 경계관이 만든 결과 ID.
    metainfo_boundary_id: str | None = None
    # 현재 실행 중인 루프 이름. 예: "L".
    current_loop: str | None = None
    # 가장 최근 실패/부족 신호의 ID.
    latest_failure_signal_id: str | None = None


@dataclass
class TurnStateCapsule:
    """이전 턴 전체를 다음 턴의 0번이 다시 읽을 수 있게 묶은 trace 색인 캡슐."""

    # 학습 메모: TurnStateCapsule은 이전 턴을 "이해한 요약"이 아니라 다시 찾아가기 위한 색인 카드다.
    # 이 캡슐이 색인하는 턴 ID.
    turn_id: str
    # 그 턴에서 지나간 모든 노드/루프 동선.
    node_movements: list[NodeMovement] = field(default_factory=list)
    # 이 캡슐이 참조하는 전체 trace 이벤트 ID 목록.
    trace_event_ids: list[str] = field(default_factory=list)
    # 해당 턴의 사용자 입력 trace ID.
    user_input_trace_id: str | None = None
    # 해당 턴의 최종 응답 trace ID.
    final_response_trace_id: str | None = None


@dataclass
class ZeroState:
    """0 기억공급관만 보는 특수 기억 상태."""

    # 최근 대화 원본. 예: 최근 8턴.
    recent_raw_conversation: list[dict[str, str]] = field(default_factory=list)
    # 이전 턴 trace를 다시 찾기 위한 캡슐 목록. 여기에는 LLM 의미 요약을 넣지 않는다.
    previous_turn_capsules: list[TurnStateCapsule] = field(default_factory=list)
    # 이번 턴에서 실시간으로 쌓이는 trace ID 목록.
    current_turn_trace_ids: list[str] = field(default_factory=list)
    # 각 노드나 루프가 어떤 정보를 필요로 하는지 적은 프로필.
    node_profiles: dict[str, dict[str, str]] = field(default_factory=dict)
    # 0번이 기억 부족을 선언한 횟수.
    memory_insufficient_count: int = 0


@dataclass
class MemoryPacketFrom0:
    """0 기억공급관이 다음 노드나 루프에 넘기는 기억 패킷의 절대정보 뼈대."""

    # 이 기억 패킷을 받을 대상. 예: node_1, node_2, L.
    target: str
    # 이 기억 패킷의 근거가 되는 trace ID 목록.
    trace_evidence_ids: list[str] = field(default_factory=list)
    # 기억 부족이나 접근 실패가 있으면 그 실패 신호 ID를 담는다.
    insufficient_signal_id: str | None = None


@dataclass
class RoutingDecision:
    """1 상황판단 라우터가 실제로 어디로 보냈는지 기록하는 라우팅 결정."""

    # 다음으로 보낼 대상. MVP에서는 "2" 또는 "L".
    route: str
    # 라우팅을 고른 이유. 현재는 규칙 기반 또는 MVP 강제 라우팅 이유다.
    route_reason: str = ""
    # 이 라우팅 결정의 실제 생성자. 현재 node_1은 LLM이 아니라 규칙 스텁이다.
    route_source: str = "CODE:RULE_STUB"
    # 다음 대상에 강제할 스키마 정보.
    required_schema: SchemaBinding | None = None
    # 라우팅 직후 0번이 어떤 모드로 호출되어야 하는지.
    expected_next_0_mode: str = ""
    # 절대 정보: 코드 스텁이 사용한 라우팅 규칙 ID.
    route_rule_id: str = ""
    # 절대 정보: 키워드 규칙이 감지한 문자열 목록.
    matched_keywords: list[str] = field(default_factory=list)
    # 절대 정보: 사용자 입력이 아니라 런타임 정책으로 강제된 경우의 policy flag.
    policy_flag: str | None = None
    route_confidence: float | None = None
    needs_more_memory: bool = False
    llm_routing_status: str = "not_run"
    llm_call_data_id: str | None = None
    llm_trace_event_id: str | None = None
    fallback_after_llm_failure: bool = False
    router_llm_failure_data_id: str | None = None
    router_llm_failure_trace_event_id: str | None = None
    router_llm_failure_type: str | None = None
    fallback_policy: str | None = None
    fallback_allowed_by_runtime_policy: bool = False
    fallback_source_route_rule_id: str | None = None


__all__ = [
    "MemoryPacketFrom0",
    "RoutingDecision",
    "TraceEvent",
    "TurnStateCapsule",
    "UnifiedState",
    "ZeroState",
]
