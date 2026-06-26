from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DataRef:
    """시스템이 확인할 수 있는 데이터 하나를 가리키는 절대정보 참조."""

    # 데이터 하나를 가리키는 고유 ID.
    data_id: str
    # 데이터 종류. 예: trace_event, user_message, node_output, schema_result.
    data_type: str
    # 시스템이 이 데이터의 존재를 확인했는지.
    exists: bool = True
    # 데이터가 만들어진 시간. 모르면 None으로 둔다.
    created_at: str | None = None
    # 이 데이터 존재를 확인하게 해준 trace ID.
    source_trace_id: str | None = None


@dataclass
class SchemaBinding:
    """어떤 스키마가 어디에 적용되고 검증됐는지 기록하는 절대정보."""

    # 적용할 스키마 이름.
    schema_name: str
    # 적용할 스키마 버전.
    schema_version: str
    # 이 스키마가 반드시 적용되어야 하는지.
    required: bool = True
    # 스키마 검증 결과. 예: passed, failed, not_checked.
    validation_status: str = "not_checked"
    # 스키마 검증 과정 자체를 기록한 trace ID.
    validation_trace_id: str | None = None


@dataclass
class NodeMovement:
    """한 턴 안에서 노드나 루프가 실제로 이동한 동선을 기록하는 절대정보."""

    # 노드 동선 하나를 구분하는 ID.
    movement_id: str
    # 이 동선이 속한 턴 ID.
    turn_id: str
    # 턴 안에서 몇 번째로 실행됐는지 나타내는 순서 번호.
    step_index: int
    # 실행된 노드나 루프의 ID. 예: node_0, node_1, L1.
    node_id: str
    # 실행 단위의 종류. 예: node, loop_node, tool.
    node_type: str = "node"
    # 실제 호출된 모드. 예: pre_route_report, final_trace_for_2.
    mode: str | None = None
    # 이 실행 단위가 입력으로 받은 trace ID 목록.
    input_trace_ids: list[str] = field(default_factory=list)
    # 이 실행 단위가 출력으로 만든 trace ID 목록.
    output_trace_ids: list[str] = field(default_factory=list)
    # 이 실행 단위가 입력으로 받은 데이터 ID 목록.
    input_data_ids: list[str] = field(default_factory=list)
    # 이 실행 단위가 출력으로 만든 데이터 ID 목록.
    output_data_ids: list[str] = field(default_factory=list)
    # 실행 시작 시간.
    started_at: str | None = None
    # 실행 종료 시간.
    finished_at: str | None = None
    # 실행 상태. 예: started, completed, failed.
    status: str = "started"


TASK_FRAME_SCHEMA_NAME = "TaskFrame"
TASK_FRAME_SCHEMA_VERSION = "0.1"
TASK_RESULT_FRAME_SCHEMA_NAME = "TaskResultFrame"
TASK_RESULT_FRAME_SCHEMA_VERSION = "0.1"


@dataclass
class TaskFrame:
    """스케줄러/큐 구조로 가기 전에 남기는 작업 장부의 최소 task 선언."""

    # task 하나를 구분하는 ID.
    task_id: str
    # 이 task가 속한 턴 ID.
    turn_id: str
    # 현재 순차 런타임에서 몇 번째 task인지 나타내는 순서 번호.
    step_index: int
    # 이 task가 실행한 노드나 루프. 예: node_0, node_1, L.
    node_id: str
    # task의 종류. 예: node, loop, scheduler_stub.
    task_kind: str
    # 실제 실행 모드. 예: routing, report, gatekeeper.
    mode: str | None = None
    # v0에서는 직전 task에만 의존하는 순차 실행으로 기록한다.
    depends_on_task_ids: list[str] = field(default_factory=list)
    # task 입력 trace ID 목록.
    input_trace_ids: list[str] = field(default_factory=list)
    # task 입력 data ID 목록.
    input_data_ids: list[str] = field(default_factory=list)
    # task가 만들 것으로 기록된 trace ID 목록.
    expected_output_trace_ids: list[str] = field(default_factory=list)
    # task가 만들 것으로 기록된 data ID 목록.
    expected_output_data_ids: list[str] = field(default_factory=list)
    # 이 task에 배정된 모델이나 코드 실행자.
    assigned_model_id: str = "CODE"
    # 이 task에 배정된 worker. v0에서는 실제 worker가 아니라 장부용 이름이다.
    assigned_worker_id: str = "local_sync_worker"
    # 현재 task 실행 정책. v0에서는 기존 순차 실행을 task로 장부화한다.
    scheduling_policy: str = "sequential_v0"
    # task frame을 만든 주체.
    created_by: str = "CODE:TASK_LEDGER_V0"
    # task 상태. v0에서는 실행 후 장부화하므로 completed가 기본이다.
    status: str = "completed"
    schema_name: str = TASK_FRAME_SCHEMA_NAME
    schema_version: str = TASK_FRAME_SCHEMA_VERSION


@dataclass
class TaskResultFrame:
    """task 실행 결과를 장부에 남기는 최소 결과 프레임."""

    # result frame 하나를 구분하는 ID.
    result_id: str
    # 대응하는 task ID.
    task_id: str
    # 이 결과가 속한 턴 ID.
    turn_id: str
    # task 실행 결과 상태.
    status: str
    # task가 실제로 만든 trace ID 목록.
    output_trace_ids: list[str] = field(default_factory=list)
    # task가 실제로 만든 data ID 목록.
    output_data_ids: list[str] = field(default_factory=list)
    # 실패 종류. 성공이면 None.
    failure_type: str | None = None
    # 실패 이유. 성공이면 None.
    failure_reason: str | None = None
    # task result를 최종 장부에 반영한 주체.
    committed_by: str = "CODE:TASK_LEDGER_V0"
    schema_name: str = TASK_RESULT_FRAME_SCHEMA_NAME
    schema_version: str = TASK_RESULT_FRAME_SCHEMA_VERSION


def validate_task_frame(frame: TaskFrame) -> None:
    """TaskFrame이 최소 작업 장부 규칙을 지키는지 확인한다."""

    for field_name, value in {
        "task_id": frame.task_id,
        "turn_id": frame.turn_id,
        "node_id": frame.node_id,
        "task_kind": frame.task_kind,
        "assigned_model_id": frame.assigned_model_id,
        "assigned_worker_id": frame.assigned_worker_id,
        "scheduling_policy": frame.scheduling_policy,
        "created_by": frame.created_by,
        "status": frame.status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"TaskFrame.{field_name} must not be empty")
    if frame.step_index < 1:
        raise ValueError("TaskFrame.step_index must be positive")
    if frame.schema_name != TASK_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown task frame schema_name: {frame.schema_name}")
    if frame.schema_version != TASK_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown task frame schema_version: {frame.schema_version}")
    if frame.status not in {"queued", "running", "completed", "failed", "skipped"}:
        raise ValueError(f"unknown TaskFrame.status: {frame.status}")
    _validate_string_list("TaskFrame.depends_on_task_ids", frame.depends_on_task_ids)
    _validate_string_list("TaskFrame.input_trace_ids", frame.input_trace_ids)
    _validate_string_list("TaskFrame.input_data_ids", frame.input_data_ids)
    _validate_string_list("TaskFrame.expected_output_trace_ids", frame.expected_output_trace_ids)
    _validate_string_list("TaskFrame.expected_output_data_ids", frame.expected_output_data_ids)


def validate_task_result_frame(frame: TaskResultFrame) -> None:
    """TaskResultFrame이 최소 결과 장부 규칙을 지키는지 확인한다."""

    for field_name, value in {
        "result_id": frame.result_id,
        "task_id": frame.task_id,
        "turn_id": frame.turn_id,
        "status": frame.status,
        "committed_by": frame.committed_by,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"TaskResultFrame.{field_name} must not be empty")
    if frame.schema_name != TASK_RESULT_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown task result schema_name: {frame.schema_name}")
    if frame.schema_version != TASK_RESULT_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown task result schema_version: {frame.schema_version}")
    if frame.status not in {"completed", "failed", "skipped"}:
        raise ValueError(f"unknown TaskResultFrame.status: {frame.status}")
    if frame.status == "failed" and not frame.failure_type:
        raise ValueError("failed TaskResultFrame must include failure_type")
    _validate_string_list("TaskResultFrame.output_trace_ids", frame.output_trace_ids)
    _validate_string_list("TaskResultFrame.output_data_ids", frame.output_data_ids)


def _validate_string_list(field_name: str, values: list[str]) -> None:
    for value in values:
        if not value:
            raise ValueError(f"{field_name} must not contain empty values")


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


RELATIVE_INFO_REF_SCHEMA_NAME = "RelativeInfoRef"
RELATIVE_INFO_REF_SCHEMA_VERSION = "0.1"
MIXED_INFO_REF_SCHEMA_NAME = "MixedInfoRef"
MIXED_INFO_REF_SCHEMA_VERSION = "0.1"


@dataclass
class RelativeInfoRef:
    """하나의 절대정보 field에 직접 대응하는 의미 판단 조각."""

    # 학습 메모: 상대정보는 "출처가 있으니 상대"가 아니다.
    # claim 하나가 특정 record의 특정 field 하나에 바로 붙어 있을 때만 이 그릇을 쓴다.
    # 절대 정보: boundary 안에서 상대 정보 조각 하나를 구분하는 ID.
    info_id: str
    # 절대 정보: 이 상대 정보가 직접 대응하는 원본 DataStore record ID.
    source_data_id: str
    # 절대 정보: 원본 payload 안의 필드 경로. 예: reason, candidates[0].purpose.
    field_path: str
    # 절대 정보: 상대 정보의 종류. 예: single_document_summary.
    info_kind: str
    # 상대 정보: 실제로 보고가 허가된 자연어 본문.
    text: str
    # 절대 정보: 이 상대 정보의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 상대 정보의 근거 data ID 목록. source_data_id를 반드시 포함한다.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 의미 정보가 하나의 field에 직접 대응한다는 분류 근거.
    source_mode: str = "direct_field"
    # 절대 정보: claim과 source의 대응 방식.
    claim_alignment: str = "one_to_one_field"
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = RELATIVE_INFO_REF_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = RELATIVE_INFO_REF_SCHEMA_VERSION


def validate_relative_info_ref(ref: RelativeInfoRef) -> None:
    """RelativeInfoRef가 하나의 원본 field와 근거 ID를 갖췄는지 확인한다."""

    for field_name, value in {
        "info_id": ref.info_id,
        "source_data_id": ref.source_data_id,
        "field_path": ref.field_path,
        "info_kind": ref.info_kind,
        "text": ref.text,
        "source_mode": ref.source_mode,
        "claim_alignment": ref.claim_alignment,
        "schema_name": ref.schema_name,
        "schema_version": ref.schema_version,
    }.items():
        if not value:
            raise ValueError(f"RelativeInfoRef.{field_name} must not be empty")
    if ref.schema_name != RELATIVE_INFO_REF_SCHEMA_NAME:
        raise ValueError(f"unknown relative info schema_name: {ref.schema_name}")
    if ref.schema_version != RELATIVE_INFO_REF_SCHEMA_VERSION:
        raise ValueError(f"unknown relative info schema_version: {ref.schema_version}")
    if ref.source_mode != "direct_field":
        raise ValueError(f"unknown RelativeInfoRef.source_mode: {ref.source_mode}")
    if ref.claim_alignment != "one_to_one_field":
        raise ValueError(f"unknown RelativeInfoRef.claim_alignment: {ref.claim_alignment}")
    if ref.source_data_id not in ref.source_data_ids:
        raise ValueError("RelativeInfoRef.source_data_ids must include source_data_id")
    if not ref.source_trace_ids:
        raise ValueError("RelativeInfoRef.source_trace_ids must not be empty")
    if not ref.source_data_ids:
        raise ValueError("RelativeInfoRef.source_data_ids must not be empty")
    for trace_id in ref.source_trace_ids:
        if not trace_id:
            raise ValueError("RelativeInfoRef.source_trace_ids must not contain empty values")
    for data_id in ref.source_data_ids:
        if not data_id:
            raise ValueError("RelativeInfoRef.source_data_ids must not contain empty values")


@dataclass
class MixedInfoRef:
    """여러 절대정보 묶음에 근거한 의미 판단 조각."""

    # 학습 메모: 혼합정보는 "출처가 여러 개라서 대충 섞인 정보"가 아니다.
    # 하나의 record/field로 못 박으면 오히려 거짓말이 되는 source bundle 기반 판단을 담는다.
    # 절대 정보: boundary 안에서 혼합 정보 조각 하나를 구분하는 ID.
    info_id: str
    # 절대 정보: 이 혼합 정보가 저장되어 있는 DataStore record ID.
    source_data_id: str
    # 절대 정보: 원본 payload 안의 필드 경로. 예: reason, candidates[0].purpose.
    field_path: str
    # 절대 정보: 혼합 정보의 종류. 예: l2_query_candidate_purpose.
    info_kind: str
    # 혼합 정보: 실제로 보고가 허가된 자연어 본문.
    text: str
    # 절대 정보: 이 혼합 정보의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 혼합 정보의 근거 data ID 목록. source_data_id를 반드시 포함한다.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 의미 정보가 source bundle에 근거한다는 분류 근거.
    source_mode: str = "source_bundle"
    # 절대 정보: claim과 source의 대응 방식.
    claim_alignment: str = "multi_source_bundle"
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = MIXED_INFO_REF_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = MIXED_INFO_REF_SCHEMA_VERSION


def validate_mixed_info_ref(ref: MixedInfoRef) -> None:
    """MixedInfoRef가 원본 위치와 source bundle 근거 ID를 갖췄는지 확인한다."""

    for field_name, value in {
        "info_id": ref.info_id,
        "source_data_id": ref.source_data_id,
        "field_path": ref.field_path,
        "info_kind": ref.info_kind,
        "text": ref.text,
        "source_mode": ref.source_mode,
        "claim_alignment": ref.claim_alignment,
        "schema_name": ref.schema_name,
        "schema_version": ref.schema_version,
    }.items():
        if not value:
            raise ValueError(f"MixedInfoRef.{field_name} must not be empty")
    if ref.schema_name != MIXED_INFO_REF_SCHEMA_NAME:
        raise ValueError(f"unknown mixed info schema_name: {ref.schema_name}")
    if ref.schema_version != MIXED_INFO_REF_SCHEMA_VERSION:
        raise ValueError(f"unknown mixed info schema_version: {ref.schema_version}")
    if ref.source_mode != "source_bundle":
        raise ValueError(f"unknown MixedInfoRef.source_mode: {ref.source_mode}")
    if ref.claim_alignment != "multi_source_bundle":
        raise ValueError(f"unknown MixedInfoRef.claim_alignment: {ref.claim_alignment}")
    if ref.source_data_id not in ref.source_data_ids:
        raise ValueError("MixedInfoRef.source_data_ids must include source_data_id")
    if not ref.source_trace_ids:
        raise ValueError("MixedInfoRef.source_trace_ids must not be empty")
    if not ref.source_data_ids:
        raise ValueError("MixedInfoRef.source_data_ids must not be empty")
    for trace_id in ref.source_trace_ids:
        if not trace_id:
            raise ValueError("MixedInfoRef.source_trace_ids must not contain empty values")
    for data_id in ref.source_data_ids:
        if not data_id:
            raise ValueError("MixedInfoRef.source_data_ids must not contain empty values")


@dataclass
class MetainfoBoundary:
    """2 메타정보 경계관이 확인한 정보 경계를 분류해서 담는다."""

    # 학습 메모: 이 boundary는 새 의미를 만드는 곳이 아니라, 다음 노드가 써도 되는 재료의 울타리다.
    # trace나 코드가 자동으로 확인한 기준점 정보.
    absolute_info: list[DataRef] = field(default_factory=list)
    # 하나의 절대정보 field에 직접 대응하는 LLM 의미 판단.
    relative_info: list[RelativeInfoRef] = field(default_factory=list)
    # 여러 절대정보 묶음에 근거한 LLM 의미 판단.
    mixed_info: list[MixedInfoRef] = field(default_factory=list)


@dataclass
class MemoryItem:
    """0 기억공급관이 다음 노드에 넘긴 기억 조각 하나."""

    # 기억 조각 ID. packet 안에서만 유일해도 된다.
    item_id: str
    # 기억 조각의 종류. 예: trace_evidence, previous_capsule, node_profile.
    item_type: str
    # 기억 조각의 짧은 설명. 지금은 원문 요약이 아니라 운영용 표지다.
    text: str
    # 이 기억 조각의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 이 기억 조각의 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)


@dataclass
class MemoryPacketPayload:
    """0 기억공급관이 만든 memory packet의 DataStore 저장용 본체."""

    packet_id: str
    turn_id: str
    target: str
    mode: str
    compression_summary: str = ""
    # 절대 정보: 이 패킷이 공급한 trace evidence 개수.
    evidence_trace_count: int = 0
    # 절대 정보: 코드가 붙인 운영 상태 라벨. 자연어 요약이 아니다.
    operation_label: str = "CODE_STATUS:trace_evidence_supplied"
    generated_by: str = "CODE:RULE_STUB"
    llm_semantic_summary_status: str = "not_run"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    evidence_trace_ids: list[str] = field(default_factory=list)
    insufficient_signal_id: str | None = None
    memory_items: list[MemoryItem] = field(default_factory=list)
    schema_name: str = "MemoryPacketPayload"
    schema_version: str = "0.1"


def validate_memory_packet_payload(payload: MemoryPacketPayload) -> None:
    """MemoryPacketPayload의 최소 절대정보 규칙을 확인한다."""

    required_text_fields = {
        "packet_id": payload.packet_id,
        "turn_id": payload.turn_id,
        "target": payload.target,
        "mode": payload.mode,
        "compression_summary": payload.compression_summary,
        "schema_name": payload.schema_name,
        "schema_version": payload.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"MemoryPacketPayload.{field_name} must not be empty")

    for item in payload.memory_items:
        if not item.item_id:
            raise ValueError("MemoryItem.item_id must not be empty")
        if not item.item_type:
            raise ValueError("MemoryItem.item_type must not be empty")
        if not item.text:
            raise ValueError("MemoryItem.text must not be empty")


@dataclass
class RoutingDecisionFrame:
    """1 라우터가 만든 라우팅 결정의 DataStore 저장용 본체."""

    frame_id: str
    turn_id: str
    route: str
    route_reason: str
    expected_next_0_mode: str
    route_source: str = "CODE:RULE_STUB"
    llm_routing_status: str = "not_run"
    llm_call_data_id: str | None = None
    llm_trace_event_id: str | None = None
    route_rule_id: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    policy_flag: str | None = None
    route_confidence: float | None = None
    needs_more_memory: bool = False
    fallback_after_llm_failure: bool = False
    router_llm_failure_data_id: str | None = None
    router_llm_failure_trace_event_id: str | None = None
    router_llm_failure_type: str | None = None
    fallback_policy: str | None = None
    fallback_allowed_by_runtime_policy: bool = False
    fallback_source_route_rule_id: str | None = None
    required_schema: dict[str, object] | None = None
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = "RoutingDecisionFrame"
    schema_version: str = "0.2"


def validate_routing_decision_frame(frame: RoutingDecisionFrame) -> None:
    """RoutingDecisionFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "route": frame.route,
        "route_reason": frame.route_reason,
        "expected_next_0_mode": frame.expected_next_0_mode,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"RoutingDecisionFrame.{field_name} must not be empty")
    if frame.route not in {"L", "2"}:
        raise ValueError(f"unknown route: {frame.route}")
    if frame.llm_routing_status not in {"not_run", "ran", "failed"}:
        raise ValueError(f"unknown llm_routing_status: {frame.llm_routing_status}")
    if frame.route_confidence is not None:
        if not isinstance(frame.route_confidence, (int, float)):
            raise TypeError("RoutingDecisionFrame.route_confidence must be numeric")
        if frame.route_confidence < 0.0 or frame.route_confidence > 1.0:
            raise ValueError("RoutingDecisionFrame.route_confidence must be between 0 and 1")
    if frame.fallback_after_llm_failure:
        if frame.llm_routing_status != "failed":
            raise ValueError("RoutingDecisionFrame fallback requires llm_routing_status=failed")
        if not frame.fallback_policy:
            raise ValueError("RoutingDecisionFrame fallback_policy must not be empty")
        if not frame.fallback_allowed_by_runtime_policy:
            raise ValueError("RoutingDecisionFrame fallback must be explicitly allowed")
        if not frame.fallback_source_route_rule_id:
            raise ValueError("RoutingDecisionFrame fallback_source_route_rule_id must not be empty")
        if not frame.router_llm_failure_type:
            raise ValueError("RoutingDecisionFrame router_llm_failure_type must not be empty")
        if not (
            frame.router_llm_failure_data_id
            or frame.router_llm_failure_trace_event_id
        ):
            raise ValueError("RoutingDecisionFrame fallback must cite the failed LLM call")


@dataclass
class ReportFrame:
    """3 보고관이 만든 최종 보고의 DataStore 저장용 본체."""

    report_id: str
    turn_id: str
    rendered_markdown: str
    allowed_info_ids: list[str] = field(default_factory=list)
    allowed_relative_info_ids: list[str] = field(default_factory=list)
    allowed_mixed_info_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    report_generation_source: str = "CODE/RENDERER"
    llm_reporter_status: str = "not_run"
    schema_name: str = "ReportFrame"
    schema_version: str = "0.1"


def validate_report_frame(frame: ReportFrame) -> None:
    """ReportFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "report_id": frame.report_id,
        "turn_id": frame.turn_id,
        "rendered_markdown": frame.rendered_markdown,
        "report_generation_source": frame.report_generation_source,
        "llm_reporter_status": frame.llm_reporter_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"ReportFrame.{field_name} must not be empty")


NODE2_BOUNDARY_REVIEW_FRAME_SCHEMA_NAME = "Node2BoundaryReviewFrame"
NODE2_BOUNDARY_REVIEW_FRAME_SCHEMA_VERSION = "0.1"
NODE2_BOUNDARY_REVIEW_STATUSES = {"ran", "failed"}


@dataclass
class Node2BoundaryReviewFrame:
    """LLM이 node_2의 metainfo boundary를 검토했다는 실행 기록."""

    review_id: str
    turn_id: str
    boundary_id: str
    review_status: str
    ready_for_report: bool
    boundary_summary: str
    review_generation_source: str
    warnings: list[str] = field(default_factory=list)
    excluded_claims: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE2_BOUNDARY_REVIEW_FRAME_SCHEMA_NAME
    schema_version: str = NODE2_BOUNDARY_REVIEW_FRAME_SCHEMA_VERSION


def validate_node2_boundary_review_frame(frame: Node2BoundaryReviewFrame) -> None:
    """Node2BoundaryReviewFrame의 최소 스키마 규칙을 확인한다."""

    for field_name, value in {
        "review_id": frame.review_id,
        "turn_id": frame.turn_id,
        "boundary_id": frame.boundary_id,
        "review_status": frame.review_status,
        "boundary_summary": frame.boundary_summary,
        "review_generation_source": frame.review_generation_source,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node2BoundaryReviewFrame.{field_name} must not be empty")
    if frame.schema_name != NODE2_BOUNDARY_REVIEW_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown Node2BoundaryReviewFrame schema_name: {frame.schema_name}")
    if frame.schema_version != NODE2_BOUNDARY_REVIEW_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown Node2BoundaryReviewFrame schema_version: {frame.schema_version}")
    if frame.review_status not in NODE2_BOUNDARY_REVIEW_STATUSES:
        raise ValueError(f"unknown Node2BoundaryReviewFrame.review_status: {frame.review_status}")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("Node2BoundaryReviewFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("Node2BoundaryReviewFrame.source_data_ids must not contain empty values")


NODE4_GATEKEEPER_FRAME_SCHEMA_NAME = "Node4GatekeeperFrame"
NODE4_GATEKEEPER_FRAME_SCHEMA_VERSION = "0.1"
NODE4_GATE_STATUSES = {"pass", "needs_revision", "failed"}


@dataclass
class Node4GatekeeperFrame:
    """node_4가 최종 보고문의 근거/환각 위험을 검사한 기록."""

    gate_id: str
    turn_id: str
    report_id: str
    boundary_id: str
    gate_status: str
    reason: str
    gate_generation_source: str
    llm_gate_status: str
    checked_claims: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    revision_targets: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE4_GATEKEEPER_FRAME_SCHEMA_NAME
    schema_version: str = NODE4_GATEKEEPER_FRAME_SCHEMA_VERSION


def validate_node4_gatekeeper_frame(frame: Node4GatekeeperFrame) -> None:
    """Node4GatekeeperFrame의 최소 스키마 규칙을 확인한다."""

    for field_name, value in {
        "gate_id": frame.gate_id,
        "turn_id": frame.turn_id,
        "report_id": frame.report_id,
        "boundary_id": frame.boundary_id,
        "gate_status": frame.gate_status,
        "reason": frame.reason,
        "gate_generation_source": frame.gate_generation_source,
        "llm_gate_status": frame.llm_gate_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node4GatekeeperFrame.{field_name} must not be empty")
    if frame.schema_name != NODE4_GATEKEEPER_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown Node4GatekeeperFrame schema_name: {frame.schema_name}")
    if frame.schema_version != NODE4_GATEKEEPER_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown Node4GatekeeperFrame schema_version: {frame.schema_version}")
    if frame.gate_status not in NODE4_GATE_STATUSES:
        raise ValueError(f"unknown Node4 gate_status: {frame.gate_status}")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("Node4GatekeeperFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("Node4GatekeeperFrame.source_data_ids must not contain empty values")


LLM_CALL_FRAME_SCHEMA_NAME = "LLMCallFrame"
LLM_CALL_FRAME_SCHEMA_VERSION = "0.1"
LLM_CALL_PARSE_STATUSES = {"passed", "failed", "not_checked"}
LLM_CALL_VALIDATION_STATUSES = {"passed", "failed", "not_checked"}
LLM_CALL_FAILURE_TYPES = {"none", "parse_failed", "schema_failed", "adapter_failed"}


@dataclass
class LLMCallFrame:
    """LLM 호출 요청과 응답 검증 결과를 DataStore에 저장하는 프레임."""

    # 절대 정보: DataStore에 저장될 LLM call data_id.
    call_id: str
    # 절대 정보: 이 호출이 속한 턴 ID.
    turn_id: str
    # 절대 정보: LLM 호출을 요청한 노드 ID.
    node_id: str
    # 절대 정보: 사용한 prompt 파일이나 prompt 식별자.
    prompt_ref: str
    # 절대 정보: 입력 payload가 근거로 삼은 DataStore record ID 목록.
    input_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 호출된 모델 ID.
    model_id: str = ""
    # 절대 정보: 요청한 응답 형식.
    response_format: str = "json"
    # 절대 정보: LLM이 실제로 반환한 원문. adapter 실패 시 비어 있을 수 있다.
    raw_text: str = ""
    # 절대 정보: JSON 파싱 통과 여부.
    parse_status: str = "not_checked"
    # 절대 정보: 출력 스키마 검증 통과 여부.
    validation_status: str = "not_checked"
    # 절대 정보: 이번 최종 호출 전 재시도 횟수.
    retry_count: int = 0
    # 절대 정보: 실패 종류. 성공하면 none.
    failure_type: str = "none"
    # 절대 정보: 실패 메시지. 성공하면 비어 있을 수 있다.
    error_message: str = ""
    # 절대 정보: 이 호출의 입력 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 호출의 입력 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = LLM_CALL_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = LLM_CALL_FRAME_SCHEMA_VERSION


def validate_llm_call_frame(frame: LLMCallFrame) -> None:
    """LLMCallFrame의 최소 절대정보 규칙을 확인한다."""

    required_text_fields = {
        "call_id": frame.call_id,
        "turn_id": frame.turn_id,
        "node_id": frame.node_id,
        "prompt_ref": frame.prompt_ref,
        "model_id": frame.model_id,
        "response_format": frame.response_format,
        "parse_status": frame.parse_status,
        "validation_status": frame.validation_status,
        "failure_type": frame.failure_type,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"LLMCallFrame.{field_name} must not be empty")

    if frame.schema_name != LLM_CALL_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown LLM call frame schema_name: {frame.schema_name}")
    if frame.schema_version != LLM_CALL_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown LLM call frame schema_version: {frame.schema_version}")
    if frame.parse_status not in LLM_CALL_PARSE_STATUSES:
        raise ValueError(f"unknown LLM parse_status: {frame.parse_status}")
    if frame.validation_status not in LLM_CALL_VALIDATION_STATUSES:
        raise ValueError(f"unknown LLM validation_status: {frame.validation_status}")
    if frame.failure_type not in LLM_CALL_FAILURE_TYPES:
        raise ValueError(f"unknown LLM failure_type: {frame.failure_type}")
    if not isinstance(frame.retry_count, int):
        raise TypeError("LLMCallFrame.retry_count must be an integer")
    if frame.retry_count < 0:
        raise ValueError("LLMCallFrame.retry_count must not be negative")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LLMCallFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LLMCallFrame.source_data_ids must not contain empty values")


@dataclass
class TurnOutcomeFrame:
    """한 턴의 종료 상태를 DataStore에 저장하기 위한 프레임."""

    outcome_id: str
    turn_id: str
    status: str
    decided_by: str
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    failure_signal_ids: list[str] = field(default_factory=list)
    schema_name: str = "TurnOutcomeFrame"
    schema_version: str = "0.1"


def validate_turn_outcome_frame(frame: TurnOutcomeFrame) -> None:
    """TurnOutcomeFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "outcome_id": frame.outcome_id,
        "turn_id": frame.turn_id,
        "status": frame.status,
        "decided_by": frame.decided_by,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"TurnOutcomeFrame.{field_name} must not be empty")


@dataclass
class Node2InputFrame:
    """0이 2 메타정보 경계관에게 넘길 입력 범위를 정리한 프레임."""

    # 절대 정보: DataStore에 저장될 node2 input frame data_id.
    frame_id: str
    # 절대 정보: 이 입력 프레임이 속한 턴.
    turn_id: str
    # 절대 정보: 0이 2에게 마지막으로 넘긴 memory packet data_id.
    final_memory_packet_id: str
    # 절대 정보: 이번 턴 종료 상태 data_id.
    turn_outcome_id: str
    # 절대 정보: 이번 턴의 라우팅 결정 data_id 목록.
    route_ids: list[str] = field(default_factory=list)
    # 절대 정보: L루프가 만든 핵심 output data_id 목록.
    l_loop_output_ids: list[str] = field(default_factory=list)
    # 절대 정보: 2가 볼 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 2가 볼 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: boundary 생성 정책 이름.
    boundary_policy: str = "absolute_info_from_node2_input_v0"
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = "Node2InputFrame"
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = "0.1"


def validate_node2_input_frame(frame: Node2InputFrame) -> None:
    """Node2InputFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "final_memory_packet_id": frame.final_memory_packet_id,
        "turn_outcome_id": frame.turn_outcome_id,
        "boundary_policy": frame.boundary_policy,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node2InputFrame.{field_name} must not be empty")

    required_data_ids = [frame.final_memory_packet_id, frame.turn_outcome_id]
    required_data_ids.extend(frame.route_ids)
    required_data_ids.extend(frame.l_loop_output_ids)
    for data_id in required_data_ids:
        if data_id not in frame.source_data_ids:
            raise ValueError(f"Node2InputFrame.source_data_ids misses required id: {data_id}")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("Node2InputFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("Node2InputFrame.source_data_ids must not contain empty values")


NODE2_HANDOFF_FRAME_SCHEMA_NAME = "Node2HandoffFrame"
NODE2_HANDOFF_FRAME_SCHEMA_VERSION = "0.1"
NODE2_HANDOFF_STATUSES = {"ready", "insufficient", "blocked"}


@dataclass
class Node2HandoffFrame:
    """1이 route=2를 고른 뒤 0/code가 2에게 넘기는 최종 handoff 기록."""

    frame_id: str
    turn_id: str
    user_question: str
    handoff_status: str
    node2_input_frame_id: str
    final_memory_packet_id: str
    turn_outcome_id: str
    route_ids: list[str] = field(default_factory=list)
    route_path: list[str] = field(default_factory=list)
    l_loop_was_run: bool = False
    l1_goal_present: bool = False
    l2_query_present: bool = False
    l3_preserved_present: bool = False
    l3_achievement_present: bool = False
    search_result_count: int = 0
    reportable_document_count: int = 0
    raw_document_extract_record_count: int = 0
    empty_document_extract_record_count: int = 0
    # 호환 필드. ORDER_098부터 의미는 reportable_document_count와 같다.
    read_doc_count: int = 0
    actual_l_run_count: int = 0
    blocked_same_turn_l_reroute_request_count: int = 0
    same_turn_l_reroute_controller_decisions: list[str] = field(default_factory=list)
    l_internal_revision_count: int = 0
    brief_available: bool = False
    insufficiency_reasons: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE2_HANDOFF_FRAME_SCHEMA_NAME
    schema_version: str = NODE2_HANDOFF_FRAME_SCHEMA_VERSION


def validate_node2_handoff_frame(frame: Node2HandoffFrame) -> None:
    """Node2HandoffFrame의 절대정보 무결성 규칙을 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "user_question": frame.user_question,
        "handoff_status": frame.handoff_status,
        "node2_input_frame_id": frame.node2_input_frame_id,
        "final_memory_packet_id": frame.final_memory_packet_id,
        "turn_outcome_id": frame.turn_outcome_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node2HandoffFrame.{field_name} must not be empty")
    if frame.schema_name != NODE2_HANDOFF_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown Node2HandoffFrame schema_name: {frame.schema_name}")
    if frame.schema_version != NODE2_HANDOFF_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown Node2HandoffFrame schema_version: {frame.schema_version}")
    if frame.handoff_status not in NODE2_HANDOFF_STATUSES:
        raise ValueError(f"unknown Node2HandoffFrame.handoff_status: {frame.handoff_status}")
    for field_name, value in {
        "search_result_count": frame.search_result_count,
        "reportable_document_count": frame.reportable_document_count,
        "raw_document_extract_record_count": frame.raw_document_extract_record_count,
        "empty_document_extract_record_count": frame.empty_document_extract_record_count,
        "read_doc_count": frame.read_doc_count,
        "actual_l_run_count": frame.actual_l_run_count,
        "blocked_same_turn_l_reroute_request_count": frame.blocked_same_turn_l_reroute_request_count,
        "l_internal_revision_count": frame.l_internal_revision_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node2HandoffFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node2HandoffFrame.{field_name} must not be negative")
    if frame.read_doc_count != frame.reportable_document_count:
        raise ValueError("Node2HandoffFrame.read_doc_count must mirror reportable_document_count")
    if frame.raw_document_extract_record_count < frame.reportable_document_count:
        raise ValueError(
            "Node2HandoffFrame.raw_document_extract_record_count must not be smaller than reportable_document_count"
        )
    if frame.empty_document_extract_record_count > frame.raw_document_extract_record_count:
        raise ValueError(
            "Node2HandoffFrame.empty_document_extract_record_count must not exceed raw_document_extract_record_count"
        )
    if frame.node2_input_frame_id not in frame.source_data_ids:
        raise ValueError("Node2HandoffFrame.source_data_ids must include node2_input_frame_id")
    if frame.final_memory_packet_id not in frame.source_data_ids:
        raise ValueError("Node2HandoffFrame.source_data_ids must include final_memory_packet_id")
    if frame.turn_outcome_id not in frame.source_data_ids:
        raise ValueError("Node2HandoffFrame.source_data_ids must include turn_outcome_id")
    for route_id in frame.route_ids:
        if not route_id:
            raise ValueError("Node2HandoffFrame.route_ids must not contain empty values")
    for decision in frame.same_turn_l_reroute_controller_decisions:
        if not decision:
            raise ValueError(
                "Node2HandoffFrame.same_turn_l_reroute_controller_decisions must not contain empty values"
            )
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("Node2HandoffFrame.source_data_ids must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("Node2HandoffFrame.source_trace_ids must not contain empty values")


NODE3_INPUT_BRIEF_FRAME_SCHEMA_NAME = "Node3InputBriefFrame"
NODE3_INPUT_BRIEF_FRAME_SCHEMA_VERSION = "0.1"
NODE3_INPUT_BRIEF_STATUSES = {"ready", "insufficient"}


@dataclass
class Node3BriefDocument:
    """node_3가 읽기 좋은 문서 재료 하나."""

    document_name: str
    char_count: int
    text: str
    source_data_id: str = ""


@dataclass
class Node3BriefClaim:
    """node_3가 답변 재료로 사용할 수 있는 근거 달린 의미 주장."""

    kind: str
    text: str
    info_class: str = "mixed"
    source_mode: str = ""
    claim_alignment: str = ""
    source_data_id: str = ""


@dataclass
class Node3BriefRuntimeTask:
    """node_3가 현재 턴 실행 순서를 설명할 때 사용할 수 있는 task 요약."""

    # 현재 턴 안에서 몇 번째로 실행된 작업인지.
    step_index: int
    # node_0, node_1, L처럼 사람이 읽을 수 있는 실행 주체.
    node_label: str
    # routing, L_loop처럼 사람이 읽을 수 있는 실행 모드.
    mode: str
    # completed, failed, skipped 같은 실행 상태.
    status: str
    # CODE:RULE_STUB, LLM:qwen3:14b처럼 배정된 실행자 라벨.
    model_label: str = ""
    # 내부 ID를 노출하지 않고도 근거 규모를 알 수 있게 하는 trace 개수.
    evidence_trace_count: int = 0
    # 내부 ID를 노출하지 않고도 근거 규모를 알 수 있게 하는 data 개수.
    evidence_data_count: int = 0


@dataclass
class Node3InputBriefFrame:
    """node_3에게 내부 ID 장부 대신 의미 단위 입력을 제공하기 위한 브리프."""

    frame_id: str
    turn_id: str
    user_question: str
    brief_status: str
    handoff_frame_id: str
    read_documents: list[Node3BriefDocument] = field(default_factory=list)
    # 절대 정보: L3가 보존한 search_docs 후보 문서의 고유 개수.
    # 후보 문서는 "검색 결과에 등장한 문서"일 뿐이고, read_documents처럼 원문을 읽은 문서가 아니다.
    search_candidate_count: int = 0
    # 절대 정보: node_3가 후보 규모를 사실대로 말할 수 있게 만든 문서명 목록.
    # 내부 추적 ID 대신 사람이 읽을 수 있는 문서명만 넣는다.
    search_candidate_documents: list[str] = field(default_factory=list)
    allowed_claims: list[Node3BriefClaim] = field(default_factory=list)
    runtime_tasks: list[Node3BriefRuntimeTask] = field(default_factory=list)
    reporting_rules: list[str] = field(default_factory=list)
    insufficiency_reasons: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE3_INPUT_BRIEF_FRAME_SCHEMA_NAME
    schema_version: str = NODE3_INPUT_BRIEF_FRAME_SCHEMA_VERSION


def validate_node3_input_brief_frame(frame: Node3InputBriefFrame) -> None:
    """Node3InputBriefFrame이 node_3용 의미 브리프 규칙을 지키는지 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "user_question": frame.user_question,
        "brief_status": frame.brief_status,
        "handoff_frame_id": frame.handoff_frame_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node3InputBriefFrame.{field_name} must not be empty")
    if frame.schema_name != NODE3_INPUT_BRIEF_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown Node3InputBriefFrame schema_name: {frame.schema_name}")
    if frame.schema_version != NODE3_INPUT_BRIEF_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown Node3InputBriefFrame schema_version: {frame.schema_version}")
    if frame.brief_status not in NODE3_INPUT_BRIEF_STATUSES:
        raise ValueError(f"unknown Node3InputBriefFrame.brief_status: {frame.brief_status}")
    if frame.handoff_frame_id not in frame.source_data_ids:
        raise ValueError("Node3InputBriefFrame.source_data_ids must include handoff_frame_id")
    if not isinstance(frame.search_candidate_count, int):
        raise TypeError("Node3InputBriefFrame.search_candidate_count must be an integer")
    if frame.search_candidate_count < 0:
        raise ValueError("Node3InputBriefFrame.search_candidate_count must not be negative")
    for document_name in frame.search_candidate_documents:
        if not document_name:
            raise ValueError("Node3InputBriefFrame.search_candidate_documents must not contain empty values")
    for document in frame.read_documents:
        _validate_node3_brief_document(document)
    for claim in frame.allowed_claims:
        _validate_node3_brief_claim(claim)
    for runtime_task in frame.runtime_tasks:
        _validate_node3_brief_runtime_task(runtime_task)
    for rule in frame.reporting_rules:
        if not rule:
            raise ValueError("Node3InputBriefFrame.reporting_rules must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("Node3InputBriefFrame.source_data_ids must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("Node3InputBriefFrame.source_trace_ids must not contain empty values")


def _validate_node3_brief_document(document: Node3BriefDocument) -> None:
    for field_name, value in {
        "document_name": document.document_name,
        "text": document.text,
    }.items():
        if not value:
            raise ValueError(f"Node3BriefDocument.{field_name} must not be empty")
    if not isinstance(document.char_count, int):
        raise TypeError("Node3BriefDocument.char_count must be an integer")
    if document.char_count < 0:
        raise ValueError("Node3BriefDocument.char_count must not be negative")


def _validate_node3_brief_claim(claim: Node3BriefClaim) -> None:
    for field_name, value in {
        "kind": claim.kind,
        "text": claim.text,
        "info_class": claim.info_class,
    }.items():
        if not value:
            raise ValueError(f"Node3BriefClaim.{field_name} must not be empty")
    if claim.info_class not in {"relative", "mixed"}:
        raise ValueError(f"unknown Node3BriefClaim.info_class: {claim.info_class}")


def _validate_node3_brief_runtime_task(runtime_task: Node3BriefRuntimeTask) -> None:
    for field_name, value in {
        "node_label": runtime_task.node_label,
        "mode": runtime_task.mode,
        "status": runtime_task.status,
    }.items():
        if not value:
            raise ValueError(f"Node3BriefRuntimeTask.{field_name} must not be empty")
    if not isinstance(runtime_task.step_index, int):
        raise TypeError("Node3BriefRuntimeTask.step_index must be an integer")
    if runtime_task.step_index < 1:
        raise ValueError("Node3BriefRuntimeTask.step_index must be positive")
    if not isinstance(runtime_task.evidence_trace_count, int):
        raise TypeError("Node3BriefRuntimeTask.evidence_trace_count must be an integer")
    if runtime_task.evidence_trace_count < 0:
        raise ValueError("Node3BriefRuntimeTask.evidence_trace_count must not be negative")
    if not isinstance(runtime_task.evidence_data_count, int):
        raise TypeError("Node3BriefRuntimeTask.evidence_data_count must be an integer")
    if runtime_task.evidence_data_count < 0:
        raise ValueError("Node3BriefRuntimeTask.evidence_data_count must not be negative")


L1_GOAL_FRAME_SCHEMA_NAME = "L1GoalFrame"
L1_GOAL_FRAME_SCHEMA_VERSION = "0.2"
L1_GOAL_SOURCES = {"rule_based_l_route", "llm_l_route"}
L1_TARGET_LOOPS = {"L"}
L1_EVIDENCE_REQUIREMENT_KINDS = {
    "unspecified",
    "single_doc_lookup",
    "multi_doc_relationship",
    "exploratory_multi_doc",
    "exact_artifact_lookup",
    "insufficiency_check",
}
L1_RANDOMNESS_MODES = {
    "not_random",
    "semantic_exploration",
    "true_random_required",
}


@dataclass
class L1GoalFrame:
    """L1이 L루프의 운영 목표를 DataStore에 저장하기 위한 프레임."""

    # 절대 정보: DataStore에 저장될 goal frame data_id와 같은 값.
    frame_id: str
    # 절대 정보: 이 goal frame이 만들어진 사용자 턴 ID.
    turn_id: str
    # 혼합 정보: 이번 L루프가 끝날 때 달성해야 할 최종 운영 목표.
    # 사용자 답변 자체가 아니라, L루프가 다음 노드에 넘겨야 할 근거 재료,
    # 문서 조회 결과, 부족 신호 같은 산출 목표를 나타낸다.
    macro_goal: str
    # 혼합 정보: macro_goal을 세운 이유. source trace/data와 함께만 의미가 있다.
    macro_goal_reason: str
    # 혼합 정보: macro_goal을 실행하기 위한 중간 목표나 바로 다음 행동.
    # 사용자 요청 조건은 주로 이 미시 목표와 그 이유에 구체적으로 반영된다.
    micro_goal: str
    # 혼합 정보: micro_goal을 세운 이유. source trace/data와 함께만 의미가 있다.
    micro_goal_reason: str
    # 절대 정보: 목표가 어디서 왔는지 나타내는 출처 표지.
    goal_source: str
    # 절대 정보: 이 목표가 적용되는 루프 이름.
    target_loop: str
    # 혼합 정보: L1이 판단한 근거 재료의 종류.
    # 코드는 이 값을 사용자 문장 해석으로 쓰지 않고, 예산 정책의 입력 신호로만 사용한다.
    evidence_requirement_kind: str = "unspecified"
    # 혼합 정보: L1이 이번 L루프 성공에 필요하다고 본 최소 원문 열람 문서 수.
    minimum_read_documents: int = 0
    # 혼합 정보: 문서 간 비교/연관점 분석이 필요한지에 대한 L1의 판단.
    requires_cross_document_analysis: bool = False
    # 혼합 정보: 사용자의 "무작위/탐색" 요구를 L1이 어떤 실행 모드로 이해했는지.
    randomness_mode: str = "not_random"
    # 혼합 정보: L루프가 node_1로 돌아가기 전에 어떤 재료를 갖추면 성공인지 적는다.
    l_loop_success_condition: str = ""
    # 혼합 정보: L1이 이번 목표 달성에 필요하다고 요청한 search_docs 후보 수.
    # 0이면 별도 요청이 없다는 뜻이며, 코드가 승인한 값은 BudgetPlanFrame에 따로 저장된다.
    requested_search_top_k: int = 0
    # 혼합 정보: L1이 요청한 전체 도구 호출 예산.
    requested_max_tool_calls: int = 0
    # 혼합 정보: L1이 요청한 문서 원문 열람 예산.
    requested_max_read_doc_calls: int = 0
    # 혼합 정보: L1이 요청한 검색/질의 시도 예산.
    requested_max_query_attempts: int = 0
    # 혼합 정보: L1이 왜 이 예산을 요청했는지 설명한다.
    budget_request_reason: str = ""
    # 실제 목표 생성자. 현재 L1은 LLM 목표 설정 노드가 아니라 규칙 스텁이다.
    goal_generation_source: str = "RULE_STUB"
    # LLM이 목표 의미판단을 수행했는지.
    llm_goal_judgement_status: str = "not_run"
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L1_GOAL_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L1_GOAL_FRAME_SCHEMA_VERSION
    # 절대 정보: L1이 입력으로 받은 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: L1이 입력으로 읽은 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)


def validate_l1_goal_frame(frame: L1GoalFrame) -> None:
    """L1GoalFrame이 현재 확정한 최소 스키마 규칙을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "macro_goal": frame.macro_goal,
        "macro_goal_reason": frame.macro_goal_reason,
        "micro_goal": frame.micro_goal,
        "micro_goal_reason": frame.micro_goal_reason,
        "goal_source": frame.goal_source,
        "target_loop": frame.target_loop,
        "evidence_requirement_kind": frame.evidence_requirement_kind,
        "randomness_mode": frame.randomness_mode,
        "l_loop_success_condition": frame.l_loop_success_condition,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L1GoalFrame.{field_name} must not be empty")

    if frame.schema_name != L1_GOAL_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L1 goal frame schema_name: {frame.schema_name}")
    if frame.schema_version != L1_GOAL_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L1 goal frame schema_version: {frame.schema_version}")
    if frame.goal_source not in L1_GOAL_SOURCES:
        raise ValueError(f"unknown L1 goal_source: {frame.goal_source}")
    if frame.target_loop not in L1_TARGET_LOOPS:
        raise ValueError(f"unknown L1 target_loop: {frame.target_loop}")
    if frame.evidence_requirement_kind not in L1_EVIDENCE_REQUIREMENT_KINDS:
        raise ValueError(
            f"unknown L1 evidence_requirement_kind: {frame.evidence_requirement_kind}"
        )
    if frame.randomness_mode not in L1_RANDOMNESS_MODES:
        raise ValueError(f"unknown L1 randomness_mode: {frame.randomness_mode}")
    if not isinstance(frame.requires_cross_document_analysis, bool):
        raise TypeError("L1GoalFrame.requires_cross_document_analysis must be a boolean")

    for field_name, value in {
        "minimum_read_documents": frame.minimum_read_documents,
        "requested_search_top_k": frame.requested_search_top_k,
        "requested_max_tool_calls": frame.requested_max_tool_calls,
        "requested_max_read_doc_calls": frame.requested_max_read_doc_calls,
        "requested_max_query_attempts": frame.requested_max_query_attempts,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"L1GoalFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"L1GoalFrame.{field_name} must not be negative")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L1GoalFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L1GoalFrame.source_data_ids must not contain empty values")


L_LOOP_BUDGET_PLAN_FRAME_SCHEMA_NAME = "LLoopBudgetPlanFrame"
L_LOOP_BUDGET_PLAN_FRAME_SCHEMA_VERSION = "0.1"


@dataclass
class LLoopBudgetPlanFrame:
    """L1 예산 요청과 코드 승인 예산을 함께 보관하는 프레임."""

    # 절대 정보: DataStore에 저장될 budget plan data_id.
    frame_id: str
    # 절대 정보: 이 budget plan이 만들어진 턴.
    turn_id: str
    # 절대 정보: 예산이 적용되는 루프 이름.
    target_loop: str
    # 절대 정보: 요청 주체. MVP에서는 L1.
    requested_by: str
    # 절대 정보: 승인 주체. MVP에서는 CODE:BUDGET_POLICY.
    approved_by: str
    # 절대 정보: 예산 요청의 근거가 되는 L1GoalFrame data_id.
    goal_data_id: str
    # 혼합 정보: L1이 요청한 예산. LLM 판단이므로 source_data_ids와 함께만 의미가 있다.
    requested_search_top_k: int
    requested_max_tool_calls: int
    requested_max_read_doc_calls: int
    requested_max_query_attempts: int
    # 절대/정책 정보: 코드가 정책 상한 안에서 승인한 예산.
    approved_search_top_k: int
    approved_max_tool_calls: int
    approved_max_read_doc_calls: int
    approved_max_query_attempts: int
    # 절대/정책 정보: 승인에 적용된 상한.
    search_top_k_ceiling: int
    max_tool_calls_ceiling: int
    max_read_doc_calls_ceiling: int
    max_query_attempts_ceiling: int
    # 혼합 정보: L1이 예산을 요청한 이유.
    budget_request_reason: str = ""
    # 절대/정책 정보: 코드가 승인/축소한 이유.
    approval_reason: str = ""
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L_LOOP_BUDGET_PLAN_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L_LOOP_BUDGET_PLAN_FRAME_SCHEMA_VERSION
    # 절대 정보: 입력 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 입력 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)


def validate_l_loop_budget_plan_frame(frame: LLoopBudgetPlanFrame) -> None:
    """LLoopBudgetPlanFrame이 요청 예산과 승인 예산을 안전하게 구분하는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "target_loop": frame.target_loop,
        "requested_by": frame.requested_by,
        "approved_by": frame.approved_by,
        "goal_data_id": frame.goal_data_id,
        "approval_reason": frame.approval_reason,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"LLoopBudgetPlanFrame.{field_name} must not be empty")

    if frame.schema_name != L_LOOP_BUDGET_PLAN_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L loop budget plan schema_name: {frame.schema_name}")
    if frame.schema_version != L_LOOP_BUDGET_PLAN_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L loop budget plan schema_version: {frame.schema_version}")
    if frame.target_loop not in L1_TARGET_LOOPS:
        raise ValueError(f"unknown L loop budget plan target_loop: {frame.target_loop}")

    numeric_fields = {
        "requested_search_top_k": frame.requested_search_top_k,
        "requested_max_tool_calls": frame.requested_max_tool_calls,
        "requested_max_read_doc_calls": frame.requested_max_read_doc_calls,
        "requested_max_query_attempts": frame.requested_max_query_attempts,
        "approved_search_top_k": frame.approved_search_top_k,
        "approved_max_tool_calls": frame.approved_max_tool_calls,
        "approved_max_read_doc_calls": frame.approved_max_read_doc_calls,
        "approved_max_query_attempts": frame.approved_max_query_attempts,
        "search_top_k_ceiling": frame.search_top_k_ceiling,
        "max_tool_calls_ceiling": frame.max_tool_calls_ceiling,
        "max_read_doc_calls_ceiling": frame.max_read_doc_calls_ceiling,
        "max_query_attempts_ceiling": frame.max_query_attempts_ceiling,
    }
    for field_name, value in numeric_fields.items():
        if not isinstance(value, int):
            raise TypeError(f"LLoopBudgetPlanFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"LLoopBudgetPlanFrame.{field_name} must not be negative")

    for field_name, value in {
        "approved_search_top_k": frame.approved_search_top_k,
        "approved_max_tool_calls": frame.approved_max_tool_calls,
        "approved_max_read_doc_calls": frame.approved_max_read_doc_calls,
        "approved_max_query_attempts": frame.approved_max_query_attempts,
        "search_top_k_ceiling": frame.search_top_k_ceiling,
        "max_tool_calls_ceiling": frame.max_tool_calls_ceiling,
        "max_read_doc_calls_ceiling": frame.max_read_doc_calls_ceiling,
        "max_query_attempts_ceiling": frame.max_query_attempts_ceiling,
    }.items():
        if value < 1:
            raise ValueError(f"LLoopBudgetPlanFrame.{field_name} must be positive")

    if frame.approved_search_top_k > frame.search_top_k_ceiling:
        raise ValueError("approved_search_top_k must not exceed search_top_k_ceiling")
    if frame.approved_max_tool_calls > frame.max_tool_calls_ceiling:
        raise ValueError("approved_max_tool_calls must not exceed max_tool_calls_ceiling")
    if frame.approved_max_read_doc_calls > frame.max_read_doc_calls_ceiling:
        raise ValueError("approved_max_read_doc_calls must not exceed max_read_doc_calls_ceiling")
    if frame.approved_max_query_attempts > frame.max_query_attempts_ceiling:
        raise ValueError("approved_max_query_attempts must not exceed max_query_attempts_ceiling")
    if frame.goal_data_id not in frame.source_data_ids:
        raise ValueError("LLoopBudgetPlanFrame.source_data_ids must include goal_data_id")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LLoopBudgetPlanFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LLoopBudgetPlanFrame.source_data_ids must not contain empty values")


L2_QUERY_FRAME_SCHEMA_NAME = "L2QueryFrame"
L2_QUERY_FRAME_SCHEMA_VERSION = "0.1"
L2_QUERY_PLAN_FRAME_SCHEMA_NAME = "L2QueryPlanFrame"
L2_QUERY_PLAN_FRAME_SCHEMA_VERSION = "0.1"
L2_REVISION_INPUT_FRAME_SCHEMA_NAME = "L2RevisionInputFrame"
L2_REVISION_INPUT_FRAME_SCHEMA_VERSION = "0.1"
L2_QUERY_SOURCES = {
    "user_input_fallback",
    "llm_query_plan",
    "revision_llm_query_plan",
    "revision_fallback_query_plan",
}
L2_QUERY_MODES = {"embedding_search", "exact_artifact_ref"}
L2_TARGET_TOOL_NAMES = {"search_docs", "read_artifact"}
L2_QUERY_PLANNER_MODES = {"llm", "fallback", "revision_llm", "revision_fallback"}
L2_REVISION_PREVIOUS_TOOL_NAMES = {"search_docs", "read_doc", "read_artifact"}
L2_REVISION_L3_GOAL_STATUSES = {"achieved", "partial", "failed", "missing", "not_run"}
L2_REVISION_GOAL_MATCH_STATUSES = {"matched", "partial", "missing", "not_applicable", "not_run"}
L2_REVISION_SEMANTIC_GOAL_MATCH_STATUSES = {"matched", "partial", "missing", "not_run"}


@dataclass
class L2QueryFrame:
    """L2가 검색 도구에 넘길 질의를 DataStore에 저장하기 위한 프레임."""

    # 절대 정보: DataStore에 저장될 query frame data_id와 같은 값.
    frame_id: str
    # 절대 정보: 이 query frame이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 실제 검색 도구에 넘길 query 문자열.
    # 지금은 LLM이 생성한 최적 검색어가 아니라 사용자 입력을 임시로 사용한 값이다.
    query_text: str
    # 절대 정보: query_text가 어디서 왔는지 나타내는 출처 표지.
    query_source: str
    # 절대 정보: 어떤 방식의 검색을 의도하는지 나타내는 모드.
    query_mode: str
    # 절대 정보: 이 query frame이 대상으로 삼는 도구 이름.
    target_tool_name: str
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L2_QUERY_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L2_QUERY_FRAME_SCHEMA_VERSION
    # 절대 정보: L2가 입력으로 받은 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: L2가 입력으로 읽은 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)


def validate_l2_query_frame(frame: L2QueryFrame) -> None:
    """L2QueryFrame이 현재 확정한 최소 스키마 규칙을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "query_text": frame.query_text,
        "query_source": frame.query_source,
        "query_mode": frame.query_mode,
        "target_tool_name": frame.target_tool_name,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L2QueryFrame.{field_name} must not be empty")

    if frame.schema_name != L2_QUERY_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L2 query frame schema_name: {frame.schema_name}")
    if frame.schema_version != L2_QUERY_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L2 query frame schema_version: {frame.schema_version}")
    if frame.query_source not in L2_QUERY_SOURCES:
        raise ValueError(f"unknown L2 query_source: {frame.query_source}")
    if frame.query_mode not in L2_QUERY_MODES:
        raise ValueError(f"unknown L2 query_mode: {frame.query_mode}")
    if frame.target_tool_name not in L2_TARGET_TOOL_NAMES:
        raise ValueError(f"unknown L2 target_tool_name: {frame.target_tool_name}")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L2QueryFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L2QueryFrame.source_data_ids must not contain empty values")


@dataclass
class L2QueryPlanCandidate:
    """L2가 검색 전에 만든 query 후보 하나."""

    # 절대 정보: query plan 안에서 후보 하나를 구분하는 ID.
    candidate_id: str
    # 분류 경계: LLM planner가 만들면 source bundle 기반 혼합 정보,
    # fallback 규칙이 만들면 코드 정책 산출 정보다.
    query_text: str
    # 분류 경계: LLM planner가 만든 이유면 혼합 정보, fallback 설명이면 코드 정책 산출 정보다.
    purpose: str
    # 분류 경계: LLM planner가 만든 기대 신호면 혼합 정보, fallback 설명이면 코드 정책 산출 정보다.
    expected_signal: str
    # 절대 정보: 후보 우선순위. 1이 가장 높다.
    priority: int
    # 절대 정보: 이 후보가 대상으로 삼는 도구.
    target_tool_name: str = "search_docs"
    # 절대 정보: 이 후보 생성의 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)


@dataclass
class L2QueryPlanFrame:
    """L2가 내부 문서 검색용 query 후보들을 DataStore에 저장하는 계획 프레임."""

    # 절대 정보: DataStore에 저장될 query plan frame data_id와 같은 값.
    frame_id: str
    # 절대 정보: 이 query plan frame이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: query plan 생성 방식. 현재는 llm 또는 fallback.
    planner_mode: str
    # 절대 정보: 실제 L2QueryFrame으로 이어갈 후보 ID.
    selected_candidate_id: str
    # 분류 경계 묶음: 후보별 생성자에 따라 혼합 정보 또는 코드 정책 산출 정보가 섞일 수 있다.
    candidates: list[L2QueryPlanCandidate] = field(default_factory=list)
    # 절대 정보: L2 query planner가 입력으로 받은 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: L2 query planner가 입력으로 읽은 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L2_QUERY_PLAN_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L2_QUERY_PLAN_FRAME_SCHEMA_VERSION


def validate_l2_query_plan_frame(frame: L2QueryPlanFrame) -> None:
    """L2QueryPlanFrame이 현재 확정한 최소 스키마 규칙을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "planner_mode": frame.planner_mode,
        "selected_candidate_id": frame.selected_candidate_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L2QueryPlanFrame.{field_name} must not be empty")

    if frame.schema_name != L2_QUERY_PLAN_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L2 query plan schema_name: {frame.schema_name}")
    if frame.schema_version != L2_QUERY_PLAN_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L2 query plan schema_version: {frame.schema_version}")
    if frame.planner_mode not in L2_QUERY_PLANNER_MODES:
        raise ValueError(f"unknown L2 query planner_mode: {frame.planner_mode}")
    if not frame.candidates:
        raise ValueError("L2QueryPlanFrame.candidates must not be empty")

    candidate_ids = {candidate.candidate_id for candidate in frame.candidates}
    if frame.selected_candidate_id not in candidate_ids:
        raise ValueError("L2QueryPlanFrame.selected_candidate_id must reference a candidate")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L2QueryPlanFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L2QueryPlanFrame.source_data_ids must not contain empty values")

    for candidate in frame.candidates:
        _validate_l2_query_plan_candidate(candidate)


def _validate_l2_query_plan_candidate(candidate: L2QueryPlanCandidate) -> None:
    """L2 query 후보 하나가 최소 규칙을 지키는지 확인한다."""

    required_text_fields = {
        "candidate_id": candidate.candidate_id,
        "query_text": candidate.query_text,
        "purpose": candidate.purpose,
        "expected_signal": candidate.expected_signal,
        "target_tool_name": candidate.target_tool_name,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L2QueryPlanCandidate.{field_name} must not be empty")
    if not isinstance(candidate.priority, int):
        raise TypeError("L2QueryPlanCandidate.priority must be an integer")
    if candidate.priority < 1:
        raise ValueError("L2QueryPlanCandidate.priority must be positive")
    if candidate.target_tool_name not in L2_TARGET_TOOL_NAMES:
        raise ValueError(f"unknown L2 target_tool_name: {candidate.target_tool_name}")
    if not candidate.source_data_ids:
        raise ValueError("L2QueryPlanCandidate.source_data_ids must not be empty")
    for data_id in candidate.source_data_ids:
        if not data_id:
            raise ValueError("L2QueryPlanCandidate.source_data_ids must not contain empty values")


@dataclass
class L2RevisionInputFrame:
    """L3 목표 미달 이후 L2가 재검색 계획을 세울 때 받는 입력 묶음.

    이 frame은 재검색을 실행하지 않는다. 역할은 L3가 남긴 판정과
    이전 검색 흔적을 L2가 다시 보기 좋은 형태로 모으는 것이다.
    """

    # 절대 정보: DataStore에 저장될 revision input frame data_id.
    frame_id: str
    # 절대 정보: 이 revision 입력이 속한 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 이번 L루프에서 몇 번째 검색 시도인지. 첫 재시도는 보통 2가 된다.
    attempt_index: int
    # 절대 정보: 이번 L루프에서 허용되는 최대 검색 시도 횟수.
    max_attempts: int
    # 절대 정보: L1이 설정한 거시 목표. L2가 목표를 잃지 않게 공급한다.
    macro_goal: str
    # 절대 정보: L1이 설정한 미시 목표. L2가 검색 범위를 좁힐 때 본다.
    micro_goal: str
    # 분류 경계: 직전 L2 검색어를 복사한 값이다. 원 생성자가 LLM이면 source ID와 함께 봐야 한다.
    previous_query_text: str
    # 절대 정보: 직전에 실행된 도구 이름.
    previous_tool_name: str
    # 절대 정보/문서 근거: 이미 읽은 문서 이름 목록. raw data_id 대신 사람이 읽는 이름만 둔다.
    read_document_names: list[str] = field(default_factory=list)
    # 분류 경계: L3가 남긴 후보 설명을 복사한 값이다. 원 생성자의 정보 등급을 따라간다.
    # 코드가 이 문장의 의미를 해석해 재시도 여부를 결정하면 안 된다.
    unread_candidate_summaries: list[str] = field(default_factory=list)
    # 분류 경계: L3 판단 상태 복사값이다. L3 생성자/status로 정보 등급을 판별한다.
    l3_goal_status: str = "not_run"
    # 분류 경계: L3 문서 매칭 상태 복사값이다. L3 생성자/status로 정보 등급을 판별한다.
    l3_goal_match_status: str = "not_run"
    # 혼합 정보: LLM 의미판단 기준의 목표 매칭 상태 복사값.
    l3_semantic_goal_match_status: str = "not_run"
    # 분류 경계: L3가 다음 L2 시도에 참고하라고 남긴 비판/피드백 복사값.
    # controller는 이 텍스트를 의미 해석하지 않고, L2에게만 전달한다.
    l3_feedback_text: str = ""
    # 절대 정보: 남은 전체 도구 호출 횟수.
    remaining_tool_calls: int = 0
    # 절대 정보: 남은 검색 query 시도 횟수.
    remaining_query_attempts: int = 0
    # 절대 정보: 남은 문서 읽기 횟수.
    remaining_read_doc_calls: int = 0
    # 절대 정보: 이 revision 입력이 근거로 삼은 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 revision 입력이 근거로 삼은 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L2_REVISION_INPUT_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L2_REVISION_INPUT_FRAME_SCHEMA_VERSION


def validate_l2_revision_input_frame(frame: L2RevisionInputFrame) -> None:
    """L2RevisionInputFrame이 L2 재검색 입력 계약을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "macro_goal": frame.macro_goal,
        "micro_goal": frame.micro_goal,
        "previous_query_text": frame.previous_query_text,
        "previous_tool_name": frame.previous_tool_name,
        "l3_goal_status": frame.l3_goal_status,
        "l3_goal_match_status": frame.l3_goal_match_status,
        "l3_semantic_goal_match_status": frame.l3_semantic_goal_match_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L2RevisionInputFrame.{field_name} must not be empty")

    if frame.schema_name != L2_REVISION_INPUT_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L2 revision input schema_name: {frame.schema_name}")
    if frame.schema_version != L2_REVISION_INPUT_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L2 revision input schema_version: {frame.schema_version}")
    if frame.previous_tool_name not in L2_REVISION_PREVIOUS_TOOL_NAMES:
        raise ValueError(f"unknown L2 revision previous_tool_name: {frame.previous_tool_name}")
    if frame.l3_goal_status not in L2_REVISION_L3_GOAL_STATUSES:
        raise ValueError(f"unknown L2 revision l3_goal_status: {frame.l3_goal_status}")
    if frame.l3_goal_match_status not in L2_REVISION_GOAL_MATCH_STATUSES:
        raise ValueError(f"unknown L2 revision l3_goal_match_status: {frame.l3_goal_match_status}")
    if frame.l3_semantic_goal_match_status not in L2_REVISION_SEMANTIC_GOAL_MATCH_STATUSES:
        raise ValueError(
            f"unknown L2 revision l3_semantic_goal_match_status: {frame.l3_semantic_goal_match_status}"
        )
    if not isinstance(frame.attempt_index, int) or frame.attempt_index < 1:
        raise ValueError("L2RevisionInputFrame.attempt_index must be a positive integer")
    if not isinstance(frame.max_attempts, int) or frame.max_attempts < 1:
        raise ValueError("L2RevisionInputFrame.max_attempts must be a positive integer")
    if frame.attempt_index > frame.max_attempts:
        raise ValueError("L2RevisionInputFrame.attempt_index must not exceed max_attempts")

    for field_name, value in {
        "remaining_tool_calls": frame.remaining_tool_calls,
        "remaining_query_attempts": frame.remaining_query_attempts,
        "remaining_read_doc_calls": frame.remaining_read_doc_calls,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"L2RevisionInputFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"L2RevisionInputFrame.{field_name} must not be negative")

    for document_name in frame.read_document_names:
        if not document_name:
            raise ValueError("L2RevisionInputFrame.read_document_names must not contain empty values")
    for summary in frame.unread_candidate_summaries:
        if not summary:
            raise ValueError("L2RevisionInputFrame.unread_candidate_summaries must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L2RevisionInputFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L2RevisionInputFrame.source_data_ids must not contain empty values")


DOCUMENT_MEMORY_INDEX_FRAME_SCHEMA_NAME = "DocumentMemoryIndexFrame"
DOCUMENT_MEMORY_INDEX_FRAME_SCHEMA_VERSION = "0.1"
DOCUMENT_MEMORY_DOCUMENT_KINDS = {
    "philosophy",
    "maintenance_system",
    "constitution",
    "constitution_map",
    "function_map",
    "development_map",
    "map",
    "order",
    "tmp_order",
    "execution_record",
    "runtime_artifact",
    "root_index",
    "unknown",
}
DOCUMENT_MEMORY_SOURCE_ROLES = {
    "original",
    "derived_summary",
    "generated_order",
    "execution_artifact",
    "index",
    "unknown",
}


@dataclass
class DocumentMemoryIndexItem:
    """Readable document metadata used by the document memory index."""

    doc_id: str
    path: str
    content_hash: str
    snapshot_id: str
    chunk_count: int
    document_kind: str
    source_role: str
    size_bytes: int
    suffix: str


@dataclass
class DocumentMemoryIndexFrame:
    """Stable index of readable internal documents and their metadata."""

    index_id: str
    root: str
    snapshot_id: str
    total_docs: int
    total_chunks: int
    items: list[DocumentMemoryIndexItem] = field(default_factory=list)
    schema_name: str = DOCUMENT_MEMORY_INDEX_FRAME_SCHEMA_NAME
    schema_version: str = DOCUMENT_MEMORY_INDEX_FRAME_SCHEMA_VERSION


def validate_document_memory_index_frame(frame: DocumentMemoryIndexFrame) -> None:
    """DocumentMemoryIndexFrame has stable IDs, counts, and valid item metadata."""

    for field_name, value in {
        "index_id": frame.index_id,
        "root": frame.root,
        "snapshot_id": frame.snapshot_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"DocumentMemoryIndexFrame.{field_name} must not be empty")
    if frame.schema_name != DOCUMENT_MEMORY_INDEX_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown document memory index schema_name: {frame.schema_name}")
    if frame.schema_version != DOCUMENT_MEMORY_INDEX_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown document memory index schema_version: {frame.schema_version}")
    if frame.total_docs != len(frame.items):
        raise ValueError("DocumentMemoryIndexFrame.total_docs must match item count")
    if frame.total_chunks != sum(item.chunk_count for item in frame.items):
        raise ValueError("DocumentMemoryIndexFrame.total_chunks must match item chunk counts")

    seen_doc_ids: set[str] = set()
    for item in frame.items:
        _validate_document_memory_index_item(item)
        if item.doc_id in seen_doc_ids:
            raise ValueError(f"duplicate document memory index item: {item.doc_id}")
        seen_doc_ids.add(item.doc_id)


def _validate_document_memory_index_item(item: DocumentMemoryIndexItem) -> None:
    """Validate one document memory index item."""

    for field_name, value in {
        "doc_id": item.doc_id,
        "path": item.path,
        "content_hash": item.content_hash,
        "snapshot_id": item.snapshot_id,
        "document_kind": item.document_kind,
        "source_role": item.source_role,
        "suffix": item.suffix,
    }.items():
        if not value:
            raise ValueError(f"DocumentMemoryIndexItem.{field_name} must not be empty")
    if item.document_kind not in DOCUMENT_MEMORY_DOCUMENT_KINDS:
        raise ValueError(f"unknown document_kind: {item.document_kind}")
    if item.source_role not in DOCUMENT_MEMORY_SOURCE_ROLES:
        raise ValueError(f"unknown source_role: {item.source_role}")
    if item.chunk_count < 0:
        raise ValueError("DocumentMemoryIndexItem.chunk_count must be non-negative")
    if item.size_bytes < 0:
        raise ValueError("DocumentMemoryIndexItem.size_bytes must be non-negative")


TOOL_CATALOG_FRAME_SCHEMA_NAME = "ToolCatalogFrame"
TOOL_CATALOG_FRAME_SCHEMA_VERSION = "0.1"
TOOL_CHOICE_FRAME_SCHEMA_NAME = "ToolChoiceFrame"
TOOL_CHOICE_FRAME_SCHEMA_VERSION = "0.1"


@dataclass
class ToolCatalogItem:
    """LLM과 노드가 읽을 수 있게 구조화한 도구 하나의 등록 정보."""

    # 절대 정보: registry에 등록된 도구 이름.
    tool_name: str
    # 절대 정보: 도구의 짧은 설명.
    description: str
    # 절대 정보: 현재 도구가 읽기 전용인지.
    read_only: bool
    # 절대 정보: 도구가 입력으로 받는 필드 이름 목록.
    input_fields: list[str] = field(default_factory=list)
    # 절대 정보: 도구 실행 결과가 저장될 data_type.
    output_data_type: str = ""


@dataclass
class ToolCatalogFrame:
    """사용 가능한 도구 목록을 DataStore에 저장하는 카탈로그 프레임."""

    # 절대 정보: DataStore에 저장될 tool catalog data_id.
    catalog_id: str
    # 절대 정보: 이 catalog가 만들어진 턴 ID.
    turn_id: str
    # 절대 정보: 사용 가능한 도구 목록.
    tools: list[ToolCatalogItem] = field(default_factory=list)
    # 절대 정보: catalog 생성의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: catalog 생성의 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = TOOL_CATALOG_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = TOOL_CATALOG_FRAME_SCHEMA_VERSION


def validate_tool_catalog_frame(frame: ToolCatalogFrame) -> None:
    """ToolCatalogFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "catalog_id": frame.catalog_id,
        "turn_id": frame.turn_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"ToolCatalogFrame.{field_name} must not be empty")
    if frame.schema_name != TOOL_CATALOG_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown tool catalog schema_name: {frame.schema_name}")
    if frame.schema_version != TOOL_CATALOG_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown tool catalog schema_version: {frame.schema_version}")
    if not frame.tools:
        raise ValueError("ToolCatalogFrame.tools must not be empty")

    seen_tool_names: set[str] = set()
    for tool in frame.tools:
        _validate_tool_catalog_item(tool)
        if tool.tool_name in seen_tool_names:
            raise ValueError(f"duplicate tool in catalog: {tool.tool_name}")
        seen_tool_names.add(tool.tool_name)
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("ToolCatalogFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("ToolCatalogFrame.source_data_ids must not contain empty values")


def _validate_tool_catalog_item(item: ToolCatalogItem) -> None:
    """ToolCatalogItem 하나의 필수 정보를 확인한다."""

    for field_name, value in {
        "tool_name": item.tool_name,
        "description": item.description,
        "output_data_type": item.output_data_type,
    }.items():
        if not value:
            raise ValueError(f"ToolCatalogItem.{field_name} must not be empty")
    if not isinstance(item.read_only, bool):
        raise TypeError("ToolCatalogItem.read_only must be a boolean")
    for input_field in item.input_fields:
        if not input_field:
            raise ValueError("ToolCatalogItem.input_fields must not contain empty values")


@dataclass
class ToolChoiceFrame:
    """노드가 어떤 도구를 쓰기로 선택했는지 DataStore에 저장하는 프레임."""

    # 절대 정보: DataStore에 저장될 tool choice data_id.
    choice_id: str
    # 절대 정보: 이 선택이 만들어진 턴 ID.
    turn_id: str
    # 절대 정보: 도구를 선택한 노드나 루프 ID.
    chooser_node_id: str
    # 절대 정보: 선택한 도구 이름.
    tool_name: str
    # 혼합 정보: 이 도구를 선택한 이유.
    reason: str
    # 혼합 정보: 이 도구로 기대하는 사용 효과.
    expected_use: str
    # 절대 정보: 이 선택이 참조한 ToolCatalogFrame data_id.
    catalog_id: str
    # 절대 정보: 코드가 사용한 tool choice 정책 ID. 자연어 이유가 아니다.
    tool_choice_policy_id: str = "unknown_policy"
    # 절대 정보: 기대 효과를 자연어 대신 표시하는 운영 라벨.
    expected_effect_label: str = "unknown_effect"
    # 절대 정보: 현재 tool choice 생성자.
    choice_generation_source: str = "CODE:OPERATION_POLICY"
    # 절대 정보: LLM이 도구 선택 의미판단을 했는지.
    llm_tool_choice_status: str = "not_run"
    # 절대 정보: 선택 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 선택 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = TOOL_CHOICE_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = TOOL_CHOICE_FRAME_SCHEMA_VERSION


def validate_tool_choice_frame(frame: ToolChoiceFrame) -> None:
    """ToolChoiceFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "choice_id": frame.choice_id,
        "turn_id": frame.turn_id,
        "chooser_node_id": frame.chooser_node_id,
        "tool_name": frame.tool_name,
        "reason": frame.reason,
        "expected_use": frame.expected_use,
        "catalog_id": frame.catalog_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"ToolChoiceFrame.{field_name} must not be empty")
    if frame.schema_name != TOOL_CHOICE_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown tool choice schema_name: {frame.schema_name}")
    if frame.schema_version != TOOL_CHOICE_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown tool choice schema_version: {frame.schema_version}")
    if frame.catalog_id not in frame.source_data_ids:
        raise ValueError("ToolChoiceFrame.source_data_ids must include catalog_id")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("ToolChoiceFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("ToolChoiceFrame.source_data_ids must not contain empty values")


TOOL_RESULT_DISTILLATION_FRAME_SCHEMA_NAME = "ToolResultDistillationFrame"
TOOL_RESULT_DISTILLATION_FRAME_SCHEMA_VERSION = "0.1"
TOOL_RESULT_DISTILLATION_TOOL_NAMES = {"search_docs", "read_doc", "read_artifact"}
TOOL_RESULT_DISTILLED_ITEM_KINDS = {"search_result", "read_doc_excerpt"}


@dataclass
class ToolResultDistilledItem:
    """도구 결과에서 L루프와 L3가 우선 읽을 작은 정보 조각."""

    # 절대 정보: distillation frame 안에서 이 조각을 구분하는 ID.
    item_id: str
    # 절대 정보: search result인지, read_doc 발췌인지 나타내는 종류.
    item_kind: str
    # 절대 정보: 원본 tool_result payload 안에서 이 조각이 나온 위치.
    source_field_path: str
    # 절대 정보: 관련 Markdown 문서 ID.
    doc_id: str
    # 절대 정보: 관련 chunk ID. read_doc 발췌에는 없을 수 있다.
    chunk_id: str | None = None
    # 절대 정보: search_docs가 붙인 result ID. read_doc 발췌에는 없을 수 있다.
    result_id: str | None = None
    # 절대 정보: search_docs가 계산한 유사도 점수. read_doc 발췌에는 없을 수 있다.
    score: float | None = None
    # 절대 정보: score를 만든 임베딩 모델 ID. read_doc 발췌에는 없을 수 있다.
    embedding_model_id: str | None = None
    # 절대 정보: read_doc 원문 전체 글자 수. search result에는 없을 수 있다.
    char_count: int | None = None
    # 절대 정보/복사 발췌: 원본 tool_result에서 잘라낸 짧은 미리보기.
    # 원문 주장의 사실성 보증은 아니며, 새 의미 판단도 아니다.
    text_preview: str = ""
    document_kind: str | None = None
    source_role: str | None = None
    document_memory_index_id: str | None = None
    snapshot_id: str | None = None


@dataclass
class ToolResultDistillationFrame:
    """큰 도구 결과를 원본 추적성을 유지한 작은 읽기 프레임으로 압축한 결과."""

    # 절대 정보: DataStore에 저장될 distillation frame data_id.
    distillation_id: str
    # 절대 정보: 이 distillation이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 원본 도구 이름.
    tool_name: str
    # 절대 정보: 원본 tool_result DataStore record ID.
    original_tool_result_data_id: str
    # 절대 정보: 원본 tool_call trace ID.
    original_tool_trace_id: str | None
    # 절대 정보: 원본 tool_result payload의 JSON byte 크기.
    original_payload_bytes: int
    # 절대 정보: LLM 입력 후보로 쓰는 distillation content의 JSON byte 크기.
    distilled_content_bytes: int
    # 절대 정보/복사 발췌 묶음: 도구 결과에서 선별한 작은 정보 조각들.
    items: list[ToolResultDistilledItem] = field(default_factory=list)
    # 절대 정보: distillation 과정에서 적용한 제한/보류 설명.
    limits: list[str] = field(default_factory=list)
    # 절대 정보: distillation 생성의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: distillation 생성의 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = TOOL_RESULT_DISTILLATION_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = TOOL_RESULT_DISTILLATION_FRAME_SCHEMA_VERSION


def validate_tool_result_distillation_frame(frame: ToolResultDistillationFrame) -> None:
    """ToolResultDistillationFrame의 원본 추적성과 최소 필수 필드를 확인한다."""

    for field_name, value in {
        "distillation_id": frame.distillation_id,
        "turn_id": frame.turn_id,
        "tool_name": frame.tool_name,
        "original_tool_result_data_id": frame.original_tool_result_data_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"ToolResultDistillationFrame.{field_name} must not be empty")

    if frame.schema_name != TOOL_RESULT_DISTILLATION_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown tool result distillation schema_name: {frame.schema_name}")
    if frame.schema_version != TOOL_RESULT_DISTILLATION_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown tool result distillation schema_version: {frame.schema_version}")
    if frame.tool_name not in TOOL_RESULT_DISTILLATION_TOOL_NAMES:
        raise ValueError(f"unknown distillation tool_name: {frame.tool_name}")
    if not isinstance(frame.original_payload_bytes, int) or frame.original_payload_bytes < 0:
        raise ValueError("ToolResultDistillationFrame.original_payload_bytes must be non-negative")
    if not isinstance(frame.distilled_content_bytes, int) or frame.distilled_content_bytes < 0:
        raise ValueError("ToolResultDistillationFrame.distilled_content_bytes must be non-negative")
    if frame.original_tool_result_data_id not in frame.source_data_ids:
        raise ValueError("ToolResultDistillationFrame.source_data_ids must include original tool result")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("ToolResultDistillationFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("ToolResultDistillationFrame.source_data_ids must not contain empty values")
    for item in frame.items:
        _validate_tool_result_distilled_item(item)
    for limit in frame.limits:
        if not limit:
            raise ValueError("ToolResultDistillationFrame.limits must not contain empty values")


def _validate_tool_result_distilled_item(item: ToolResultDistilledItem) -> None:
    """distilled item 하나의 필수 필드를 확인한다."""

    for field_name, value in {
        "item_id": item.item_id,
        "item_kind": item.item_kind,
        "source_field_path": item.source_field_path,
        "doc_id": item.doc_id,
        "text_preview": item.text_preview,
    }.items():
        if not value:
            raise ValueError(f"ToolResultDistilledItem.{field_name} must not be empty")

    if item.item_kind not in TOOL_RESULT_DISTILLED_ITEM_KINDS:
        raise ValueError(f"unknown distilled item_kind: {item.item_kind}")
    if item.item_kind == "search_result":
        for field_name, value in {
            "chunk_id": item.chunk_id,
            "result_id": item.result_id,
            "embedding_model_id": item.embedding_model_id,
        }.items():
            if not value:
                raise ValueError(f"ToolResultDistilledItem.{field_name} must not be empty for search_result")
        if item.score is None or not isinstance(item.score, (int, float)):
            raise TypeError("ToolResultDistilledItem.score must be numeric for search_result")
    if item.item_kind == "read_doc_excerpt":
        if item.char_count is None or not isinstance(item.char_count, int):
            raise TypeError("ToolResultDistilledItem.char_count must be an integer for read_doc_excerpt")
        if item.char_count < 0:
            raise ValueError("ToolResultDistilledItem.char_count must be non-negative")


TOOL_USE_BUDGET_FRAME_SCHEMA_NAME = "ToolUseBudgetFrame"
TOOL_USE_BUDGET_FRAME_SCHEMA_VERSION = "0.1"
TOOL_USE_BUDGET_STOP_REASONS = {
    "within_budget",
    "completed",
    "max_tool_calls_reached",
    "max_query_attempts_reached",
    "max_query_candidates_reached",
    "max_read_doc_calls_reached",
    "max_input_chars_reached",
    "duplicate_query",
    "duplicate_doc",
    "low_yield_stop",
}


@dataclass
class ToolCacheStatusRecord:
    """도구 사용 효율 판단에 쓰이는 vector index cache 상태 기록."""

    # 절대 정보: cache_status가 확인된 원본 tool_result data_id.
    tool_result_data_id: str
    # 절대 정보: search_docs payload에서 확인한 cache 상태. 예: hit, miss.
    cache_status: str
    # 절대 정보: 해당 search_docs 호출에 사용된 query.
    query_text: str


@dataclass
class ToolUseBudgetFrame:
    """L루프 도구 사용 예산과 현재 사용량을 DataStore에 저장하는 프레임."""

    # 절대 정보: DataStore에 저장될 budget frame data_id.
    budget_id: str
    # 절대 정보: 이 budget frame이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: budget을 적용하는 루프 ID. 현재는 L.
    loop_id: str
    # 절대 정보: 이 budget frame이 몇 번째로 기록됐는지.
    sequence_index: int
    # 절대 정보: 허용된 최대 도구 호출 횟수.
    max_tool_calls: int
    # 절대 정보: search_docs 한 번이 반환할 최대 검색 결과 후보 수.
    search_top_k: int
    # 절대 정보: 허용된 최대 search query 실행/수정 시도 횟수.
    max_query_attempts: int
    # 절대 정보: 예전 이름. 현재 의미는 max_query_attempts와 같다.
    max_query_candidates: int
    # 절대 정보: 허용된 최대 read_doc 호출 횟수.
    max_read_doc_calls: int
    # 절대 정보: LLM 입력 후보로 넘길 수 있는 최대 문자/byte 예산.
    max_input_chars: int
    # 절대 정보: 현재까지 실행된 도구 호출 횟수.
    tool_call_count: int
    # 절대 정보: 현재까지 실행된 search query 수.
    query_count: int
    # 절대 정보: 현재까지 실행된 read_doc 호출 횟수.
    read_doc_count: int
    # 절대 정보: 현재까지 distillation 기준으로 누적한 입력 크기.
    input_chars_used: int
    # 절대 정보: 이미 실행한 query 목록.
    executed_queries: list[str] = field(default_factory=list)
    # 절대 정보: 이미 읽은 doc_id 목록.
    read_doc_ids: list[str] = field(default_factory=list)
    # 절대 정보: search_docs 호출에서 확인한 cache 상태 목록.
    cache_statuses: list[ToolCacheStatusRecord] = field(default_factory=list)
    # 절대 정보: 중복 query 시도 횟수.
    duplicate_query_count: int = 0
    # 절대 정보: 중복 doc 읽기 시도 횟수.
    duplicate_doc_count: int = 0
    # 절대 정보/코드 정책 결과: 현재 예산 상태나 종료 이유.
    stop_reason: str = "within_budget"
    # 절대 정보/코드 정책 설명: stop_reason을 붙인 설명.
    reason: str = ""
    # 절대 정보: reason 자연어 대신 코드가 쓸 수 있는 조건 플래그 목록.
    condition_flags: list[str] = field(default_factory=list)
    # 절대 정보: budget frame 생성의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: budget frame 생성의 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = TOOL_USE_BUDGET_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = TOOL_USE_BUDGET_FRAME_SCHEMA_VERSION


def validate_tool_use_budget_frame(frame: ToolUseBudgetFrame) -> None:
    """ToolUseBudgetFrame이 예산과 사용량을 일관되게 기록하는지 확인한다."""

    for field_name, value in {
        "budget_id": frame.budget_id,
        "turn_id": frame.turn_id,
        "loop_id": frame.loop_id,
        "stop_reason": frame.stop_reason,
        "reason": frame.reason,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"ToolUseBudgetFrame.{field_name} must not be empty")

    if frame.schema_name != TOOL_USE_BUDGET_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown tool use budget schema_name: {frame.schema_name}")
    if frame.schema_version != TOOL_USE_BUDGET_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown tool use budget schema_version: {frame.schema_version}")
    if frame.stop_reason not in TOOL_USE_BUDGET_STOP_REASONS:
        raise ValueError(f"unknown tool use budget stop_reason: {frame.stop_reason}")

    numeric_fields = {
        "sequence_index": frame.sequence_index,
        "max_tool_calls": frame.max_tool_calls,
        "search_top_k": frame.search_top_k,
        "max_query_attempts": frame.max_query_attempts,
        "max_query_candidates": frame.max_query_candidates,
        "max_read_doc_calls": frame.max_read_doc_calls,
        "max_input_chars": frame.max_input_chars,
        "tool_call_count": frame.tool_call_count,
        "query_count": frame.query_count,
        "read_doc_count": frame.read_doc_count,
        "input_chars_used": frame.input_chars_used,
        "duplicate_query_count": frame.duplicate_query_count,
        "duplicate_doc_count": frame.duplicate_doc_count,
    }
    for field_name, value in numeric_fields.items():
        if not isinstance(value, int):
            raise TypeError(f"ToolUseBudgetFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"ToolUseBudgetFrame.{field_name} must not be negative")

    for field_name in {
        "sequence_index",
        "max_tool_calls",
        "search_top_k",
        "max_query_attempts",
        "max_query_candidates",
        "max_read_doc_calls",
        "max_input_chars",
    }:
        if numeric_fields[field_name] < 1:
            raise ValueError(f"ToolUseBudgetFrame.{field_name} must be positive")
    if frame.tool_call_count > frame.max_tool_calls:
        raise ValueError("ToolUseBudgetFrame.tool_call_count must not exceed max_tool_calls")
    if frame.query_count > frame.max_query_attempts:
        raise ValueError("ToolUseBudgetFrame.query_count must not exceed max_query_attempts")
    if frame.max_query_candidates != frame.max_query_attempts:
        raise ValueError("ToolUseBudgetFrame.max_query_candidates must mirror max_query_attempts")
    if frame.read_doc_count > frame.max_read_doc_calls:
        raise ValueError("ToolUseBudgetFrame.read_doc_count must not exceed max_read_doc_calls")

    for query in frame.executed_queries:
        if not query:
            raise ValueError("ToolUseBudgetFrame.executed_queries must not contain empty values")
    for doc_id in frame.read_doc_ids:
        if not doc_id:
            raise ValueError("ToolUseBudgetFrame.read_doc_ids must not contain empty values")
    for cache_status in frame.cache_statuses:
        _validate_tool_cache_status_record(cache_status)
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("ToolUseBudgetFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("ToolUseBudgetFrame.source_data_ids must not contain empty values")


def _validate_tool_cache_status_record(record: ToolCacheStatusRecord) -> None:
    """ToolCacheStatusRecord 하나의 필수 정보를 확인한다."""

    for field_name, value in {
        "tool_result_data_id": record.tool_result_data_id,
        "cache_status": record.cache_status,
        "query_text": record.query_text,
    }.items():
        if not value:
            raise ValueError(f"ToolCacheStatusRecord.{field_name} must not be empty")
    if record.cache_status not in {"hit", "miss", "unknown"}:
        raise ValueError(f"unknown cache_status: {record.cache_status}")


L_LOOP_CONTROL_FRAME_SCHEMA_NAME = "LLoopControlFrame"
L_LOOP_CONTROL_FRAME_SCHEMA_VERSION = "0.1"
L_LOOP_CONTINUATION_FRAME_SCHEMA_NAME = "LLoopContinuationFrame"
L_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION = "0.1"
L_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME = "LLoopReturnSummaryFrame"
L_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION = "0.1"
L_LOOP_CONTROL_DECISIONS = {
    "continue_search",
    "continue_read_artifact",
    "read_document",
    "stop_success",
    "stop_failed",
}
L_LOOP_CONTINUATION_STATUSES = {
    "continue",
    "stop_achieved",
    "stop_budget_exhausted",
    "stop_no_actionable_gap",
    "stop_failed_final",
}
L_LOOP_CONTINUATION_NEXT_TARGETS = {"L2", "loop_return_summary"}
L_LOOP_RETURN_TASK_STATUSES = {"achieved", "partial", "failed", "unknown"}
L_LOOP_RETURN_FAILURE_LEVELS = {
    "none",
    "l2_retryable",
    "l1_replan_needed",
    "budget_exhausted",
    "give_up_recommended",
    "unknown",
}
L_LOOP_RETURN_ROUTE_HINTS = {"L", "2", "W_later", "none"}


@dataclass
class LLoopControlFrame:
    """L루프 controller가 다음 행동을 무엇으로 정했는지 저장하는 프레임."""

    # 절대 정보: DataStore에 저장될 control frame data_id.
    control_id: str
    # 절대 정보: 이 control frame이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: controller가 속한 루프 ID. 현재는 L.
    loop_id: str
    # 절대 정보: L루프 안에서 몇 번째 controller 판단인지.
    iteration_index: int
    # 절대 정보/코드 정책 결과: controller가 선택한 다음 행동 이름.
    decision: str
    # 절대 정보/코드 정책 설명: decision을 고른 이유. 반드시 source trace/data와 함께 저장한다.
    reason: str
    # 절대 정보: 이번 L루프에 허용된 최대 controller 판단 횟수.
    max_iterations: int
    # 절대 정보: 이번 L루프에 허용된 최대 도구 호출 횟수.
    max_tool_calls: int
    # 절대 정보: 이 판단 시점까지 이미 실행한 도구 호출 횟수.
    tool_call_count: int
    # 절대 정보: 이 판단의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 판단의 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: decision이 도구 실행을 요구할 때 선택된 도구 이름.
    selected_tool_name: str | None = None
    # 절대 정보: search_docs를 실행할 때 사용할 query 문자열.
    query_text: str | None = None
    # 절대 정보: read_doc을 실행할 때 사용할 문서 ID.
    doc_id: str | None = None
    # 절대 정보: stop_failed가 실패 신호를 동반할 때 연결되는 failure data_id.
    failure_signal_id: str | None = None
    # 절대 정보: decision을 만든 코드 조건 플래그 목록.
    condition_flags: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L_LOOP_CONTROL_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L_LOOP_CONTROL_FRAME_SCHEMA_VERSION


def validate_l_loop_control_frame(frame: LLoopControlFrame) -> None:
    """LLoopControlFrame이 budget과 근거 ID를 가진 안전한 controller 판단인지 확인한다."""

    for field_name, value in {
        "control_id": frame.control_id,
        "turn_id": frame.turn_id,
        "loop_id": frame.loop_id,
        "decision": frame.decision,
        "reason": frame.reason,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"LLoopControlFrame.{field_name} must not be empty")

    if frame.schema_name != L_LOOP_CONTROL_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L loop control schema_name: {frame.schema_name}")
    if frame.schema_version != L_LOOP_CONTROL_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L loop control schema_version: {frame.schema_version}")
    if frame.decision not in L_LOOP_CONTROL_DECISIONS:
        raise ValueError(f"unknown L loop control decision: {frame.decision}")
    if not isinstance(frame.iteration_index, int) or frame.iteration_index < 1:
        raise ValueError("LLoopControlFrame.iteration_index must be a positive integer")
    if not isinstance(frame.max_iterations, int) or frame.max_iterations < 1:
        raise ValueError("LLoopControlFrame.max_iterations must be a positive integer")
    if not isinstance(frame.max_tool_calls, int) or frame.max_tool_calls < 1:
        raise ValueError("LLoopControlFrame.max_tool_calls must be a positive integer")
    if not isinstance(frame.tool_call_count, int) or frame.tool_call_count < 0:
        raise ValueError("LLoopControlFrame.tool_call_count must be a non-negative integer")
    if frame.iteration_index > frame.max_iterations:
        raise ValueError("LLoopControlFrame.iteration_index must not exceed max_iterations")
    if frame.tool_call_count > frame.max_tool_calls:
        raise ValueError("LLoopControlFrame.tool_call_count must not exceed max_tool_calls")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LLoopControlFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LLoopControlFrame.source_data_ids must not contain empty values")

    if frame.selected_tool_name is not None and not frame.selected_tool_name:
        raise ValueError("LLoopControlFrame.selected_tool_name must not be empty")
    if frame.query_text is not None and not frame.query_text.strip():
        raise ValueError("LLoopControlFrame.query_text must not be empty")
    if frame.doc_id is not None and not frame.doc_id.strip():
        raise ValueError("LLoopControlFrame.doc_id must not be empty")
    if frame.failure_signal_id is not None and not frame.failure_signal_id:
        raise ValueError("LLoopControlFrame.failure_signal_id must not be empty")
    if frame.decision == "continue_search" and frame.selected_tool_name != "search_docs":
        raise ValueError("continue_search must select search_docs")
    if frame.decision == "continue_search" and frame.query_text is None:
        raise ValueError("continue_search must include query_text")
    if frame.decision == "continue_read_artifact" and frame.selected_tool_name != "read_artifact":
        raise ValueError("continue_read_artifact must select read_artifact")
    if frame.decision == "continue_read_artifact" and frame.query_text is None:
        raise ValueError("continue_read_artifact must include query_text")
    if frame.decision == "read_document" and frame.selected_tool_name != "read_doc":
        raise ValueError("read_document must select read_doc")
    if frame.decision == "read_document" and frame.doc_id is None:
        raise ValueError("read_document must include doc_id")


@dataclass
class LLoopContinuationFrame:
    """L3 이후 L루프 controller가 재검색을 계속할지 기록하는 프레임.

    이 frame은 LLM의 자유 판단문이 아니라 controller의 조건 판정을 남긴다.
    따라서 continuation_reason_code는 반드시 CODE_STATUS 라벨이어야 한다.
    """

    # 절대 정보: DataStore에 저장될 continuation frame data_id.
    frame_id: str
    # 절대 정보: 이 continuation 판단이 속한 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 이번 L루프에서 몇 번째 검색 시도 직후인지.
    attempt_index: int
    # 절대 정보: 이번 L루프에 허용된 최대 검색 시도 횟수.
    max_attempts: int
    # 절대 정보/조건 라벨: 계속할지 멈출지 나타내는 controller 상태.
    continuation_status: str
    # 절대 정보: controller가 사용한 조건 라벨.
    # LLM reason을 여기에 넣으면 안 된다.
    continuation_reason_code: str
    # 절대 정보: 이 판단이 기준으로 삼은 L3AchievementFrame data_id.
    source_l3_achievement_id: str
    # 절대 정보: 이 판단이 기준으로 삼은 직전 L2QueryFrame data_id.
    source_l2_query_frame_id: str
    # 절대 정보/혼합 정보 경계: 직전 L2 검색어.
    previous_query_text: str
    # 절대 정보: 이미 읽은 문서 ID 목록.
    read_doc_ids: list[str] = field(default_factory=list)
    # 절대 정보: 아직 읽지 않은 후보 문서 ID 목록.
    unread_candidate_doc_ids: list[str] = field(default_factory=list)
    # 절대 정보: 예산 상태 라벨. 예: within_budget, max_tool_calls_reached.
    tool_budget_status: str = "within_budget"
    # 절대 정보: 다음에 갈 대상. continue면 L2, stop이면 loop_return_summary.
    next_target_node: str = "loop_return_summary"
    # 절대 정보: 이 continuation 판단의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 continuation 판단의 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L_LOOP_CONTINUATION_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION


def validate_l_loop_continuation_frame(frame: LLoopContinuationFrame) -> None:
    """LLoopContinuationFrame이 재검색 continuation의 안전장치를 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "continuation_status": frame.continuation_status,
        "continuation_reason_code": frame.continuation_reason_code,
        "source_l3_achievement_id": frame.source_l3_achievement_id,
        "source_l2_query_frame_id": frame.source_l2_query_frame_id,
        "previous_query_text": frame.previous_query_text,
        "tool_budget_status": frame.tool_budget_status,
        "next_target_node": frame.next_target_node,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"LLoopContinuationFrame.{field_name} must not be empty")

    if frame.schema_name != L_LOOP_CONTINUATION_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L loop continuation schema_name: {frame.schema_name}")
    if frame.schema_version != L_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L loop continuation schema_version: {frame.schema_version}")
    if frame.continuation_status not in L_LOOP_CONTINUATION_STATUSES:
        raise ValueError(f"unknown L loop continuation_status: {frame.continuation_status}")
    if not frame.continuation_reason_code.startswith("CODE_STATUS:"):
        raise ValueError("LLoopContinuationFrame.continuation_reason_code must start with CODE_STATUS:")
    if frame.next_target_node not in L_LOOP_CONTINUATION_NEXT_TARGETS:
        raise ValueError(f"unknown L loop continuation next_target_node: {frame.next_target_node}")
    if frame.tool_budget_status not in TOOL_USE_BUDGET_STOP_REASONS:
        raise ValueError(f"unknown L loop continuation tool_budget_status: {frame.tool_budget_status}")

    if not isinstance(frame.attempt_index, int) or frame.attempt_index < 1:
        raise ValueError("LLoopContinuationFrame.attempt_index must be a positive integer")
    if not isinstance(frame.max_attempts, int) or frame.max_attempts < 1:
        raise ValueError("LLoopContinuationFrame.max_attempts must be a positive integer")
    if frame.attempt_index > frame.max_attempts:
        raise ValueError("LLoopContinuationFrame.attempt_index must not exceed max_attempts")

    if frame.continuation_status == "continue" and frame.next_target_node != "L2":
        raise ValueError("continue continuation must target L2")
    if frame.continuation_status != "continue" and frame.next_target_node == "L2":
        raise ValueError("stop continuation must not target L2")
    if frame.continuation_status == "continue" and frame.attempt_index >= frame.max_attempts:
        raise ValueError("continue continuation requires remaining attempts")

    if frame.source_l3_achievement_id not in frame.source_data_ids:
        raise ValueError("LLoopContinuationFrame.source_data_ids must include source_l3_achievement_id")
    if frame.source_l2_query_frame_id not in frame.source_data_ids:
        raise ValueError("LLoopContinuationFrame.source_data_ids must include source_l2_query_frame_id")

    for doc_id in frame.read_doc_ids:
        if not doc_id:
            raise ValueError("LLoopContinuationFrame.read_doc_ids must not contain empty values")
    for doc_id in frame.unread_candidate_doc_ids:
        if not doc_id:
            raise ValueError("LLoopContinuationFrame.unread_candidate_doc_ids must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LLoopContinuationFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LLoopContinuationFrame.source_data_ids must not contain empty values")


@dataclass
class LLoopReturnSummaryFrame:
    """0이 L루프 종료 후 node_1에게 넘길 구조화 요약.

    이 프레임은 1이 상위 라우팅을 다시 판단할 수 있게 만드는 재료다.
    0은 여기서 새 의미 판단을 하지 않고, L1/L3/budget/continuation의 구조화
    필드와 절대 count를 복사하거나 조합한다.
    """

    # 절대 정보: DataStore에 저장될 return summary data_id.
    frame_id: str
    # 절대 정보: 이 요약이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 요약 대상 루프. 현재는 L.
    loop_id: str
    # 복사 정보: L3가 판단한 최종 task 상태. 원 L3 frame의 생성자/status로 정보 등급을 판별한다.
    l_loop_task_status: str
    # 절대/조건 라벨: 상위 라우팅 관점에서 어느 종류의 실패/부족인지.
    failure_level: str
    # 복사 정보: L1이 선언한 근거 요구 종류. 원 L1 frame의 생성자/status로 정보 등급을 판별한다.
    evidence_requirement_kind: str
    # 복사 정보: L1이 요구한 최소 읽은 문서 수. 코드가 승인한 예산은 별도 budget frame에 있다.
    required_min_read_documents: int
    # 절대 정보: 실제 read_doc으로 읽은 문서 수.
    actual_read_doc_count: int
    # 절대 정보: L3 보존 검색 후보 문서 수.
    search_candidate_count: int
    # 절대 정보: continuation controller의 최종 상태.
    final_continuation_status: str
    # 절대 정보: 마지막 tool budget stop_reason.
    budget_stop_reason: str
    # 절대 정보: 마지막 tool budget 기준 남은 tool call 수.
    remaining_tool_calls: int
    # 절대 정보: 마지막 tool budget 기준 남은 read_doc 수.
    remaining_read_doc_calls: int
    # 절대 정보: 마지막 tool budget 기준 남은 query attempt 수.
    remaining_query_attempts: int
    # 복사 정보: L3의 특정 문서 목표 매칭 상태. 원 L3 frame의 생성자/status로 정보 등급을 판별한다.
    l3_goal_match_status: str
    # 복사 정보: L3의 의미 목표 매칭 상태. 원 L3 frame의 생성자/status로 정보 등급을 판별한다.
    l3_semantic_goal_match_status: str
    # 참고 신호: 1이 다음 라우팅을 판단할 때 참고할 수 있는 후보. 확정 라우팅이 아니다.
    recommended_next_route_for_node1: str
    # 절대/정책 설명: route hint를 만든 코드 조건 라벨.
    route_hint_reason: str
    # 절대 정보: 실제 읽은 문서 ID 목록.
    read_doc_ids: list[str] = field(default_factory=list)
    # 절대 정보: 검색 후보 문서 ID 목록.
    search_result_doc_ids: list[str] = field(default_factory=list)
    # 절대 정보: 입력 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 입력 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION


def validate_l_loop_return_summary_frame(frame: LLoopReturnSummaryFrame) -> None:
    """LLoopReturnSummaryFrame이 1에게 줄 안전한 구조화 요약인지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "loop_id": frame.loop_id,
        "l_loop_task_status": frame.l_loop_task_status,
        "failure_level": frame.failure_level,
        "evidence_requirement_kind": frame.evidence_requirement_kind,
        "final_continuation_status": frame.final_continuation_status,
        "budget_stop_reason": frame.budget_stop_reason,
        "l3_goal_match_status": frame.l3_goal_match_status,
        "l3_semantic_goal_match_status": frame.l3_semantic_goal_match_status,
        "recommended_next_route_for_node1": frame.recommended_next_route_for_node1,
        "route_hint_reason": frame.route_hint_reason,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"LLoopReturnSummaryFrame.{field_name} must not be empty")

    if frame.schema_name != L_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L loop return summary schema_name: {frame.schema_name}")
    if frame.schema_version != L_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L loop return summary schema_version: {frame.schema_version}")
    if frame.loop_id != "L":
        raise ValueError(f"unknown L loop return summary loop_id: {frame.loop_id}")
    if frame.l_loop_task_status not in L_LOOP_RETURN_TASK_STATUSES:
        raise ValueError(f"unknown L loop task status: {frame.l_loop_task_status}")
    if frame.failure_level not in L_LOOP_RETURN_FAILURE_LEVELS:
        raise ValueError(f"unknown L loop failure_level: {frame.failure_level}")
    if frame.evidence_requirement_kind not in L1_EVIDENCE_REQUIREMENT_KINDS:
        raise ValueError(
            f"unknown L loop return evidence_requirement_kind: {frame.evidence_requirement_kind}"
        )
    if frame.l3_goal_match_status not in L3_GOAL_MATCH_STATUSES:
        raise ValueError(f"unknown L loop return l3_goal_match_status: {frame.l3_goal_match_status}")
    if frame.l3_semantic_goal_match_status not in L3_SEMANTIC_GOAL_MATCH_STATUSES:
        raise ValueError(
            f"unknown L loop return l3_semantic_goal_match_status: {frame.l3_semantic_goal_match_status}"
        )
    if frame.recommended_next_route_for_node1 not in L_LOOP_RETURN_ROUTE_HINTS:
        raise ValueError(
            f"unknown L loop return route hint: {frame.recommended_next_route_for_node1}"
        )

    for field_name, value in {
        "required_min_read_documents": frame.required_min_read_documents,
        "actual_read_doc_count": frame.actual_read_doc_count,
        "search_candidate_count": frame.search_candidate_count,
        "remaining_tool_calls": frame.remaining_tool_calls,
        "remaining_read_doc_calls": frame.remaining_read_doc_calls,
        "remaining_query_attempts": frame.remaining_query_attempts,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"LLoopReturnSummaryFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"LLoopReturnSummaryFrame.{field_name} must not be negative")

    for doc_id in frame.read_doc_ids:
        if not doc_id:
            raise ValueError("LLoopReturnSummaryFrame.read_doc_ids must not contain empty values")
    for doc_id in frame.search_result_doc_ids:
        if not doc_id:
            raise ValueError("LLoopReturnSummaryFrame.search_result_doc_ids must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LLoopReturnSummaryFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LLoopReturnSummaryFrame.source_data_ids must not contain empty values")


L_LOOP_RUN_FRAME_SCHEMA_NAME = "LLoopRunFrame"
L_LOOP_RUN_FRAME_SCHEMA_VERSION = "0.1"
L_LOOP_RUN_NAMESPACE_POLICIES = {
    "fixed_primary_ids_v0",
    "attempt_scoped_primary_ids_v1",
    "run_scoped_l_internal_ids_v1",
    "run_scoped_l_internal_and_return_ids_v1",
    "run_scoped_l_internal_return_and_downstream_ids_v1",
}


@dataclass
class LLoopRunFrame:
    """상위 라우팅 관점에서 L루프 실행 1회를 식별하는 절대정보 프레임.

    1회차 L 실행은 호환성을 위해 `L1:goal_frame` 같은 고정 ID를 유지한다.
    2회차부터는 `L:run:0002:*` 이름표로 L 내부/복귀 기록을 구분한다.
    이 프레임은 그래도 상위 재라우팅이 아직 닫혀 있는 이유를 숨기지 않고
    다음에 남은 ID 정리 대상을 확인하게 해준다.
    """

    # 절대 정보: DataStore에 저장될 L루프 실행 프레임 ID.
    frame_id: str
    # 절대 정보: 이 L루프 실행이 속한 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 실행 대상 루프. 현재는 L.
    loop_id: str
    # 절대 정보: 같은 턴 안에서 몇 번째 L루프 실행인지. 현재 MVP는 1만 사용한다.
    run_index: int
    # 절대/정책 정보: 현재 L루프 산출물 ID 정책.
    namespace_policy: str
    # 절대 정보: 첫 L1/L2/L3 산출물 ID가 run_index별로 분리되는지.
    primary_ids_are_attempt_scoped: bool
    # 절대 정보: 현재 구조에서 같은 턴 상위 L 재실행을 허용하는지.
    same_turn_rerun_allowed: bool
    # 절대/정책 설명: 재실행이 막히는 이유 또는 허용되는 이유.
    rerun_block_reason: str
    # 절대/운영 메모: 다음 개발 단계에서 무엇을 바꿔야 하는지.
    planned_next_step: str
    # 절대 정보: 입력 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 입력 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L_LOOP_RUN_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L_LOOP_RUN_FRAME_SCHEMA_VERSION


def validate_l_loop_run_frame(frame: LLoopRunFrame) -> None:
    """LLoopRunFrame이 L루프 실행 단위의 절대정보 계약을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "loop_id": frame.loop_id,
        "namespace_policy": frame.namespace_policy,
        "rerun_block_reason": frame.rerun_block_reason,
        "planned_next_step": frame.planned_next_step,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"LLoopRunFrame.{field_name} must not be empty")

    if frame.schema_name != L_LOOP_RUN_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L loop run schema_name: {frame.schema_name}")
    if frame.schema_version != L_LOOP_RUN_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L loop run schema_version: {frame.schema_version}")
    if frame.loop_id != "L":
        raise ValueError(f"unknown L loop run loop_id: {frame.loop_id}")
    if frame.run_index < 1:
        raise ValueError("LLoopRunFrame.run_index must be positive")
    if frame.namespace_policy not in L_LOOP_RUN_NAMESPACE_POLICIES:
        raise ValueError(f"unknown L loop run namespace policy: {frame.namespace_policy}")
    if frame.same_turn_rerun_allowed and not frame.primary_ids_are_attempt_scoped:
        raise ValueError("same_turn_rerun_allowed requires attempt-scoped primary IDs")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LLoopRunFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LLoopRunFrame.source_data_ids must not contain empty values")


L3_PRESERVED_INFO_FRAME_SCHEMA_NAME = "L3PreservedInfoFrame"
L3_PRESERVED_INFO_FRAME_SCHEMA_VERSION = "0.1"
L3_JUDGEMENT_STATUSES = {"not_judged"}
L3_ACHIEVEMENT_FRAME_SCHEMA_NAME = "L3AchievementFrame"
L3_ACHIEVEMENT_FRAME_SCHEMA_VERSION = "0.1"
L3_ACHIEVEMENT_STATUSES = {"achieved", "partial", "failed"}
L3_GOAL_MATCH_STATUSES = {"matched", "partial", "missing", "not_applicable"}
L3_SEMANTIC_GOAL_MATCH_STATUSES = {"matched", "partial", "missing", "not_run"}


@dataclass
class L3PreservedSearchCandidate:
    """L3가 search_docs 결과에서 다음 흐름에 넘기기로 보존한 후보 하나."""

    # 절대 정보: L3 보존 프레임 안에서 후보 하나를 구분하는 ID.
    candidate_id: str
    # 절대 정보: 이 후보가 나온 원본 tool_result data_id.
    source_data_id: str
    # 절대 정보: 이 후보가 나온 원본 tool_call trace ID.
    source_trace_id: str | None
    # 절대 정보: search_docs 도구가 붙인 검색 결과 ID.
    result_id: str
    # 절대 정보: 문서 루트 안에서의 Markdown 문서 ID.
    doc_id: str
    # 절대 정보: 문서 chunk ID.
    chunk_id: str
    # 절대 정보: 현재 임베딩 모델이 계산한 유사도 점수.
    # 이 값은 "내용이 맞다"가 아니라 "도구가 이렇게 계산했다"는 뜻이다.
    score: float
    # 절대 정보: 점수를 만든 임베딩 모델 ID.
    embedding_model_id: str
    # 절대 정보: 도구가 해당 chunk에서 잘라낸 미리보기 문자열.
    # 이 문자열의 주장 내용이 참이라는 뜻은 아니다.
    text_preview: str
    document_kind: str | None = None
    source_role: str | None = None
    document_memory_index_id: str | None = None
    snapshot_id: str | None = None


@dataclass
class L3PreservedInfoFrame:
    """L3가 L루프 결과를 다음 노드에게 넘기기 위해 DataStore에 저장하는 보존 프레임."""

    # 절대 정보: DataStore에 저장될 프레임의 data_id와 같은 값.
    frame_id: str
    # 절대 정보: 이 프레임이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L3_PRESERVED_INFO_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L3_PRESERVED_INFO_FRAME_SCHEMA_VERSION
    # 절대 정보: L3가 입력으로 받은 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: L3가 읽은 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 아직 의미 판단을 하지 않았다는 처리 상태.
    # 나중에 L3 판단 노드가 생기면 achieved, partial, failed 같은 값으로 확장할 수 있다.
    judgement_status: str = "not_judged"
    # 절대 정보: search_docs tool_result에서 보존한 검색 후보 목록.
    candidates: list[L3PreservedSearchCandidate] = field(default_factory=list)


def validate_l3_preserved_info_frame(frame: L3PreservedInfoFrame) -> None:
    """L3PreservedInfoFrame이 현재 확정한 최소 스키마 규칙을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
        "judgement_status": frame.judgement_status,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L3PreservedInfoFrame.{field_name} must not be empty")

    if frame.schema_name != L3_PRESERVED_INFO_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L3 preserved frame schema_name: {frame.schema_name}")
    if frame.schema_version != L3_PRESERVED_INFO_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L3 preserved frame schema_version: {frame.schema_version}")
    if frame.judgement_status not in L3_JUDGEMENT_STATUSES:
        raise ValueError(f"unknown L3 judgement_status: {frame.judgement_status}")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L3PreservedInfoFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L3PreservedInfoFrame.source_data_ids must not contain empty values")

    for candidate in frame.candidates:
        _validate_l3_preserved_candidate(candidate)


def _validate_l3_preserved_candidate(candidate: L3PreservedSearchCandidate) -> None:
    """L3 검색 후보 하나의 절대정보 필드를 확인한다."""

    required_text_fields = {
        "candidate_id": candidate.candidate_id,
        "source_data_id": candidate.source_data_id,
        "result_id": candidate.result_id,
        "doc_id": candidate.doc_id,
        "chunk_id": candidate.chunk_id,
        "embedding_model_id": candidate.embedding_model_id,
        "text_preview": candidate.text_preview,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L3PreservedSearchCandidate.{field_name} must not be empty")

    if not isinstance(candidate.score, (int, float)):
        raise TypeError("L3PreservedSearchCandidate.score must be numeric")
    if candidate.score < -1.0 or candidate.score > 1.0:
        raise ValueError("L3PreservedSearchCandidate.score must be between -1.0 and 1.0")


@dataclass
class L3AchievementFrame:
    """L3가 L루프의 운영 목표 달성 여부와 이유를 DataStore에 저장하는 판단 프레임."""

    # 절대 정보: DataStore에 저장될 achievement frame data_id와 같은 값.
    frame_id: str
    # 절대 정보: 이 판단 프레임이 만들어진 사용자 턴 ID.
    turn_id: str
    # 분류 경계: code operation check이면 코드 정책 결과, LLM semantic check이면 source bundle 기반 혼합 정보다.
    achievement_status: str
    # 분류 경계: achievement_status를 선택한 이유. 생성자/status로 정보 등급을 판별한다.
    # 반드시 evidence_trace_ids/evidence_data_ids를 함께 가져야 한다.
    reason: str
    # 절대 정보: L3가 기준으로 삼은 L1 목표 프레임 data_id.
    target_goal_data_id: str
    # 절대 정보: 이 판단이 참조한 L3 보존 프레임 data_id.
    preserved_info_frame_id: str
    # 절대 정보: L3 보존 프레임 안의 검색 후보 개수.
    candidate_count: int = 0
    # 절대 정보: 이 판단의 근거 trace ID 목록.
    evidence_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 이 판단의 근거 DataStore record ID 목록.
    evidence_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: L3가 입력으로 받은 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: L3가 입력으로 읽었거나 만든 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: L3가 참조한 최종 LLoopControlFrame data_id.
    final_control_data_id: str | None = None
    # 절대 정보/복사값: 최종 controller 판단 이름. 원 control frame과 함께 봐야 한다.
    controller_decision: str | None = None
    # 실제 달성 상태 생성자. 현재 L3는 LLM 의미 판단이 아니라 코드 운영 체크다.
    achievement_generation_source: str = "CODE:OPERATION_CHECK"
    # LLM이 의미적 충분성/달성 판단을 수행했는지.
    llm_semantic_judgement_status: str = "not_run"
    # 절대 정보: L3가 평가한 L1 거시 목표.
    target_macro_goal: str = ""
    # 절대 정보: L3가 평가한 L1 미시 목표.
    target_micro_goal: str = ""
    # 분류 경계: 거시 목표 달성 상태. 생성자/status로 정보 등급을 판별한다.
    macro_achievement_status: str = ""
    # 분류 경계: 거시 목표 달성 이유. 생성자/status로 정보 등급을 판별한다.
    macro_achievement_reason: str = ""
    # 분류 경계: 미시 목표 달성 상태. 생성자/status로 정보 등급을 판별한다.
    micro_achievement_status: str = ""
    # 분류 경계: 미시 목표 달성 이유. 생성자/status로 정보 등급을 판별한다.
    micro_achievement_reason: str = ""
    # 절대 정보/코드 힌트: 사용자 입력에서 추출한 특정 문서 요청 후보.
    # 비어 있으면 특정 문서 요청을 확정하지 않은 것이다.
    requested_doc_hint: str = ""
    # 절대 정보: 이번 L루프에서 실제 read_doc으로 읽은 문서 ID 목록.
    read_doc_ids: list[str] = field(default_factory=list)
    # 절대 정보: search_docs 결과에서 L3가 보존한 문서 ID 목록.
    search_result_doc_ids: list[str] = field(default_factory=list)
    # 분류 경계: 특정 문서 요청과 실제 검색/읽기 결과의 대응 상태.
    # code guard이면 코드 정책 결과, LLM 판단이면 source bundle 기반 혼합 정보다.
    goal_match_status: str = "not_applicable"
    # 분류 경계: goal_match_status를 선택한 이유.
    goal_match_reason: str = "CODE_STATUS:no_specific_doc_hint_detected"
    semantic_goal_match_status: str = "not_run"
    semantic_goal_match_reason: str = "CODE_STATUS:llm_semantic_goal_match_not_run"
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L3_ACHIEVEMENT_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L3_ACHIEVEMENT_FRAME_SCHEMA_VERSION


def validate_l3_achievement_frame(frame: L3AchievementFrame) -> None:
    """L3AchievementFrame이 현재 확정한 최소 스키마 규칙을 지키는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "achievement_status": frame.achievement_status,
        "reason": frame.reason,
        "target_goal_data_id": frame.target_goal_data_id,
        "preserved_info_frame_id": frame.preserved_info_frame_id,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"L3AchievementFrame.{field_name} must not be empty")

    if frame.schema_name != L3_ACHIEVEMENT_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown L3 achievement frame schema_name: {frame.schema_name}")
    if frame.schema_version != L3_ACHIEVEMENT_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown L3 achievement frame schema_version: {frame.schema_version}")
    if frame.achievement_status not in L3_ACHIEVEMENT_STATUSES:
        raise ValueError(f"unknown L3 achievement_status: {frame.achievement_status}")
    if frame.controller_decision is not None and frame.controller_decision not in L_LOOP_CONTROL_DECISIONS:
        raise ValueError(f"unknown L3 controller_decision: {frame.controller_decision}")
    if frame.goal_match_status not in L3_GOAL_MATCH_STATUSES:
        raise ValueError(f"unknown L3 goal_match_status: {frame.goal_match_status}")
    if frame.semantic_goal_match_status not in L3_SEMANTIC_GOAL_MATCH_STATUSES:
        raise ValueError(f"unknown L3 semantic_goal_match_status: {frame.semantic_goal_match_status}")
    if frame.semantic_goal_match_status != "not_run" and not frame.semantic_goal_match_reason:
        raise ValueError("L3AchievementFrame.semantic_goal_match_reason must not be empty when semantic match ran")
    for field_name, status in {
        "macro_achievement_status": frame.macro_achievement_status,
        "micro_achievement_status": frame.micro_achievement_status,
    }.items():
        if status and status not in L3_ACHIEVEMENT_STATUSES:
            raise ValueError(f"unknown L3 {field_name}: {status}")
    if not isinstance(frame.candidate_count, int):
        raise TypeError("L3AchievementFrame.candidate_count must be an integer")
    if frame.candidate_count < 0:
        raise ValueError("L3AchievementFrame.candidate_count must not be negative")

    for doc_id in frame.read_doc_ids:
        if not doc_id:
            raise ValueError("L3AchievementFrame.read_doc_ids must not contain empty values")
    for doc_id in frame.search_result_doc_ids:
        if not doc_id:
            raise ValueError("L3AchievementFrame.search_result_doc_ids must not contain empty values")
    for trace_id in frame.evidence_trace_ids:
        if not trace_id:
            raise ValueError("L3AchievementFrame.evidence_trace_ids must not contain empty values")
    for data_id in frame.evidence_data_ids:
        if not data_id:
            raise ValueError("L3AchievementFrame.evidence_data_ids must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L3AchievementFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L3AchievementFrame.source_data_ids must not contain empty values")


@dataclass
class FailureSignal:
    """기억 부족이나 스키마 실패 같은 문제 발생 사실을 알리는 신호."""

    # 이 실패 신호를 만든 주체. 예: node_0, trace_tracker, node_2.
    raised_by: str
    # 실패 종류. 예: memory_insufficient, schema_failed, tool_failed.
    type: str
    # 이 실패 판단의 근거가 되는 trace ID 목록.
    evidence_trace_ids: list[str] = field(default_factory=list)


@dataclass
class FailureSignalFrame:
    """실패/부족 신호를 DataStore에 저장하기 위한 v0.2 프레임."""

    failure_id: str
    turn_id: str
    type: str
    severity: str
    raised_by: str
    recoverable: bool
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    message: str = ""
    schema_name: str = "FailureSignalFrame"
    schema_version: str = "0.2"


def validate_failure_signal_frame(frame: FailureSignalFrame) -> None:
    """FailureSignalFrame의 최소 절대정보 규칙을 확인한다."""

    for field_name, value in {
        "failure_id": frame.failure_id,
        "turn_id": frame.turn_id,
        "type": frame.type,
        "severity": frame.severity,
        "raised_by": frame.raised_by,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"FailureSignalFrame.{field_name} must not be empty")
