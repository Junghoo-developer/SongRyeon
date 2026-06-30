from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    LLoopReturnSummaryFrame,
    MemoryItem,
    MemoryPacketFrom0,
    MemoryPacketPayload,
    MemoryRelevanceCandidateFrame,
    Node0DocumentMaterialItem,
    Node0DocumentMaterialPacketFrame,
    RawMemoryCompressionCandidateFrame,
    ZeroState,
    validate_l_loop_return_summary_frame,
    validate_memory_packet_payload,
    validate_node0_document_material_packet_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds


# 학습 메모: 이 값은 장기기억 크기가 아니라, 0이 이번 턴에 넘길 "최근 턴 색인 카드" 개수다.
RECENT_TURN_CAPSULE_READ_WINDOW = 3
# 학습 메모: 이 값은 장기기억 크기가 아니라, 최근 원문 대화와 capsule 좌표를 대응시켜
# 이번 턴의 pre_route_report packet에 복사할 후보 창 크기다.
RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW = 8
# 학습 메모: 관련성 후보 창은 ORDER_101의 raw-capsule alignment 창을 그대로 따른다.
# 여기서 후보는 "판단 결과"가 아니라 "나중에 판단할 수 있는 좌표"다.
RECENT_MEMORY_RELEVANCE_CANDIDATE_WINDOW = RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW
# 학습 메모: 아래 네 값은 원문 기억을 삭제하는 보관 정책이 아니라,
# node_5가 나중에 압축할 후보 좌표를 나누는 node_0 공급 정책이다.
RAW_MEMORY_WINDOW_POLICY_ID = "RAW_MEMORY_WINDOW_POLICY_V0"
RECENT_RAW_CONVERSATION_MAX_WINDOW = 8
RECENT_RAW_CONVERSATION_MIN_GUARANTEE = 3
RAW_MEMORY_POST_COMPRESSION_KEEP = 5
RAW_MEMORY_COMPRESSION_BATCH_SIZE = 4
L3_CONTINUATION_SUMMARY_MODE = "l3_continuation_summary_for_L2"
L_LOOP_RETURN_SUMMARY_FRAME_DATA_ID = "L:return_summary_frame"
NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID = "node_0:document_material_packet_frame"

NODE_0_MODES = {
    "pre_route_report",
    "targeted_memory_supply",
    "loop_return_summary",
    "final_trace_for_2",
    L3_CONTINUATION_SUMMARY_MODE,
}


def memory_packet_data_id(target: str, mode: str, packet_id_suffix: str | None = None) -> str:
    """memory packet DataStore ID를 만든다."""

    base_id = f"memory_packet:{target}:{mode}"
    if packet_id_suffix is None:
        return base_id
    return f"{base_id}:{packet_id_suffix}"


def document_material_packet_frame_data_id(*, id_namespace: LRunIds | None) -> str:
    """L 이후 node_0 문서 장부 frame ID를 만든다."""

    if id_namespace is None:
        return NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID
    return id_namespace.scoped_data_id(NODE0_DOCUMENT_MATERIAL_PACKET_FRAME_DATA_ID)


def supply_memory(
    *,
    target: str,
    mode: str,
    zero_state: ZeroState,
    trace_store: TraceStore,
    turn_id: str,
    insufficient_signal_id: str | None = None,
) -> MemoryPacketFrom0:
    """0 기억공급관의 규칙 기반 기억 패킷을 만든다."""

    if mode not in NODE_0_MODES:
        raise ValueError(f"unknown node_0 mode: {mode}")

    # 지금 단계의 0은 내용을 요약하지 않는다.
    # 대신 현재 턴 trace ID와 0.state의 trace ID를 근거 목록으로 공급한다.
    trace_ids = [event.event_id for event in trace_store.events_for_turn(turn_id)]
    for trace_id in zero_state.current_turn_trace_ids:
        if trace_id not in trace_ids:
            trace_ids.append(trace_id)

    return MemoryPacketFrom0(
        target=target,
        trace_evidence_ids=trace_ids,
        insufficient_signal_id=insufficient_signal_id,
    )


def build_trace_evidence_memory_item(
    *,
    packet_id: str,
    packet: MemoryPacketFrom0,
    source_data_ids: list[str] | None = None,
) -> MemoryItem:
    """기본 trace evidence item을 만든다."""

    return MemoryItem(
        item_id=f"{packet_id}:trace_evidence",
        item_type="trace_evidence",
        text="CODE_STATUS:trace_evidence_ids_supplied",
        source_trace_ids=packet.trace_evidence_ids,
        source_data_ids=source_data_ids or [],
    )


def build_previous_turn_capsule_index_items(
    *,
    zero_state: ZeroState,
    packet_id: str,
    read_window: int = RECENT_TURN_CAPSULE_READ_WINDOW,
) -> list[MemoryItem]:
    """최근 TurnStateCapsule의 구조화 필드만 복사해 pre-route item으로 만든다."""

    if read_window <= 0:
        return []

    # 학습 메모: 여기서 하는 일은 capsule 내용을 요약하는 것이 아니다.
    # turn_id와 trace 좌표 같은 절대 필드만 COPIED_FIELDS로 복사한다.
    recent_capsules = zero_state.previous_turn_capsules[-read_window:]
    items: list[MemoryItem] = []
    for index, capsule in enumerate(recent_capsules, start=1):
        user_input_trace_id = _existing_capsule_trace_id(
            capsule.trace_event_ids,
            capsule.user_input_trace_id,
        )
        final_response_trace_id = _existing_capsule_trace_id(
            capsule.trace_event_ids,
            capsule.final_response_trace_id,
        )
        items.append(
            MemoryItem(
                item_id=f"{packet_id}:previous_turn_capsule_index:{index:03d}",
                item_type="previous_turn_capsule_index",
                text=(
                    "COPIED_FIELDS:"
                    f"turn_id={capsule.turn_id};"
                    f"trace_count={len(capsule.trace_event_ids)};"
                    f"movement_count={len(capsule.node_movements)};"
                    f"user_input_trace_id={user_input_trace_id or ''};"
                    f"final_response_trace_id={final_response_trace_id or ''}"
                ),
                source_trace_ids=_unique_strings(
                    [user_input_trace_id, final_response_trace_id]
                ),
                source_data_ids=[],
            )
        )
    return items


def build_recent_raw_conversation_capsule_alignment_items(
    *,
    zero_state: ZeroState,
    packet_id: str,
    read_window: int = RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW,
) -> list[MemoryItem]:
    """최근 raw conversation과 TurnStateCapsule을 turn_id 기준으로만 대응시킨다."""

    if read_window <= 0:
        return []

    capsules_by_turn_id = {
        capsule.turn_id: capsule
        for capsule in zero_state.previous_turn_capsules
    }
    recent_raw_entries = zero_state.recent_raw_conversation[-read_window:]

    items: list[MemoryItem] = []
    for raw_entry in recent_raw_entries:
        turn_id = _raw_conversation_text(raw_entry, "turn_id")
        if turn_id is None:
            continue
        capsule = capsules_by_turn_id.get(turn_id)
        if capsule is None:
            continue

        raw_user_text = _raw_conversation_text(raw_entry, "user")
        raw_assistant_text = _raw_conversation_text(raw_entry, "assistant")
        user_input_trace_id = _existing_capsule_trace_id(
            capsule.trace_event_ids,
            capsule.user_input_trace_id,
        )
        final_response_trace_id = _existing_capsule_trace_id(
            capsule.trace_event_ids,
            capsule.final_response_trace_id,
        )
        items.append(
            MemoryItem(
                item_id=(
                    f"{packet_id}:recent_raw_conversation_capsule_alignment:"
                    f"{len(items) + 1:03d}"
                ),
                item_type="recent_raw_conversation_capsule_alignment",
                text=(
                    "COPIED_FIELDS:"
                    f"turn_id={turn_id};"
                    f"raw_user_text_present={_bool_text(raw_user_text is not None)};"
                    f"raw_assistant_text_present={_bool_text(raw_assistant_text is not None)};"
                    f"raw_user_text_chars={len(raw_user_text or '')};"
                    f"raw_assistant_text_chars={len(raw_assistant_text or '')};"
                    f"capsule_trace_count={len(capsule.trace_event_ids)};"
                    f"capsule_movement_count={len(capsule.node_movements)};"
                    f"user_input_trace_id={user_input_trace_id or ''};"
                    f"final_response_trace_id={final_response_trace_id or ''}"
                ),
                source_trace_ids=_unique_strings(
                    [user_input_trace_id, final_response_trace_id]
                ),
                source_data_ids=[],
            )
        )
    return items


def build_recent_memory_relevance_candidate_frames(
    *,
    zero_state: ZeroState,
    packet_id: str,
    turn_id: str,
    read_window: int = RECENT_MEMORY_RELEVANCE_CANDIDATE_WINDOW,
) -> list[MemoryRelevanceCandidateFrame]:
    """최근 raw-capsule 대응표를 나중의 관련성 판단 후보 frame으로 만든다."""

    if read_window <= 0:
        return []

    capsules_by_turn_id = {
        capsule.turn_id: capsule
        for capsule in zero_state.previous_turn_capsules
    }
    recent_raw_entries = zero_state.recent_raw_conversation[-read_window:]

    frames: list[MemoryRelevanceCandidateFrame] = []
    for raw_entry in recent_raw_entries:
        candidate_turn_id = _raw_conversation_text(raw_entry, "turn_id")
        if candidate_turn_id is None:
            continue
        capsule = capsules_by_turn_id.get(candidate_turn_id)
        if capsule is None:
            continue

        user_input_trace_id = _existing_capsule_trace_id(
            capsule.trace_event_ids,
            capsule.user_input_trace_id,
        )
        final_response_trace_id = _existing_capsule_trace_id(
            capsule.trace_event_ids,
            capsule.final_response_trace_id,
        )
        frame_index = len(frames) + 1
        frames.append(
            MemoryRelevanceCandidateFrame(
                frame_id=f"{packet_id}:memory_relevance_candidate:{frame_index:03d}",
                turn_id=turn_id,
                candidate_turn_id=candidate_turn_id,
                source_memory_item_id=(
                    f"{packet_id}:recent_raw_conversation_capsule_alignment:"
                    f"{frame_index:03d}"
                ),
                source_trace_ids=_unique_strings(
                    [user_input_trace_id, final_response_trace_id]
                ),
                source_data_ids=[],
                judgement_status="not_run",
            )
        )
    return frames


def build_raw_memory_window_policy_frame(
    *,
    zero_state: ZeroState,
    packet_id: str,
    turn_id: str,
    max_raw_window: int = RECENT_RAW_CONVERSATION_MAX_WINDOW,
    min_raw_guarantee: int = RECENT_RAW_CONVERSATION_MIN_GUARANTEE,
    post_compression_keep: int = RAW_MEMORY_POST_COMPRESSION_KEEP,
    compression_batch_size: int = RAW_MEMORY_COMPRESSION_BATCH_SIZE,
) -> RawMemoryCompressionCandidateFrame:
    """최근 raw 원문 창을 retained window와 node_5 압축 후보 좌표로 나눈다."""

    raw_entries = list(zero_state.recent_raw_conversation)
    raw_count = len(raw_entries)
    frame_id = f"{packet_id}:raw_memory_compression_candidate:001"

    if raw_count <= max_raw_window:
        retained_entries = raw_entries
        candidate_entries: list[dict[str, str]] = []
        candidate_status = "not_needed"
        older_unmanaged_raw_turn_count = 0
    else:
        retained_entries = raw_entries[-post_compression_keep:]
        candidate_start = max(0, raw_count - post_compression_keep - compression_batch_size)
        candidate_end = raw_count - post_compression_keep
        candidate_entries = raw_entries[candidate_start:candidate_end]
        candidate_status = "pending_node5_compression"
        older_unmanaged_raw_turn_count = candidate_start

    return RawMemoryCompressionCandidateFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        policy_id=RAW_MEMORY_WINDOW_POLICY_ID,
        raw_conversation_count=raw_count,
        max_raw_window=max_raw_window,
        min_raw_guarantee=min_raw_guarantee,
        post_compression_keep=post_compression_keep,
        compression_batch_size=compression_batch_size,
        candidate_status=candidate_status,
        candidate_turn_ids=_raw_conversation_turn_ids(candidate_entries),
        candidate_raw_entry_count=len(candidate_entries),
        retained_raw_turn_ids=_raw_conversation_turn_ids(retained_entries),
        retained_raw_entry_count=len(retained_entries),
        older_unmanaged_raw_turn_count=older_unmanaged_raw_turn_count,
        source_memory_item_ids=[],
        source_trace_ids=[],
        source_data_ids=[],
        generated_by="CODE:RAW_MEMORY_WINDOW_POLICY",
        info_class="absolute_policy_decision",
        semantic_judgement_status="not_run",
        node5_compression_status="not_run",
        node4_approval_status="not_run",
    )


def build_recent_raw_conversation_compression_candidate(
    *,
    zero_state: ZeroState,
    packet_id: str,
    turn_id: str,
) -> RawMemoryCompressionCandidateFrame:
    """ORDER_107 이름에 맞춘 thin wrapper."""

    return build_raw_memory_window_policy_frame(
        zero_state=zero_state,
        packet_id=packet_id,
        turn_id=turn_id,
    )


def build_pre_route_memory_items(
    *,
    zero_state: ZeroState,
    packet_id: str,
    packet: MemoryPacketFrom0,
    read_window: int = RECENT_TURN_CAPSULE_READ_WINDOW,
    alignment_read_window: int = RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW,
) -> list[MemoryItem]:
    """pre_route_report용 기본 item과 최근 turn 좌표 item을 함께 만든다."""

    # 학습 메모: pre_route_report packet은 현재 턴 trace_evidence를 유지하면서,
    # 이전 턴 capsule index와 raw-capsule alignment를 추가로 붙인다.
    # 셋을 섞어 하나의 요약문으로 만들지 않는다.
    return [
        build_trace_evidence_memory_item(packet_id=packet_id, packet=packet),
        *build_previous_turn_capsule_index_items(
            zero_state=zero_state,
            packet_id=packet_id,
            read_window=read_window,
        ),
        *build_recent_raw_conversation_capsule_alignment_items(
            zero_state=zero_state,
            packet_id=packet_id,
            read_window=alignment_read_window,
        ),
    ]


def record_memory_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    packet: MemoryPacketFrom0,
    mode: str,
    input_ref: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    packet_id_suffix: str | None = None,
    compression_summary: str = "CODE_STATUS:trace_evidence_ids_supplied",
    operation_label: str = "CODE_STATUS:trace_evidence_ids_supplied",
    memory_items: list[MemoryItem] | None = None,
    relevance_candidate_frames: list[MemoryRelevanceCandidateFrame] | None = None,
    compression_candidate_frames: list[RawMemoryCompressionCandidateFrame] | None = None,
    id_namespace: LRunIds | None = None,
) -> str:
    """MemoryPacketFrom0이 만들어졌다는 사실을 trace로 기록한다."""

    packet_id = (
        id_namespace.memory_packet_data_id(
            target=packet.target,
            mode=mode,
            packet_id_suffix=packet_id_suffix,
        )
        if id_namespace is not None
        else memory_packet_data_id(packet.target, mode, packet_id_suffix)
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="memory_packet",
        input_ref=input_ref or packet.trace_evidence_ids,
        output_ref=[packet_id],
        schema_status="passed",
    )
    if data_store is not None:
        payload = MemoryPacketPayload(
            packet_id=packet_id,
            turn_id=turn_id,
            target=packet.target,
            mode=mode,
            compression_summary=compression_summary,
            evidence_trace_count=len(packet.trace_evidence_ids),
            operation_label=operation_label,
            generated_by="CODE:RULE_STUB",
            llm_semantic_summary_status="not_run",
            source_trace_ids=input_ref or packet.trace_evidence_ids,
            source_data_ids=source_data_ids or [],
            evidence_trace_ids=packet.trace_evidence_ids,
            insufficient_signal_id=packet.insufficient_signal_id,
            memory_items=memory_items or [
                MemoryItem(
                    item_id=f"{packet_id}:trace_evidence",
                    item_type="trace_evidence",
                    text="CODE_STATUS:trace_evidence_ids_supplied",
                    source_trace_ids=packet.trace_evidence_ids,
                    source_data_ids=source_data_ids or [],
                )
            ],
            relevance_candidate_frames=relevance_candidate_frames or [],
            compression_candidate_frames=compression_candidate_frames or [],
        )
        validate_memory_packet_payload(payload)
        data_store.create_record(
            data_id=packet_id,
            data_type="node_output:memory_packet",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(payload),
        )
    return event.event_id


def record_l3_continuation_summary_for_l2(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    zero_state: ZeroState,
    continuation_frame_id: str,
    input_ref: list[str] | None = None,
    id_namespace: LRunIds | None = None,
) -> str:
    """0이 L3 판정 이후 L2 재시도에 필요한 구조화 기억만 공급했다는 사실을 기록한다.

    이 함수는 L2를 다시 실행하지 않는다. 여기서 하는 일은 continuation frame,
    L3 achievement frame, L2 query frame에 이미 적힌 값을 복사해서 L2가 다음
    검색 계획을 세울 때 볼 수 있는 memory packet으로 묶는 것뿐이다.
    """

    continuation_payload = _require_payload(data_store, continuation_frame_id)
    attempt_index = _required_int(continuation_payload, "attempt_index")
    source_l3_id = _required_text(continuation_payload, "source_l3_achievement_id")
    source_l2_id = _required_text(continuation_payload, "source_l2_query_frame_id")

    packet = supply_memory(
        target="L2",
        mode=L3_CONTINUATION_SUMMARY_MODE,
        zero_state=zero_state,
        trace_store=trace_store,
        turn_id=turn_id,
    )
    source_data_ids = _unique_strings([continuation_frame_id, source_l3_id, source_l2_id])
    memory_items = build_l3_continuation_summary_items(
        data_store=data_store,
        continuation_frame_id=continuation_frame_id,
    )
    return record_memory_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        packet=packet,
        mode=L3_CONTINUATION_SUMMARY_MODE,
        input_ref=input_ref or packet.trace_evidence_ids,
        source_data_ids=source_data_ids,
        packet_id_suffix=f"{attempt_index:04d}",
        compression_summary="CODE_STATUS:l3_continuation_summary_supplied",
        operation_label="CODE_STATUS:l3_continuation_summary_supplied",
        memory_items=memory_items,
        id_namespace=id_namespace,
    )


def record_l_loop_return_summary_for_node1(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    zero_state: ZeroState,
    input_ref: list[str],
    source_data_ids: list[str],
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, str, MemoryPacketFrom0]:
    """0이 L루프 결과를 node_1이 다시 판단하기 좋게 구조화해서 공급한다.

    일반 `loop_return_summary`가 trace ID 묶음만 주던 문제를 줄이기 위한 함수다.
    여기서 0은 새 의미 판단을 하지 않는다. L1/L3/budget/continuation frame의
    구조화 필드와 절대 count만 복사하거나 정책 라벨로 조합한다.
    """

    return_summary_frame_id = (
        id_namespace.return_summary_frame_id()
        if id_namespace is not None
        else L_LOOP_RETURN_SUMMARY_FRAME_DATA_ID
    )
    frame = build_l_loop_return_summary_frame(
        data_store=data_store,
        turn_id=turn_id,
        frame_id=return_summary_frame_id,
        source_trace_ids=input_ref,
        source_data_ids=source_data_ids,
    )
    validate_l_loop_return_summary_frame(frame)
    summary_event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=input_ref,
        output_ref=[return_summary_frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=return_summary_frame_id,
        data_type="node_output:l_loop_return_summary_frame",
        exists=True,
        created_at=summary_event.timestamp,
        source_trace_id=summary_event.event_id,
        payload=asdict(frame),
    )
    material_trace_id, material_frame_id, material_frame = record_node0_document_material_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame_id=document_material_packet_frame_data_id(id_namespace=id_namespace),
        source_trace_ids=_unique_strings([*input_ref, summary_event.event_id]),
        source_data_ids=_unique_strings([return_summary_frame_id, *source_data_ids]),
    )

    packet = supply_memory(
        target="node_1",
        mode="loop_return_summary",
        zero_state=zero_state,
        trace_store=trace_store,
        turn_id=turn_id,
    )
    packet_trace_id = record_memory_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        packet=packet,
        mode="loop_return_summary",
        input_ref=_unique_strings([*input_ref, summary_event.event_id, material_trace_id]),
        source_data_ids=_unique_strings(
            [return_summary_frame_id, material_frame_id, *source_data_ids]
        ),
        compression_summary="CODE_STATUS:l_loop_return_summary_supplied",
        operation_label="CODE_STATUS:l_loop_return_summary_supplied",
        memory_items=[
            *build_l_loop_return_summary_items(frame),
            build_document_material_packet_status_item(material_frame),
        ],
        id_namespace=id_namespace,
    )
    packet_data_id = (
        id_namespace.loop_return_memory_packet_id()
        if id_namespace is not None
        else memory_packet_data_id("node_1", "loop_return_summary")
    )
    return packet_trace_id, packet_data_id, return_summary_frame_id, packet


def record_node0_document_material_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> tuple[str, str, Node0DocumentMaterialPacketFrame]:
    """L 이후 문서 검색/읽기/context 공급 상태를 node_0 절대정보 장부로 기록한다."""

    frame = build_node0_document_material_packet_frame(
        data_store=data_store,
        turn_id=turn_id,
        frame_id=frame_id,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_node0_document_material_packet_frame(frame)
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
        data_type="node_output:node0_document_material_packet_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id, frame


def build_node0_document_material_packet_frame(
    *,
    data_store: DataStore,
    turn_id: str,
    frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> Node0DocumentMaterialPacketFrame:
    """흩어진 L 산출 문서 좌표를 문서별 절대정보 장부로 합친다."""

    return_summary_payload = _latest_payload_by_exact_type(
        data_store=data_store,
        source_data_ids=source_data_ids,
        data_type="node_output:l_loop_return_summary_frame",
    )
    l3_payload = _latest_payload_by_type_fragment(
        data_store=data_store,
        source_data_ids=source_data_ids,
        type_fragment="L3_achievement_frame",
    )
    context_pack_payload = _latest_payload_by_exact_type(
        data_store=data_store,
        source_data_ids=source_data_ids,
        data_type="node_output:document_context_pack_frame",
    )
    read_doc_ids = _unique_strings(
        [
            *_string_list(return_summary_payload.get("read_doc_ids")),
            *_document_extract_doc_ids(
                data_store=data_store,
                source_data_ids=source_data_ids,
                require_text=True,
            ),
        ]
    )
    if not read_doc_ids:
        read_doc_ids = _string_list(l3_payload.get("read_doc_ids"))
    search_doc_ids = _string_list(return_summary_payload.get("search_result_doc_ids"))
    if not search_doc_ids:
        search_doc_ids = _string_list(l3_payload.get("search_result_doc_ids"))

    item_map: dict[str, dict[str, object]] = {}
    source_trace_ids_by_data_id = _source_trace_ids_by_data_id(
        data_store=data_store,
        source_data_ids=source_data_ids,
    )
    return_summary_data_id = _text(return_summary_payload, "frame_id", fallback="")
    l3_data_id = _text(l3_payload, "frame_id", fallback="")
    context_pack_data_id = _text(context_pack_payload, "frame_id", fallback="")

    for rank, doc_id in enumerate(search_doc_ids, start=1):
        entry = _material_entry(item_map, doc_id)
        _add_material_role(entry, "search_candidate")
        entry["was_search_candidate"] = True
        entry["search_candidate_rank"] = rank
        _extend_material_sources(
            entry,
            data_ids=[return_summary_data_id, l3_data_id],
            trace_ids=source_trace_ids_by_data_id,
        )

    tool_read_sources = _tool_read_sources_by_doc_id(
        data_store=data_store,
        source_data_ids=source_data_ids,
    )
    for rank, doc_id in enumerate(read_doc_ids, start=1):
        entry = _material_entry(item_map, doc_id)
        _add_material_role(entry, "actual_tool_read_doc")
        entry["was_actual_tool_read_doc"] = True
        entry["actual_read_rank"] = rank
        tool_source = tool_read_sources.get(doc_id, {})
        char_count = tool_source.get("char_count")
        if isinstance(char_count, int) and char_count > int(entry["char_count"]):
            entry["char_count"] = char_count
        _extend_material_sources(
            entry,
            data_ids=[return_summary_data_id, l3_data_id, str(tool_source.get("data_id") or "")],
            trace_ids=source_trace_ids_by_data_id,
        )

    included_documents = context_pack_payload.get("included_documents")
    if isinstance(included_documents, list):
        for rank, item in enumerate(included_documents, start=1):
            if not isinstance(item, dict):
                continue
            doc_id = _text_from_value(item.get("doc_id"))
            if not doc_id:
                continue
            entry = _material_entry(item_map, doc_id)
            _add_material_role(entry, "supplied_document_context")
            entry["was_supplied_document_context"] = True
            entry["supplied_context_rank"] = rank
            entry["document_name"] = _text_from_value(item.get("document_name")) or _document_name(doc_id)
            char_count = item.get("char_count")
            if isinstance(char_count, int) and char_count > int(entry["char_count"]):
                entry["char_count"] = char_count
            _extend_material_sources(
                entry,
                data_ids=[context_pack_data_id, _text_from_value(item.get("source_data_id"))],
                trace_ids=source_trace_ids_by_data_id,
            )

    excluded_documents = context_pack_payload.get("excluded_documents")
    if isinstance(excluded_documents, list):
        for rank, item in enumerate(excluded_documents, start=1):
            if not isinstance(item, dict):
                continue
            doc_id = _text_from_value(item.get("doc_id"))
            if not doc_id:
                continue
            entry = _material_entry(item_map, doc_id)
            _add_material_role(entry, "excluded_document_context")
            entry["was_excluded_document_context"] = True
            entry["excluded_context_rank"] = rank
            entry["document_name"] = _text_from_value(item.get("document_name")) or _document_name(doc_id)
            char_count = item.get("char_count")
            if isinstance(char_count, int) and char_count > int(entry["char_count"]):
                entry["char_count"] = char_count
            _extend_material_sources(
                entry,
                data_ids=[context_pack_data_id, _text_from_value(item.get("source_data_id"))],
                trace_ids=source_trace_ids_by_data_id,
            )

    for entry in item_map.values():
        if bool(entry["was_search_candidate"]) and not bool(entry["was_actual_tool_read_doc"]):
            _add_material_role(entry, "unread_candidate")
            entry["was_unread_candidate"] = True

    items = [_entry_to_document_material_item(entry) for entry in item_map.values()]
    items.sort(
        key=lambda item: (
            item.search_candidate_rank or 999999,
            item.actual_read_rank or 999999,
            item.supplied_context_rank or 999999,
            item.excluded_context_rank or 999999,
            item.document_name,
        )
    )
    return Node0DocumentMaterialPacketFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        items=items,
        item_count=len(items),
        search_candidate_count=sum(1 for item in items if item.was_search_candidate),
        actual_tool_read_doc_count=sum(1 for item in items if item.was_actual_tool_read_doc),
        supplied_document_context_count=sum(1 for item in items if item.was_supplied_document_context),
        excluded_document_context_count=sum(1 for item in items if item.was_excluded_document_context),
        unread_candidate_count=sum(1 for item in items if item.was_unread_candidate),
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
    )


def build_document_material_packet_status_item(
    frame: Node0DocumentMaterialPacketFrame,
) -> MemoryItem:
    """node_1도 문서 장부 존재와 count를 알 수 있게 memory item으로 복사한다."""

    return _memory_item(
        packet_source_id=frame.frame_id,
        item_type="document_material_packet_status",
        text=(
            "COPIED_FIELDS:"
            f"item_count={frame.item_count};"
            f"search_candidate_count={frame.search_candidate_count};"
            f"actual_tool_read_doc_count={frame.actual_tool_read_doc_count};"
            f"supplied_document_context_count={frame.supplied_document_context_count};"
            f"unread_candidate_count={frame.unread_candidate_count}"
        ),
        source_data_ids=[frame.frame_id, *frame.source_data_ids],
    )


def build_l_loop_return_summary_frame(
    *,
    data_store: DataStore,
    turn_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    frame_id: str = L_LOOP_RETURN_SUMMARY_FRAME_DATA_ID,
) -> LLoopReturnSummaryFrame:
    """L루프 산출 record들에서 node_1 상위 판단용 요약 frame을 만든다."""

    l1_payload = _latest_payload_by_type_fragment(
        data_store=data_store,
        source_data_ids=source_data_ids,
        type_fragment="L1_goal_frame",
    )
    l3_payload = _latest_payload_by_type_fragment(
        data_store=data_store,
        source_data_ids=source_data_ids,
        type_fragment="L3_achievement_frame",
    )
    budget_payload = _latest_payload_by_exact_type(
        data_store=data_store,
        source_data_ids=source_data_ids,
        data_type="tool_use_budget",
    )
    continuation_payload = _latest_payload_by_exact_type(
        data_store=data_store,
        source_data_ids=source_data_ids,
        data_type="node_output:L_loop_continuation_frame",
    )

    evidence_requirement_kind = _text(
        l1_payload,
        "evidence_requirement_kind",
        fallback="unspecified",
    )
    required_min_read_documents = _int(l1_payload, "minimum_read_documents")
    read_doc_ids = _unique_strings(
        [
            *_string_list(l3_payload.get("read_doc_ids")),
            *_document_extract_doc_ids(
                data_store=data_store,
                source_data_ids=source_data_ids,
                require_text=True,
            ),
        ]
    )
    if not read_doc_ids:
        read_doc_ids = _string_list(budget_payload.get("read_doc_ids"))
    read_code_file_paths = _unique_strings(
        [
            *_string_list(l3_payload.get("read_code_file_paths")),
            *_code_extract_file_paths(
                data_store=data_store,
                source_data_ids=source_data_ids,
                require_text=True,
            ),
        ]
    )
    search_result_doc_ids = _string_list(l3_payload.get("search_result_doc_ids"))
    actual_read_doc_count = len(read_doc_ids)
    actual_read_code_file_count = len(read_code_file_paths)
    search_candidate_count = len(search_result_doc_ids)
    if search_candidate_count == 0:
        search_candidate_count = _int(l3_payload, "candidate_count")

    l_loop_task_status = _text(l3_payload, "achievement_status", fallback="unknown")
    l3_goal_match_status = _text(l3_payload, "goal_match_status", fallback="not_applicable")
    l3_semantic_goal_match_status = _text(
        l3_payload,
        "semantic_goal_match_status",
        fallback="not_run",
    )
    final_continuation_status = _text(
        continuation_payload,
        "continuation_status",
        fallback="not_recorded",
    )
    budget_stop_reason = _text(budget_payload, "stop_reason", fallback="unknown")
    remaining_tool_calls = _remaining_budget(
        budget_payload,
        max_field="max_tool_calls",
        used_field="tool_call_count",
    )
    remaining_read_doc_calls = _remaining_budget(
        budget_payload,
        max_field="max_read_doc_calls",
        used_field="read_doc_count",
    )
    remaining_query_attempts = _remaining_budget(
        budget_payload,
        max_field="max_query_attempts",
        used_field="query_count",
    )
    failure_level, route_hint, route_hint_reason = _return_failure_level_and_route_hint(
        l_loop_task_status=l_loop_task_status,
        l3_goal_match_status=l3_goal_match_status,
        l3_semantic_goal_match_status=l3_semantic_goal_match_status,
        required_min_read_documents=required_min_read_documents,
        actual_read_doc_count=actual_read_doc_count,
        actual_source_evidence_count=actual_read_doc_count + actual_read_code_file_count,
        budget_stop_reason=budget_stop_reason,
        final_continuation_status=final_continuation_status,
        remaining_tool_calls=remaining_tool_calls,
        remaining_read_doc_calls=remaining_read_doc_calls,
        remaining_query_attempts=remaining_query_attempts,
    )

    return LLoopReturnSummaryFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        loop_id="L",
        l_loop_task_status=l_loop_task_status,
        failure_level=failure_level,
        evidence_requirement_kind=evidence_requirement_kind,
        required_min_read_documents=required_min_read_documents,
        actual_read_doc_count=actual_read_doc_count,
        actual_read_code_file_count=actual_read_code_file_count,
        search_candidate_count=search_candidate_count,
        final_continuation_status=final_continuation_status,
        budget_stop_reason=budget_stop_reason,
        remaining_tool_calls=remaining_tool_calls,
        remaining_read_doc_calls=remaining_read_doc_calls,
        remaining_query_attempts=remaining_query_attempts,
        l3_goal_match_status=l3_goal_match_status,
        l3_semantic_goal_match_status=l3_semantic_goal_match_status,
        recommended_next_route_for_node1=route_hint,
        route_hint_reason=route_hint_reason,
        read_doc_ids=read_doc_ids,
        read_code_file_paths=read_code_file_paths,
        search_result_doc_ids=search_result_doc_ids,
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
    )


def build_l_loop_return_summary_items(frame: LLoopReturnSummaryFrame) -> list[MemoryItem]:
    """LLoopReturnSummaryFrame을 node_1 memory packet에 넣을 짧은 항목들로 바꾼다."""

    source_data_ids = [frame.frame_id, *frame.source_data_ids]
    return [
        _memory_item(
            packet_source_id=frame.frame_id,
            item_type="l_loop_return_status",
            text=(
                "COPIED_FIELDS:"
                f"task_status={frame.l_loop_task_status};"
                f"failure_level={frame.failure_level};"
                f"final_continuation_status={frame.final_continuation_status}"
            ),
            source_data_ids=source_data_ids,
        ),
        _memory_item(
            packet_source_id=frame.frame_id,
            item_type="l_loop_evidence_requirement_status",
            text=(
                "COPIED_FIELDS:"
                f"evidence_requirement_kind={frame.evidence_requirement_kind};"
                f"required_min_read_documents={frame.required_min_read_documents};"
                f"actual_read_doc_count={frame.actual_read_doc_count};"
                f"actual_read_code_file_count={frame.actual_read_code_file_count};"
                f"search_candidate_count={frame.search_candidate_count}"
            ),
            source_data_ids=source_data_ids,
        ),
        _memory_item(
            packet_source_id=frame.frame_id,
            item_type="l_loop_budget_return_status",
            text=(
                "COPIED_FIELDS:"
                f"budget_stop_reason={frame.budget_stop_reason};"
                f"remaining_tool_calls={frame.remaining_tool_calls};"
                f"remaining_read_doc_calls={frame.remaining_read_doc_calls};"
                f"remaining_query_attempts={frame.remaining_query_attempts}"
            ),
            source_data_ids=source_data_ids,
        ),
        _memory_item(
            packet_source_id=frame.frame_id,
            item_type="l_loop_route_hint_for_node1",
            text=(
                "CODE_STATUS:"
                f"recommended_next_route_for_node1={frame.recommended_next_route_for_node1};"
                f"reason={frame.route_hint_reason}"
            ),
            source_data_ids=source_data_ids,
        ),
        _memory_item(
            packet_source_id=frame.frame_id,
            item_type="l_loop_read_and_candidate_ids_copy",
            text=(
                "COPIED_FIELDS:"
                f"read_doc_ids={_format_list(frame.read_doc_ids)};"
                f"read_code_file_paths={_format_list(frame.read_code_file_paths)};"
                f"search_result_doc_ids={_format_list(frame.search_result_doc_ids)}"
            ),
            source_data_ids=source_data_ids,
        ),
    ]


def _latest_payload_by_type_fragment(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
    type_fragment: str,
) -> dict[str, object]:
    for data_id in reversed(source_data_ids):
        record = data_store.get_record(data_id)
        if record is None or type_fragment not in record.data_type:
            continue
        if isinstance(record.payload, dict):
            return record.payload
    return {}


def _latest_payload_by_exact_type(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
    data_type: str,
) -> dict[str, object]:
    for data_id in reversed(source_data_ids):
        record = data_store.get_record(data_id)
        if record is None or record.data_type != data_type:
            continue
        if isinstance(record.payload, dict):
            return record.payload
    return {}


def _remaining_budget(payload: dict[str, object], *, max_field: str, used_field: str) -> int:
    max_value = payload.get(max_field)
    used_value = payload.get(used_field)
    if not isinstance(max_value, int) or not isinstance(used_value, int):
        return 0
    return max(max_value - used_value, 0)


def _return_failure_level_and_route_hint(
    *,
    l_loop_task_status: str,
    l3_goal_match_status: str,
    l3_semantic_goal_match_status: str,
    required_min_read_documents: int,
    actual_read_doc_count: int,
    actual_source_evidence_count: int,
    budget_stop_reason: str,
    final_continuation_status: str,
    remaining_tool_calls: int,
    remaining_read_doc_calls: int,
    remaining_query_attempts: int,
) -> tuple[str, str, str]:
    """구조화 상태와 절대 count만 보고 node_1용 참고 라벨을 만든다."""

    minimum_evidence_missing = (
        required_min_read_documents > 0
        and actual_source_evidence_count < required_min_read_documents
    )
    l3_unsatisfied = (
        l_loop_task_status in {"partial", "failed", "unknown"}
        or l3_goal_match_status in {"partial", "missing"}
        or l3_semantic_goal_match_status in {"partial", "missing"}
    )
    if not minimum_evidence_missing and not l3_unsatisfied:
        return "none", "2", "CODE_STATUS:l_loop_return_achieved"

    budget_exhausted = (
        final_continuation_status == "stop_budget_exhausted"
        or budget_stop_reason
        in {
            "max_tool_calls_reached",
            "max_read_doc_calls_reached",
            "max_query_attempts_reached",
            "max_input_chars_reached",
        }
        or (
            remaining_tool_calls == 0
            and remaining_read_doc_calls == 0
            and remaining_query_attempts == 0
        )
    )
    if budget_exhausted:
        return (
            "budget_exhausted",
            "L",
            "CODE_STATUS:l_loop_budget_exhausted_before_task_success",
        )

    if minimum_evidence_missing:
        return (
            "l1_replan_needed",
            "L",
            "CODE_STATUS:l_loop_minimum_evidence_missing",
        )

    return (
        "l2_retryable",
        "L",
        "CODE_STATUS:l3_not_achieved_but_retry_may_be_possible",
    )


def build_l3_continuation_summary_items(
    *,
    data_store: DataStore,
    continuation_frame_id: str,
) -> list[MemoryItem]:
    """L2 재검색에 넘길 값을 구조화 record에서만 복사한다.

    자유 텍스트를 해석하지 않기 위해 L3 reason 같은 문장도 판단하지 않는다.
    필요한 경우 그대로 복사하고, 그 출처 data_id를 MemoryItem에 붙인다.
    """

    continuation_payload = _require_payload(data_store, continuation_frame_id)
    source_l3_id = _required_text(continuation_payload, "source_l3_achievement_id")
    source_l2_id = _required_text(continuation_payload, "source_l2_query_frame_id")
    l3_payload = _require_payload(data_store, source_l3_id)
    l2_payload = _require_payload(data_store, source_l2_id)

    items: list[MemoryItem] = []
    items.append(
        _memory_item(
            packet_source_id=continuation_frame_id,
            item_type="l_loop_continuation_status",
            text=(
                "CODE_STATUS:"
                f"continuation_status={_required_text(continuation_payload, 'continuation_status')};"
                f"reason={_required_text(continuation_payload, 'continuation_reason_code')};"
                f"next_target={_required_text(continuation_payload, 'next_target_node')}"
            ),
            source_data_ids=[continuation_frame_id],
        )
    )
    items.append(
        _memory_item(
            packet_source_id=continuation_frame_id,
            item_type="l3_goal_status_copy",
            text=(
                "COPIED_FIELDS:"
                f"achievement_status={_text(l3_payload, 'achievement_status', fallback='unknown')};"
                f"goal_match_status={_text(l3_payload, 'goal_match_status', fallback='unknown')};"
                "semantic_goal_match_status="
                f"{_text(l3_payload, 'semantic_goal_match_status', fallback='unknown')}"
            ),
            source_data_ids=[continuation_frame_id, source_l3_id],
        )
    )
    l3_feedback = _join_nonempty(
        [
            _text(l3_payload, "reason", fallback=""),
            _text(l3_payload, "macro_achievement_reason", fallback=""),
            _text(l3_payload, "micro_achievement_reason", fallback=""),
        ]
    )
    if l3_feedback:
        items.append(
            _memory_item(
                packet_source_id=continuation_frame_id,
                item_type="l3_feedback_text_copy",
                text=f"COPIED_FIELDS:l3_feedback={l3_feedback}",
                source_data_ids=[continuation_frame_id, source_l3_id],
            )
        )
    items.append(
        _memory_item(
            packet_source_id=continuation_frame_id,
            item_type="previous_l2_query_copy",
            text=f"COPIED_FIELDS:previous_query={_text(l2_payload, 'query_text', fallback='unknown_query')}",
            source_data_ids=[continuation_frame_id, source_l2_id],
        )
    )
    items.append(
        _memory_item(
            packet_source_id=continuation_frame_id,
            item_type="tool_budget_status_copy",
            text=(
                "COPIED_FIELDS:"
                f"tool_budget_status={_required_text(continuation_payload, 'tool_budget_status')};"
                f"attempt_index={_required_int(continuation_payload, 'attempt_index')};"
                f"max_attempts={_required_int(continuation_payload, 'max_attempts')}"
            ),
            source_data_ids=[continuation_frame_id],
        )
    )
    items.append(
        _memory_item(
            packet_source_id=continuation_frame_id,
            item_type="read_and_unread_candidate_ids_copy",
            text=(
                "COPIED_FIELDS:"
                f"read_doc_ids={_format_list(_string_list(continuation_payload.get('read_doc_ids')))};"
                "unread_candidate_doc_ids="
                f"{_format_list(_string_list(continuation_payload.get('unread_candidate_doc_ids')))}"
            ),
            source_data_ids=[continuation_frame_id],
        )
    )
    return items


def _material_entry(item_map: dict[str, dict[str, object]], doc_id: str) -> dict[str, object]:
    if doc_id not in item_map:
        item_map[doc_id] = {
            "doc_id": doc_id,
            "document_name": _document_name(doc_id),
            "source_roles": [],
            "was_search_candidate": False,
            "was_actual_tool_read_doc": False,
            "was_supplied_document_context": False,
            "was_excluded_document_context": False,
            "was_unread_candidate": False,
            "search_candidate_rank": 0,
            "actual_read_rank": 0,
            "supplied_context_rank": 0,
            "excluded_context_rank": 0,
            "char_count": 0,
            "source_trace_ids": [],
            "source_data_ids": [],
        }
    return item_map[doc_id]


def _add_material_role(entry: dict[str, object], role: str) -> None:
    roles = entry.get("source_roles")
    if not isinstance(roles, list):
        roles = []
        entry["source_roles"] = roles
    if role not in roles:
        roles.append(role)


def _extend_material_sources(
    entry: dict[str, object],
    *,
    data_ids: list[str],
    trace_ids: dict[str, str],
) -> None:
    source_data_ids = entry.get("source_data_ids")
    if not isinstance(source_data_ids, list):
        source_data_ids = []
    source_trace_ids = entry.get("source_trace_ids")
    if not isinstance(source_trace_ids, list):
        source_trace_ids = []

    for data_id in data_ids:
        if not data_id:
            continue
        if data_id not in source_data_ids:
            source_data_ids.append(data_id)
        trace_id = trace_ids.get(data_id)
        if trace_id and trace_id not in source_trace_ids:
            source_trace_ids.append(trace_id)

    entry["source_data_ids"] = source_data_ids
    entry["source_trace_ids"] = source_trace_ids


def _entry_to_document_material_item(entry: dict[str, object]) -> Node0DocumentMaterialItem:
    return Node0DocumentMaterialItem(
        doc_id=str(entry.get("doc_id") or ""),
        document_name=str(entry.get("document_name") or ""),
        source_roles=_string_list(entry.get("source_roles")),
        was_search_candidate=bool(entry.get("was_search_candidate")),
        was_actual_tool_read_doc=bool(entry.get("was_actual_tool_read_doc")),
        was_supplied_document_context=bool(entry.get("was_supplied_document_context")),
        was_excluded_document_context=bool(entry.get("was_excluded_document_context")),
        was_unread_candidate=bool(entry.get("was_unread_candidate")),
        search_candidate_rank=_int(entry, "search_candidate_rank"),
        actual_read_rank=_int(entry, "actual_read_rank"),
        supplied_context_rank=_int(entry, "supplied_context_rank"),
        excluded_context_rank=_int(entry, "excluded_context_rank"),
        char_count=_int(entry, "char_count"),
        source_trace_ids=_string_list(entry.get("source_trace_ids")),
        source_data_ids=_string_list(entry.get("source_data_ids")),
    )


def _source_trace_ids_by_data_id(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
) -> dict[str, str]:
    trace_ids: dict[str, str] = {}
    for data_id in source_data_ids:
        record = data_store.get_record(data_id)
        if record is None or not record.source_trace_id:
            continue
        trace_ids[data_id] = record.source_trace_id
    return trace_ids


def _tool_read_sources_by_doc_id(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
) -> dict[str, dict[str, object]]:
    sources: dict[str, dict[str, object]] = {}
    for source in _document_extract_sources(
        data_store=data_store,
        source_data_ids=source_data_ids,
    ):
        if source.get("has_text") is not True:
            continue
        doc_id = str(source.get("doc_id") or "")
        if doc_id and doc_id not in sources:
            sources[doc_id] = source
    return sources


def _document_extract_doc_ids(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
    require_text: bool,
) -> list[str]:
    doc_ids: list[str] = []
    for source in _document_extract_sources(
        data_store=data_store,
        source_data_ids=source_data_ids,
    ):
        if require_text and source.get("has_text") is not True:
            continue
        doc_id = source.get("doc_id")
        if isinstance(doc_id, str) and doc_id and doc_id not in doc_ids:
            doc_ids.append(doc_id)
    return doc_ids


def _code_extract_file_paths(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
    require_text: bool,
) -> list[str]:
    file_paths: list[str] = []
    for data_id in source_data_ids:
        record = data_store.get_record(data_id)
        if record is None or not _is_code_extract_record(record.data_type):
            continue
        payload = record.payload if isinstance(record.payload, dict) else {}
        if payload.get("read_status") != "ok":
            continue
        if require_text:
            text = payload.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
        file_path = _text_from_value(payload.get("file_path"))
        if file_path and file_path not in file_paths:
            file_paths.append(file_path)
    return file_paths


def _document_extract_sources(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    seen_data_ids: set[str] = set()
    for data_id in source_data_ids:
        if data_id in seen_data_ids:
            continue
        seen_data_ids.add(data_id)
        record = data_store.get_record(data_id)
        if record is None:
            continue
        if not _is_document_extract_record(record.data_type):
            continue
        payload = record.payload if isinstance(record.payload, dict) else {}
        doc_id = _text_from_value(payload.get("doc_id"))
        if not doc_id:
            continue
        text = payload.get("text")
        has_text = isinstance(text, str) and bool(text.strip())
        sources.append(
            {
                "doc_id": doc_id,
                "data_id": record.data_id,
                "source_trace_id": record.source_trace_id or "",
                "char_count": payload.get("char_count"),
                "has_text": has_text,
            }
        )
    return sources


def _document_name(doc_id: str) -> str:
    normalized = doc_id.replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] or doc_id


def _text_from_value(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _is_document_extract_record(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_doc") or data_type.startswith("tool_result:read_artifact")


def _is_code_extract_record(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_code_file")


def _memory_item(
    *,
    packet_source_id: str,
    item_type: str,
    text: str,
    source_data_ids: list[str],
) -> MemoryItem:
    return MemoryItem(
        item_id=f"{packet_source_id}:{item_type}",
        item_type=item_type,
        text=text,
        source_trace_ids=[],
        source_data_ids=_unique_strings(source_data_ids),
    )


def _require_payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.require_record(data_id)
    if not isinstance(record.payload, dict):
        raise TypeError(f"{data_id} payload must be a dict")
    return record.payload


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    raise ValueError(f"{field_name} must be a non-empty string")


def _required_int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, int):
        return value
    raise ValueError(f"{field_name} must be an integer")


def _int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    return value if isinstance(value, int) else 0


def _text(payload: dict[str, object], field_name: str, *, fallback: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
    return result


def _format_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


def _join_nonempty(values: list[str]) -> str:
    return " | ".join(value for value in values if value)


def _existing_capsule_trace_id(trace_event_ids: list[str], trace_id: str | None) -> str | None:
    if trace_id is None:
        return None
    if trace_id not in trace_event_ids:
        return None
    return trace_id


def _raw_conversation_text(entry: dict[str, str], field_kind: str) -> str | None:
    """raw conversation entry에서 정해진 필드명만 원문 그대로 읽는다."""

    field_names_by_kind = {
        "turn_id": ["turn_id"],
        "user": ["raw_user_text", "user_text", "user_input", "user"],
        "assistant": [
            "raw_assistant_text",
            "assistant_text",
            "final_response",
            "assistant",
        ],
    }
    field_names = field_names_by_kind.get(field_kind, [])
    for field_name in field_names:
        value = entry.get(field_name)
        if isinstance(value, str):
            return value
    return None


def _raw_conversation_turn_ids(entries: list[dict[str, str]]) -> list[str]:
    turn_ids: list[str] = []
    for entry in entries:
        turn_id = _raw_conversation_text(entry, "turn_id")
        if turn_id is None:
            continue
        turn_ids.append(turn_id)
    return turn_ids


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
