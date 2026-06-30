from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schema_parts.base import (
    DataRef,
    NodeMovement,
    SchemaBinding,
    _validate_no_duplicates,
    _validate_string_list,
)
from songryeon_core.core.schema_parts.graph_memory import (
    CORE_EGO_GUIDE_WORKER_HINT_FAILURE_TYPES,
    CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_NAME,
    CORE_EGO_GUIDE_WORKER_HINT_FRAME_SCHEMA_VERSION,
    CORE_EGO_GUIDE_WORKER_HINT_STATUSES,
    CORE_EGO_GUIDE_WORKER_PARSE_STATUSES,
    CORE_EGO_TIME_AXIS_FRAME_SCHEMA_NAME,
    CORE_EGO_TIME_AXIS_FRAME_SCHEMA_VERSION,
    GRAPH_MEMORY_CODE_GENERATOR,
    GRAPH_MEMORY_EDGE_FRAME_SCHEMA_NAME,
    GRAPH_MEMORY_EDGE_FRAME_SCHEMA_VERSION,
    GRAPH_MEMORY_EDGE_KINDS,
    GRAPH_MEMORY_NODE_FRAME_SCHEMA_NAME,
    GRAPH_MEMORY_NODE_FRAME_SCHEMA_VERSION,
    GRAPH_MEMORY_NODE_KINDS,
    GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_NAME,
    GRAPH_MEMORY_SNAPSHOT_FRAME_SCHEMA_VERSION,
    RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_NAME,
    RLOOP_GRAPH_GUIDE_PACKET_FRAME_SCHEMA_VERSION,
    RLOOP_GUIDE_CODE_GENERATOR,
    R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_NAME,
    R_LOOP_MEMORY_HANDOFF_PACKET_FRAME_SCHEMA_VERSION,
    R_LOOP_MEMORY_HANDOFF_SEMANTIC_HINT_STATUSES,
    R_LOOP_MEMORY_HANDOFF_STATUSES,
    CoreEgoGuideWorkerHintFrame,
    CoreEgoTimeAxisFrame,
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    GraphMemorySnapshotFrame,
    RLoopGraphGuidePacketFrame,
    RLoopMemoryHandoffPacketFrame,
    validate_core_ego_guide_worker_hint_frame,
    validate_core_ego_time_axis_frame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
    validate_graph_memory_snapshot_frame,
    validate_r_loop_memory_handoff_packet_frame,
    validate_rloop_graph_guide_packet_frame,
)
from songryeon_core.core.schema_parts.r_loop import (
    R1GraphGoalFrame,
    R2GraphNodeSelectionFrame,
    R3GraphInspectionFrame,
    RLoopBudgetFrame,
    RLoopContinuationFrame,
    RLoopReturnSummaryFrame,
    R1_GRAPH_GOAL_FRAME_SCHEMA_NAME,
    R1_GRAPH_GOAL_FRAME_SCHEMA_VERSION,
    R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_NAME,
    R2_GRAPH_NODE_SELECTION_FRAME_SCHEMA_VERSION,
    R3_GRAPH_INSPECTION_FRAME_SCHEMA_NAME,
    R3_GRAPH_INSPECTION_FRAME_SCHEMA_VERSION,
    R_LOOP_BUDGET_FRAME_SCHEMA_NAME,
    R_LOOP_BUDGET_FRAME_SCHEMA_VERSION,
    R_LOOP_CONTINUATION_FRAME_SCHEMA_NAME,
    R_LOOP_CONTINUATION_FRAME_SCHEMA_VERSION,
    R_LOOP_CONTINUATION_STATUSES,
    R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_NAME,
    R_LOOP_RETURN_SUMMARY_FRAME_SCHEMA_VERSION,
    R_LOOP_SCHEMA_ONLY_GENERATOR,
    validate_r1_graph_goal_frame,
    validate_r2_graph_node_selection_frame,
    validate_r3_graph_inspection_frame,
    validate_r_loop_budget_frame,
    validate_r_loop_continuation_frame,
    validate_r_loop_return_summary_frame,
)
from songryeon_core.core.schema_parts.task_ledger import (
    TASK_FRAME_SCHEMA_NAME,
    TASK_FRAME_SCHEMA_VERSION,
    TASK_RESULT_FRAME_SCHEMA_NAME,
    TASK_RESULT_FRAME_SCHEMA_VERSION,
    TaskFrame,
    TaskResultFrame,
    validate_task_frame,
    validate_task_result_frame,
)
from songryeon_core.core.schema_parts.trace_data import (
    MemoryPacketFrom0,
    RoutingDecision,
    TraceEvent,
    TurnStateCapsule,
    UnifiedState,
    ZeroState,
)


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


MEMORY_RELEVANCE_CANDIDATE_FRAME_SCHEMA_NAME = "MemoryRelevanceCandidateFrame"
MEMORY_RELEVANCE_CANDIDATE_FRAME_SCHEMA_VERSION = "0.1"
MEMORY_RELEVANCE_SELECTION_FRAME_SCHEMA_NAME = "MemoryRelevanceSelectionFrame"
MEMORY_RELEVANCE_SELECTION_FRAME_SCHEMA_VERSION = "0.1"
MEMORY_RELEVANCE_SELECTION_STATUSES = {"selected", "none_selected", "failed"}
SELECTED_RECENT_MEMORY_CONTEXT_FRAME_SCHEMA_NAME = "SelectedRecentMemoryContextFrame"
SELECTED_RECENT_MEMORY_CONTEXT_FRAME_SCHEMA_VERSION = "0.1"
RAW_MEMORY_COMPRESSION_CANDIDATE_FRAME_SCHEMA_NAME = "RawMemoryCompressionCandidateFrame"
RAW_MEMORY_COMPRESSION_CANDIDATE_FRAME_SCHEMA_VERSION = "0.1"
RAW_MEMORY_COMPRESSION_CANDIDATE_STATUSES = {
    "not_needed",
    "pending_node5_compression",
}


@dataclass
class MemoryRelevanceCandidateFrame:
    """나중에 LLM이 기억 관련성 판단을 남길 수 있는 빈 후보 그릇."""

    # 학습 메모: 이 frame은 "관련 있다"는 판단이 아니다.
    # 최근 raw 대화와 capsule이 절대 좌표로 대응됐으니, 나중에 판단자가 볼 후보임을 표시한다.
    frame_id: str
    # 현재 사용자 턴 ID.
    turn_id: str
    # 후보가 가리키는 이전 턴 ID.
    candidate_turn_id: str
    # 이 후보 frame의 바탕이 된 memory item ID.
    source_memory_item_id: str
    # 후보 좌표의 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 후보 좌표의 근거 data ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 아직 관련성 판단을 하지 않았다는 절대 상태.
    judgement_status: str = "not_run"
    # 아래 네 필드는 나중에 판단자가 채운다. not_run일 때는 반드시 비어 있어야 한다.
    judged_by: str | None = None
    relevance_label: str | None = None
    relevance_reason: str | None = None
    info_class: str | None = None
    schema_name: str = MEMORY_RELEVANCE_CANDIDATE_FRAME_SCHEMA_NAME
    schema_version: str = MEMORY_RELEVANCE_CANDIDATE_FRAME_SCHEMA_VERSION


@dataclass
class MemoryRelevanceSelectionFrame:
    """LLM selector가 최근 기억 후보 관련성을 판단한 결과."""

    # 이 frame은 0의 판단이 아니라 selector LLM 판단 또는 code status close를 기록한다.
    frame_id: str
    turn_id: str
    selector_target_node: str
    current_user_input_trace_id: str
    source_memory_packet_id: str
    candidate_frame_ids: list[str] = field(default_factory=list)
    selected_candidate_turn_ids: list[str] = field(default_factory=list)
    selected_candidate_frame_ids: list[str] = field(default_factory=list)
    selection_status: str = "none_selected"
    selection_reason: str = ""
    judged_by: str | None = None
    generated_by: str = "LLM:memory_relevance_selector"
    llm_call_data_id: str | None = None
    llm_trace_event_id: str | None = None
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    source_memory_item_ids: list[str] = field(default_factory=list)
    info_class: str = "mixed"
    source_mode: str = "source_bundle"
    claim_alignment: str = "multi_source_bundle"
    schema_name: str = MEMORY_RELEVANCE_SELECTION_FRAME_SCHEMA_NAME
    schema_version: str = MEMORY_RELEVANCE_SELECTION_FRAME_SCHEMA_VERSION


@dataclass
class SelectedRecentMemoryContextItem:
    """selector가 고른 이전 턴 raw 원문을 요약 없이 복사한 항목."""

    item_id: str
    source_turn_id: str
    source_candidate_frame_id: str
    source_memory_item_id: str
    raw_user_text: str
    raw_assistant_text: str
    raw_user_text_chars: int
    raw_assistant_text_chars: int
    raw_user_text_truncated: bool
    raw_assistant_text_truncated: bool
    copied_from: str
    selection_reason_source_data_id: str
    selection_info_class: str
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)


@dataclass
class SelectedRecentMemoryContextFrame:
    """선택된 최근 기억 후보의 raw 대화 원문 복사본을 담는 절대정보 frame."""

    frame_id: str
    turn_id: str
    selection_frame_id: str
    selection_status: str
    selected_turn_count: int
    items: list[SelectedRecentMemoryContextItem] = field(default_factory=list)
    missing_selected_memory_context_count: int = 0
    generated_by: str = "CODE:SELECTED_RECENT_MEMORY_CONTEXT_BUILDER"
    info_class: str = "absolute_copied_context"
    semantic_judgement_status: str = "not_run"
    source_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    schema_name: str = SELECTED_RECENT_MEMORY_CONTEXT_FRAME_SCHEMA_NAME
    schema_version: str = SELECTED_RECENT_MEMORY_CONTEXT_FRAME_SCHEMA_VERSION


@dataclass
class RawMemoryCompressionCandidateFrame:
    """최근 raw 원문 창에서 node_5가 나중에 압축할 후보 좌표만 기록한다."""

    # 학습 메모: 이 frame은 0의 의미 요약이 아니다.
    # raw entry 개수와 정책 상수만으로 retained/candidate turn 좌표를 나눈 결과다.
    frame_id: str
    turn_id: str
    policy_id: str
    raw_conversation_count: int
    max_raw_window: int
    min_raw_guarantee: int
    post_compression_keep: int
    compression_batch_size: int
    candidate_status: str
    candidate_turn_ids: list[str] = field(default_factory=list)
    candidate_raw_entry_count: int = 0
    retained_raw_turn_ids: list[str] = field(default_factory=list)
    retained_raw_entry_count: int = 0
    older_unmanaged_raw_turn_count: int = 0
    source_memory_item_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    generated_by: str = "CODE:RAW_MEMORY_WINDOW_POLICY"
    info_class: str = "absolute_policy_decision"
    semantic_judgement_status: str = "not_run"
    node5_compression_status: str = "not_run"
    node4_approval_status: str = "not_run"
    schema_name: str = RAW_MEMORY_COMPRESSION_CANDIDATE_FRAME_SCHEMA_NAME
    schema_version: str = RAW_MEMORY_COMPRESSION_CANDIDATE_FRAME_SCHEMA_VERSION


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
    relevance_candidate_frames: list[MemoryRelevanceCandidateFrame] = field(default_factory=list)
    compression_candidate_frames: list[RawMemoryCompressionCandidateFrame] = field(default_factory=list)
    schema_name: str = "MemoryPacketPayload"
    schema_version: str = "0.2"


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

    for frame in payload.relevance_candidate_frames:
        validate_memory_relevance_candidate_frame(frame)
    for frame in payload.compression_candidate_frames:
        validate_raw_memory_compression_candidate_frame(frame)


def validate_memory_relevance_candidate_frame(frame: MemoryRelevanceCandidateFrame) -> None:
    """MemoryRelevanceCandidateFrame이 판단 없이 후보 좌표만 담는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "candidate_turn_id": frame.candidate_turn_id,
        "source_memory_item_id": frame.source_memory_item_id,
        "judgement_status": frame.judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"MemoryRelevanceCandidateFrame.{field_name} must not be empty")

    if frame.schema_name != MEMORY_RELEVANCE_CANDIDATE_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown memory relevance candidate schema_name: {frame.schema_name}"
        )
    if frame.schema_version != MEMORY_RELEVANCE_CANDIDATE_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown memory relevance candidate schema_version: {frame.schema_version}"
        )
    if frame.judgement_status != "not_run":
        raise ValueError("MemoryRelevanceCandidateFrame v0 only allows judgement_status=not_run")
    if any(
        value is not None
        for value in (
            frame.judged_by,
            frame.relevance_label,
            frame.relevance_reason,
            frame.info_class,
        )
    ):
        raise ValueError("not_run MemoryRelevanceCandidateFrame must not contain judgement fields")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError(
                "MemoryRelevanceCandidateFrame.source_trace_ids must not contain empty values"
            )
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError(
                "MemoryRelevanceCandidateFrame.source_data_ids must not contain empty values"
            )


def validate_selected_recent_memory_context_frame(
    frame: SelectedRecentMemoryContextFrame,
) -> None:
    """SelectedRecentMemoryContextFrame이 요약 없이 raw 복사본만 담는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "selection_frame_id": frame.selection_frame_id,
        "selection_status": frame.selection_status,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"SelectedRecentMemoryContextFrame.{field_name} must not be empty")
    if frame.schema_name != SELECTED_RECENT_MEMORY_CONTEXT_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown selected recent memory context schema_name: {frame.schema_name}"
        )
    if frame.schema_version != SELECTED_RECENT_MEMORY_CONTEXT_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown selected recent memory context schema_version: {frame.schema_version}"
        )
    if frame.selection_status not in (MEMORY_RELEVANCE_SELECTION_STATUSES | {"not_recorded"}):
        raise ValueError(
            f"unknown SelectedRecentMemoryContextFrame.selection_status: {frame.selection_status}"
        )
    if frame.generated_by != "CODE:SELECTED_RECENT_MEMORY_CONTEXT_BUILDER":
        raise ValueError("SelectedRecentMemoryContextFrame.generated_by must be code builder")
    if frame.info_class != "absolute_copied_context":
        raise ValueError(
            "SelectedRecentMemoryContextFrame.info_class must be absolute_copied_context"
        )
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("SelectedRecentMemoryContextFrame must not run semantic judgement")
    if frame.selected_turn_count < 0:
        raise ValueError("SelectedRecentMemoryContextFrame.selected_turn_count must be >= 0")
    if frame.missing_selected_memory_context_count < 0:
        raise ValueError(
            "SelectedRecentMemoryContextFrame.missing_selected_memory_context_count must be >= 0"
        )
    if frame.selected_turn_count != len(frame.items):
        raise ValueError("SelectedRecentMemoryContextFrame.selected_turn_count must match items")
    if frame.selection_status in {"none_selected", "failed", "not_recorded"}:
        if frame.selected_turn_count != 0 or frame.items:
            raise ValueError("non-selected memory context frame must not include copied items")
    _validate_string_list(
        "SelectedRecentMemoryContextFrame.source_data_ids",
        frame.source_data_ids,
    )
    _validate_string_list(
        "SelectedRecentMemoryContextFrame.source_trace_ids",
        frame.source_trace_ids,
    )
    if frame.selection_frame_id not in frame.source_data_ids:
        raise ValueError(
            "SelectedRecentMemoryContextFrame.source_data_ids must include selection_frame_id"
        )
    seen_turn_ids: set[str] = set()
    for item in frame.items:
        _validate_selected_recent_memory_context_item(item)
        if item.source_turn_id in seen_turn_ids:
            raise ValueError("SelectedRecentMemoryContextFrame.items must not duplicate turns")
        seen_turn_ids.add(item.source_turn_id)


def _validate_selected_recent_memory_context_item(
    item: SelectedRecentMemoryContextItem,
) -> None:
    for field_name, value in {
        "item_id": item.item_id,
        "source_turn_id": item.source_turn_id,
        "source_candidate_frame_id": item.source_candidate_frame_id,
        "source_memory_item_id": item.source_memory_item_id,
        "copied_from": item.copied_from,
        "selection_reason_source_data_id": item.selection_reason_source_data_id,
        "selection_info_class": item.selection_info_class,
    }.items():
        if not value:
            raise ValueError(f"SelectedRecentMemoryContextItem.{field_name} must not be empty")
    if item.selection_info_class != "mixed":
        raise ValueError("SelectedRecentMemoryContextItem.selection_info_class must preserve mixed")
    for field_name, value in {
        "raw_user_text_chars": item.raw_user_text_chars,
        "raw_assistant_text_chars": item.raw_assistant_text_chars,
    }.items():
        if value < 0:
            raise ValueError(f"SelectedRecentMemoryContextItem.{field_name} must be >= 0")
    if len(item.raw_user_text) > item.raw_user_text_chars:
        raise ValueError("SelectedRecentMemoryContextItem.raw_user_text exceeds original char count")
    if len(item.raw_assistant_text) > item.raw_assistant_text_chars:
        raise ValueError(
            "SelectedRecentMemoryContextItem.raw_assistant_text exceeds original char count"
        )
    if not item.raw_user_text_truncated and len(item.raw_user_text) != item.raw_user_text_chars:
        raise ValueError("untruncated raw_user_text length must match original char count")
    if not item.raw_assistant_text_truncated and len(item.raw_assistant_text) != item.raw_assistant_text_chars:
        raise ValueError("untruncated raw_assistant_text length must match original char count")
    _validate_string_list("SelectedRecentMemoryContextItem.source_trace_ids", item.source_trace_ids)
    _validate_string_list("SelectedRecentMemoryContextItem.source_data_ids", item.source_data_ids)
    for required_data_id in (
        item.selection_reason_source_data_id,
    ):
        if required_data_id not in item.source_data_ids:
            raise ValueError(
                "SelectedRecentMemoryContextItem.source_data_ids must include selection source"
            )


def validate_raw_memory_compression_candidate_frame(
    frame: RawMemoryCompressionCandidateFrame,
) -> None:
    """RawMemoryCompressionCandidateFrame이 요약 없이 정책 좌표만 담는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "policy_id": frame.policy_id,
        "candidate_status": frame.candidate_status,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "node5_compression_status": frame.node5_compression_status,
        "node4_approval_status": frame.node4_approval_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(
                f"RawMemoryCompressionCandidateFrame.{field_name} must not be empty"
            )

    if frame.schema_name != RAW_MEMORY_COMPRESSION_CANDIDATE_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown raw memory compression candidate schema_name: {frame.schema_name}"
        )
    if frame.schema_version != RAW_MEMORY_COMPRESSION_CANDIDATE_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown raw memory compression candidate schema_version: {frame.schema_version}"
        )
    if frame.candidate_status not in RAW_MEMORY_COMPRESSION_CANDIDATE_STATUSES:
        raise ValueError(
            f"unknown RawMemoryCompressionCandidateFrame.candidate_status: {frame.candidate_status}"
        )

    if frame.generated_by != "CODE:RAW_MEMORY_WINDOW_POLICY":
        raise ValueError("RawMemoryCompressionCandidateFrame.generated_by must be CODE policy")
    if frame.info_class != "absolute_policy_decision":
        raise ValueError(
            "RawMemoryCompressionCandidateFrame.info_class must be absolute_policy_decision"
        )
    for field_name, value in {
        "semantic_judgement_status": frame.semantic_judgement_status,
        "node5_compression_status": frame.node5_compression_status,
        "node4_approval_status": frame.node4_approval_status,
    }.items():
        if value != "not_run":
            raise ValueError(f"RawMemoryCompressionCandidateFrame.{field_name} must be not_run")

    for field_name, value in {
        "raw_conversation_count": frame.raw_conversation_count,
        "max_raw_window": frame.max_raw_window,
        "min_raw_guarantee": frame.min_raw_guarantee,
        "post_compression_keep": frame.post_compression_keep,
        "compression_batch_size": frame.compression_batch_size,
        "candidate_raw_entry_count": frame.candidate_raw_entry_count,
        "retained_raw_entry_count": frame.retained_raw_entry_count,
        "older_unmanaged_raw_turn_count": frame.older_unmanaged_raw_turn_count,
    }.items():
        if value < 0:
            raise ValueError(f"RawMemoryCompressionCandidateFrame.{field_name} must be >= 0")

    if frame.max_raw_window <= 0:
        raise ValueError("RawMemoryCompressionCandidateFrame.max_raw_window must be positive")
    if frame.min_raw_guarantee <= 0:
        raise ValueError("RawMemoryCompressionCandidateFrame.min_raw_guarantee must be positive")
    if frame.compression_batch_size <= 0:
        raise ValueError(
            "RawMemoryCompressionCandidateFrame.compression_batch_size must be positive"
        )
    if frame.post_compression_keep < frame.min_raw_guarantee:
        raise ValueError(
            "RawMemoryCompressionCandidateFrame.post_compression_keep must satisfy min guarantee"
        )
    if frame.max_raw_window != frame.post_compression_keep + frame.compression_batch_size - 1:
        raise ValueError("RawMemoryCompressionCandidateFrame policy constants are inconsistent")

    _validate_string_list(
        "RawMemoryCompressionCandidateFrame.candidate_turn_ids",
        frame.candidate_turn_ids,
    )
    _validate_string_list(
        "RawMemoryCompressionCandidateFrame.retained_raw_turn_ids",
        frame.retained_raw_turn_ids,
    )
    _validate_string_list(
        "RawMemoryCompressionCandidateFrame.source_memory_item_ids",
        frame.source_memory_item_ids,
    )
    _validate_string_list(
        "RawMemoryCompressionCandidateFrame.source_trace_ids",
        frame.source_trace_ids,
    )
    _validate_string_list(
        "RawMemoryCompressionCandidateFrame.source_data_ids",
        frame.source_data_ids,
    )
    _validate_no_duplicates(
        "RawMemoryCompressionCandidateFrame.candidate_turn_ids",
        frame.candidate_turn_ids,
    )
    _validate_no_duplicates(
        "RawMemoryCompressionCandidateFrame.retained_raw_turn_ids",
        frame.retained_raw_turn_ids,
    )
    if set(frame.candidate_turn_ids).intersection(frame.retained_raw_turn_ids):
        raise ValueError("raw memory candidate and retained turn ids must not overlap")

    if frame.candidate_status == "not_needed":
        if frame.raw_conversation_count > frame.max_raw_window:
            raise ValueError("not_needed raw memory candidate cannot exceed max_raw_window")
        if frame.candidate_turn_ids or frame.candidate_raw_entry_count != 0:
            raise ValueError("not_needed raw memory candidate must not include candidate ids")
        if frame.older_unmanaged_raw_turn_count != 0:
            raise ValueError("not_needed raw memory candidate must not expose older unmanaged turns")

    if frame.candidate_status == "pending_node5_compression":
        if frame.raw_conversation_count <= frame.max_raw_window:
            raise ValueError("pending raw memory candidate must exceed max_raw_window")
        if frame.candidate_raw_entry_count != frame.compression_batch_size:
            raise ValueError("pending raw memory candidate must use one compression batch")
        if len(frame.candidate_turn_ids) != frame.compression_batch_size:
            raise ValueError("pending raw memory candidate must include batch turn ids")
        if frame.retained_raw_entry_count != frame.post_compression_keep:
            raise ValueError("pending raw memory candidate must retain post_compression_keep turns")
        if len(frame.retained_raw_turn_ids) != frame.post_compression_keep:
            raise ValueError("pending raw memory candidate must include retained turn ids")


def validate_memory_relevance_selection_frame(frame: MemoryRelevanceSelectionFrame) -> None:
    """MemoryRelevanceSelectionFrame이 selector 판단 출처와 실패 경계를 드러내는지 확인한다."""

    required_text_fields = {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "selector_target_node": frame.selector_target_node,
        "current_user_input_trace_id": frame.current_user_input_trace_id,
        "source_memory_packet_id": frame.source_memory_packet_id,
        "selection_status": frame.selection_status,
        "selection_reason": frame.selection_reason,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "source_mode": frame.source_mode,
        "claim_alignment": frame.claim_alignment,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }
    for field_name, value in required_text_fields.items():
        if not value:
            raise ValueError(f"MemoryRelevanceSelectionFrame.{field_name} must not be empty")

    if frame.schema_name != MEMORY_RELEVANCE_SELECTION_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown memory relevance selection schema_name: {frame.schema_name}"
        )
    if frame.schema_version != MEMORY_RELEVANCE_SELECTION_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown memory relevance selection schema_version: {frame.schema_version}"
        )
    if frame.selection_status not in MEMORY_RELEVANCE_SELECTION_STATUSES:
        raise ValueError(
            f"unknown MemoryRelevanceSelectionFrame.selection_status: {frame.selection_status}"
        )
    if frame.source_mode != "source_bundle":
        raise ValueError(f"unknown MemoryRelevanceSelectionFrame.source_mode: {frame.source_mode}")
    if frame.claim_alignment != "multi_source_bundle":
        raise ValueError(
            f"unknown MemoryRelevanceSelectionFrame.claim_alignment: {frame.claim_alignment}"
        )

    _validate_string_list(
        "MemoryRelevanceSelectionFrame.candidate_frame_ids",
        frame.candidate_frame_ids,
    )
    _validate_string_list(
        "MemoryRelevanceSelectionFrame.selected_candidate_turn_ids",
        frame.selected_candidate_turn_ids,
    )
    _validate_string_list(
        "MemoryRelevanceSelectionFrame.selected_candidate_frame_ids",
        frame.selected_candidate_frame_ids,
    )
    _validate_string_list(
        "MemoryRelevanceSelectionFrame.source_trace_ids",
        frame.source_trace_ids,
    )
    _validate_string_list(
        "MemoryRelevanceSelectionFrame.source_data_ids",
        frame.source_data_ids,
    )
    _validate_string_list(
        "MemoryRelevanceSelectionFrame.source_memory_item_ids",
        frame.source_memory_item_ids,
    )
    _validate_no_duplicates(
        "MemoryRelevanceSelectionFrame.selected_candidate_frame_ids",
        frame.selected_candidate_frame_ids,
    )
    _validate_no_duplicates(
        "MemoryRelevanceSelectionFrame.selected_candidate_turn_ids",
        frame.selected_candidate_turn_ids,
    )

    if frame.current_user_input_trace_id not in frame.source_trace_ids:
        raise ValueError(
            "MemoryRelevanceSelectionFrame.source_trace_ids must include current_user_input_trace_id"
        )
    if frame.source_memory_packet_id not in frame.source_data_ids:
        raise ValueError(
            "MemoryRelevanceSelectionFrame.source_data_ids must include source_memory_packet_id"
        )
    for selected_frame_id in frame.selected_candidate_frame_ids:
        if selected_frame_id not in frame.candidate_frame_ids:
            raise ValueError(
                "selected_candidate_frame_ids must be a subset of candidate_frame_ids"
            )

    if frame.selection_status == "selected":
        if not frame.selected_candidate_turn_ids or not frame.selected_candidate_frame_ids:
            raise ValueError("selected MemoryRelevanceSelectionFrame must include selected candidates")
        if frame.info_class != "mixed":
            raise ValueError("selected MemoryRelevanceSelectionFrame must use info_class=mixed")

    if frame.selection_status in {"none_selected", "failed"}:
        if frame.selected_candidate_turn_ids or frame.selected_candidate_frame_ids:
            raise ValueError(
                "none_selected/failed MemoryRelevanceSelectionFrame must not include selected candidates"
            )

    if frame.candidate_frame_ids:
        if frame.selection_status in {"selected", "none_selected"}:
            if frame.judged_by is None or not frame.judged_by.startswith("LLM:"):
                raise ValueError("LLM selection result must reveal judged_by=LLM:*")
            if not frame.generated_by.startswith("LLM:"):
                raise ValueError("LLM selection result must reveal generated_by=LLM:*")
            if frame.llm_call_data_id is None or frame.llm_trace_event_id is None:
                raise ValueError("LLM selection result must cite llm call data and trace")
            if frame.llm_call_data_id not in frame.source_data_ids:
                raise ValueError(
                    "LLM selection source_data_ids must include llm_call_data_id"
                )
            if frame.llm_trace_event_id not in frame.source_trace_ids:
                raise ValueError(
                    "LLM selection source_trace_ids must include llm_trace_event_id"
                )
            if frame.info_class != "mixed":
                raise ValueError("LLM selection result must use info_class=mixed")
        if frame.selection_status == "failed":
            if frame.selected_candidate_turn_ids or frame.selected_candidate_frame_ids:
                raise ValueError("failed selector must not contain fallback selections")
            if not frame.selection_reason.startswith("CODE_STATUS:"):
                raise ValueError("failed selector reason must be a code status")
    else:
        if frame.selection_status != "none_selected":
            raise ValueError("selection with no candidates must close as none_selected")
        if frame.selection_reason != "CODE_STATUS:no_memory_relevance_candidates":
            raise ValueError("selection with no candidates must use no-candidates code status")
        if frame.judged_by is not None:
            raise ValueError("selection with no candidates must not have judged_by")
        if frame.llm_call_data_id is not None or frame.llm_trace_event_id is not None:
            raise ValueError("selection with no candidates must not cite an LLM call")


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


R_ROUTE_EXPERIMENTAL_POLICY_FLAG = "enable_r_route_experimental"
R_ROUTE_EXPERIMENTAL_NEXT_0_MODE = "r_loop_graph_guide_handoff"


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
    if frame.route == "R":
        if frame.policy_flag != R_ROUTE_EXPERIMENTAL_POLICY_FLAG:
            raise ValueError("RoutingDecisionFrame route=R requires experimental policy flag")
        if frame.expected_next_0_mode != R_ROUTE_EXPERIMENTAL_NEXT_0_MODE:
            raise ValueError("RoutingDecisionFrame route=R requires R graph handoff mode")
        if not frame.route_source.startswith("LLM:"):
            raise ValueError("RoutingDecisionFrame route=R must be selected by node_1 LLM")
        if frame.llm_routing_status != "ran":
            raise ValueError("RoutingDecisionFrame route=R requires llm_routing_status=ran")
        if frame.route_rule_id != "llm_router":
            raise ValueError("RoutingDecisionFrame route=R requires llm_router rule id")
    elif frame.route not in {"L", "2"}:
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


NODE2_ANSWER_BASIS_FRAME_SCHEMA_NAME = "Node2AnswerBasisFrame"
NODE2_ANSWER_BASIS_FRAME_SCHEMA_VERSION = "0.1"
ANSWER_BASIS_MODES = {
    "absolute_first",
    "relative_allowed",
    "mixed_or_uncertain",
}
BASIS_REASON_CODES = {
    "code_verified_fact_required",
    "user_asked_for_interpretation",
    "multi_source_bundle",
    "source_mapping_unclear",
    "insufficient_grounding",
    "partial_evidence_only",
    "recent_conversation_basis_present",
    "document_basis_present",
    "runtime_state_basis_present",
    "llm_mode_selection_failed",
}
EVIDENCE_ROLES = {
    "primary_answer_basis",
    "supporting_context",
    "available_but_not_used",
    "candidate_not_read",
    "excluded_by_budget",
    "failed_or_empty",
    "not_supplied",
}
ANSWER_BASIS_INFO_CLASSES = {"relative", "mixed", "absolute_status"}
ANSWER_BASIS_SEMANTIC_STATUSES = {"ran", "failed"}
ANSWER_BASIS_FAILURE_TYPES = {
    "none",
    "adapter_missing",
    "parse_failed",
    "schema_failed",
    "adapter_failed",
}
ANSWER_BASIS_PAYLOAD_PARSE_STATUSES = {"passed", "failed", "not_checked"}


@dataclass
class Node2EvidenceRole:
    """node_2가 source 하나에 부여한 답변 근거 역할 판단."""

    source_data_id: str
    evidence_role: str
    role_reason: str = ""
    role_reason_info_class: str = "mixed"


@dataclass
class Node2AnswerBasisFrame:
    """node_2가 node_3에게 넘기는 최종 답변 근거 자세 프레임."""

    frame_id: str
    turn_id: str
    answer_basis_mode: str
    basis_reason_codes: list[str]
    mode_selection_reason: str
    mode_selection_reason_info_class: str
    evidence_roles: list[Node2EvidenceRole] = field(default_factory=list)
    generated_by: str = "LLM:NODE_2"
    info_class: str = "mixed"
    semantic_judgement_status: str = "ran"
    answer_basis_failure_type: str = "none"
    answer_basis_llm_call_data_id: str | None = None
    answer_basis_trace_event_id: str | None = None
    answer_basis_validation_error: str = ""
    answer_basis_raw_text_present: bool = False
    answer_basis_prompt_ref: str = ""
    answer_basis_payload_parse_status: str = "not_checked"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE2_ANSWER_BASIS_FRAME_SCHEMA_NAME
    schema_version: str = NODE2_ANSWER_BASIS_FRAME_SCHEMA_VERSION


def validate_node2_answer_basis_frame(frame: Node2AnswerBasisFrame) -> None:
    """Node2AnswerBasisFrame의 enum과 metainfo 경계를 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "answer_basis_mode": frame.answer_basis_mode,
        "mode_selection_reason": frame.mode_selection_reason,
        "mode_selection_reason_info_class": frame.mode_selection_reason_info_class,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node2AnswerBasisFrame.{field_name} must not be empty")
    if frame.schema_name != NODE2_ANSWER_BASIS_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown Node2AnswerBasisFrame schema_name: {frame.schema_name}")
    if frame.schema_version != NODE2_ANSWER_BASIS_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown Node2AnswerBasisFrame schema_version: {frame.schema_version}")
    if frame.answer_basis_mode not in ANSWER_BASIS_MODES:
        raise ValueError(f"unknown answer_basis_mode: {frame.answer_basis_mode}")
    if frame.mode_selection_reason_info_class not in ANSWER_BASIS_INFO_CLASSES:
        raise ValueError(
            "unknown Node2AnswerBasisFrame.mode_selection_reason_info_class: "
            f"{frame.mode_selection_reason_info_class}"
        )
    if frame.info_class not in ANSWER_BASIS_INFO_CLASSES:
        raise ValueError(f"unknown Node2AnswerBasisFrame.info_class: {frame.info_class}")
    if frame.semantic_judgement_status not in ANSWER_BASIS_SEMANTIC_STATUSES:
        raise ValueError(
            "unknown Node2AnswerBasisFrame.semantic_judgement_status: "
            f"{frame.semantic_judgement_status}"
        )
    if frame.answer_basis_failure_type not in ANSWER_BASIS_FAILURE_TYPES:
        raise ValueError(
            "unknown Node2AnswerBasisFrame.answer_basis_failure_type: "
            f"{frame.answer_basis_failure_type}"
        )
    if frame.answer_basis_payload_parse_status not in ANSWER_BASIS_PAYLOAD_PARSE_STATUSES:
        raise ValueError(
            "unknown Node2AnswerBasisFrame.answer_basis_payload_parse_status: "
            f"{frame.answer_basis_payload_parse_status}"
        )
    if not isinstance(frame.answer_basis_raw_text_present, bool):
        raise TypeError("Node2AnswerBasisFrame.answer_basis_raw_text_present must be bool")
    if frame.answer_basis_llm_call_data_id is not None and not frame.answer_basis_llm_call_data_id:
        raise ValueError("Node2AnswerBasisFrame.answer_basis_llm_call_data_id must not be empty")
    if frame.answer_basis_trace_event_id is not None and not frame.answer_basis_trace_event_id:
        raise ValueError("Node2AnswerBasisFrame.answer_basis_trace_event_id must not be empty")
    if not frame.basis_reason_codes:
        raise ValueError("Node2AnswerBasisFrame.basis_reason_codes must not be empty")
    for code in frame.basis_reason_codes:
        if code not in BASIS_REASON_CODES:
            raise ValueError(f"unknown basis_reason_code: {code}")
    if frame.semantic_judgement_status == "failed":
        if frame.generated_by != "CODE:FALLBACK":
            raise ValueError("failed answer basis frame must use generated_by=CODE:FALLBACK")
        if frame.info_class != "absolute_status":
            raise ValueError("failed answer basis frame must use info_class=absolute_status")
        if frame.mode_selection_reason_info_class != "absolute_status":
            raise ValueError(
                "failed answer basis frame must use mode_selection_reason_info_class=absolute_status"
            )
        if frame.basis_reason_codes != ["llm_mode_selection_failed"]:
            raise ValueError("failed answer basis frame must use only llm_mode_selection_failed")
        if frame.answer_basis_failure_type == "none":
            raise ValueError("failed answer basis frame must expose a failure type")
    else:
        if not frame.generated_by.startswith("LLM:"):
            raise ValueError("ran answer basis frame must preserve generated_by=LLM:*")
        if frame.info_class not in {"relative", "mixed"}:
            raise ValueError("ran answer basis frame must be relative or mixed")
        if frame.mode_selection_reason_info_class not in {"relative", "mixed"}:
            raise ValueError("ran answer basis reason must be relative or mixed")
        if frame.answer_basis_failure_type != "none":
            raise ValueError("ran answer basis frame must use failure_type=none")

    _validate_no_duplicates("Node2AnswerBasisFrame.basis_reason_codes", frame.basis_reason_codes)
    _validate_string_list("Node2AnswerBasisFrame.source_trace_ids", frame.source_trace_ids)
    _validate_string_list("Node2AnswerBasisFrame.source_data_ids", frame.source_data_ids)
    for role in frame.evidence_roles:
        _validate_node2_evidence_role(role, allowed_source_data_ids=frame.source_data_ids)


def _validate_node2_evidence_role(
    role: Node2EvidenceRole,
    *,
    allowed_source_data_ids: list[str],
) -> None:
    for field_name, value in {
        "source_data_id": role.source_data_id,
        "evidence_role": role.evidence_role,
        "role_reason_info_class": role.role_reason_info_class,
    }.items():
        if not value:
            raise ValueError(f"Node2EvidenceRole.{field_name} must not be empty")
    if role.evidence_role not in EVIDENCE_ROLES:
        raise ValueError(f"unknown evidence_role: {role.evidence_role}")
    if role.role_reason_info_class not in ANSWER_BASIS_INFO_CLASSES:
        raise ValueError(
            f"unknown Node2EvidenceRole.role_reason_info_class: {role.role_reason_info_class}"
        )
    if role.evidence_role != "not_supplied" and role.source_data_id not in allowed_source_data_ids:
        raise ValueError("Node2EvidenceRole.source_data_id must exist in frame.source_data_ids")


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
    recent_memory_guard_status: str = "not_run"
    recent_memory_guard_reason_codes: list[str] = field(default_factory=list)
    recent_memory_claim_count: int = 0
    unsupported_recent_memory_claim_count: int = 0
    recent_memory_internal_id_leak_count: int = 0
    recent_memory_revision_targets: list[str] = field(default_factory=list)
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
    if frame.recent_memory_guard_status not in {"not_run", "pass", "needs_revision"}:
        raise ValueError(
            f"unknown Node4 recent_memory_guard_status: {frame.recent_memory_guard_status}"
        )
    for field_name, value in {
        "recent_memory_claim_count": frame.recent_memory_claim_count,
        "unsupported_recent_memory_claim_count": frame.unsupported_recent_memory_claim_count,
        "recent_memory_internal_id_leak_count": frame.recent_memory_internal_id_leak_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node4GatekeeperFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node4GatekeeperFrame.{field_name} must not be negative")
    _validate_string_list(
        "Node4GatekeeperFrame.recent_memory_guard_reason_codes",
        frame.recent_memory_guard_reason_codes,
    )
    _validate_string_list(
        "Node4GatekeeperFrame.recent_memory_revision_targets",
        frame.recent_memory_revision_targets,
    )
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


NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_SCHEMA_NAME = "Node0DocumentMaterialPacketFrame"
NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_SCHEMA_VERSION = "0.1"
NODE0_DOCUMENT_MATERIAL_ROLES = {
    "search_candidate",
    "actual_tool_read_doc",
    "supplied_document_context",
    "excluded_document_context",
    "unread_candidate",
}


@dataclass
class Node0DocumentMaterialItem:
    """node_0이 L 이후 문서별 역할을 정리한 절대정보 항목."""

    doc_id: str
    document_name: str
    source_roles: list[str] = field(default_factory=list)
    was_search_candidate: bool = False
    was_actual_tool_read_doc: bool = False
    was_supplied_document_context: bool = False
    was_excluded_document_context: bool = False
    was_unread_candidate: bool = False
    search_candidate_rank: int = 0
    actual_read_rank: int = 0
    supplied_context_rank: int = 0
    excluded_context_rank: int = 0
    char_count: int = 0
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)


@dataclass
class Node0DocumentMaterialPacketFrame:
    """L 이후 node_0이 문서 검색/읽기/context 공급 상태를 한 장부로 묶은 frame."""

    frame_id: str
    turn_id: str
    items: list[Node0DocumentMaterialItem] = field(default_factory=list)
    item_count: int = 0
    search_candidate_count: int = 0
    actual_tool_read_doc_count: int = 0
    supplied_document_context_count: int = 0
    excluded_document_context_count: int = 0
    unread_candidate_count: int = 0
    generated_by: str = "CODE:NODE0_DOCUMENT_MATERIAL_PACKET"
    info_class: str = "absolute_material_index"
    semantic_judgement_status: str = "not_run"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_SCHEMA_NAME
    schema_version: str = NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_SCHEMA_VERSION


def validate_node0_document_material_packet_frame(
    frame: Node0DocumentMaterialPacketFrame,
) -> None:
    """Node0DocumentMaterialPacketFrame이 의미 판단 없이 문서 장부만 담는지 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(
                f"Node0DocumentMaterialPacketFrame.{field_name} must not be empty"
            )
    if frame.schema_name != NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_SCHEMA_NAME:
        raise ValueError(
            "unknown Node0DocumentMaterialPacketFrame schema_name: "
            f"{frame.schema_name}"
        )
    if frame.schema_version != NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_SCHEMA_VERSION:
        raise ValueError(
            "unknown Node0DocumentMaterialPacketFrame schema_version: "
            f"{frame.schema_version}"
        )
    if frame.generated_by != "CODE:NODE0_DOCUMENT_MATERIAL_PACKET":
        raise ValueError("Node0DocumentMaterialPacketFrame.generated_by must reveal node_0 code")
    if frame.info_class != "absolute_material_index":
        raise ValueError(
            "Node0DocumentMaterialPacketFrame.info_class must be absolute_material_index"
        )
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "Node0DocumentMaterialPacketFrame.semantic_judgement_status must be not_run"
        )

    expected_counts = {
        "item_count": len(frame.items),
        "search_candidate_count": sum(1 for item in frame.items if item.was_search_candidate),
        "actual_tool_read_doc_count": sum(
            1 for item in frame.items if item.was_actual_tool_read_doc
        ),
        "supplied_document_context_count": sum(
            1 for item in frame.items if item.was_supplied_document_context
        ),
        "excluded_document_context_count": sum(
            1 for item in frame.items if item.was_excluded_document_context
        ),
        "unread_candidate_count": sum(1 for item in frame.items if item.was_unread_candidate),
    }
    actual_counts = {
        "item_count": frame.item_count,
        "search_candidate_count": frame.search_candidate_count,
        "actual_tool_read_doc_count": frame.actual_tool_read_doc_count,
        "supplied_document_context_count": frame.supplied_document_context_count,
        "excluded_document_context_count": frame.excluded_document_context_count,
        "unread_candidate_count": frame.unread_candidate_count,
    }
    for field_name, value in actual_counts.items():
        if not isinstance(value, int):
            raise TypeError(f"Node0DocumentMaterialPacketFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node0DocumentMaterialPacketFrame.{field_name} must not be negative")
        if value != expected_counts[field_name]:
            raise ValueError(
                f"Node0DocumentMaterialPacketFrame.{field_name} must mirror items"
            )

    seen_doc_ids: set[str] = set()
    for item in frame.items:
        _validate_node0_document_material_item(item)
        if item.doc_id in seen_doc_ids:
            raise ValueError("Node0DocumentMaterialPacketFrame.items must have unique doc_id")
        seen_doc_ids.add(item.doc_id)
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError(
                "Node0DocumentMaterialPacketFrame.source_trace_ids must not contain empty values"
            )
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError(
                "Node0DocumentMaterialPacketFrame.source_data_ids must not contain empty values"
            )


def _validate_node0_document_material_item(item: Node0DocumentMaterialItem) -> None:
    if not item.doc_id:
        raise ValueError("Node0DocumentMaterialItem.doc_id must not be empty")
    if not item.document_name:
        raise ValueError("Node0DocumentMaterialItem.document_name must not be empty")
    for role in item.source_roles:
        if role not in NODE0_DOCUMENT_MATERIAL_ROLES:
            raise ValueError(f"unknown Node0DocumentMaterialItem.source_role: {role}")
    if item.was_search_candidate and "search_candidate" not in item.source_roles:
        raise ValueError("search candidate item must include search_candidate role")
    if item.was_actual_tool_read_doc and "actual_tool_read_doc" not in item.source_roles:
        raise ValueError("actual read item must include actual_tool_read_doc role")
    if item.was_supplied_document_context and "supplied_document_context" not in item.source_roles:
        raise ValueError("supplied context item must include supplied_document_context role")
    if item.was_excluded_document_context and "excluded_document_context" not in item.source_roles:
        raise ValueError("excluded context item must include excluded_document_context role")
    if item.was_unread_candidate and "unread_candidate" not in item.source_roles:
        raise ValueError("unread candidate item must include unread_candidate role")
    if item.was_unread_candidate and not item.was_search_candidate:
        raise ValueError("unread candidate item must also be a search candidate")
    if item.was_unread_candidate and item.was_actual_tool_read_doc:
        raise ValueError("unread candidate item must not be an actual read document")
    for field_name, value in {
        "search_candidate_rank": item.search_candidate_rank,
        "actual_read_rank": item.actual_read_rank,
        "supplied_context_rank": item.supplied_context_rank,
        "excluded_context_rank": item.excluded_context_rank,
        "char_count": item.char_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node0DocumentMaterialItem.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node0DocumentMaterialItem.{field_name} must not be negative")
    for trace_id in item.source_trace_ids:
        if not trace_id:
            raise ValueError("Node0DocumentMaterialItem.source_trace_ids must not contain empty values")
    for data_id in item.source_data_ids:
        if not data_id:
            raise ValueError("Node0DocumentMaterialItem.source_data_ids must not contain empty values")


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
    reportable_code_file_count: int = 0
    raw_code_extract_record_count: int = 0
    empty_code_extract_record_count: int = 0
    # 호환 필드. ORDER_098부터 의미는 reportable_document_count와 같다.
    read_doc_count: int = 0
    document_context_pack_frame_id: str | None = None
    document_context_included_count: int = 0
    document_context_excluded_count: int = 0
    document_context_cutoff_reason: str = ""
    document_material_packet_frame_id: str | None = None
    document_material_item_count: int = 0
    document_material_unread_candidate_count: int = 0
    actual_l_run_count: int = 0
    blocked_same_turn_l_reroute_request_count: int = 0
    same_turn_l_reroute_controller_decisions: list[str] = field(default_factory=list)
    l_internal_revision_count: int = 0
    memory_relevance_selection_frame_id: str | None = None
    memory_relevance_selection_status: str = "not_recorded"
    memory_relevance_candidate_count: int = 0
    memory_relevance_selected_count: int = 0
    memory_relevance_info_class: str = ""
    memory_relevance_generated_by: str = ""
    memory_relevance_llm_call_data_id: str | None = None
    selected_recent_memory_context_frame_id: str | None = None
    selected_recent_memory_context_count: int = 0
    missing_selected_memory_context_count: int = 0
    selected_recent_memory_context_generated_by: str = ""
    selected_recent_memory_context_info_class: str = ""
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
        "reportable_code_file_count": frame.reportable_code_file_count,
        "raw_code_extract_record_count": frame.raw_code_extract_record_count,
        "empty_code_extract_record_count": frame.empty_code_extract_record_count,
        "read_doc_count": frame.read_doc_count,
        "document_context_included_count": frame.document_context_included_count,
        "document_context_excluded_count": frame.document_context_excluded_count,
        "document_material_item_count": frame.document_material_item_count,
        "document_material_unread_candidate_count": frame.document_material_unread_candidate_count,
        "actual_l_run_count": frame.actual_l_run_count,
        "blocked_same_turn_l_reroute_request_count": frame.blocked_same_turn_l_reroute_request_count,
        "l_internal_revision_count": frame.l_internal_revision_count,
        "memory_relevance_candidate_count": frame.memory_relevance_candidate_count,
        "memory_relevance_selected_count": frame.memory_relevance_selected_count,
        "selected_recent_memory_context_count": frame.selected_recent_memory_context_count,
        "missing_selected_memory_context_count": frame.missing_selected_memory_context_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node2HandoffFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node2HandoffFrame.{field_name} must not be negative")
    if frame.read_doc_count != frame.reportable_document_count:
        raise ValueError("Node2HandoffFrame.read_doc_count must mirror reportable_document_count")
    if (
        frame.document_context_pack_frame_id is None
        and frame.raw_document_extract_record_count < frame.reportable_document_count
    ):
        raise ValueError(
            "Node2HandoffFrame.raw_document_extract_record_count must not be smaller than reportable_document_count"
        )
    if frame.empty_document_extract_record_count > frame.raw_document_extract_record_count:
        raise ValueError(
            "Node2HandoffFrame.empty_document_extract_record_count must not exceed raw_document_extract_record_count"
        )
    if frame.empty_code_extract_record_count > frame.raw_code_extract_record_count:
        raise ValueError(
            "Node2HandoffFrame.empty_code_extract_record_count must not exceed raw_code_extract_record_count"
        )
    if frame.document_context_pack_frame_id is not None:
        if not frame.document_context_pack_frame_id:
            raise ValueError("Node2HandoffFrame.document_context_pack_frame_id must not be empty")
        if frame.document_context_pack_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node2HandoffFrame.source_data_ids must include document_context_pack_frame_id"
            )
        if frame.reportable_document_count != frame.document_context_included_count:
            raise ValueError(
                "document context pack handoff reportable count must mirror included count"
            )
    elif frame.document_context_included_count != 0 or frame.document_context_excluded_count != 0:
        raise ValueError("missing document context pack frame requires zero pack counts")
    if frame.document_material_packet_frame_id is not None:
        if not frame.document_material_packet_frame_id:
            raise ValueError("Node2HandoffFrame.document_material_packet_frame_id must not be empty")
        if frame.document_material_packet_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node2HandoffFrame.source_data_ids must include document_material_packet_frame_id"
            )
    elif frame.document_material_item_count != 0 or frame.document_material_unread_candidate_count != 0:
        raise ValueError("missing document material packet frame requires zero material counts")
    if frame.memory_relevance_selection_status not in (
        MEMORY_RELEVANCE_SELECTION_STATUSES | {"not_recorded"}
    ):
        raise ValueError(
            "unknown Node2HandoffFrame.memory_relevance_selection_status: "
            f"{frame.memory_relevance_selection_status}"
        )
    if frame.memory_relevance_selected_count > frame.memory_relevance_candidate_count:
        raise ValueError(
            "Node2HandoffFrame.memory_relevance_selected_count must not exceed candidate count"
        )
    if frame.memory_relevance_selection_frame_id is not None:
        if not frame.memory_relevance_selection_frame_id:
            raise ValueError("Node2HandoffFrame.memory_relevance_selection_frame_id must not be empty")
        if frame.memory_relevance_selection_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node2HandoffFrame.source_data_ids must include memory_relevance_selection_frame_id"
            )
        if frame.memory_relevance_selection_status == "not_recorded":
            raise ValueError("memory relevance frame id requires a recorded selection status")
        if not frame.memory_relevance_info_class:
            raise ValueError("memory relevance frame id requires memory_relevance_info_class")
        if not frame.memory_relevance_generated_by:
            raise ValueError("memory relevance frame id requires memory_relevance_generated_by")
    else:
        if frame.memory_relevance_selection_status != "not_recorded":
            raise ValueError("memory relevance selection status requires a frame id")
        if frame.memory_relevance_candidate_count != 0 or frame.memory_relevance_selected_count != 0:
            raise ValueError("not_recorded memory relevance selection must have zero counts")
    if frame.memory_relevance_selection_status == "selected":
        if frame.memory_relevance_selected_count < 1:
            raise ValueError("selected memory relevance handoff must include selected count")
        if frame.memory_relevance_info_class != "mixed":
            raise ValueError("selected memory relevance handoff must preserve info_class=mixed")
    if frame.memory_relevance_selection_status in {"none_selected", "failed", "not_recorded"}:
        if frame.memory_relevance_selected_count != 0:
            raise ValueError("non-selected memory relevance handoff must not include selected count")
    if frame.memory_relevance_selection_status in {"selected", "none_selected"}:
        if frame.memory_relevance_candidate_count > 0 and not frame.memory_relevance_generated_by.startswith("LLM:"):
            raise ValueError("LLM memory relevance status must preserve generated_by=LLM:*")
    if frame.selected_recent_memory_context_frame_id is not None:
        if not frame.selected_recent_memory_context_frame_id:
            raise ValueError(
                "Node2HandoffFrame.selected_recent_memory_context_frame_id must not be empty"
            )
        if frame.selected_recent_memory_context_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node2HandoffFrame.source_data_ids must include selected recent memory context frame id"
            )
        if frame.selected_recent_memory_context_generated_by != (
            "CODE:SELECTED_RECENT_MEMORY_CONTEXT_BUILDER"
        ):
            raise ValueError("selected recent memory context must reveal code builder")
        if frame.selected_recent_memory_context_info_class != "absolute_copied_context":
            raise ValueError("selected recent memory context must be absolute_copied_context")
    else:
        if frame.selected_recent_memory_context_count != 0:
            raise ValueError("missing selected recent memory context frame id requires zero count")
        if frame.missing_selected_memory_context_count != 0:
            raise ValueError("missing selected recent memory context frame id requires zero missing count")
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
NODE3_DOCUMENT_CONTEXT_PACK_STATUSES = {
    "not_recorded",
    "packed",
    "no_candidates",
}
NODE3_MATERIAL_DELIVERY_POLICY_FRAME_SCHEMA_NAME = "Node3MaterialDeliveryPolicyFrame"
NODE3_MATERIAL_DELIVERY_POLICY_FRAME_SCHEMA_VERSION = "0.1"
NODE3_MATERIAL_DELIVERY_MODES = {
    "raw_document_primary",
    "l3_summary_replaces_raw_context",
    "l3_summary_replaces_raw_context_with_uncertainty",
    "raw_document_fallback_no_l3_summary",
}
NODE3_RAW_DOCUMENT_POLICIES = {
    "preserve_supplied_raw_context",
    "omit_raw_text_from_llm_payload",
    "preserve_raw_context_because_l3_summary_missing",
}
NODE3_L3_SUMMARY_POLICIES = {
    "auxiliary_only",
    "replace_raw_context_with_labeled_l3_summary",
    "replace_raw_context_with_labeled_l3_summary_and_limits",
    "unavailable",
}
NODE3_UNCERTAINTY_POLICIES = {
    "do_not_replace_raw_with_summary",
    "keep_summary_boundary_visible",
    "surface_partial_or_bundle_based_grounding",
    "expose_summary_absence",
}
NODE3_MATERIAL_POLICY_REASON_CODES = {
    "absolute_first_requires_checkable_material",
    "relative_allowed_uses_l3_summary_to_reduce_context_volume",
    "mixed_or_uncertain_uses_l3_summary_with_limit_visibility",
    "l3_summary_unavailable_cannot_replace_raw_context",
}


@dataclass
class Node3BriefDocument:
    """node_3가 읽기 좋은 문서 재료 하나."""

    document_name: str
    char_count: int
    text: str
    source_data_id: str = ""


@dataclass
class Node3ExcludedDocumentContext:
    """node_3에게 읽은 문서가 아니라는 경계와 함께 전달되는 제외 후보."""

    document_name: str
    char_count: int
    selection_basis: str
    exclusion_reason: str
    would_exceed_budget: bool
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
class Node3MemorySelectionMaterial:
    """node_3가 기억 선택 결과를 판단 출처와 함께 볼 수 있게 하는 짧은 재료."""

    selected_memory_count: int = 0
    memory_selection_status: str = "not_recorded"
    memory_selection_reason: str = ""
    memory_selection_info_class: str = ""
    memory_selection_source_mode: str = ""
    memory_selection_claim_alignment: str = ""
    selected_candidate_turn_ids: list[str] = field(default_factory=list)
    source_memory_item_ids: list[str] = field(default_factory=list)
    source_data_id: str = ""
    generated_by: str = ""


@dataclass
class Node3SelectedRecentMemoryContext:
    """node_3에게 넘길 선택된 이전 턴 raw 대화 복사본."""

    source_turn_id: str
    raw_user_text: str
    raw_assistant_text: str
    raw_user_text_chars: int
    raw_assistant_text_chars: int
    raw_user_text_truncated: bool
    raw_assistant_text_truncated: bool
    selection_status: str
    selection_info_class: str
    selection_reason: str
    selection_reason_generated_by: str
    copied_from: str = ""


@dataclass
class Node3L3DocumentSummaryMaterial:
    """node_3가 L3 문서별 요약을 정보 등급 경계와 함께 볼 수 있게 하는 재료."""

    document_name: str
    source_char_count: int
    summary_status: str
    plain_document_summary: str = ""
    plain_summary_info_class: str = "relative"
    plain_summary_source_mode: str = "direct_record"
    plain_summary_claim_alignment: str = "one_document_to_one_summary"
    task_relevant_summary: str = ""
    task_relevant_summary_info_class: str = "mixed"
    task_relevant_summary_source_mode: str = "source_bundle"
    task_relevant_summary_claim_alignment: str = "one_document_plus_task_context"
    summary_limit_note: str = ""
    generated_by: str = ""
    semantic_judgement_status: str = "not_run"
    source_data_id: str = ""


@dataclass
class Node3MaterialDeliveryPolicyFrame:
    """node_2 answer_basis_mode를 node_3 재료 전달 정책으로 고정 변환한 프레임."""

    frame_id: str
    turn_id: str
    answer_basis_mode: str
    material_delivery_mode: str
    raw_document_policy: str
    l3_summary_policy: str
    uncertainty_policy: str
    policy_reason_code: str
    supplied_document_context_count: int = 0
    l3_document_summary_count: int = 0
    llm_raw_document_text_count: int = 0
    llm_l3_summary_context_count: int = 0
    raw_context_replaced_by_summary_count: int = 0
    answer_basis_frame_id: str | None = None
    generated_by: str = "CODE:ANSWER_BASIS_MATERIAL_POLICY"
    info_class: str = "absolute_policy_decision"
    semantic_judgement_status: str = "not_run"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = NODE3_MATERIAL_DELIVERY_POLICY_FRAME_SCHEMA_NAME
    schema_version: str = NODE3_MATERIAL_DELIVERY_POLICY_FRAME_SCHEMA_VERSION


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
class Node3RLoopResultMaterial:
    """node_3가 R route experimental 결과를 과장 없이 볼 수 있게 하는 장부."""

    source_data_id: str
    r_loop_task_status: str
    continuation_status: str
    budget_status: str
    final_information_granularity: str
    summary_depth_used: int
    selected_entry_node_count: int
    inspected_graph_node_count: int
    source_graph_node_count: int
    generated_by: str
    info_class: str
    semantic_judgement_status: str
    attitude_hint: str = "r_loop_partial_or_skeleton_only"


@dataclass
class Node3SourceCodeSymbol:
    """read_code_file 원문에서 code가 문법적으로 확인한 top-level symbol."""

    # 절대 정보: Python AST에서 확인한 이름. 의미 요약이 아니다.
    name: str
    # 절대 정보: function, async_function, class, constant 중 하나.
    symbol_kind: str
    # 절대 정보: 원본 파일 안의 1-based line number.
    line_number: int
    # 절대 정보: 이름이 underscore로 시작하지 않는지에 따른 공개 표지.
    is_public: bool
    # 절대 정보: docstring 존재 여부. docstring 내용 자체는 여기서 요약하지 않는다.
    docstring_present: bool = False


@dataclass
class Node3SourceCodeOutline:
    """node_3가 source-code 답변 coverage를 놓치지 않게 보는 문법 장부."""

    # 절대 정보: read_code_file payload의 file_path.
    file_path: str
    # 절대 정보: 현재 파서는 python만 구조화한다.
    language: str
    # 절대 정보: parsed, unsupported_language, parse_failed 중 하나.
    parse_status: str
    # 절대 정보: 이 outline이 대응하는 read_code_file DataStore record.
    source_data_id: str
    # 절대 정보: top-level symbol 수.
    top_level_symbol_count: int = 0
    # 절대 정보: public symbol 수.
    public_symbol_count: int = 0
    # 절대 정보: public top-level function 이름만 모은 coverage checklist.
    public_function_names: list[str] = field(default_factory=list)
    # 절대 정보: top-level symbol 목록.
    top_level_symbols: list[Node3SourceCodeSymbol] = field(default_factory=list)
    # 절대 정보: 파싱 실패 시 예외 종류만 기록한다. 의미 판단이 아니다.
    parse_error_type: str = ""


@dataclass
class Node3InputBriefFrame:
    """node_3에게 내부 ID 장부 대신 의미 단위 입력을 제공하기 위한 브리프."""

    frame_id: str
    turn_id: str
    user_question: str
    brief_status: str
    handoff_frame_id: str
    read_documents: list[Node3BriefDocument] = field(default_factory=list)
    # 절대 정보: L루프에서 실제 read_doc 계열 도구가 기록한 원문 읽기 수.
    # document_context_pack included count와 섞으면 안 된다.
    actual_tool_read_doc_count: int = 0
    # 절대 정보: 실제 read_doc/read_artifact 도구가 기록한 문서명 목록.
    actual_tool_read_doc_documents: list[str] = field(default_factory=list)
    # 절대 정보: 실제 read_code_file 도구가 기록한 source/config 파일 수.
    actual_tool_read_code_file_count: int = 0
    # 절대 정보: 실제 read_code_file 도구가 기록한 source/config 파일 경로 목록.
    actual_tool_read_code_file_paths: list[str] = field(default_factory=list)
    # 절대 정보: node_3에게 본문 context로 공급된 문서 수.
    supplied_document_context_count: int = 0
    # 절대 정보: node_3에게 본문 context로 공급된 source-code context 수.
    supplied_source_code_context_count: int = 0
    # 절대 정보: read_code_file 원문에서 code가 문법적으로 뽑은 source-code 구조 목록.
    source_code_outlines: list[Node3SourceCodeOutline] = field(default_factory=list)
    document_context_pack_frame_id: str | None = None
    document_context_pack_status: str = "not_recorded"
    excluded_document_contexts: list[Node3ExcludedDocumentContext] = field(default_factory=list)
    document_material_packet_frame_id: str | None = None
    document_material_items: list[Node0DocumentMaterialItem] = field(default_factory=list)
    # 절대 정보: 최종/최신 L3 return summary 기준 search candidate 문서 수.
    final_search_candidate_count: int = 0
    final_search_candidate_documents: list[str] = field(default_factory=list)
    # 절대 정보: L3 initial/revision preserved frame 전체를 훑은 누적 search candidate 문서 수.
    accumulated_search_candidate_count: int = 0
    accumulated_search_candidate_documents: list[str] = field(default_factory=list)
    # 호환용 alias: 현재 의미는 final_search_candidate_*와 같다.
    search_candidate_count: int = 0
    search_candidate_documents: list[str] = field(default_factory=list)
    allowed_claims: list[Node3BriefClaim] = field(default_factory=list)
    memory_selection_material: Node3MemorySelectionMaterial | None = None
    selected_recent_memory_contexts: list[Node3SelectedRecentMemoryContext] = field(default_factory=list)
    l3_document_summaries: list[Node3L3DocumentSummaryMaterial] = field(default_factory=list)
    material_delivery_policy_frame_id: str | None = None
    material_delivery_mode: str = "raw_document_fallback_no_l3_summary"
    raw_document_policy: str = "preserve_raw_context_because_l3_summary_missing"
    l3_summary_policy: str = "unavailable"
    uncertainty_policy: str = "expose_summary_absence"
    material_policy_reason_code: str = "l3_summary_unavailable_cannot_replace_raw_context"
    llm_raw_document_text_count: int = 0
    llm_l3_summary_context_count: int = 0
    raw_context_replaced_by_summary_count: int = 0
    material_policy_generated_by: str = "CODE:ANSWER_BASIS_MATERIAL_POLICY"
    material_policy_info_class: str = "absolute_policy_decision"
    material_policy_semantic_judgement_status: str = "not_run"
    runtime_tasks: list[Node3BriefRuntimeTask] = field(default_factory=list)
    r_loop_result_material: Node3RLoopResultMaterial | None = None
    l_loop_return_summary_frame_id: str | None = None
    l_loop_task_status: str = "not_recorded"
    l_loop_failure_level: str = "none"
    l3_goal_match_status: str = "not_run"
    l3_semantic_goal_match_status: str = "not_run"
    remaining_query_attempts: int = 0
    remaining_read_doc_calls: int = 0
    l_loop_result_attitude_hint: str = "not_recorded"
    answer_basis_frame_id: str | None = None
    answer_basis_mode: str = "mixed_or_uncertain"
    basis_reason_codes: list[str] = field(default_factory=lambda: ["llm_mode_selection_failed"])
    mode_selection_reason: str = "CODE_STATUS:node2_answer_basis_mode_selection_failed"
    mode_selection_reason_info_class: str = "absolute_status"
    evidence_roles: list[Node2EvidenceRole] = field(default_factory=list)
    answer_basis_generated_by: str = "CODE:FALLBACK"
    answer_basis_info_class: str = "absolute_status"
    answer_basis_semantic_judgement_status: str = "failed"
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
    if frame.document_context_pack_status not in NODE3_DOCUMENT_CONTEXT_PACK_STATUSES:
        raise ValueError(
            "unknown Node3InputBriefFrame.document_context_pack_status: "
            f"{frame.document_context_pack_status}"
        )
    if frame.document_context_pack_frame_id is not None:
        if not frame.document_context_pack_frame_id:
            raise ValueError("Node3InputBriefFrame.document_context_pack_frame_id must not be empty")
        if frame.document_context_pack_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include document_context_pack_frame_id"
            )
    elif frame.document_context_pack_status != "not_recorded":
        raise ValueError("document context pack status requires document_context_pack_frame_id")
    if frame.document_material_packet_frame_id is not None:
        if not frame.document_material_packet_frame_id:
            raise ValueError("Node3InputBriefFrame.document_material_packet_frame_id must not be empty")
        if frame.document_material_packet_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include document_material_packet_frame_id"
            )
    for field_name, (count, documents) in {
        "final_search_candidate": (
            frame.final_search_candidate_count,
            frame.final_search_candidate_documents,
        ),
        "accumulated_search_candidate": (
            frame.accumulated_search_candidate_count,
            frame.accumulated_search_candidate_documents,
        ),
        "search_candidate": (
            frame.search_candidate_count,
            frame.search_candidate_documents,
        ),
    }.items():
        if not isinstance(count, int):
            raise TypeError(f"Node3InputBriefFrame.{field_name}_count must be an integer")
        if count < 0:
            raise ValueError(f"Node3InputBriefFrame.{field_name}_count must not be negative")
        if count != len(documents):
            raise ValueError(
                f"Node3InputBriefFrame.{field_name}_count must mirror documents length"
            )
        for document_name in documents:
            if not document_name:
                raise ValueError(
                    f"Node3InputBriefFrame.{field_name}_documents must not contain empty values"
                )
    if frame.search_candidate_count != frame.final_search_candidate_count:
        raise ValueError(
            "Node3InputBriefFrame.search_candidate_count must mirror final_search_candidate_count"
        )
    if frame.search_candidate_documents != frame.final_search_candidate_documents:
        raise ValueError(
            "Node3InputBriefFrame.search_candidate_documents must mirror final_search_candidate_documents"
        )
    for document in frame.read_documents:
        _validate_node3_brief_document(document)
    for outline in frame.source_code_outlines:
        _validate_node3_source_code_outline(outline)
        if outline.source_data_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include source_code_outline source_data_id"
            )
    for field_name, value in {
        "actual_tool_read_doc_count": frame.actual_tool_read_doc_count,
        "actual_tool_read_code_file_count": frame.actual_tool_read_code_file_count,
        "supplied_document_context_count": frame.supplied_document_context_count,
        "supplied_source_code_context_count": frame.supplied_source_code_context_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node3InputBriefFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node3InputBriefFrame.{field_name} must not be negative")
    if frame.supplied_document_context_count != len(frame.read_documents):
        raise ValueError(
            "Node3InputBriefFrame.supplied_document_context_count must mirror read_documents length"
        )
    for document_name in frame.actual_tool_read_doc_documents:
        if not document_name:
            raise ValueError(
                "Node3InputBriefFrame.actual_tool_read_doc_documents must not contain empty values"
            )
    if frame.actual_tool_read_code_file_count != len(frame.actual_tool_read_code_file_paths):
        raise ValueError(
            "Node3InputBriefFrame.actual_tool_read_code_file_count must mirror actual_tool_read_code_file_paths length"
        )
    if frame.supplied_source_code_context_count > frame.supplied_document_context_count:
        raise ValueError(
            "Node3InputBriefFrame.supplied_source_code_context_count must not exceed supplied_document_context_count"
        )
    for file_path in frame.actual_tool_read_code_file_paths:
        if not file_path:
            raise ValueError(
                "Node3InputBriefFrame.actual_tool_read_code_file_paths must not contain empty values"
            )
    for document in frame.excluded_document_contexts:
        _validate_node3_excluded_document_context(document)
    for item in frame.document_material_items:
        _validate_node0_document_material_item(item)
    for claim in frame.allowed_claims:
        _validate_node3_brief_claim(claim)
    if frame.memory_selection_material is not None:
        _validate_node3_memory_selection_material(frame.memory_selection_material)
    for context in frame.selected_recent_memory_contexts:
        _validate_node3_selected_recent_memory_context(context)
    for summary in frame.l3_document_summaries:
        _validate_node3_l3_document_summary_material(summary)
        if summary.source_data_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include L3 document summary source_data_id"
            )
    _validate_node3_material_delivery_fields(frame)
    for runtime_task in frame.runtime_tasks:
        _validate_node3_brief_runtime_task(runtime_task)
    if frame.r_loop_result_material is not None:
        _validate_node3_r_loop_result_material(frame.r_loop_result_material)
        if frame.r_loop_result_material.source_data_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include R loop result source_data_id"
            )
    _validate_node3_l_loop_result_fields(frame)
    _validate_node3_answer_basis_fields(frame)
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


def _validate_node3_source_code_outline(outline: Node3SourceCodeOutline) -> None:
    for field_name, value in {
        "file_path": outline.file_path,
        "language": outline.language,
        "parse_status": outline.parse_status,
        "source_data_id": outline.source_data_id,
    }.items():
        if not value:
            raise ValueError(f"Node3SourceCodeOutline.{field_name} must not be empty")
    if outline.parse_status not in {"parsed", "unsupported_language", "parse_failed"}:
        raise ValueError(f"unknown Node3SourceCodeOutline.parse_status: {outline.parse_status}")
    for field_name, value in {
        "top_level_symbol_count": outline.top_level_symbol_count,
        "public_symbol_count": outline.public_symbol_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node3SourceCodeOutline.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node3SourceCodeOutline.{field_name} must not be negative")
    if outline.top_level_symbol_count != len(outline.top_level_symbols):
        raise ValueError(
            "Node3SourceCodeOutline.top_level_symbol_count must mirror top_level_symbols length"
        )
    if outline.public_symbol_count != sum(1 for symbol in outline.top_level_symbols if symbol.is_public):
        raise ValueError(
            "Node3SourceCodeOutline.public_symbol_count must mirror public top_level_symbols length"
        )
    for name in outline.public_function_names:
        if not name:
            raise ValueError("Node3SourceCodeOutline.public_function_names must not contain empty values")
    symbol_public_functions = [
        symbol.name
        for symbol in outline.top_level_symbols
        if symbol.is_public and symbol.symbol_kind in {"function", "async_function"}
    ]
    if outline.public_function_names != symbol_public_functions:
        raise ValueError(
            "Node3SourceCodeOutline.public_function_names must mirror public function symbols"
        )
    for symbol in outline.top_level_symbols:
        _validate_node3_source_code_symbol(symbol)


def _validate_node3_source_code_symbol(symbol: Node3SourceCodeSymbol) -> None:
    if not symbol.name:
        raise ValueError("Node3SourceCodeSymbol.name must not be empty")
    if symbol.symbol_kind not in {"function", "async_function", "class", "constant"}:
        raise ValueError(f"unknown Node3SourceCodeSymbol.symbol_kind: {symbol.symbol_kind}")
    if not isinstance(symbol.line_number, int):
        raise TypeError("Node3SourceCodeSymbol.line_number must be an integer")
    if symbol.line_number < 1:
        raise ValueError("Node3SourceCodeSymbol.line_number must be positive")
    if not isinstance(symbol.is_public, bool):
        raise TypeError("Node3SourceCodeSymbol.is_public must be a boolean")
    if not isinstance(symbol.docstring_present, bool):
        raise TypeError("Node3SourceCodeSymbol.docstring_present must be a boolean")


def _validate_node3_l_loop_result_fields(frame: Node3InputBriefFrame) -> None:
    if frame.l_loop_return_summary_frame_id is not None:
        if not frame.l_loop_return_summary_frame_id:
            raise ValueError("Node3InputBriefFrame.l_loop_return_summary_frame_id must not be empty")
        if frame.l_loop_return_summary_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include l_loop_return_summary_frame_id"
            )
    if frame.l_loop_task_status not in {"not_recorded", "achieved", "partial", "failed", "unknown"}:
        raise ValueError(f"unknown Node3InputBriefFrame.l_loop_task_status: {frame.l_loop_task_status}")
    if frame.l_loop_failure_level not in {
        "not_recorded",
        "none",
        "l2_retryable",
        "l1_replan_needed",
        "budget_exhausted",
        "give_up_recommended",
        "unknown",
    }:
        raise ValueError(
            f"unknown Node3InputBriefFrame.l_loop_failure_level: {frame.l_loop_failure_level}"
        )
    if frame.l3_goal_match_status not in {
        "matched",
        "partial",
        "missing",
        "not_applicable",
        "not_run",
    }:
        raise ValueError(
            f"unknown Node3InputBriefFrame.l3_goal_match_status: {frame.l3_goal_match_status}"
        )
    if frame.l3_semantic_goal_match_status not in {
        "matched",
        "partial",
        "missing",
        "not_run",
        "not_applicable",
    }:
        raise ValueError(
            "unknown Node3InputBriefFrame.l3_semantic_goal_match_status: "
            f"{frame.l3_semantic_goal_match_status}"
        )
    for field_name, value in {
        "remaining_query_attempts": frame.remaining_query_attempts,
        "remaining_read_doc_calls": frame.remaining_read_doc_calls,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node3InputBriefFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node3InputBriefFrame.{field_name} must not be negative")
    if frame.l_loop_result_attitude_hint not in {
        "not_recorded",
        "l_loop_achieved",
        "l_loop_partial_or_failed",
        "l_loop_budget_exhausted",
        "l_loop_missing_or_uncertain",
    }:
        raise ValueError(
            "unknown Node3InputBriefFrame.l_loop_result_attitude_hint: "
            f"{frame.l_loop_result_attitude_hint}"
        )


def _validate_node3_r_loop_result_material(material: Node3RLoopResultMaterial) -> None:
    for field_name, value in {
        "source_data_id": material.source_data_id,
        "r_loop_task_status": material.r_loop_task_status,
        "continuation_status": material.continuation_status,
        "budget_status": material.budget_status,
        "final_information_granularity": material.final_information_granularity,
        "generated_by": material.generated_by,
        "info_class": material.info_class,
        "semantic_judgement_status": material.semantic_judgement_status,
        "attitude_hint": material.attitude_hint,
    }.items():
        if not value:
            raise ValueError(f"Node3RLoopResultMaterial.{field_name} must not be empty")
    if material.r_loop_task_status not in {"not_run", "sufficient", "partial", "failed"}:
        raise ValueError(
            f"unknown Node3RLoopResultMaterial.r_loop_task_status: {material.r_loop_task_status}"
        )
    if material.continuation_status not in {
        "stop_sufficient",
        "continue_deeper",
        "continue_switch_branch",
        "stop_budget_exhausted",
        "stop_no_actionable_path",
        "stop_failed_final",
        "not_run",
    }:
        raise ValueError(
            f"unknown Node3RLoopResultMaterial.continuation_status: {material.continuation_status}"
        )
    if material.budget_status not in {"within_budget", "exhausted", "not_run"}:
        raise ValueError(
            f"unknown Node3RLoopResultMaterial.budget_status: {material.budget_status}"
        )
    if material.info_class != "absolute":
        raise ValueError("Node3RLoopResultMaterial.info_class must be absolute")
    if material.semantic_judgement_status != "not_run":
        raise ValueError("Node3RLoopResultMaterial.semantic_judgement_status must be not_run")
    if material.attitude_hint not in {
        "not_recorded",
        "r_loop_sufficient",
        "r_loop_partial_or_skeleton_only",
        "r_loop_budget_exhausted",
        "r_loop_failed",
    }:
        raise ValueError(
            f"unknown Node3RLoopResultMaterial.attitude_hint: {material.attitude_hint}"
        )
    for field_name, value in {
        "summary_depth_used": material.summary_depth_used,
        "selected_entry_node_count": material.selected_entry_node_count,
        "inspected_graph_node_count": material.inspected_graph_node_count,
        "source_graph_node_count": material.source_graph_node_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node3RLoopResultMaterial.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node3RLoopResultMaterial.{field_name} must not be negative")


def _validate_node3_l3_document_summary_material(
    material: Node3L3DocumentSummaryMaterial,
) -> None:
    for field_name, value in {
        "document_name": material.document_name,
        "summary_status": material.summary_status,
        "plain_summary_info_class": material.plain_summary_info_class,
        "plain_summary_source_mode": material.plain_summary_source_mode,
        "plain_summary_claim_alignment": material.plain_summary_claim_alignment,
        "task_relevant_summary_info_class": material.task_relevant_summary_info_class,
        "task_relevant_summary_source_mode": material.task_relevant_summary_source_mode,
        "task_relevant_summary_claim_alignment": material.task_relevant_summary_claim_alignment,
        "generated_by": material.generated_by,
        "semantic_judgement_status": material.semantic_judgement_status,
        "source_data_id": material.source_data_id,
    }.items():
        if not value:
            raise ValueError(f"Node3L3DocumentSummaryMaterial.{field_name} must not be empty")
    if not isinstance(material.source_char_count, int):
        raise TypeError("Node3L3DocumentSummaryMaterial.source_char_count must be an integer")
    if material.source_char_count < 0:
        raise ValueError("Node3L3DocumentSummaryMaterial.source_char_count must not be negative")
    if material.summary_status not in L3_DOCUMENT_SUMMARY_STATUSES:
        raise ValueError(
            f"unknown Node3L3DocumentSummaryMaterial.summary_status: {material.summary_status}"
        )
    if material.semantic_judgement_status not in {"ran", "failed"}:
        raise ValueError(
            "unknown Node3L3DocumentSummaryMaterial.semantic_judgement_status: "
            f"{material.semantic_judgement_status}"
        )
    if material.plain_summary_info_class != "relative":
        raise ValueError("plain document summary material must be relative")
    if material.plain_summary_source_mode != "direct_record":
        raise ValueError("plain document summary material must use direct_record")
    if material.plain_summary_claim_alignment != "one_document_to_one_summary":
        raise ValueError(
            "plain document summary material must use one_document_to_one_summary"
        )
    if material.task_relevant_summary_info_class != "mixed":
        raise ValueError("task relevant summary material must be mixed")
    if material.task_relevant_summary_source_mode != "source_bundle":
        raise ValueError("task relevant summary material must use source_bundle")
    if material.task_relevant_summary_claim_alignment != "one_document_plus_task_context":
        raise ValueError(
            "task relevant summary material must use one_document_plus_task_context"
        )
    if material.summary_status == "ran":
        if not material.plain_document_summary.strip():
            raise ValueError("plain_document_summary must not be empty when summary ran")
        if not material.task_relevant_summary.strip():
            raise ValueError("task_relevant_summary must not be empty when summary ran")


def validate_node3_material_delivery_policy_frame(
    frame: Node3MaterialDeliveryPolicyFrame,
) -> None:
    """Node3 material delivery policy가 고정 mapping 결과인지 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "answer_basis_mode": frame.answer_basis_mode,
        "material_delivery_mode": frame.material_delivery_mode,
        "raw_document_policy": frame.raw_document_policy,
        "l3_summary_policy": frame.l3_summary_policy,
        "uncertainty_policy": frame.uncertainty_policy,
        "policy_reason_code": frame.policy_reason_code,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"Node3MaterialDeliveryPolicyFrame.{field_name} must not be empty")
    if frame.schema_name != NODE3_MATERIAL_DELIVERY_POLICY_FRAME_SCHEMA_NAME:
        raise ValueError(
            "unknown Node3MaterialDeliveryPolicyFrame.schema_name: "
            f"{frame.schema_name}"
        )
    if frame.schema_version != NODE3_MATERIAL_DELIVERY_POLICY_FRAME_SCHEMA_VERSION:
        raise ValueError(
            "unknown Node3MaterialDeliveryPolicyFrame.schema_version: "
            f"{frame.schema_version}"
        )
    if frame.answer_basis_mode not in ANSWER_BASIS_MODES:
        raise ValueError(
            f"unknown Node3MaterialDeliveryPolicyFrame.answer_basis_mode: {frame.answer_basis_mode}"
        )
    _validate_node3_material_policy_values(
        material_delivery_mode=frame.material_delivery_mode,
        raw_document_policy=frame.raw_document_policy,
        l3_summary_policy=frame.l3_summary_policy,
        uncertainty_policy=frame.uncertainty_policy,
        policy_reason_code=frame.policy_reason_code,
        supplied_document_context_count=frame.supplied_document_context_count,
        l3_document_summary_count=frame.l3_document_summary_count,
        llm_raw_document_text_count=frame.llm_raw_document_text_count,
        llm_l3_summary_context_count=frame.llm_l3_summary_context_count,
        raw_context_replaced_by_summary_count=frame.raw_context_replaced_by_summary_count,
    )
    if frame.generated_by != "CODE:ANSWER_BASIS_MATERIAL_POLICY":
        raise ValueError("Node3MaterialDeliveryPolicyFrame.generated_by must be CODE policy")
    if frame.info_class != "absolute_policy_decision":
        raise ValueError("Node3MaterialDeliveryPolicyFrame.info_class must be absolute_policy_decision")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "Node3MaterialDeliveryPolicyFrame.semantic_judgement_status must be not_run"
        )
    if frame.answer_basis_frame_id is not None:
        if not frame.answer_basis_frame_id:
            raise ValueError("Node3MaterialDeliveryPolicyFrame.answer_basis_frame_id must not be empty")
        if frame.answer_basis_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node3MaterialDeliveryPolicyFrame.source_data_ids must include answer_basis_frame_id"
            )
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("Node3MaterialDeliveryPolicyFrame.source_data_ids must not contain empty values")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("Node3MaterialDeliveryPolicyFrame.source_trace_ids must not contain empty values")


def _validate_node3_material_delivery_fields(frame: Node3InputBriefFrame) -> None:
    if frame.material_delivery_policy_frame_id is not None:
        if not frame.material_delivery_policy_frame_id:
            raise ValueError("Node3InputBriefFrame.material_delivery_policy_frame_id must not be empty")
        if frame.material_delivery_policy_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include material_delivery_policy_frame_id"
            )
    else:
        for field_name, value in {
            "llm_raw_document_text_count": frame.llm_raw_document_text_count,
            "llm_l3_summary_context_count": frame.llm_l3_summary_context_count,
            "raw_context_replaced_by_summary_count": frame.raw_context_replaced_by_summary_count,
        }.items():
            if not isinstance(value, int):
                raise TypeError(f"Node3InputBriefFrame.{field_name} must be an integer")
            if value < 0:
                raise ValueError(f"Node3InputBriefFrame.{field_name} must not be negative")
        return
    _validate_node3_material_policy_values(
        material_delivery_mode=frame.material_delivery_mode,
        raw_document_policy=frame.raw_document_policy,
        l3_summary_policy=frame.l3_summary_policy,
        uncertainty_policy=frame.uncertainty_policy,
        policy_reason_code=frame.material_policy_reason_code,
        supplied_document_context_count=frame.supplied_document_context_count,
        l3_document_summary_count=len(frame.l3_document_summaries),
        llm_raw_document_text_count=frame.llm_raw_document_text_count,
        llm_l3_summary_context_count=frame.llm_l3_summary_context_count,
        raw_context_replaced_by_summary_count=frame.raw_context_replaced_by_summary_count,
    )
    if frame.material_policy_generated_by != "CODE:ANSWER_BASIS_MATERIAL_POLICY":
        raise ValueError("Node3InputBriefFrame.material_policy_generated_by must be CODE policy")
    if frame.material_policy_info_class != "absolute_policy_decision":
        raise ValueError(
            "Node3InputBriefFrame.material_policy_info_class must be absolute_policy_decision"
        )
    if frame.material_policy_semantic_judgement_status != "not_run":
        raise ValueError(
            "Node3InputBriefFrame.material_policy_semantic_judgement_status must be not_run"
        )


def _validate_node3_material_policy_values(
    *,
    material_delivery_mode: str,
    raw_document_policy: str,
    l3_summary_policy: str,
    uncertainty_policy: str,
    policy_reason_code: str,
    supplied_document_context_count: int,
    l3_document_summary_count: int,
    llm_raw_document_text_count: int,
    llm_l3_summary_context_count: int,
    raw_context_replaced_by_summary_count: int,
) -> None:
    if material_delivery_mode not in NODE3_MATERIAL_DELIVERY_MODES:
        raise ValueError(f"unknown material_delivery_mode: {material_delivery_mode}")
    if raw_document_policy not in NODE3_RAW_DOCUMENT_POLICIES:
        raise ValueError(f"unknown raw_document_policy: {raw_document_policy}")
    if l3_summary_policy not in NODE3_L3_SUMMARY_POLICIES:
        raise ValueError(f"unknown l3_summary_policy: {l3_summary_policy}")
    if uncertainty_policy not in NODE3_UNCERTAINTY_POLICIES:
        raise ValueError(f"unknown uncertainty_policy: {uncertainty_policy}")
    if policy_reason_code not in NODE3_MATERIAL_POLICY_REASON_CODES:
        raise ValueError(f"unknown material policy reason code: {policy_reason_code}")
    for field_name, value in {
        "supplied_document_context_count": supplied_document_context_count,
        "l3_document_summary_count": l3_document_summary_count,
        "llm_raw_document_text_count": llm_raw_document_text_count,
        "llm_l3_summary_context_count": llm_l3_summary_context_count,
        "raw_context_replaced_by_summary_count": raw_context_replaced_by_summary_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{field_name} must not be negative")
    if llm_raw_document_text_count > supplied_document_context_count:
        raise ValueError("llm_raw_document_text_count must not exceed supplied context count")
    if raw_context_replaced_by_summary_count > supplied_document_context_count:
        raise ValueError("raw_context_replaced_by_summary_count must not exceed supplied context count")
    if llm_l3_summary_context_count > l3_document_summary_count:
        raise ValueError("llm_l3_summary_context_count must not exceed L3 summary count")
    if material_delivery_mode == "raw_document_primary":
        if llm_raw_document_text_count != supplied_document_context_count:
            raise ValueError("raw_document_primary must preserve all supplied raw document text")
        if raw_context_replaced_by_summary_count != 0:
            raise ValueError("raw_document_primary must not replace raw context")
    if material_delivery_mode in {
        "l3_summary_replaces_raw_context",
        "l3_summary_replaces_raw_context_with_uncertainty",
    }:
        if l3_document_summary_count < 1:
            raise ValueError("summary replacement requires at least one L3 summary")
        if llm_raw_document_text_count != 0:
            raise ValueError("summary replacement must omit raw document text from LLM payload")
        if raw_context_replaced_by_summary_count != supplied_document_context_count:
            raise ValueError("summary replacement must account for every supplied raw context")
        if llm_l3_summary_context_count != l3_document_summary_count:
            raise ValueError("summary replacement must expose all L3 summary materials")
    if material_delivery_mode == "raw_document_fallback_no_l3_summary":
        if l3_document_summary_count != 0:
            raise ValueError("raw fallback is only valid when L3 summaries are absent")
        if llm_raw_document_text_count != supplied_document_context_count:
            raise ValueError("raw fallback must preserve supplied raw document text")
        if raw_context_replaced_by_summary_count != 0:
            raise ValueError("raw fallback must not replace raw context")


def _validate_node3_answer_basis_fields(frame: Node3InputBriefFrame) -> None:
    if frame.answer_basis_frame_id is not None:
        if not frame.answer_basis_frame_id:
            raise ValueError("Node3InputBriefFrame.answer_basis_frame_id must not be empty")
        if frame.answer_basis_frame_id not in frame.source_data_ids:
            raise ValueError(
                "Node3InputBriefFrame.source_data_ids must include answer_basis_frame_id"
            )
    if frame.answer_basis_mode not in ANSWER_BASIS_MODES:
        raise ValueError(f"unknown Node3InputBriefFrame.answer_basis_mode: {frame.answer_basis_mode}")
    if not frame.basis_reason_codes:
        raise ValueError("Node3InputBriefFrame.basis_reason_codes must not be empty")
    for code in frame.basis_reason_codes:
        if code not in BASIS_REASON_CODES:
            raise ValueError(f"unknown Node3InputBriefFrame.basis_reason_code: {code}")
    if not frame.mode_selection_reason:
        raise ValueError("Node3InputBriefFrame.mode_selection_reason must not be empty")
    if frame.mode_selection_reason_info_class not in ANSWER_BASIS_INFO_CLASSES:
        raise ValueError(
            "unknown Node3InputBriefFrame.mode_selection_reason_info_class: "
            f"{frame.mode_selection_reason_info_class}"
        )
    if not frame.answer_basis_generated_by:
        raise ValueError("Node3InputBriefFrame.answer_basis_generated_by must not be empty")
    if frame.answer_basis_info_class not in ANSWER_BASIS_INFO_CLASSES:
        raise ValueError(
            f"unknown Node3InputBriefFrame.answer_basis_info_class: {frame.answer_basis_info_class}"
        )
    if frame.answer_basis_semantic_judgement_status not in ANSWER_BASIS_SEMANTIC_STATUSES:
        raise ValueError(
            "unknown Node3InputBriefFrame.answer_basis_semantic_judgement_status: "
            f"{frame.answer_basis_semantic_judgement_status}"
        )
    _validate_no_duplicates(
        "Node3InputBriefFrame.basis_reason_codes",
        frame.basis_reason_codes,
    )
    for role in frame.evidence_roles:
        _validate_node2_evidence_role(role, allowed_source_data_ids=frame.source_data_ids)


def _validate_node3_excluded_document_context(document: Node3ExcludedDocumentContext) -> None:
    for field_name, value in {
        "document_name": document.document_name,
        "selection_basis": document.selection_basis,
        "exclusion_reason": document.exclusion_reason,
    }.items():
        if not value:
            raise ValueError(f"Node3ExcludedDocumentContext.{field_name} must not be empty")
    if document.exclusion_reason not in {
        "excluded_due_to_context_budget",
        "excluded_after_strict_rank_cutoff",
        "excluded_not_readable_markdown_document",
    }:
        raise ValueError(
            "unknown Node3ExcludedDocumentContext.exclusion_reason: "
            f"{document.exclusion_reason}"
        )
    if not isinstance(document.char_count, int):
        raise TypeError("Node3ExcludedDocumentContext.char_count must be an integer")
    if document.char_count < 0:
        raise ValueError("Node3ExcludedDocumentContext.char_count must not be negative")


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


def _validate_node3_memory_selection_material(material: Node3MemorySelectionMaterial) -> None:
    if material.memory_selection_status not in (
        MEMORY_RELEVANCE_SELECTION_STATUSES | {"not_recorded"}
    ):
        raise ValueError(
            "unknown Node3MemorySelectionMaterial.memory_selection_status: "
            f"{material.memory_selection_status}"
        )
    if not isinstance(material.selected_memory_count, int):
        raise TypeError("Node3MemorySelectionMaterial.selected_memory_count must be an integer")
    if material.selected_memory_count < 0:
        raise ValueError("Node3MemorySelectionMaterial.selected_memory_count must not be negative")
    _validate_string_list(
        "Node3MemorySelectionMaterial.selected_candidate_turn_ids",
        material.selected_candidate_turn_ids,
    )
    _validate_string_list(
        "Node3MemorySelectionMaterial.source_memory_item_ids",
        material.source_memory_item_ids,
    )
    if material.memory_selection_status == "selected":
        required_text_fields = {
            "memory_selection_reason": material.memory_selection_reason,
            "memory_selection_info_class": material.memory_selection_info_class,
            "memory_selection_source_mode": material.memory_selection_source_mode,
            "memory_selection_claim_alignment": material.memory_selection_claim_alignment,
            "source_data_id": material.source_data_id,
            "generated_by": material.generated_by,
        }
        for field_name, value in required_text_fields.items():
            if not value:
                raise ValueError(f"Node3MemorySelectionMaterial.{field_name} must not be empty")
        if material.memory_selection_info_class != "mixed":
            raise ValueError("selected memory material must preserve info_class=mixed")
        if material.memory_selection_source_mode != "source_bundle":
            raise ValueError("selected memory material must preserve source_mode=source_bundle")
        if material.memory_selection_claim_alignment != "multi_source_bundle":
            raise ValueError(
                "selected memory material must preserve claim_alignment=multi_source_bundle"
            )
        if material.selected_memory_count != len(material.selected_candidate_turn_ids):
            raise ValueError(
                "selected memory material count must match selected_candidate_turn_ids"
            )
        if material.selected_memory_count < 1:
            raise ValueError("selected memory material must include at least one selection")
    else:
        if material.selected_memory_count != 0:
            raise ValueError("non-selected memory material must have selected_memory_count=0")
        if material.selected_candidate_turn_ids:
            raise ValueError("non-selected memory material must not include selected turn ids")
    if material.memory_selection_status != "not_recorded" and not material.source_data_id:
        raise ValueError("recorded memory selection material must include source_data_id")


def _validate_node3_selected_recent_memory_context(
    context: Node3SelectedRecentMemoryContext,
) -> None:
    for field_name, value in {
        "source_turn_id": context.source_turn_id,
        "selection_status": context.selection_status,
        "selection_info_class": context.selection_info_class,
        "selection_reason": context.selection_reason,
        "selection_reason_generated_by": context.selection_reason_generated_by,
    }.items():
        if not value:
            raise ValueError(f"Node3SelectedRecentMemoryContext.{field_name} must not be empty")
    if context.selection_status != "selected":
        raise ValueError("Node3 selected recent memory contexts must come from selected status")
    if context.selection_info_class != "mixed":
        raise ValueError("Node3 selected recent memory context must preserve mixed info_class")
    for field_name, value in {
        "raw_user_text_chars": context.raw_user_text_chars,
        "raw_assistant_text_chars": context.raw_assistant_text_chars,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"Node3SelectedRecentMemoryContext.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"Node3SelectedRecentMemoryContext.{field_name} must be >= 0")
    if len(context.raw_user_text) > context.raw_user_text_chars:
        raise ValueError("Node3 selected recent memory raw_user_text exceeds original chars")
    if len(context.raw_assistant_text) > context.raw_assistant_text_chars:
        raise ValueError("Node3 selected recent memory raw_assistant_text exceeds original chars")
    if not context.raw_user_text_truncated and len(context.raw_user_text) != context.raw_user_text_chars:
        raise ValueError("Node3 untruncated raw_user_text length must match original chars")
    if (
        not context.raw_assistant_text_truncated
        and len(context.raw_assistant_text) != context.raw_assistant_text_chars
    ):
        raise ValueError("Node3 untruncated raw_assistant_text length must match original chars")


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
L_TOOL_SCOPE_FRAME_SCHEMA_NAME = "LToolScopeFrame"
L_TOOL_SCOPE_FRAME_SCHEMA_VERSION = "0.1"
L_TOOL_BUDGET_PARTITION_FRAME_SCHEMA_NAME = "LToolBudgetPartitionFrame"
L_TOOL_BUDGET_PARTITION_FRAME_SCHEMA_VERSION = "0.1"
L_TOOL_SCOPE_MODES = {
    "document_only",
    "code_only",
    "document_and_code",
    "runtime_trace_only",
    "mixed_evidence",
}
L_TOOL_GROUPS = {
    "document_tools",
    "code_inspection_tools",
    "runtime_record_tools",
}
L_REQUIRED_MATERIALS = {
    "order_document",
    "source_code_file",
    "code_search_result",
    "runtime_trace",
    "execution_record",
    "project_document",
}
L_TOOL_SCOPE_INFO_CLASSES = {"mixed", "absolute_status"}
L_TOOL_SCOPE_SEMANTIC_STATUSES = {"ran", "failed"}


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


@dataclass
class LToolScopeFrame:
    """L루프가 L2에 넘기기 전에 이번 턴의 허용 도구 범위를 정한 frame."""

    frame_id: str
    turn_id: str
    tool_scope_mode: str
    allowed_tool_groups: list[str]
    required_materials: list[str]
    scope_reason: str
    scope_reason_info_class: str
    generated_by: str = "LLM:L_TOOL_SCOPE"
    info_class: str = "mixed"
    semantic_judgement_status: str = "ran"
    scope_failure_type: str = "none"
    llm_call_data_id: str | None = None
    prompt_ref: str = ""
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = L_TOOL_SCOPE_FRAME_SCHEMA_NAME
    schema_version: str = L_TOOL_SCOPE_FRAME_SCHEMA_VERSION


def validate_l_tool_scope_frame(frame: LToolScopeFrame) -> None:
    """LToolScopeFrame의 enum, fallback 정직성, source 경계를 검증한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "tool_scope_mode": frame.tool_scope_mode,
        "scope_reason": frame.scope_reason,
        "scope_reason_info_class": frame.scope_reason_info_class,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"LToolScopeFrame.{field_name} must not be empty")
    if frame.schema_name != L_TOOL_SCOPE_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown LToolScopeFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != L_TOOL_SCOPE_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown LToolScopeFrame.schema_version: {frame.schema_version}")
    if frame.tool_scope_mode not in L_TOOL_SCOPE_MODES:
        raise ValueError(f"unknown L tool_scope_mode: {frame.tool_scope_mode}")
    if frame.scope_reason_info_class not in L_TOOL_SCOPE_INFO_CLASSES:
        raise ValueError(
            "unknown LToolScopeFrame.scope_reason_info_class: "
            f"{frame.scope_reason_info_class}"
        )
    if frame.info_class not in L_TOOL_SCOPE_INFO_CLASSES:
        raise ValueError(f"unknown LToolScopeFrame.info_class: {frame.info_class}")
    if frame.semantic_judgement_status not in L_TOOL_SCOPE_SEMANTIC_STATUSES:
        raise ValueError(
            "unknown LToolScopeFrame.semantic_judgement_status: "
            f"{frame.semantic_judgement_status}"
        )
    if not frame.allowed_tool_groups:
        raise ValueError("LToolScopeFrame.allowed_tool_groups must not be empty")
    if not frame.required_materials:
        raise ValueError("LToolScopeFrame.required_materials must not be empty")
    _validate_no_duplicates("LToolScopeFrame.allowed_tool_groups", frame.allowed_tool_groups)
    _validate_no_duplicates("LToolScopeFrame.required_materials", frame.required_materials)
    for group in frame.allowed_tool_groups:
        if group not in L_TOOL_GROUPS:
            raise ValueError(f"unknown L tool group: {group}")
    for material in frame.required_materials:
        if material not in L_REQUIRED_MATERIALS:
            raise ValueError(f"unknown L required material: {material}")
    if frame.llm_call_data_id is not None and not frame.llm_call_data_id:
        raise ValueError("LToolScopeFrame.llm_call_data_id must not be empty")

    if frame.semantic_judgement_status == "failed":
        if frame.generated_by != "CODE:FALLBACK":
            raise ValueError("failed LToolScopeFrame must use generated_by=CODE:FALLBACK")
        if frame.info_class != "absolute_status":
            raise ValueError("failed LToolScopeFrame must use info_class=absolute_status")
        if frame.scope_reason_info_class != "absolute_status":
            raise ValueError(
                "failed LToolScopeFrame must use scope_reason_info_class=absolute_status"
            )
    else:
        if not frame.generated_by.startswith("LLM:"):
            raise ValueError("ran LToolScopeFrame must preserve generated_by=LLM:*")
        if frame.info_class != "mixed":
            raise ValueError("ran LToolScopeFrame must use info_class=mixed")
        if frame.scope_reason_info_class != "mixed":
            raise ValueError("ran LToolScopeFrame reason must use info_class=mixed")

    if frame.tool_scope_mode == "document_only" and frame.allowed_tool_groups != ["document_tools"]:
        raise ValueError("document_only scope must allow only document_tools")
    if frame.tool_scope_mode == "code_only" and frame.allowed_tool_groups != ["code_inspection_tools"]:
        raise ValueError("code_only scope must allow only code_inspection_tools")
    if frame.tool_scope_mode == "document_and_code":
        for group in ("document_tools", "code_inspection_tools"):
            if group not in frame.allowed_tool_groups:
                raise ValueError("document_and_code scope must allow document and code tools")
    if frame.tool_scope_mode == "runtime_trace_only" and frame.allowed_tool_groups != ["runtime_record_tools"]:
        raise ValueError("runtime_trace_only scope must allow only runtime_record_tools")
    if frame.tool_scope_mode == "mixed_evidence" and len(frame.allowed_tool_groups) < 2:
        raise ValueError("mixed_evidence scope must allow at least two tool groups")

    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("LToolScopeFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("LToolScopeFrame.source_data_ids must not contain empty values")


@dataclass
class LToolBudgetPartitionFrame:
    """승인된 L 예산을 tool scope에 따라 도구군별로 나눈 code policy frame."""

    frame_id: str
    turn_id: str
    tool_scope_frame_id: str
    budget_plan_frame_id: str
    tool_scope_mode: str
    allowed_tool_groups: list[str]
    document_tool_call_budget: int = 0
    document_query_budget: int = 0
    document_read_budget: int = 0
    code_tool_call_budget: int = 0
    code_query_budget: int = 0
    code_read_budget: int = 0
    runtime_record_budget: int = 0
    partition_policy_id: str = "l_tool_scope_budget_partition_v0"
    partition_reason: str = ""
    generated_by: str = "CODE:L_TOOL_BUDGET_PARTITION_POLICY"
    info_class: str = "absolute_policy_decision"
    semantic_judgement_status: str = "not_run"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = L_TOOL_BUDGET_PARTITION_FRAME_SCHEMA_NAME
    schema_version: str = L_TOOL_BUDGET_PARTITION_FRAME_SCHEMA_VERSION


def validate_l_tool_budget_partition_frame(frame: LToolBudgetPartitionFrame) -> None:
    """Tool scope에서 파생한 예산 분배 frame의 절대 정책 경계를 검증한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "tool_scope_frame_id": frame.tool_scope_frame_id,
        "budget_plan_frame_id": frame.budget_plan_frame_id,
        "tool_scope_mode": frame.tool_scope_mode,
        "partition_policy_id": frame.partition_policy_id,
        "partition_reason": frame.partition_reason,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"LToolBudgetPartitionFrame.{field_name} must not be empty")
    if frame.schema_name != L_TOOL_BUDGET_PARTITION_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown LToolBudgetPartitionFrame.schema_name: {frame.schema_name}"
        )
    if frame.schema_version != L_TOOL_BUDGET_PARTITION_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown LToolBudgetPartitionFrame.schema_version: {frame.schema_version}"
        )
    if frame.tool_scope_mode not in L_TOOL_SCOPE_MODES:
        raise ValueError(f"unknown budget partition tool_scope_mode: {frame.tool_scope_mode}")
    if frame.generated_by != "CODE:L_TOOL_BUDGET_PARTITION_POLICY":
        raise ValueError("LToolBudgetPartitionFrame.generated_by must reveal code policy")
    if frame.info_class != "absolute_policy_decision":
        raise ValueError("LToolBudgetPartitionFrame.info_class must be absolute_policy_decision")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("LToolBudgetPartitionFrame.semantic_judgement_status must be not_run")
    if frame.tool_scope_frame_id not in frame.source_data_ids:
        raise ValueError(
            "LToolBudgetPartitionFrame.source_data_ids must include tool_scope_frame_id"
        )
    if frame.budget_plan_frame_id not in frame.source_data_ids:
        raise ValueError(
            "LToolBudgetPartitionFrame.source_data_ids must include budget_plan_frame_id"
        )
    _validate_no_duplicates("LToolBudgetPartitionFrame.allowed_tool_groups", frame.allowed_tool_groups)
    for group in frame.allowed_tool_groups:
        if group not in L_TOOL_GROUPS:
            raise ValueError(f"unknown budget partition tool group: {group}")
    for field_name, value in {
        "document_tool_call_budget": frame.document_tool_call_budget,
        "document_query_budget": frame.document_query_budget,
        "document_read_budget": frame.document_read_budget,
        "code_tool_call_budget": frame.code_tool_call_budget,
        "code_query_budget": frame.code_query_budget,
        "code_read_budget": frame.code_read_budget,
        "runtime_record_budget": frame.runtime_record_budget,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"LToolBudgetPartitionFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"LToolBudgetPartitionFrame.{field_name} must not be negative")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError(
                "LToolBudgetPartitionFrame.source_trace_ids must not contain empty values"
            )
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError(
                "LToolBudgetPartitionFrame.source_data_ids must not contain empty values"
            )


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
L2_QUERY_MODES = {
    "embedding_search",
    "exact_artifact_ref",
    "direct_doc_read",
    "code_file_list",
    "code_search",
    "code_file_read",
}
L2_TARGET_TOOL_NAMES = {
    "search_docs",
    "read_artifact",
    "list_code_files",
    "search_code",
    "read_code_file",
}
L2_REVISION_TARGET_TOOL_NAMES = {
    "search_docs",
    "read_artifact",
    "read_doc",
    "list_code_files",
    "search_code",
    "read_code_file",
}
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
    allowed_target_tools = (
        L2_REVISION_TARGET_TOOL_NAMES
        if frame.query_source in {"revision_llm_query_plan", "revision_fallback_query_plan"}
        else L2_TARGET_TOOL_NAMES
    )
    if frame.target_tool_name not in allowed_target_tools:
        raise ValueError(f"unknown L2 target_tool_name: {frame.target_tool_name}")
    if frame.target_tool_name == "read_doc" and frame.query_mode != "direct_doc_read":
        raise ValueError("read_doc L2 query must use direct_doc_read mode")
    if frame.query_mode == "direct_doc_read" and frame.target_tool_name != "read_doc":
        raise ValueError("direct_doc_read mode must target read_doc")
    if frame.target_tool_name == "list_code_files" and frame.query_mode != "code_file_list":
        raise ValueError("list_code_files L2 query must use code_file_list mode")
    if frame.query_mode == "code_file_list" and frame.target_tool_name != "list_code_files":
        raise ValueError("code_file_list mode must target list_code_files")
    if frame.target_tool_name == "search_code" and frame.query_mode != "code_search":
        raise ValueError("search_code L2 query must use code_search mode")
    if frame.query_mode == "code_search" and frame.target_tool_name != "search_code":
        raise ValueError("code_search mode must target search_code")
    if frame.target_tool_name == "read_code_file" and frame.query_mode != "code_file_read":
        raise ValueError("read_code_file L2 query must use code_file_read mode")
    if frame.query_mode == "code_file_read" and frame.target_tool_name != "read_code_file":
        raise ValueError("code_file_read mode must target read_code_file")

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
        _validate_l2_query_plan_candidate(candidate, planner_mode=frame.planner_mode)


def _validate_l2_query_plan_candidate(
    candidate: L2QueryPlanCandidate,
    *,
    planner_mode: str,
) -> None:
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
    allowed_target_tools = (
        L2_REVISION_TARGET_TOOL_NAMES
        if planner_mode in {"revision_llm", "revision_fallback"}
        else L2_TARGET_TOOL_NAMES
    )
    if candidate.target_tool_name not in allowed_target_tools:
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
    # 절대 정보: 아직 읽지 않은 검색 후보 문서 ID 목록. revision read_doc은 이 목록 안에서만 가능하다.
    unread_candidate_doc_ids: list[str] = field(default_factory=list)
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
    for doc_id in frame.unread_candidate_doc_ids:
        if not doc_id:
            raise ValueError("L2RevisionInputFrame.unread_candidate_doc_ids must not contain empty values")
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


EXPLICIT_ARTIFACT_REFERENCE_FRAME_SCHEMA_NAME = "ExplicitArtifactReferenceFrame"
EXPLICIT_ARTIFACT_REFERENCE_FRAME_SCHEMA_VERSION = "0.1"
EXPLICIT_ARTIFACT_RESOLVE_STATUSES = {
    "unique",
    "ambiguous",
    "not_found",
    "invalid_ref",
}


@dataclass
class ExplicitArtifactResolvedReference:
    """사용자 입력 표면에서 추출한 artifact reference와 resolver 결과."""

    raw_ref: str
    normalized_ref: str
    occurrence_index: int
    resolve_status: str
    candidate_count: int
    selected_doc_id: str | None = None
    match_type: str | None = None
    char_count: int = 0
    candidates: list[dict[str, object]] = field(default_factory=list)


@dataclass
class ExplicitArtifactReferenceFrame:
    """명시 artifact reference 추출과 direct resolve 결과를 담는 절대정보 frame."""

    frame_id: str
    turn_id: str
    source_user_text: str
    extracted_reference_count: int
    resolved_references: list[ExplicitArtifactResolvedReference] = field(default_factory=list)
    unique_count: int = 0
    ambiguous_count: int = 0
    not_found_count: int = 0
    invalid_count: int = 0
    generated_by: str = "CODE:EXPLICIT_ARTIFACT_RESOLVER"
    info_class: str = "absolute_resolve_result"
    semantic_judgement_status: str = "not_run"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = EXPLICIT_ARTIFACT_REFERENCE_FRAME_SCHEMA_NAME
    schema_version: str = EXPLICIT_ARTIFACT_REFERENCE_FRAME_SCHEMA_VERSION


def validate_explicit_artifact_reference_frame(
    frame: ExplicitArtifactReferenceFrame,
) -> None:
    """ExplicitArtifactReferenceFrame이 표면 문자열 resolver 결과만 담는지 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"ExplicitArtifactReferenceFrame.{field_name} must not be empty")
    if frame.schema_name != EXPLICIT_ARTIFACT_REFERENCE_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown ExplicitArtifactReferenceFrame.schema_name: {frame.schema_name}"
        )
    if frame.schema_version != EXPLICIT_ARTIFACT_REFERENCE_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown ExplicitArtifactReferenceFrame.schema_version: {frame.schema_version}"
        )
    if frame.generated_by != "CODE:EXPLICIT_ARTIFACT_RESOLVER":
        raise ValueError("ExplicitArtifactReferenceFrame.generated_by must reveal code resolver")
    if frame.info_class != "absolute_resolve_result":
        raise ValueError("ExplicitArtifactReferenceFrame.info_class must be absolute_resolve_result")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("ExplicitArtifactReferenceFrame semantic judgement must not run")
    if frame.extracted_reference_count != len(frame.resolved_references):
        raise ValueError("explicit reference count must match resolved references")
    status_counts = {
        "unique": frame.unique_count,
        "ambiguous": frame.ambiguous_count,
        "not_found": frame.not_found_count,
        "invalid_ref": frame.invalid_count,
    }
    for status, count in status_counts.items():
        if not isinstance(count, int):
            raise TypeError(f"ExplicitArtifactReferenceFrame.{status}_count must be integer")
        if count < 0:
            raise ValueError(f"ExplicitArtifactReferenceFrame.{status}_count must be non-negative")
    actual_counts = {status: 0 for status in EXPLICIT_ARTIFACT_RESOLVE_STATUSES}
    for item in frame.resolved_references:
        _validate_explicit_artifact_resolved_reference(item)
        actual_counts[item.resolve_status] += 1
    if status_counts != actual_counts:
        raise ValueError("explicit reference status counts do not match resolved references")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("ExplicitArtifactReferenceFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("ExplicitArtifactReferenceFrame.source_data_ids must not contain empty values")


def _validate_explicit_artifact_resolved_reference(
    item: ExplicitArtifactResolvedReference,
) -> None:
    for field_name, value in {
        "raw_ref": item.raw_ref,
        "normalized_ref": item.normalized_ref,
        "resolve_status": item.resolve_status,
    }.items():
        if not value:
            raise ValueError(f"ExplicitArtifactResolvedReference.{field_name} must not be empty")
    if item.resolve_status not in EXPLICIT_ARTIFACT_RESOLVE_STATUSES:
        raise ValueError(f"unknown explicit artifact resolve status: {item.resolve_status}")
    if item.occurrence_index < 1:
        raise ValueError("ExplicitArtifactResolvedReference.occurrence_index must be positive")
    if item.candidate_count < 0:
        raise ValueError("ExplicitArtifactResolvedReference.candidate_count must be non-negative")
    if item.char_count < 0:
        raise ValueError("ExplicitArtifactResolvedReference.char_count must be non-negative")
    if item.resolve_status == "unique":
        if not item.selected_doc_id:
            raise ValueError("unique explicit reference must include selected_doc_id")
        if not item.match_type:
            raise ValueError("unique explicit reference must include match_type")
        if item.candidate_count != 1:
            raise ValueError("unique explicit reference candidate_count must be 1")
    else:
        if item.selected_doc_id is not None:
            raise ValueError("non-unique explicit reference must not include selected_doc_id")


DOCUMENT_CONTEXT_PACK_FRAME_SCHEMA_NAME = "DocumentContextPackFrame"
DOCUMENT_CONTEXT_PACK_FRAME_SCHEMA_VERSION = "0.1"
DOCUMENT_CONTEXT_EXCLUSION_REASONS = {
    "excluded_due_to_context_budget",
    "excluded_after_strict_rank_cutoff",
    "excluded_not_readable_markdown_document",
}
DOCUMENT_CONTEXT_BUDGET_UNITS = {"chars"}


@dataclass
class DocumentContextPackIncludedDocument:
    """node_3에 전체 원문으로 공급된 문서 하나."""

    doc_id: str
    document_name: str
    char_count: int
    rank_index: int
    selection_basis: str
    text: str
    source_data_id: str


@dataclass
class DocumentContextPackExcludedDocument:
    """후보였지만 whole-document packing 정책 때문에 공급되지 않은 문서."""

    doc_id: str
    document_name: str
    char_count: int
    rank_index: int
    selection_basis: str
    exclusion_reason: str
    would_exceed_budget: bool
    source_data_id: str


@dataclass
class DocumentContextPackFrame:
    """node_3 read_documents에 넣을 whole-document context packing 결과."""

    frame_id: str
    turn_id: str
    max_document_context_chars: int
    budget_unit: str
    whole_document_only: bool
    strict_rank_order: bool
    included_documents: list[DocumentContextPackIncludedDocument] = field(default_factory=list)
    excluded_documents: list[DocumentContextPackExcludedDocument] = field(default_factory=list)
    included_document_count: int = 0
    excluded_document_count: int = 0
    included_total_chars: int = 0
    cutoff_reason: str = "none"
    source_query_frame_ids: list[str] = field(default_factory=list)
    source_search_result_data_ids: list[str] = field(default_factory=list)
    source_explicit_reference_data_id: str | None = None
    generated_by: str = "CODE:DOCUMENT_CONTEXT_PACKER"
    info_class: str = "absolute_context_packing_result"
    semantic_judgement_status: str = "not_run"
    source_trace_ids: list[str] = field(default_factory=list)
    source_data_ids: list[str] = field(default_factory=list)
    schema_name: str = DOCUMENT_CONTEXT_PACK_FRAME_SCHEMA_NAME
    schema_version: str = DOCUMENT_CONTEXT_PACK_FRAME_SCHEMA_VERSION


def validate_document_context_pack_frame(frame: DocumentContextPackFrame) -> None:
    """DocumentContextPackFrame이 whole-document/strict rank 정책을 지키는지 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "budget_unit": frame.budget_unit,
        "cutoff_reason": frame.cutoff_reason,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"DocumentContextPackFrame.{field_name} must not be empty")
    if frame.schema_name != DOCUMENT_CONTEXT_PACK_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown DocumentContextPackFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != DOCUMENT_CONTEXT_PACK_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown DocumentContextPackFrame.schema_version: {frame.schema_version}"
        )
    if frame.budget_unit not in DOCUMENT_CONTEXT_BUDGET_UNITS:
        raise ValueError(f"unknown DocumentContextPackFrame.budget_unit: {frame.budget_unit}")
    if frame.max_document_context_chars < 1:
        raise ValueError("DocumentContextPackFrame.max_document_context_chars must be positive")
    if frame.whole_document_only is not True:
        raise ValueError("DocumentContextPackFrame.whole_document_only must be true")
    if frame.strict_rank_order is not True:
        raise ValueError("DocumentContextPackFrame.strict_rank_order must be true")
    if frame.generated_by != "CODE:DOCUMENT_CONTEXT_PACKER":
        raise ValueError("DocumentContextPackFrame.generated_by must reveal code packer")
    if frame.info_class != "absolute_context_packing_result":
        raise ValueError("DocumentContextPackFrame.info_class must be absolute_context_packing_result")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError("DocumentContextPackFrame semantic judgement must not run")
    if frame.included_document_count != len(frame.included_documents):
        raise ValueError("included_document_count must match included_documents")
    if frame.excluded_document_count != len(frame.excluded_documents):
        raise ValueError("excluded_document_count must match excluded_documents")
    if frame.included_total_chars != sum(item.char_count for item in frame.included_documents):
        raise ValueError("included_total_chars must match included document char counts")
    if frame.included_total_chars > frame.max_document_context_chars:
        raise ValueError("included_total_chars must not exceed max_document_context_chars")
    if frame.source_explicit_reference_data_id and (
        frame.source_explicit_reference_data_id not in frame.source_data_ids
    ):
        raise ValueError("source_data_ids must include source_explicit_reference_data_id")
    for data_id in frame.source_query_frame_ids:
        if not data_id:
            raise ValueError("DocumentContextPackFrame.source_query_frame_ids must not contain empty values")
    for data_id in frame.source_search_result_data_ids:
        if not data_id:
            raise ValueError(
                "DocumentContextPackFrame.source_search_result_data_ids must not contain empty values"
            )
    for item in frame.included_documents:
        _validate_document_context_pack_included_document(item)
    cutoff_seen = False
    for item in frame.excluded_documents:
        _validate_document_context_pack_excluded_document(item)
        if item.exclusion_reason == "excluded_due_to_context_budget":
            cutoff_seen = True
        elif item.exclusion_reason == "excluded_after_strict_rank_cutoff" and not cutoff_seen:
            raise ValueError("strict rank cutoff exclusion must follow a budget exclusion")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("DocumentContextPackFrame.source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("DocumentContextPackFrame.source_data_ids must not contain empty values")


def _validate_document_context_pack_included_document(
    item: DocumentContextPackIncludedDocument,
) -> None:
    for field_name, value in {
        "doc_id": item.doc_id,
        "document_name": item.document_name,
        "selection_basis": item.selection_basis,
        "text": item.text,
        "source_data_id": item.source_data_id,
    }.items():
        if not value:
            raise ValueError(f"DocumentContextPackIncludedDocument.{field_name} must not be empty")
    if item.rank_index < 1:
        raise ValueError("DocumentContextPackIncludedDocument.rank_index must be positive")
    if item.char_count < 0:
        raise ValueError("DocumentContextPackIncludedDocument.char_count must be non-negative")
    if len(item.text) != item.char_count:
        raise ValueError("included document text length must match char_count")


def _validate_document_context_pack_excluded_document(
    item: DocumentContextPackExcludedDocument,
) -> None:
    for field_name, value in {
        "doc_id": item.doc_id,
        "document_name": item.document_name,
        "selection_basis": item.selection_basis,
        "exclusion_reason": item.exclusion_reason,
        "source_data_id": item.source_data_id,
    }.items():
        if not value:
            raise ValueError(f"DocumentContextPackExcludedDocument.{field_name} must not be empty")
    if item.rank_index < 1:
        raise ValueError("DocumentContextPackExcludedDocument.rank_index must be positive")
    if item.char_count < 0:
        raise ValueError("DocumentContextPackExcludedDocument.char_count must be non-negative")
    if item.exclusion_reason not in DOCUMENT_CONTEXT_EXCLUSION_REASONS:
        raise ValueError(f"unknown document context exclusion reason: {item.exclusion_reason}")
    if item.exclusion_reason == "excluded_due_to_context_budget" and not item.would_exceed_budget:
        raise ValueError("budget exclusion must mark would_exceed_budget=true")


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
TOOL_RESULT_DISTILLATION_TOOL_NAMES = {
    "search_docs",
    "read_doc",
    "read_artifact",
    "list_code_files",
    "search_code",
    "read_code_file",
}
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
    "continue_code_search",
    "list_code_files",
    "read_code_file",
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
    if frame.decision == "continue_code_search" and frame.selected_tool_name != "search_code":
        raise ValueError("continue_code_search must select search_code")
    if frame.decision == "continue_code_search" and frame.query_text is None:
        raise ValueError("continue_code_search must include query_text")
    if frame.decision == "list_code_files" and frame.selected_tool_name != "list_code_files":
        raise ValueError("list_code_files must select list_code_files")
    if frame.decision == "read_code_file" and frame.selected_tool_name != "read_code_file":
        raise ValueError("read_code_file must select read_code_file")
    if frame.decision == "read_code_file" and frame.query_text is None:
        raise ValueError("read_code_file must include query_text")
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
    # 절대 정보: 실제 read_code_file로 읽은 source/config 파일 경로 목록.
    read_code_file_paths: list[str] = field(default_factory=list)
    # 절대 정보: read_code_file 성공 기록 수. read_doc 수와 섞지 않는다.
    actual_read_code_file_count: int = 0
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
        "actual_read_code_file_count": frame.actual_read_code_file_count,
    }.items():
        if not isinstance(value, int):
            raise TypeError(f"LLoopReturnSummaryFrame.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"LLoopReturnSummaryFrame.{field_name} must not be negative")

    for doc_id in frame.read_doc_ids:
        if not doc_id:
            raise ValueError("LLoopReturnSummaryFrame.read_doc_ids must not contain empty values")
    if frame.actual_read_code_file_count != len(frame.read_code_file_paths):
        raise ValueError(
            "LLoopReturnSummaryFrame.actual_read_code_file_count must mirror read_code_file_paths length"
        )
    for file_path in frame.read_code_file_paths:
        if not file_path:
            raise ValueError("LLoopReturnSummaryFrame.read_code_file_paths must not contain empty values")
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
L3_PER_DOCUMENT_SUMMARY_FRAME_SCHEMA_NAME = "L3PerDocumentSummaryFrame"
L3_PER_DOCUMENT_SUMMARY_FRAME_SCHEMA_VERSION = "0.1"
L3_DOCUMENT_SUMMARY_STATUSES = {"ran", "failed"}
L3_DOCUMENT_SUMMARY_FAILURE_TYPES = {
    "none",
    "parse_failed",
    "schema_failed",
    "adapter_failed",
    "timeout",
    "unknown",
}


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
    # 절대 정보: 이번 L루프에서 실제 read_code_file로 읽은 source/config 파일 경로 목록.
    read_code_file_paths: list[str] = field(default_factory=list)
    # 절대 정보: read_code_file 성공 기록 수. read_doc 수와 섞지 않는다.
    actual_read_code_file_count: int = 0
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
    if not isinstance(frame.actual_read_code_file_count, int):
        raise TypeError("L3AchievementFrame.actual_read_code_file_count must be an integer")
    if frame.actual_read_code_file_count < 0:
        raise ValueError("L3AchievementFrame.actual_read_code_file_count must not be negative")
    if frame.actual_read_code_file_count != len(frame.read_code_file_paths):
        raise ValueError(
            "L3AchievementFrame.actual_read_code_file_count must mirror read_code_file_paths length"
        )

    for doc_id in frame.read_doc_ids:
        if not doc_id:
            raise ValueError("L3AchievementFrame.read_doc_ids must not contain empty values")
    for file_path in frame.read_code_file_paths:
        if not file_path:
            raise ValueError("L3AchievementFrame.read_code_file_paths must not contain empty values")
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
class L3PerDocumentSummaryFrame:
    """L3가 실제 읽은 문서 하나에 대해 남기는 문서별 의미 요약 프레임."""

    # 절대 정보: DataStore에 저장될 summary frame data_id와 같은 값.
    frame_id: str
    # 절대 정보: 이 요약 프레임이 만들어진 사용자 턴 ID.
    turn_id: str
    # 절대 정보: 요약 대상이 된 원본 document extract record ID.
    source_document_data_id: str
    # 절대 정보: 원본 document extract payload의 doc_id.
    source_doc_id: str
    # 절대 정보/표시명: doc_id에서 만든 문서명.
    source_document_name: str
    # 절대 정보: 원본 문서 text 길이.
    source_char_count: int
    # 절대 정보: LLM 요약 실행 상태.
    summary_status: str
    # 상대 정보: 원본 문서 하나에만 대응하는 담백 요약.
    plain_document_summary: str = ""
    # 절대 정보: 담백 요약의 정보 분류 라벨.
    plain_summary_info_class: str = "relative"
    # 절대 정보: 담백 요약이 직접 record 하나에 붙어 있다는 source mode.
    plain_summary_source_mode: str = "direct_record"
    # 절대 정보: 담백 요약과 원본 문서의 대응 방식.
    plain_summary_claim_alignment: str = "one_document_to_one_summary"
    # 절대 정보: 담백 요약이 직접 대응하는 원본 record ID.
    plain_summary_source_data_id: str = ""
    # 혼합 정보: 현재 질문/L1 목표와 문서 원문을 함께 본 상황 맞춤 요약.
    task_relevant_summary: str = ""
    # 절대 정보: 상황 요약의 정보 분류 라벨.
    task_relevant_summary_info_class: str = "mixed"
    # 절대 정보: 상황 요약이 source bundle에 기대고 있다는 source mode.
    task_relevant_summary_source_mode: str = "source_bundle"
    # 절대 정보: 상황 요약과 source bundle의 대응 방식.
    task_relevant_summary_claim_alignment: str = "one_document_plus_task_context"
    # 절대 정보: 상황 요약이 참조한 source bundle record ID 목록.
    task_relevant_summary_source_data_ids: list[str] = field(default_factory=list)
    # 상대/혼합 정보의 한계 메모. LLM이 요약 범위를 드러낼 때만 채운다.
    summary_limit_note: str = ""
    # 절대 정보: 요약을 생성한 실행자.
    generated_by: str = "LLM:unknown"
    # 절대 정보: LLM 의미 생성 실행 상태.
    semantic_judgement_status: str = "failed"
    # 절대 정보: 실패 유형. 성공이면 none.
    summary_failure_type: str = "unknown"
    # 절대 정보: 이 요약을 만든 LLM call record ID.
    llm_call_data_id: str | None = None
    # 절대 정보: 사용한 prompt 파일.
    prompt_ref: str = ""
    # 절대 정보: 근거 trace ID 목록.
    source_trace_ids: list[str] = field(default_factory=list)
    # 절대 정보: 근거 DataStore record ID 목록.
    source_data_ids: list[str] = field(default_factory=list)
    # 절대 정보: 적용된 스키마 이름.
    schema_name: str = L3_PER_DOCUMENT_SUMMARY_FRAME_SCHEMA_NAME
    # 절대 정보: 적용된 스키마 버전.
    schema_version: str = L3_PER_DOCUMENT_SUMMARY_FRAME_SCHEMA_VERSION


def validate_l3_per_document_summary_frame(frame: L3PerDocumentSummaryFrame) -> None:
    """L3 문서별 요약이 정보 등급/출처 경계를 지키는지 확인한다."""

    for field_name, value in {
        "frame_id": frame.frame_id,
        "turn_id": frame.turn_id,
        "source_document_data_id": frame.source_document_data_id,
        "source_doc_id": frame.source_doc_id,
        "source_document_name": frame.source_document_name,
        "summary_status": frame.summary_status,
        "plain_summary_info_class": frame.plain_summary_info_class,
        "plain_summary_source_mode": frame.plain_summary_source_mode,
        "plain_summary_claim_alignment": frame.plain_summary_claim_alignment,
        "plain_summary_source_data_id": frame.plain_summary_source_data_id,
        "task_relevant_summary_info_class": frame.task_relevant_summary_info_class,
        "task_relevant_summary_source_mode": frame.task_relevant_summary_source_mode,
        "task_relevant_summary_claim_alignment": frame.task_relevant_summary_claim_alignment,
        "generated_by": frame.generated_by,
        "semantic_judgement_status": frame.semantic_judgement_status,
        "summary_failure_type": frame.summary_failure_type,
        "prompt_ref": frame.prompt_ref,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"L3PerDocumentSummaryFrame.{field_name} must not be empty")

    if frame.schema_name != L3_PER_DOCUMENT_SUMMARY_FRAME_SCHEMA_NAME:
        raise ValueError(
            f"unknown L3 per-document summary schema_name: {frame.schema_name}"
        )
    if frame.schema_version != L3_PER_DOCUMENT_SUMMARY_FRAME_SCHEMA_VERSION:
        raise ValueError(
            f"unknown L3 per-document summary schema_version: {frame.schema_version}"
        )
    if not isinstance(frame.source_char_count, int):
        raise TypeError("L3PerDocumentSummaryFrame.source_char_count must be an integer")
    if frame.source_char_count < 0:
        raise ValueError("L3PerDocumentSummaryFrame.source_char_count must not be negative")
    if frame.summary_status not in L3_DOCUMENT_SUMMARY_STATUSES:
        raise ValueError(f"unknown L3 summary_status: {frame.summary_status}")
    if frame.summary_failure_type not in L3_DOCUMENT_SUMMARY_FAILURE_TYPES:
        raise ValueError(f"unknown L3 summary_failure_type: {frame.summary_failure_type}")
    if frame.summary_status == "ran":
        if frame.semantic_judgement_status != "ran":
            raise ValueError("successful L3 summary must have semantic_judgement_status=ran")
        if frame.summary_failure_type != "none":
            raise ValueError("successful L3 summary must have summary_failure_type=none")
        if not frame.plain_document_summary.strip():
            raise ValueError("plain_document_summary must not be empty when summary ran")
        if not frame.task_relevant_summary.strip():
            raise ValueError("task_relevant_summary must not be empty when summary ran")
    else:
        if frame.semantic_judgement_status != "failed":
            raise ValueError("failed L3 summary must have semantic_judgement_status=failed")
        if frame.summary_failure_type == "none":
            raise ValueError("failed L3 summary must include failure type")

    if frame.plain_summary_info_class != "relative":
        raise ValueError("plain_document_summary must be marked relative")
    if frame.plain_summary_source_mode != "direct_record":
        raise ValueError("plain_document_summary must use direct_record")
    if frame.plain_summary_claim_alignment != "one_document_to_one_summary":
        raise ValueError("plain_document_summary must use one_document_to_one_summary")
    if frame.plain_summary_source_data_id != frame.source_document_data_id:
        raise ValueError("plain summary source must be the source document data_id")

    if frame.task_relevant_summary_info_class != "mixed":
        raise ValueError("task_relevant_summary must be marked mixed")
    if frame.task_relevant_summary_source_mode != "source_bundle":
        raise ValueError("task_relevant_summary must use source_bundle")
    if frame.task_relevant_summary_claim_alignment != "one_document_plus_task_context":
        raise ValueError("task_relevant_summary must use one_document_plus_task_context")
    if len(frame.task_relevant_summary_source_data_ids) < 2:
        raise ValueError("task_relevant_summary_source_data_ids must contain a source bundle")

    if frame.source_document_data_id not in frame.source_data_ids:
        raise ValueError("L3 summary source_data_ids must include source_document_data_id")
    for data_id in frame.task_relevant_summary_source_data_ids:
        if not data_id:
            raise ValueError(
                "L3 summary task_relevant_summary_source_data_ids must not contain empty values"
            )
        if data_id not in frame.source_data_ids:
            raise ValueError(
                "L3 summary source_data_ids must include every task_relevant source data_id"
            )
    if frame.llm_call_data_id is not None:
        if not frame.llm_call_data_id:
            raise ValueError("L3 summary llm_call_data_id must not be empty")
        if frame.llm_call_data_id not in frame.source_data_ids:
            raise ValueError("L3 summary source_data_ids must include llm_call_data_id")
    for trace_id in frame.source_trace_ids:
        if not trace_id:
            raise ValueError("L3 summary source_trace_ids must not contain empty values")
    for data_id in frame.source_data_ids:
        if not data_id:
            raise ValueError("L3 summary source_data_ids must not contain empty values")


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
