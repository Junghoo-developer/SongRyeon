from __future__ import annotations

import ast
from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    NodeMovement,
    Node2AnswerBasisFrame,
    Node2EvidenceRole,
    Node2HandoffFrame,
    Node0DocumentMaterialItem,
    Node3BriefClaim,
    Node3BriefDocument,
    Node3ExcludedDocumentContext,
    Node3L3DocumentSummaryMaterial,
    Node3MaterialDeliveryPolicyFrame,
    Node3MemorySelectionMaterial,
    Node3RLoopResultMaterial,
    Node3SourceCodeOutline,
    Node3SourceCodeSymbol,
    Node3SelectedRecentMemoryContext,
    Node3InputBriefFrame,
    Node3BriefRuntimeTask,
    SelectedRecentMemoryContextFrame,
    SelectedRecentMemoryContextItem,
    ZeroState,
    validate_node2_handoff_frame,
    validate_node3_material_delivery_policy_frame,
    validate_node3_input_brief_frame,
    validate_selected_recent_memory_context_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.tools.document_context_pack import latest_document_context_pack_payload


NODE2_HANDOFF_FRAME_DATA_ID = "node_2:handoff_frame"
NODE3_INPUT_BRIEF_FRAME_DATA_ID = "node_3:input_brief_frame"
NODE3_MATERIAL_DELIVERY_POLICY_FRAME_DATA_ID = "node_3:material_delivery_policy_frame"
SELECTED_MEMORY_RAW_USER_TEXT_MAX_CHARS = 800
SELECTED_MEMORY_RAW_ASSISTANT_TEXT_MAX_CHARS = 1200
SELECTED_MEMORY_MAX_ITEMS = 3


def selected_recent_memory_context_frame_data_id(selection_frame_id: str) -> str:
    return f"{selection_frame_id}:selected_recent_memory_context"


def record_selected_recent_memory_context(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    zero_state: ZeroState,
    selection_frame_id: str,
    frame_id: str | None = None,
) -> tuple[str, str, SelectedRecentMemoryContextFrame]:
    """selector가 고른 이전 raw 대화를 요약 없이 node_3용 context frame으로 복사한다."""

    context_frame_id = frame_id or selected_recent_memory_context_frame_data_id(
        selection_frame_id
    )
    frame = build_selected_recent_memory_context_frame(
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        selection_frame_id=selection_frame_id,
        frame_id=context_frame_id,
    )
    validate_selected_recent_memory_context_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[context_frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=context_frame_id,
        data_type="node_output:selected_recent_memory_context_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, context_frame_id, frame


def build_selected_recent_memory_context_frame(
    *,
    data_store: DataStore,
    turn_id: str,
    zero_state: ZeroState,
    selection_frame_id: str,
    frame_id: str | None = None,
    max_items: int = SELECTED_MEMORY_MAX_ITEMS,
    raw_user_text_max_chars: int = SELECTED_MEMORY_RAW_USER_TEXT_MAX_CHARS,
    raw_assistant_text_max_chars: int = SELECTED_MEMORY_RAW_ASSISTANT_TEXT_MAX_CHARS,
) -> SelectedRecentMemoryContextFrame:
    """선택된 candidate turn_id와 정확히 일치하는 raw entry만 복사한다."""

    context_frame_id = frame_id or selected_recent_memory_context_frame_data_id(
        selection_frame_id
    )
    selection_record = data_store.get_record(selection_frame_id)
    if selection_record is None or not isinstance(selection_record.payload, dict):
        return SelectedRecentMemoryContextFrame(
            frame_id=context_frame_id,
            turn_id=turn_id,
            selection_frame_id=selection_frame_id,
            selection_status="not_recorded",
            selected_turn_count=0,
            items=[],
            missing_selected_memory_context_count=0,
            source_data_ids=[selection_frame_id],
            source_trace_ids=[],
        )

    selection_payload = selection_record.payload
    selection_status = _text(selection_payload, "selection_status", fallback="not_recorded")
    source_memory_packet_id = _text(selection_payload, "source_memory_packet_id", fallback="")
    source_data_ids = _unique_strings([selection_frame_id, source_memory_packet_id])
    source_trace_ids = _string_list(selection_payload.get("source_trace_ids"))
    if selection_status != "selected":
        return SelectedRecentMemoryContextFrame(
            frame_id=context_frame_id,
            turn_id=turn_id,
            selection_frame_id=selection_frame_id,
            selection_status=selection_status,
            selected_turn_count=0,
            items=[],
            missing_selected_memory_context_count=0,
            source_data_ids=source_data_ids,
            source_trace_ids=source_trace_ids,
        )

    packet_payload = _payload(data_store, source_memory_packet_id)
    candidate_by_frame_id = _candidate_by_frame_id(packet_payload)
    selected_frame_ids = _string_list(selection_payload.get("selected_candidate_frame_ids"))
    raw_by_turn_id = _raw_conversation_by_turn_id(zero_state.recent_raw_conversation)

    items: list[SelectedRecentMemoryContextItem] = []
    missing_count = 0
    for selected_frame_id in selected_frame_ids[:max_items]:
        candidate = candidate_by_frame_id.get(selected_frame_id)
        if candidate is None:
            missing_count += 1
            continue
        source_turn_id = _text(candidate, "candidate_turn_id", fallback="")
        raw_entry = raw_by_turn_id.get(source_turn_id)
        if raw_entry is None:
            missing_count += 1
            continue
        raw_user_text = _raw_conversation_text(raw_entry, "user") or ""
        raw_assistant_text = _raw_conversation_text(raw_entry, "assistant") or ""
        copied_user_text, user_truncated = _truncate(raw_user_text, raw_user_text_max_chars)
        copied_assistant_text, assistant_truncated = _truncate(
            raw_assistant_text,
            raw_assistant_text_max_chars,
        )
        source_memory_item_id = _text(candidate, "source_memory_item_id", fallback="")
        item_source_trace_ids = _unique_strings(
            [
                *_string_list(candidate.get("source_trace_ids")),
                *_string_list(selection_payload.get("source_trace_ids")),
            ]
        )
        item_source_data_ids = _unique_strings([selection_frame_id, source_memory_packet_id])
        items.append(
            SelectedRecentMemoryContextItem(
                item_id=f"{context_frame_id}:item:{len(items) + 1:03d}",
                source_turn_id=source_turn_id,
                source_candidate_frame_id=selected_frame_id,
                source_memory_item_id=source_memory_item_id,
                raw_user_text=copied_user_text,
                raw_assistant_text=copied_assistant_text,
                raw_user_text_chars=len(raw_user_text),
                raw_assistant_text_chars=len(raw_assistant_text),
                raw_user_text_truncated=user_truncated,
                raw_assistant_text_truncated=assistant_truncated,
                copied_from=f"ZeroState.recent_raw_conversation[turn_id={source_turn_id}]",
                selection_reason_source_data_id=selection_frame_id,
                selection_info_class=_text(selection_payload, "info_class", fallback=""),
                source_trace_ids=item_source_trace_ids,
                source_data_ids=item_source_data_ids,
            )
        )

    if len(selected_frame_ids) > max_items:
        missing_count += len(selected_frame_ids) - max_items

    return SelectedRecentMemoryContextFrame(
        frame_id=context_frame_id,
        turn_id=turn_id,
        selection_frame_id=selection_frame_id,
        selection_status=selection_status,
        selected_turn_count=len(items),
        items=items,
        missing_selected_memory_context_count=missing_count,
        source_data_ids=source_data_ids,
        source_trace_ids=source_trace_ids,
    )


def record_route2_handoff(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_question: str,
    node2_input_frame_id: str,
    node2_input_trace_id: str,
    final_memory_packet_id: str,
    turn_outcome_id: str,
    route_ids: list[str],
    l_loop_output_ids: list[str],
    memory_relevance_selection_frame_id: str | None = None,
    selected_recent_memory_context_frame_id: str | None = None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str]:
    """route=2 진입 시 0/code가 2에게 넘길 handoff 무결성 프레임을 기록한다."""

    handoff_frame_id = (
        id_namespace.route2_handoff_frame_id()
        if id_namespace is not None
        else NODE2_HANDOFF_FRAME_DATA_ID
    )
    existing_data_ids = {record.data_id for record in data_store.list_records()}
    l_loop_was_run = bool(l_loop_output_ids)
    current_l_loop_output_ids = _current_namespace_ids(
        l_loop_output_ids,
        id_namespace=id_namespace,
    )
    l1_goal_present = _has_legacy_or_typed_l_output(
        data_store=data_store,
        l_loop_output_ids=current_l_loop_output_ids,
        legacy_id="L1:goal_frame",
        type_fragment="L1_goal_frame",
    )
    l2_query_present = _has_legacy_or_typed_l_output(
        data_store=data_store,
        l_loop_output_ids=current_l_loop_output_ids,
        legacy_id="L2:query_frame",
        type_fragment="L2_query_frame",
    )
    l3_preserved_present = _has_legacy_or_typed_l_output(
        data_store=data_store,
        l_loop_output_ids=current_l_loop_output_ids,
        legacy_id="L3:preserved_info_frame",
        type_fragment="L3_preserved_info_frame",
    )
    l3_achievement_present = _has_legacy_or_typed_l_output(
        data_store=data_store,
        l_loop_output_ids=current_l_loop_output_ids,
        legacy_id="L3:achievement_frame",
        type_fragment="L3_achievement_frame",
    )
    search_result_count = _count_records_with_type_prefix(
        data_store,
        "tool_result:search_docs",
        id_namespace=id_namespace,
    )
    document_counts = _document_extract_counts(
        data_store,
        id_namespace=id_namespace,
    )
    reportable_document_count = int(document_counts["reportable"])
    raw_document_extract_record_count = int(document_counts["raw"])
    empty_document_extract_record_count = int(document_counts["empty"])
    code_counts = _code_extract_counts(
        data_store,
        id_namespace=id_namespace,
    )
    reportable_code_file_count = int(code_counts["reportable"])
    raw_code_extract_record_count = int(code_counts["raw"])
    empty_code_extract_record_count = int(code_counts["empty"])
    read_doc_count = reportable_document_count
    document_context_pack_frame_id = document_counts["pack_frame_id"]
    document_context_included_count = int(document_counts["pack_included"])
    document_context_excluded_count = int(document_counts["pack_excluded"])
    document_context_cutoff_reason = str(document_counts["pack_cutoff_reason"])
    document_material_frame_id, document_material_payload = _latest_document_material_packet(
        data_store,
        id_namespace=id_namespace,
    )
    document_material_item_count = _int(document_material_payload, "item_count")
    document_material_unread_candidate_count = _int(
        document_material_payload,
        "unread_candidate_count",
    )
    actual_l_run_count = _count_records_by_type(data_store, "node_output:L_loop_run_frame")
    blocked_reroute_count = _blocked_same_turn_l_reroute_request_count(data_store)
    controller_decisions = _same_turn_l_reroute_controller_decisions(data_store)
    l_internal_revision_count = _count_l_internal_revision_records(
        data_store,
        id_namespace=id_namespace,
    )
    memory_relevance_summary = _memory_relevance_handoff_summary(
        data_store=data_store,
        selection_frame_id=memory_relevance_selection_frame_id,
    )
    selected_memory_context_summary = _selected_recent_memory_context_handoff_summary(
        data_store=data_store,
        context_frame_id=selected_recent_memory_context_frame_id,
    )

    insufficiency_reasons: list[str] = []
    if node2_input_frame_id not in existing_data_ids:
        insufficiency_reasons.append("missing_node2_input_frame")
    if final_memory_packet_id not in existing_data_ids:
        insufficiency_reasons.append("missing_final_memory_packet")
    if turn_outcome_id not in existing_data_ids:
        insufficiency_reasons.append("missing_turn_outcome")
    if not any(_route_value(route_id) == "2" for route_id in route_ids):
        insufficiency_reasons.append("missing_route_2_decision")
    if l_loop_was_run:
        if not l1_goal_present:
            insufficiency_reasons.append("missing_l1_goal_frame")
        if not l2_query_present:
            insufficiency_reasons.append("missing_l2_query_frame")
        if not l3_preserved_present:
            insufficiency_reasons.append("missing_l3_preserved_frame")
        if not l3_achievement_present:
            insufficiency_reasons.append("missing_l3_achievement_frame")
        if search_result_count < 1 and reportable_document_count < 1 and reportable_code_file_count < 1:
            insufficiency_reasons.append("missing_l_evidence_result")

    has_blocker = any(reason.startswith("missing_") for reason in insufficiency_reasons[:3])
    handoff_status = "blocked" if has_blocker else "insufficient" if insufficiency_reasons else "ready"
    source_data_ids = _unique_strings(
        [
            node2_input_frame_id,
            final_memory_packet_id,
            turn_outcome_id,
            memory_relevance_summary["frame_id"],
            selected_memory_context_summary["frame_id"],
            document_context_pack_frame_id if isinstance(document_context_pack_frame_id, str) else None,
            document_material_frame_id,
            *route_ids,
            *l_loop_output_ids,
            *_same_turn_l_reroute_controller_ids(data_store),
        ]
    )
    frame = Node2HandoffFrame(
        frame_id=handoff_frame_id,
        turn_id=turn_id,
        user_question=user_question,
        handoff_status=handoff_status,
        node2_input_frame_id=node2_input_frame_id,
        final_memory_packet_id=final_memory_packet_id,
        turn_outcome_id=turn_outcome_id,
        route_ids=_unique_strings(route_ids),
        route_path=_route_path(route_ids, actual_l_run_count=actual_l_run_count),
        l_loop_was_run=l_loop_was_run,
        l1_goal_present=l1_goal_present,
        l2_query_present=l2_query_present,
        l3_preserved_present=l3_preserved_present,
        l3_achievement_present=l3_achievement_present,
        search_result_count=search_result_count,
        reportable_document_count=reportable_document_count,
        raw_document_extract_record_count=raw_document_extract_record_count,
        empty_document_extract_record_count=empty_document_extract_record_count,
        reportable_code_file_count=reportable_code_file_count,
        raw_code_extract_record_count=raw_code_extract_record_count,
        empty_code_extract_record_count=empty_code_extract_record_count,
        read_doc_count=read_doc_count,
        document_context_pack_frame_id=(
            document_context_pack_frame_id
            if isinstance(document_context_pack_frame_id, str) and document_context_pack_frame_id
            else None
        ),
        document_context_included_count=document_context_included_count,
        document_context_excluded_count=document_context_excluded_count,
        document_context_cutoff_reason=document_context_cutoff_reason,
        document_material_packet_frame_id=document_material_frame_id,
        document_material_item_count=document_material_item_count,
        document_material_unread_candidate_count=document_material_unread_candidate_count,
        actual_l_run_count=actual_l_run_count,
        blocked_same_turn_l_reroute_request_count=blocked_reroute_count,
        same_turn_l_reroute_controller_decisions=controller_decisions,
        l_internal_revision_count=l_internal_revision_count,
        memory_relevance_selection_frame_id=memory_relevance_summary["frame_id"],
        memory_relevance_selection_status=str(memory_relevance_summary["status"]),
        memory_relevance_candidate_count=int(memory_relevance_summary["candidate_count"]),
        memory_relevance_selected_count=int(memory_relevance_summary["selected_count"]),
        memory_relevance_info_class=str(memory_relevance_summary["info_class"]),
        memory_relevance_generated_by=str(memory_relevance_summary["generated_by"]),
        memory_relevance_llm_call_data_id=memory_relevance_summary["llm_call_data_id"],
        selected_recent_memory_context_frame_id=selected_memory_context_summary["frame_id"],
        selected_recent_memory_context_count=int(selected_memory_context_summary["count"]),
        missing_selected_memory_context_count=int(selected_memory_context_summary["missing_count"]),
        selected_recent_memory_context_generated_by=str(
            selected_memory_context_summary["generated_by"]
        ),
        selected_recent_memory_context_info_class=str(
            selected_memory_context_summary["info_class"]
        ),
        brief_available=reportable_document_count > 0 or reportable_code_file_count > 0,
        insufficiency_reasons=insufficiency_reasons,
        source_trace_ids=[node2_input_trace_id],
        source_data_ids=source_data_ids,
    )
    validate_node2_handoff_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=[node2_input_trace_id],
        output_ref=[handoff_frame_id],
        schema_status="passed" if handoff_status == "ready" else "failed",
    )
    data_store.create_record(
        data_id=handoff_frame_id,
        data_type="node_output:node2_handoff_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, handoff_frame_id


def record_node3_input_brief(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_question: str,
    handoff_frame_id: str,
    boundary: MetainfoBoundary,
    input_trace_ids: list[str],
    source_data_ids: list[str],
    answer_basis_frame: Node2AnswerBasisFrame | None = None,
    runtime_movements: list[NodeMovement] | None = None,
    assigned_model_by_node: dict[str, str] | None = None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, Node3InputBriefFrame]:
    """2/2.5가 node_3에게 줄 의미 단위 브리프를 만든다."""

    brief_frame_id = (
        id_namespace.node3_input_brief_frame_id()
        if id_namespace is not None
        else NODE3_INPUT_BRIEF_FRAME_DATA_ID
    )
    read_documents = _read_documents(data_store, id_namespace=id_namespace)
    document_context_pack = latest_document_context_pack_payload(
        data_store,
        id_namespace=id_namespace,
    )
    l_loop_return_summary_frame_id, l_loop_return_summary = _latest_l_loop_return_summary(
        data_store,
        id_namespace=id_namespace,
    )
    actual_tool_read_doc_documents = _actual_tool_read_doc_documents(
        data_store=data_store,
        l_loop_return_summary=l_loop_return_summary,
        id_namespace=id_namespace,
    )
    actual_tool_read_doc_count = _actual_tool_read_doc_count(
        data_store=data_store,
        l_loop_return_summary=l_loop_return_summary,
        id_namespace=id_namespace,
        document_names=actual_tool_read_doc_documents,
    )
    actual_tool_read_code_file_paths = _actual_tool_read_code_file_paths(
        data_store=data_store,
        l_loop_return_summary=l_loop_return_summary,
        id_namespace=id_namespace,
    )
    actual_tool_read_code_file_count = len(actual_tool_read_code_file_paths)
    supplied_source_code_context_count = _supplied_source_code_context_count(
        data_store=data_store,
        read_documents=read_documents,
    )
    source_code_outlines = _source_code_outlines(
        data_store=data_store,
        read_documents=read_documents,
    )
    excluded_document_contexts = _excluded_document_contexts(document_context_pack)
    document_context_pack_frame_id = _text(document_context_pack, "frame_id", fallback="")
    document_context_pack_status = _document_context_pack_status(document_context_pack)
    accumulated_search_candidate_documents = _accumulated_search_candidate_documents(
        data_store,
        id_namespace=id_namespace,
    )
    document_material_frame_id, document_material_payload = _latest_document_material_packet(
        data_store,
        id_namespace=id_namespace,
    )
    document_material_items = _node3_document_material_items(document_material_payload)
    final_search_candidate_documents = _final_search_candidate_documents(
        document_material_items=document_material_items,
        l_loop_return_summary=l_loop_return_summary,
    )
    memory_selection_material = _node3_memory_selection_material(
        data_store=data_store,
        handoff_frame_id=handoff_frame_id,
    )
    selected_recent_memory_contexts = _node3_selected_recent_memory_contexts(
        data_store=data_store,
        handoff_frame_id=handoff_frame_id,
    )
    l3_document_summaries = _node3_l3_document_summary_materials(
        data_store=data_store,
        id_namespace=id_namespace,
    )
    runtime_tasks = _runtime_tasks(
        runtime_movements or [],
        assigned_model_by_node or {},
    )
    r_loop_result_material = _node3_r_loop_result_material(data_store)
    # 학습 메모: node_3 brief는 claim의 의미 등급을 다시 판단하지 않는다.
    # node_2 boundary가 붙인 relative/mixed 라벨을 사용자 답변 재료까지 그대로 운반한다.
    allowed_claims = [
        Node3BriefClaim(
            kind=info_ref.info_kind,
            text=info_ref.text,
            info_class="relative",
            source_mode=info_ref.source_mode,
            claim_alignment=info_ref.claim_alignment,
            source_data_id=info_ref.source_data_id,
        )
        for info_ref in boundary.relative_info[:20]
    ]
    allowed_claims.extend(
        Node3BriefClaim(
            kind=info_ref.info_kind,
            text=info_ref.text,
            info_class="mixed",
            source_mode=info_ref.source_mode,
            claim_alignment=info_ref.claim_alignment,
            source_data_id=info_ref.source_data_id,
        )
        for info_ref in boundary.mixed_info[:20]
    )
    insufficiency_reasons: list[str] = []
    has_selected_memory_material = (
        memory_selection_material is not None
        and memory_selection_material.selected_memory_count > 0
    )
    has_selected_memory_context = bool(selected_recent_memory_contexts)
    has_l3_document_summary_material = bool(l3_document_summaries)
    if (
        not read_documents
        and not allowed_claims
        and not runtime_tasks
        and not has_selected_memory_material
        and not has_selected_memory_context
        and not has_l3_document_summary_material
    ):
        insufficiency_reasons.append("no_document_or_claim_material")

    runtime_trace_ids = _runtime_task_trace_ids(runtime_movements or [])
    runtime_data_ids = _runtime_task_data_ids(runtime_movements or [])
    memory_selection_source_data_id = (
        memory_selection_material.source_data_id
        if memory_selection_material is not None
        else None
    )
    selected_memory_context_source_data_id = _selected_recent_memory_context_frame_id(
        data_store=data_store,
        handoff_frame_id=handoff_frame_id,
    )
    answer_basis_frame_id = answer_basis_frame.frame_id if answer_basis_frame is not None else None
    answer_basis_mode = (
        answer_basis_frame.answer_basis_mode
        if answer_basis_frame is not None
        else "mixed_or_uncertain"
    )
    material_policy_frame_id = (
        id_namespace.scoped_data_id(NODE3_MATERIAL_DELIVERY_POLICY_FRAME_DATA_ID)
        if id_namespace is not None
        else NODE3_MATERIAL_DELIVERY_POLICY_FRAME_DATA_ID
    )
    material_policy_source_data_ids = _unique_strings(
        [
            handoff_frame_id,
            answer_basis_frame_id,
            document_context_pack_frame_id or None,
            document_material_frame_id,
            *[
                summary.source_data_id
                for summary in l3_document_summaries
                if summary.source_data_id
            ],
        ]
    )
    material_policy_frame = build_node3_material_delivery_policy_frame(
        frame_id=material_policy_frame_id,
        turn_id=turn_id,
        answer_basis_frame_id=answer_basis_frame_id,
        answer_basis_mode=answer_basis_mode,
        supplied_document_context_count=len(read_documents),
        l3_document_summary_count=len(l3_document_summaries),
        source_trace_ids=_unique_strings([*input_trace_ids, *runtime_trace_ids]),
        source_data_ids=material_policy_source_data_ids,
    )
    validate_node3_material_delivery_policy_frame(material_policy_frame)
    material_policy_event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_2",
        event_type="node_output",
        input_ref=material_policy_frame.source_trace_ids,
        output_ref=[material_policy_frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=material_policy_frame_id,
        data_type="node_output:node3_material_delivery_policy_frame",
        exists=True,
        created_at=material_policy_event.timestamp,
        source_trace_id=material_policy_event.event_id,
        payload=asdict(material_policy_frame),
    )
    frame = Node3InputBriefFrame(
        frame_id=brief_frame_id,
        turn_id=turn_id,
        user_question=user_question,
        brief_status="ready" if not insufficiency_reasons else "insufficient",
        handoff_frame_id=handoff_frame_id,
        read_documents=read_documents,
        actual_tool_read_doc_count=actual_tool_read_doc_count,
        actual_tool_read_doc_documents=actual_tool_read_doc_documents,
        actual_tool_read_code_file_count=actual_tool_read_code_file_count,
        actual_tool_read_code_file_paths=actual_tool_read_code_file_paths,
        supplied_document_context_count=len(read_documents),
        supplied_source_code_context_count=supplied_source_code_context_count,
        source_code_outlines=source_code_outlines,
        document_context_pack_frame_id=document_context_pack_frame_id or None,
        document_context_pack_status=document_context_pack_status,
        excluded_document_contexts=excluded_document_contexts,
        document_material_packet_frame_id=document_material_frame_id,
        document_material_items=document_material_items,
        final_search_candidate_count=len(final_search_candidate_documents),
        final_search_candidate_documents=final_search_candidate_documents,
        accumulated_search_candidate_count=len(accumulated_search_candidate_documents),
        accumulated_search_candidate_documents=accumulated_search_candidate_documents,
        search_candidate_count=len(final_search_candidate_documents),
        search_candidate_documents=final_search_candidate_documents,
        allowed_claims=allowed_claims,
        memory_selection_material=memory_selection_material,
        selected_recent_memory_contexts=selected_recent_memory_contexts,
        l3_document_summaries=l3_document_summaries,
        material_delivery_policy_frame_id=material_policy_frame_id,
        material_delivery_mode=material_policy_frame.material_delivery_mode,
        raw_document_policy=material_policy_frame.raw_document_policy,
        l3_summary_policy=material_policy_frame.l3_summary_policy,
        uncertainty_policy=material_policy_frame.uncertainty_policy,
        material_policy_reason_code=material_policy_frame.policy_reason_code,
        llm_raw_document_text_count=material_policy_frame.llm_raw_document_text_count,
        llm_l3_summary_context_count=material_policy_frame.llm_l3_summary_context_count,
        raw_context_replaced_by_summary_count=(
            material_policy_frame.raw_context_replaced_by_summary_count
        ),
        material_policy_generated_by=material_policy_frame.generated_by,
        material_policy_info_class=material_policy_frame.info_class,
        material_policy_semantic_judgement_status=(
            material_policy_frame.semantic_judgement_status
        ),
        runtime_tasks=runtime_tasks,
        r_loop_result_material=r_loop_result_material,
        l_loop_return_summary_frame_id=l_loop_return_summary_frame_id,
        l_loop_task_status=_text(l_loop_return_summary, "l_loop_task_status", fallback="not_recorded"),
        l_loop_failure_level=_text(l_loop_return_summary, "failure_level", fallback="none"),
        l3_goal_match_status=_text(l_loop_return_summary, "l3_goal_match_status", fallback="not_run"),
        l3_semantic_goal_match_status=_text(
            l_loop_return_summary,
            "l3_semantic_goal_match_status",
            fallback="not_run",
        ),
        remaining_query_attempts=_int(l_loop_return_summary, "remaining_query_attempts"),
        remaining_read_doc_calls=_int(l_loop_return_summary, "remaining_read_doc_calls"),
        l_loop_result_attitude_hint=_l_loop_result_attitude_hint(l_loop_return_summary),
        answer_basis_frame_id=answer_basis_frame_id,
        answer_basis_mode=answer_basis_mode,
        basis_reason_codes=(
            list(answer_basis_frame.basis_reason_codes)
            if answer_basis_frame is not None
            else ["llm_mode_selection_failed"]
        ),
        mode_selection_reason=(
            answer_basis_frame.mode_selection_reason
            if answer_basis_frame is not None
            else "CODE_STATUS:node2_answer_basis_mode_selection_failed"
        ),
        mode_selection_reason_info_class=(
            answer_basis_frame.mode_selection_reason_info_class
            if answer_basis_frame is not None
            else "absolute_status"
        ),
        evidence_roles=(
            list(answer_basis_frame.evidence_roles)
            if answer_basis_frame is not None
            else []
        ),
        answer_basis_generated_by=(
            answer_basis_frame.generated_by if answer_basis_frame is not None else "CODE:FALLBACK"
        ),
        answer_basis_info_class=(
            answer_basis_frame.info_class if answer_basis_frame is not None else "absolute_status"
        ),
        answer_basis_semantic_judgement_status=(
            answer_basis_frame.semantic_judgement_status
            if answer_basis_frame is not None
            else "failed"
        ),
        reporting_rules=[
            "사용자 질문에 직접 답한다.",
            "문서 재료가 있으면 문서나 데이터가 없다고 말하지 않는다.",
            "답변 첫머리의 '근거 기준:' 블록은 code가 Node3InputBriefFrame의 절대 count로 고정 생성한다.",
            "node_3 LLM은 읽은 문서 수, 검색 후보 문서 수, 현재 턴 실행 순서 자료 수를 직접 쓰지 않고 본문만 작성한다.",
            "실제 read_doc 도구 원문 읽기 수와 node_3 공급 문서 context 수는 다른 count다.",
            "실제 read_code_file 도구 원문 읽기 수와 read_doc 도구 원문 읽기 수는 다른 count다.",
            "사용자가 read_doc 수를 물으면 actual_tool_read_doc_count만 기준으로 답하고, supplied_document_context_count를 read_doc 수로 말하지 않는다.",
            "사용자가 코드 파일 원문 읽기 여부를 물으면 actual_tool_read_code_file_count와 actual_tool_read_code_file_paths를 기준으로 답한다.",
            "source_code_outlines는 read_code_file 원문에서 code가 뽑은 문법 장부이며, source 파일 기능 설명의 coverage checklist로 사용한다.",
            "source_code_outlines의 함수명만 보고 의미를 단정하지 않고, supplied source text를 함께 근거로 설명한다.",
            "최종 검색 후보와 L3 누적 검색 후보는 다른 count다.",
            "검색 후보 문서는 원문을 읽은 문서가 아니다. 검색 후보만 보고 읽은 문서처럼 말하지 않는다.",
            "document_context_pack excluded 문서는 읽은 문서가 아니다. 예산 때문에 공급되지 않은 후보로만 언급한다.",
            "document_material_packet의 문서별 role flag가 true인 역할만 해당 문서에 주장한다.",
            "문서가 node_3 context로 공급됐더라도 was_actual_tool_read_doc=false이면 read_doc으로 읽었다고 말하지 않는다.",
            "README, 요약, 실행기록은 사용자가 명시한 ORDER 원문을 대체한다고 말하지 않는다.",
            "L3 문서별 요약은 L3 LLM이 만든 의미 요약 재료이며 원문이나 code fact를 대체하지 않는다.",
            "L3 담백 문서 요약은 문서 하나에 직접 대응하는 relative 정보로만 취급한다.",
            "L3 상황 맞춤 요약은 현재 질문/목표와 문서 원문 source bundle에 근거한 mixed 정보로만 취급한다.",
            "material_delivery_policy가 l3_summary_replaces_raw_context 계열이면 node_3 LLM payload의 원문 text는 생략되고 L3 요약 재료를 기준으로 답한다.",
            "원문 text가 payload에서 생략되어도 DataStore의 원문 document extract record는 삭제된 것이 아니다.",
            "현재 턴 실행 순서 자료가 있으면 실행 순서와 작업 장부 설명의 근거로 사용할 수 있다.",
            "기억 선택 결과가 있으면 LLM selector가 고른 mixed 판단으로만 취급하고, 선택된 과거 턴을 code 사실처럼 단정하지 않는다.",
            "선택된 최근 기억 context가 있으면 raw_user_text/raw_assistant_text에 복사된 범위에서만 이전 대화를 언급한다.",
            "선택된 최근 기억 context는 과거 대화 원문을 code가 복사한 context이며, 실행기록 문서나 새로 읽은 문서가 아니다.",
            "과거 대화 안에서 문서/실행기록이 언급되었더라도, 그것을 이번 턴에 직접 읽은 문서처럼 말하지 않는다.",
            "선택된 최근 기억 context의 관련성은 selector의 mixed 판단이며 code fact가 아니다.",
            "truncated=true인 최근 기억 context는 전체 이전 대화라고 단정하지 않는다.",
            "해석, 정의, 평가, 요약을 말할 때는 답변 안에 근거 기준을 짧게 밝히고, 문서/허용 주장/현재 턴 실행 순서 자료 중 무엇에 기대는지와 왜 그 근거로 말할 수 있는지 설명한다.",
            "너는 특정 내부 노드 그 자체가 아니라, 사용자에게 보고하는 송련의 최종 응답자 관점으로 말한다.",
            "node_0/node_1/node_2/node_3 같은 내부 역할명은 자기정체성으로 쓰지 않고, 필요할 때 실행 경로 설명에만 제한적으로 쓴다.",
            "내부 추적용 raw ID를 답변 본문에 쓰지 않는다.",
            "문서 내용의 최종 진실성은 단정하지 않는다.",
            "answer_basis_mode=absolute_first이면 코드/문서/trace/data로 확인 가능한 사실을 우선하고 추측을 줄인다.",
            "answer_basis_mode=relative_allowed이면 해석/조언/비판/구상이 가능하되 절대정보처럼 단정하지 않는다.",
            "answer_basis_mode=mixed_or_uncertain이면 출처 묶음, 부분 근거, 불확실성을 드러내고 부족한 근거를 지어내지 않는다.",
            "R route 실험 결과가 있으면 graph memory skeleton 실행 상태로만 말하고, 완전한 장기기억 탐색 성공처럼 말하지 않는다.",
            "R loop result material은 R return summary 장부에서 복사된 절대 상태이며, R1/R2/R3 의미 판단이 실행됐다는 뜻이 아니다.",
        ],
        insufficiency_reasons=insufficiency_reasons,
        source_trace_ids=_unique_strings([*input_trace_ids, *runtime_trace_ids]),
        source_data_ids=_unique_strings(
            [
                handoff_frame_id,
                material_policy_frame_id,
                *source_data_ids,
                answer_basis_frame_id,
                memory_selection_source_data_id,
                selected_memory_context_source_data_id,
                document_context_pack_frame_id or None,
                document_material_frame_id,
                l_loop_return_summary_frame_id,
                *[
                    outline.source_data_id
                    for outline in source_code_outlines
                    if outline.source_data_id
                ],
                *[
                    summary.source_data_id
                    for summary in l3_document_summaries
                    if summary.source_data_id
                ],
                r_loop_result_material.source_data_id
                if r_loop_result_material is not None
                else None,
                *runtime_data_ids,
            ]
        ),
    )
    validate_node3_input_brief_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_2",
        event_type="node_output",
        input_ref=_unique_strings([*frame.source_trace_ids, material_policy_event.event_id]),
        output_ref=[brief_frame_id],
        schema_status="passed" if frame.brief_status == "ready" else "failed",
    )
    data_store.create_record(
        data_id=brief_frame_id,
        data_type="node_output:node3_input_brief_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, brief_frame_id, frame


def build_node3_material_delivery_policy_frame(
    *,
    frame_id: str,
    turn_id: str,
    answer_basis_frame_id: str | None,
    answer_basis_mode: str,
    supplied_document_context_count: int,
    l3_document_summary_count: int,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> Node3MaterialDeliveryPolicyFrame:
    """answer_basis_mode와 summary availability를 고정 정책표로 변환한다."""

    (
        material_delivery_mode,
        raw_document_policy,
        l3_summary_policy,
        uncertainty_policy,
        policy_reason_code,
        llm_raw_document_text_count,
        llm_l3_summary_context_count,
        raw_context_replaced_by_summary_count,
    ) = _node3_material_delivery_policy_values(
        answer_basis_mode=answer_basis_mode,
        supplied_document_context_count=supplied_document_context_count,
        l3_document_summary_count=l3_document_summary_count,
    )
    return Node3MaterialDeliveryPolicyFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        answer_basis_frame_id=answer_basis_frame_id,
        answer_basis_mode=answer_basis_mode,
        material_delivery_mode=material_delivery_mode,
        raw_document_policy=raw_document_policy,
        l3_summary_policy=l3_summary_policy,
        uncertainty_policy=uncertainty_policy,
        policy_reason_code=policy_reason_code,
        supplied_document_context_count=supplied_document_context_count,
        l3_document_summary_count=l3_document_summary_count,
        llm_raw_document_text_count=llm_raw_document_text_count,
        llm_l3_summary_context_count=llm_l3_summary_context_count,
        raw_context_replaced_by_summary_count=raw_context_replaced_by_summary_count,
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
    )


def _node3_material_delivery_policy_values(
    *,
    answer_basis_mode: str,
    supplied_document_context_count: int,
    l3_document_summary_count: int,
) -> tuple[str, str, str, str, str, int, int, int]:
    """ORDER_132의 명시 정책표. 의미 판단 없이 모드와 summary 존재 여부만 본다."""

    if answer_basis_mode == "absolute_first":
        return (
            "raw_document_primary",
            "preserve_supplied_raw_context",
            "auxiliary_only",
            "do_not_replace_raw_with_summary",
            "absolute_first_requires_checkable_material",
            supplied_document_context_count,
            l3_document_summary_count,
            0,
        )
    if l3_document_summary_count < 1:
        return (
            "raw_document_fallback_no_l3_summary",
            "preserve_raw_context_because_l3_summary_missing",
            "unavailable",
            "expose_summary_absence",
            "l3_summary_unavailable_cannot_replace_raw_context",
            supplied_document_context_count,
            0,
            0,
        )
    if answer_basis_mode == "relative_allowed":
        return (
            "l3_summary_replaces_raw_context",
            "omit_raw_text_from_llm_payload",
            "replace_raw_context_with_labeled_l3_summary",
            "keep_summary_boundary_visible",
            "relative_allowed_uses_l3_summary_to_reduce_context_volume",
            0,
            l3_document_summary_count,
            supplied_document_context_count,
        )
    return (
        "l3_summary_replaces_raw_context_with_uncertainty",
        "omit_raw_text_from_llm_payload",
        "replace_raw_context_with_labeled_l3_summary_and_limits",
        "surface_partial_or_bundle_based_grounding",
        "mixed_or_uncertain_uses_l3_summary_with_limit_visibility",
        0,
        l3_document_summary_count,
        supplied_document_context_count,
    )


def _node3_r_loop_result_material(
    data_store: DataStore,
) -> Node3RLoopResultMaterial | None:
    data_id, payload = _latest_r_loop_return_summary(data_store)
    if not data_id:
        return None
    return Node3RLoopResultMaterial(
        source_data_id=data_id,
        r_loop_task_status=_text(payload, "r_loop_task_status", fallback="not_run"),
        continuation_status=_text(payload, "continuation_status", fallback="not_run"),
        budget_status=_text(payload, "budget_status", fallback="not_run"),
        final_information_granularity=_text(
            payload,
            "final_information_granularity",
            fallback="unknown",
        ),
        summary_depth_used=_int(payload, "summary_depth_used"),
        selected_entry_node_count=len(
            _string_list(payload.get("selected_entry_node_ids"))
        ),
        inspected_graph_node_count=len(
            _string_list(payload.get("inspected_graph_node_ids"))
        ),
        source_graph_node_count=len(_string_list(payload.get("source_graph_node_ids"))),
        generated_by=_text(payload, "generated_by", fallback="unknown"),
        info_class=_text(payload, "info_class", fallback="absolute"),
        semantic_judgement_status=_text(
            payload,
            "semantic_judgement_status",
            fallback="not_run",
        ),
        attitude_hint=_r_loop_result_attitude_hint(payload),
    )


def _latest_r_loop_return_summary(data_store: DataStore) -> tuple[str | None, dict[str, object]]:
    for record in reversed(data_store.list_records()):
        if record.data_type != "node_output:R_loop_return_summary_frame":
            continue
        if not isinstance(record.payload, dict):
            continue
        return record.data_id, record.payload
    return None, {}


def _r_loop_result_attitude_hint(payload: dict[str, object]) -> str:
    if not payload:
        return "not_recorded"
    task_status = _text(payload, "r_loop_task_status", fallback="not_run")
    continuation_status = _text(payload, "continuation_status", fallback="not_run")
    budget_status = _text(payload, "budget_status", fallback="not_run")
    if task_status == "sufficient":
        return "r_loop_sufficient"
    if task_status == "failed":
        return "r_loop_failed"
    if budget_status == "exhausted" or continuation_status == "stop_budget_exhausted":
        return "r_loop_budget_exhausted"
    if task_status == "partial":
        return "r_loop_partial_or_skeleton_only"
    return "not_recorded"


def node3_brief_llm_payload(frame: Node3InputBriefFrame) -> dict[str, object]:
    """내부 ID를 제거한 node_3 LLM용 payload를 만든다."""

    raw_document_payloads = _node3_raw_document_payloads(frame)
    omitted_raw_document_payloads = _node3_omitted_raw_document_payloads(frame)
    return {
        "user_question": frame.user_question,
        "brief_status": frame.brief_status,
        "actual_tool_read_doc": {
            "count": frame.actual_tool_read_doc_count,
            "document_names": list(frame.actual_tool_read_doc_documents),
        },
        "actual_tool_read_code_file": {
            "count": frame.actual_tool_read_code_file_count,
            "file_paths": list(frame.actual_tool_read_code_file_paths),
            "boundary": "This counts successful read_code_file tool outputs only. It is separate from read_doc.",
        },
        "supplied_document_context": {
            "count": frame.supplied_document_context_count,
            "source_code_context_count": frame.supplied_source_code_context_count,
            "raw_text_payload_count": frame.llm_raw_document_text_count,
            "raw_text_replaced_by_l3_summary_count": frame.raw_context_replaced_by_summary_count,
            "source_kind": (
                "document_context_pack"
                if frame.document_context_pack_frame_id
                else "tool_document_extract_records"
            ),
            "boundary": (
                "count is the preserved Node3InputBriefFrame document context count. "
                "source_code_context_count is the subset copied from read_code_file outputs. "
                "raw_text_payload_count is the number of full raw document texts actually included "
                "in this LLM payload. These are not the same count as actual read_doc tool calls."
            ),
        },
        "source_code_outlines": {
            "count": len(frame.source_code_outlines),
            "boundary": (
                "Code-built syntax inventory from successful read_code_file outputs. "
                "It lists top-level names and line numbers only; it is not a semantic summary. "
                "Use public_function_names as a coverage checklist when explaining a source file."
            ),
            "items": _node3_source_code_outline_payloads(frame),
        },
        "material_delivery_policy": _node3_material_delivery_policy_llm_payload(frame),
        "document_material_packet": {
            "status": "present" if frame.document_material_packet_frame_id else "not_recorded",
            "item_count": len(frame.document_material_items),
            "unread_candidate_count": sum(
                1 for item in frame.document_material_items if item.was_unread_candidate
            ),
            "boundary": (
                "This is a code-built document material ledger. "
                "It records roles such as search candidate, actual tool read, "
                "supplied context, excluded context, and unread candidate. "
                "It is not a semantic summary."
            ),
            "items": [
                {
                    "document_name": item.document_name,
                    "source_roles": list(item.source_roles),
                    "was_search_candidate": item.was_search_candidate,
                    "was_actual_tool_read_doc": item.was_actual_tool_read_doc,
                    "was_supplied_document_context": item.was_supplied_document_context,
                    "was_excluded_document_context": item.was_excluded_document_context,
                    "was_unread_candidate": item.was_unread_candidate,
                    "search_candidate_rank": item.search_candidate_rank,
                    "actual_read_rank": item.actual_read_rank,
                    "supplied_context_rank": item.supplied_context_rank,
                    "excluded_context_rank": item.excluded_context_rank,
                    "char_count": item.char_count,
                }
                for item in frame.document_material_items
            ],
        },
        "document_evidence_role_boundaries": {
            "boundary": (
                "For each document, claim only roles whose corresponding role flag is true. "
                "A supplied context document is usable as context, but it is not an actual read_doc "
                "tool read unless it appears in actual_tool_read_doc_document_names."
            ),
            "actual_tool_read_doc_document_names": list(frame.actual_tool_read_doc_documents),
            "actual_tool_read_code_file_paths": list(frame.actual_tool_read_code_file_paths),
            "supplied_context_document_names": [
                item.document_name
                for item in frame.document_material_items
                if item.was_supplied_document_context
            ],
            "search_candidate_document_names": [
                item.document_name
                for item in frame.document_material_items
                if item.was_search_candidate
            ],
            "excluded_context_document_names": [
                item.document_name
                for item in frame.document_material_items
                if item.was_excluded_document_context
            ],
            "unread_candidate_document_names": [
                item.document_name
                for item in frame.document_material_items
                if item.was_unread_candidate
            ],
            "supplied_but_not_actual_read_doc_document_names": [
                item.document_name
                for item in frame.document_material_items
                if item.was_supplied_document_context and not item.was_actual_tool_read_doc
            ],
        },
        "available_document_extract_count": frame.supplied_document_context_count,
        "available_raw_document_text_count": frame.llm_raw_document_text_count,
        "available_search_candidate_document_count": frame.final_search_candidate_count,
        "search_candidate_scope": {
            "legacy_search_candidate_count_is": "final_search_candidate_count",
            "final_search_candidate": {
                "count": frame.final_search_candidate_count,
                "document_names": list(frame.final_search_candidate_documents),
                "source_scope": "latest_l3_return_summary_or_node0_material_packet",
            },
            "accumulated_search_candidate": {
                "count": frame.accumulated_search_candidate_count,
                "document_names": list(frame.accumulated_search_candidate_documents),
                "source_scope": "all_l3_preserved_info_frames_in_namespace",
            },
            "boundary": (
                "Final search candidates and accumulated preserved candidates are different scopes. "
                "Use final_search_candidate for current grounding counts, and use accumulated_search_candidate "
                "only when explaining L3 revision/search churn."
            ),
        },
        "search_candidate_documents": list(frame.final_search_candidate_documents),
        "document_context_pack_status": frame.document_context_pack_status,
        "excluded_document_contexts": [
            {
                "document_name": document.document_name,
                "char_count": document.char_count,
                "selection_basis": document.selection_basis,
                "exclusion_reason": document.exclusion_reason,
                "would_exceed_budget": document.would_exceed_budget,
            }
            for document in frame.excluded_document_contexts
        ],
        "supplied_document_contexts": [
            dict(document)
            for document in raw_document_payloads
        ],
        "omitted_supplied_document_contexts": omitted_raw_document_payloads,
        "read_documents": [
            {**document, "legacy_alias": "supplied_document_context"}
            for document in raw_document_payloads
        ],
        "l3_document_summaries": {
            "count": len(frame.l3_document_summaries),
            "boundary": (
                "These are L3-generated semantic summaries of individual document extracts. "
                "plain_document_summary is relative/direct_record/one_document_to_one_summary. "
                "task_relevant_summary is mixed/source_bundle/one_document_plus_task_context. "
                "They do not replace the original supplied document text."
            ),
            "items": [
                {
                    "document_name": summary.document_name,
                    "source_char_count": summary.source_char_count,
                    "summary_status": summary.summary_status,
                    "plain_document_summary": summary.plain_document_summary,
                    "plain_summary_info_class": summary.plain_summary_info_class,
                    "plain_summary_source_mode": summary.plain_summary_source_mode,
                    "plain_summary_claim_alignment": summary.plain_summary_claim_alignment,
                    "task_relevant_summary": summary.task_relevant_summary,
                    "task_relevant_summary_info_class": summary.task_relevant_summary_info_class,
                    "task_relevant_summary_source_mode": summary.task_relevant_summary_source_mode,
                    "task_relevant_summary_claim_alignment": (
                        summary.task_relevant_summary_claim_alignment
                    ),
                    "summary_limit_note": summary.summary_limit_note,
                    "generated_by": summary.generated_by,
                    "semantic_judgement_status": summary.semantic_judgement_status,
                }
                for summary in frame.l3_document_summaries
            ],
        },
        "allowed_claims": [
            {
                "kind": claim.kind,
                "text": claim.text,
                "info_class": claim.info_class,
                "source_mode": claim.source_mode,
                "claim_alignment": claim.claim_alignment,
            }
            for claim in frame.allowed_claims
        ],
        "memory_selection": _node3_memory_selection_llm_payload(
            frame.memory_selection_material
        ),
        "selected_recent_memory_contexts": [
            {
                "source_turn_id": context.source_turn_id,
                "raw_user_text": context.raw_user_text,
                "raw_assistant_text": context.raw_assistant_text,
                "raw_user_text_chars": context.raw_user_text_chars,
                "raw_assistant_text_chars": context.raw_assistant_text_chars,
                "raw_user_text_truncated": context.raw_user_text_truncated,
                "raw_assistant_text_truncated": context.raw_assistant_text_truncated,
                "selection_status": context.selection_status,
                "selection_info_class": context.selection_info_class,
                "selection_reason": context.selection_reason,
                "selection_reason_generated_by": context.selection_reason_generated_by,
                "copied_from": context.copied_from,
            }
            for context in frame.selected_recent_memory_contexts
        ],
        "available_runtime_task_count": len(frame.runtime_tasks),
        "answer_basis": {
            "answer_basis_mode": frame.answer_basis_mode,
            "basis_reason_codes": list(frame.basis_reason_codes),
            "mode_selection_reason": frame.mode_selection_reason,
            "mode_selection_reason_info_class": frame.mode_selection_reason_info_class,
            "generated_by": frame.answer_basis_generated_by,
            "info_class": frame.answer_basis_info_class,
            "semantic_judgement_status": frame.answer_basis_semantic_judgement_status,
            "evidence_roles": [
                _node3_evidence_role_llm_payload(role)
                for role in frame.evidence_roles
            ],
        },
        "l_loop_result": {
            "task_status": frame.l_loop_task_status,
            "failure_level": frame.l_loop_failure_level,
            "l3_goal_match_status": frame.l3_goal_match_status,
            "l3_semantic_goal_match_status": frame.l3_semantic_goal_match_status,
            "remaining_query_attempts": frame.remaining_query_attempts,
            "remaining_read_doc_calls": frame.remaining_read_doc_calls,
            "attitude_hint": frame.l_loop_result_attitude_hint,
        },
        "r_loop_result": _node3_r_loop_result_llm_payload(
            frame.r_loop_result_material
        ),
        "runtime_task_sequence_note": (
            "This sequence is captured before node_3 report generation. "
            "Later node_3 reporting and node_4 gatekeeping tasks may appear in the final runtime ledger."
        ),
        "selected_recent_memory_source_boundary": (
            "Selected recent memory context is copied previous conversation text. "
            "It is not a read document, not an execution-record document, and not newly read evidence. "
            "Even if that conversation text mentions a document or execution record, do not describe it as a document read in this turn."
        ),
        "reporter_identity_boundary": (
            "Speak from SongRyeon's final-report perspective, not as node_0, node_1, node_2, node_3, "
            "or any other internal implementation role."
        ),
        "runtime_task_sequence": [
            {
                "step_index": task.step_index,
                "node": task.node_label,
                "mode": task.mode,
                "status": task.status,
                "model": task.model_label,
                "evidence_trace_count": task.evidence_trace_count,
                "evidence_data_count": task.evidence_data_count,
            }
            for task in frame.runtime_tasks
        ],
        "reporting_rules": list(frame.reporting_rules),
        "insufficiency_reasons": list(frame.insufficiency_reasons),
    }


def _node3_r_loop_result_llm_payload(
    material: Node3RLoopResultMaterial | None,
) -> dict[str, object]:
    if material is None:
        return {
            "status": "not_recorded",
            "boundary": "No R route result material was supplied to node_3.",
        }
    return {
        "status": "present",
        "task_status": material.r_loop_task_status,
        "continuation_status": material.continuation_status,
        "budget_status": material.budget_status,
        "final_information_granularity": material.final_information_granularity,
        "summary_depth_used": material.summary_depth_used,
        "selected_entry_node_count": material.selected_entry_node_count,
        "inspected_graph_node_count": material.inspected_graph_node_count,
        "source_graph_node_count": material.source_graph_node_count,
        "generated_by": material.generated_by,
        "info_class": material.info_class,
        "semantic_judgement_status": material.semantic_judgement_status,
        "attitude_hint": material.attitude_hint,
        "boundary": (
            "This is a code-copied R return summary ledger. "
            "It reports that an experimental R skeleton ran; it does not prove that "
            "R graph traversal fully answered the user goal."
        ),
    }


def _node3_material_delivery_policy_llm_payload(
    frame: Node3InputBriefFrame,
) -> dict[str, object]:
    return {
        "material_delivery_mode": frame.material_delivery_mode,
        "raw_document_policy": frame.raw_document_policy,
        "l3_summary_policy": frame.l3_summary_policy,
        "uncertainty_policy": frame.uncertainty_policy,
        "policy_reason_code": frame.material_policy_reason_code,
        "generated_by": frame.material_policy_generated_by,
        "info_class": frame.material_policy_info_class,
        "semantic_judgement_status": frame.material_policy_semantic_judgement_status,
        "supplied_document_context_count": frame.supplied_document_context_count,
        "l3_document_summary_count": len(frame.l3_document_summaries),
        "llm_raw_document_text_count": frame.llm_raw_document_text_count,
        "llm_l3_summary_context_count": frame.llm_l3_summary_context_count,
        "raw_context_replaced_by_summary_count": frame.raw_context_replaced_by_summary_count,
        "boundary": (
            "This is a CODE policy mapping from answer_basis_mode and L3 summary availability. "
            "It is not a semantic judgement about document importance. "
            "When raw_document_policy=omit_raw_text_from_llm_payload, original document records remain in DataStore "
            "but full raw text is omitted from this node_3 LLM payload."
        ),
    }


def _node3_raw_document_payloads(
    frame: Node3InputBriefFrame,
) -> list[dict[str, object]]:
    if frame.raw_document_policy == "omit_raw_text_from_llm_payload":
        return []
    return [
        {
            "document_name": document.document_name,
            "char_count": document.char_count,
            "text": document.text,
            "text_payload_status": "included",
        }
        for document in frame.read_documents
    ]


def _node3_omitted_raw_document_payloads(
    frame: Node3InputBriefFrame,
) -> list[dict[str, object]]:
    if frame.raw_document_policy != "omit_raw_text_from_llm_payload":
        return []
    return [
        {
            "document_name": document.document_name,
            "char_count": document.char_count,
            "text_payload_status": "omitted_by_material_delivery_policy",
            "replacement_material": "l3_document_summaries",
        }
        for document in frame.read_documents
    ]


def _node3_source_code_outline_payloads(
    frame: Node3InputBriefFrame,
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for outline in frame.source_code_outlines:
        payloads.append(
            {
                "file_path": outline.file_path,
                "language": outline.language,
                "parse_status": outline.parse_status,
                "top_level_symbol_count": outline.top_level_symbol_count,
                "public_symbol_count": outline.public_symbol_count,
                "public_function_names": list(outline.public_function_names),
                "top_level_symbols": [
                    {
                        "name": symbol.name,
                        "symbol_kind": symbol.symbol_kind,
                        "line_number": symbol.line_number,
                        "is_public": symbol.is_public,
                        "docstring_present": symbol.docstring_present,
                    }
                    for symbol in outline.top_level_symbols
                ],
                "parse_error_type": outline.parse_error_type,
            }
        )
    return payloads


def _node3_evidence_role_llm_payload(role: Node2EvidenceRole) -> dict[str, object]:
    return {
        "source_label": _safe_evidence_source_label(role.source_data_id),
        "evidence_role": role.evidence_role,
        "role_reason": role.role_reason,
        "role_reason_info_class": role.role_reason_info_class,
    }


def _safe_evidence_source_label(source_data_id: str) -> str:
    if "selected_recent_memory_context" in source_data_id:
        return "선택된 최근 기억"
    if "memory_relevance" in source_data_id:
        return "최근 기억 선택 판단"
    if "read_doc" in source_data_id or "read_artifact" in source_data_id:
        return "읽은 문서"
    if "document_context_pack" in source_data_id:
        return "문서 context pack"
    if "L3" in source_data_id or "preserved" in source_data_id or "achievement" in source_data_id:
        return "L loop 결과"
    if "route" in source_data_id:
        return "라우팅 결과"
    if "boundary" in source_data_id:
        return "메타정보 경계"
    if "handoff" in source_data_id:
        return "node_2 handoff"
    if "node2_input" in source_data_id:
        return "node_2 입력 프레임"
    return "공급된 근거 자료"


def _memory_relevance_handoff_summary(
    *,
    data_store: DataStore,
    selection_frame_id: str | None,
) -> dict[str, object]:
    if not selection_frame_id:
        return {
            "frame_id": None,
            "status": "not_recorded",
            "candidate_count": 0,
            "selected_count": 0,
            "info_class": "",
            "generated_by": "",
            "llm_call_data_id": None,
        }

    record = data_store.get_record(selection_frame_id)
    if record is None or not isinstance(record.payload, dict):
        return {
            "frame_id": None,
            "status": "not_recorded",
            "candidate_count": 0,
            "selected_count": 0,
            "info_class": "",
            "generated_by": "",
            "llm_call_data_id": None,
        }

    payload = record.payload
    llm_call_data_id = payload.get("llm_call_data_id")
    return {
        "frame_id": selection_frame_id,
        "status": _text(payload, "selection_status", fallback="not_recorded"),
        "candidate_count": len(_string_list(payload.get("candidate_frame_ids"))),
        "selected_count": len(_string_list(payload.get("selected_candidate_frame_ids"))),
        "info_class": _text(payload, "info_class", fallback=""),
        "generated_by": _text(payload, "generated_by", fallback=""),
        "llm_call_data_id": llm_call_data_id if isinstance(llm_call_data_id, str) else None,
    }


def _selected_recent_memory_context_handoff_summary(
    *,
    data_store: DataStore,
    context_frame_id: str | None,
) -> dict[str, object]:
    if not context_frame_id:
        return {
            "frame_id": None,
            "count": 0,
            "missing_count": 0,
            "generated_by": "",
            "info_class": "",
        }

    record = data_store.get_record(context_frame_id)
    if record is None or not isinstance(record.payload, dict):
        return {
            "frame_id": None,
            "count": 0,
            "missing_count": 0,
            "generated_by": "",
            "info_class": "",
        }

    payload = record.payload
    count = payload.get("selected_turn_count")
    missing_count = payload.get("missing_selected_memory_context_count")
    return {
        "frame_id": context_frame_id,
        "count": count if isinstance(count, int) else 0,
        "missing_count": missing_count if isinstance(missing_count, int) else 0,
        "generated_by": _text(payload, "generated_by", fallback=""),
        "info_class": _text(payload, "info_class", fallback=""),
    }


def _node3_memory_selection_material(
    *,
    data_store: DataStore,
    handoff_frame_id: str,
) -> Node3MemorySelectionMaterial | None:
    handoff_record = data_store.get_record(handoff_frame_id)
    if handoff_record is None or not isinstance(handoff_record.payload, dict):
        return None

    selection_frame_id = handoff_record.payload.get("memory_relevance_selection_frame_id")
    if not isinstance(selection_frame_id, str) or not selection_frame_id:
        return None

    selection_record = data_store.get_record(selection_frame_id)
    if selection_record is None or not isinstance(selection_record.payload, dict):
        return None

    payload = selection_record.payload
    status = _text(payload, "selection_status", fallback="not_recorded")
    selected_turn_ids = (
        _string_list(payload.get("selected_candidate_turn_ids"))
        if status == "selected"
        else []
    )
    selected_frame_ids = (
        _string_list(payload.get("selected_candidate_frame_ids"))
        if status == "selected"
        else []
    )
    source_memory_item_ids = _selected_source_memory_item_ids(
        data_store=data_store,
        selection_payload=payload,
        selected_frame_ids=selected_frame_ids,
    )
    return Node3MemorySelectionMaterial(
        selected_memory_count=len(selected_turn_ids),
        memory_selection_status=status,
        memory_selection_reason=_text(payload, "selection_reason", fallback=""),
        memory_selection_info_class=_text(payload, "info_class", fallback=""),
        memory_selection_source_mode=_text(payload, "source_mode", fallback=""),
        memory_selection_claim_alignment=_text(payload, "claim_alignment", fallback=""),
        selected_candidate_turn_ids=selected_turn_ids,
        source_memory_item_ids=source_memory_item_ids if status == "selected" else [],
        source_data_id=selection_frame_id,
        generated_by=_text(payload, "generated_by", fallback=""),
    )


def _selected_recent_memory_context_frame_id(
    *,
    data_store: DataStore,
    handoff_frame_id: str,
) -> str | None:
    handoff_record = data_store.get_record(handoff_frame_id)
    if handoff_record is None or not isinstance(handoff_record.payload, dict):
        return None
    value = handoff_record.payload.get("selected_recent_memory_context_frame_id")
    if isinstance(value, str) and value:
        return value
    return None


def _node3_selected_recent_memory_contexts(
    *,
    data_store: DataStore,
    handoff_frame_id: str,
) -> list[Node3SelectedRecentMemoryContext]:
    context_frame_id = _selected_recent_memory_context_frame_id(
        data_store=data_store,
        handoff_frame_id=handoff_frame_id,
    )
    if context_frame_id is None:
        return []

    context_record = data_store.get_record(context_frame_id)
    if context_record is None or not isinstance(context_record.payload, dict):
        return []

    payload = context_record.payload
    if _text(payload, "selection_status", fallback="") != "selected":
        return []
    selection_frame_id = _text(payload, "selection_frame_id", fallback="")
    selection_payload = _payload(data_store, selection_frame_id)
    selection_reason = _text(selection_payload, "selection_reason", fallback="")
    selection_generated_by = _text(selection_payload, "generated_by", fallback="")
    contexts: list[Node3SelectedRecentMemoryContext] = []
    items = payload.get("items")
    if not isinstance(items, list):
        return contexts
    for item in items:
        if not isinstance(item, dict):
            continue
        contexts.append(
            Node3SelectedRecentMemoryContext(
                source_turn_id=_text(item, "source_turn_id", fallback=""),
                raw_user_text=str(item.get("raw_user_text") or ""),
                raw_assistant_text=str(item.get("raw_assistant_text") or ""),
                raw_user_text_chars=_int(item, "raw_user_text_chars"),
                raw_assistant_text_chars=_int(item, "raw_assistant_text_chars"),
                raw_user_text_truncated=bool(item.get("raw_user_text_truncated")),
                raw_assistant_text_truncated=bool(item.get("raw_assistant_text_truncated")),
                selection_status=_text(payload, "selection_status", fallback="selected"),
                selection_info_class=_text(item, "selection_info_class", fallback=""),
                selection_reason=selection_reason,
                selection_reason_generated_by=selection_generated_by,
                copied_from=_text(item, "copied_from", fallback=""),
            )
        )
    return contexts


def _selected_source_memory_item_ids(
    *,
    data_store: DataStore,
    selection_payload: dict[str, object],
    selected_frame_ids: list[str],
) -> list[str]:
    if not selected_frame_ids:
        return []

    packet_id = selection_payload.get("source_memory_packet_id")
    if not isinstance(packet_id, str) or not packet_id:
        return _string_list(selection_payload.get("source_memory_item_ids"))

    packet_record = data_store.get_record(packet_id)
    if packet_record is None or not isinstance(packet_record.payload, dict):
        return _string_list(selection_payload.get("source_memory_item_ids"))

    candidates = packet_record.payload.get("relevance_candidate_frames")
    if not isinstance(candidates, list):
        return _string_list(selection_payload.get("source_memory_item_ids"))

    selected_frame_id_set = set(selected_frame_ids)
    source_memory_item_ids: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("frame_id") not in selected_frame_id_set:
            continue
        source_memory_item_id = candidate.get("source_memory_item_id")
        if isinstance(source_memory_item_id, str) and source_memory_item_id:
            source_memory_item_ids.append(source_memory_item_id)
    return _unique_strings(source_memory_item_ids)


def _node3_memory_selection_llm_payload(
    material: Node3MemorySelectionMaterial | None,
) -> dict[str, object] | None:
    if material is None:
        return None
    return {
        "selected_memory_count": material.selected_memory_count,
        "memory_selection_status": material.memory_selection_status,
        "memory_selection_reason": material.memory_selection_reason,
        "memory_selection_info_class": material.memory_selection_info_class,
        "memory_selection_source_mode": material.memory_selection_source_mode,
        "memory_selection_claim_alignment": material.memory_selection_claim_alignment,
        "generated_by": material.generated_by,
    }


def _node3_l3_document_summary_materials(
    *,
    data_store: DataStore,
    id_namespace: LRunIds | None,
) -> list[Node3L3DocumentSummaryMaterial]:
    materials: list[Node3L3DocumentSummaryMaterial] = []
    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if record.data_type != "node_output:L3_per_document_summary_frame":
            continue
        if not isinstance(record.payload, dict):
            continue
        payload = record.payload
        document_name = _text(payload, "source_document_name", fallback="")
        source_data_id = _text(payload, "frame_id", fallback=record.data_id)
        summary_status = _text(payload, "summary_status", fallback="")
        generated_by = _text(payload, "generated_by", fallback="")
        semantic_status = _text(payload, "semantic_judgement_status", fallback="")
        if not document_name or not summary_status or not generated_by or not semantic_status:
            continue
        materials.append(
            Node3L3DocumentSummaryMaterial(
                document_name=document_name,
                source_char_count=_int(payload, "source_char_count"),
                summary_status=summary_status,
                plain_document_summary=_text(
                    payload,
                    "plain_document_summary",
                    fallback="",
                ),
                plain_summary_info_class=_text(
                    payload,
                    "plain_summary_info_class",
                    fallback="relative",
                ),
                plain_summary_source_mode=_text(
                    payload,
                    "plain_summary_source_mode",
                    fallback="direct_record",
                ),
                plain_summary_claim_alignment=_text(
                    payload,
                    "plain_summary_claim_alignment",
                    fallback="one_document_to_one_summary",
                ),
                task_relevant_summary=_text(
                    payload,
                    "task_relevant_summary",
                    fallback="",
                ),
                task_relevant_summary_info_class=_text(
                    payload,
                    "task_relevant_summary_info_class",
                    fallback="mixed",
                ),
                task_relevant_summary_source_mode=_text(
                    payload,
                    "task_relevant_summary_source_mode",
                    fallback="source_bundle",
                ),
                task_relevant_summary_claim_alignment=_text(
                    payload,
                    "task_relevant_summary_claim_alignment",
                    fallback="one_document_plus_task_context",
                ),
                summary_limit_note=_text(payload, "summary_limit_note", fallback=""),
                generated_by=generated_by,
                semantic_judgement_status=semantic_status,
                source_data_id=source_data_id,
            )
        )
    return materials


def _read_documents(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> list[Node3BriefDocument]:
    pack_payload = latest_document_context_pack_payload(
        data_store,
        id_namespace=id_namespace,
    )
    if pack_payload:
        documents = _packed_read_documents(pack_payload)
        documents.extend(
            _read_code_documents(
                data_store,
                id_namespace=id_namespace,
                existing_source_data_ids={document.source_data_id for document in documents},
            )
        )
        return documents

    documents: list[Node3BriefDocument] = []
    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not _is_document_extract_record(record.data_type):
            continue
        if not isinstance(record.payload, dict):
            continue
        text = record.payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        doc_id = record.payload.get("doc_id")
        char_count = record.payload.get("char_count")
        documents.append(
            Node3BriefDocument(
                document_name=_document_name(doc_id),
                char_count=char_count if isinstance(char_count, int) else len(text),
                text=text,
                source_data_id=record.data_id,
            )
        )
    documents.extend(
        _read_code_documents(
            data_store,
            id_namespace=id_namespace,
            existing_source_data_ids={document.source_data_id for document in documents},
        )
    )
    return documents


def _read_code_documents(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
    existing_source_data_ids: set[str],
) -> list[Node3BriefDocument]:
    """read_code_file 결과를 node_3가 읽을 수 있는 source-code context로 복사한다."""

    documents: list[Node3BriefDocument] = []
    for record in data_store.list_records():
        if record.data_id in existing_source_data_ids:
            continue
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not _is_code_extract_record(record.data_type):
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get("read_status") != "ok":
            continue
        text = record.payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        file_path = record.payload.get("file_path")
        char_count = record.payload.get("char_count")
        documents.append(
            Node3BriefDocument(
                document_name=file_path if isinstance(file_path, str) and file_path else "읽은 코드 파일",
                char_count=char_count if isinstance(char_count, int) else len(text),
                text=text,
                source_data_id=record.data_id,
            )
        )
    return documents


def _packed_read_documents(pack_payload: dict[str, object]) -> list[Node3BriefDocument]:
    included_documents = pack_payload.get("included_documents")
    if not isinstance(included_documents, list):
        return []
    documents: list[Node3BriefDocument] = []
    pack_frame_id = _text(pack_payload, "frame_id", fallback="")
    for item in included_documents:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text:
            continue
        char_count = item.get("char_count")
        documents.append(
            Node3BriefDocument(
                document_name=_document_name(item.get("doc_id")),
                char_count=char_count if isinstance(char_count, int) else len(text),
                text=text,
                source_data_id=pack_frame_id,
            )
        )
    return documents


def _excluded_document_contexts(
    pack_payload: dict[str, object],
) -> list[Node3ExcludedDocumentContext]:
    excluded_documents = pack_payload.get("excluded_documents")
    if not isinstance(excluded_documents, list):
        return []
    pack_frame_id = _text(pack_payload, "frame_id", fallback="")
    contexts: list[Node3ExcludedDocumentContext] = []
    for item in excluded_documents:
        if not isinstance(item, dict):
            continue
        char_count = item.get("char_count")
        contexts.append(
            Node3ExcludedDocumentContext(
                document_name=_document_name(item.get("doc_id")),
                char_count=char_count if isinstance(char_count, int) else 0,
                selection_basis=_text(item, "selection_basis", fallback="unknown"),
                exclusion_reason=_text(item, "exclusion_reason", fallback="excluded_due_to_context_budget"),
                would_exceed_budget=bool(item.get("would_exceed_budget")),
                source_data_id=pack_frame_id,
            )
        )
    return contexts


def _node3_document_material_items(
    material_payload: dict[str, object],
) -> list[Node0DocumentMaterialItem]:
    raw_items = material_payload.get("items")
    if not isinstance(raw_items, list):
        return []
    items: list[Node0DocumentMaterialItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        doc_id = _text(raw_item, "doc_id", fallback="")
        document_name = _text(raw_item, "document_name", fallback="")
        if not doc_id or not document_name:
            continue
        items.append(
            Node0DocumentMaterialItem(
                doc_id=doc_id,
                document_name=document_name,
                source_roles=_string_list(raw_item.get("source_roles")),
                was_search_candidate=bool(raw_item.get("was_search_candidate")),
                was_actual_tool_read_doc=bool(raw_item.get("was_actual_tool_read_doc")),
                was_supplied_document_context=bool(
                    raw_item.get("was_supplied_document_context")
                ),
                was_excluded_document_context=bool(
                    raw_item.get("was_excluded_document_context")
                ),
                was_unread_candidate=bool(raw_item.get("was_unread_candidate")),
                search_candidate_rank=_int(raw_item, "search_candidate_rank"),
                actual_read_rank=_int(raw_item, "actual_read_rank"),
                supplied_context_rank=_int(raw_item, "supplied_context_rank"),
                excluded_context_rank=_int(raw_item, "excluded_context_rank"),
                char_count=_int(raw_item, "char_count"),
                source_trace_ids=_string_list(raw_item.get("source_trace_ids")),
                source_data_ids=_string_list(raw_item.get("source_data_ids")),
            )
        )
    return items


def _document_context_pack_status(pack_payload: dict[str, object]) -> str:
    if not pack_payload:
        return "not_recorded"
    included = pack_payload.get("included_document_count")
    excluded = pack_payload.get("excluded_document_count")
    if included == 0 and excluded == 0:
        return "no_candidates"
    return "packed"


def _final_search_candidate_documents(
    *,
    document_material_items: list[Node0DocumentMaterialItem],
    l_loop_return_summary: dict[str, object],
) -> list[str]:
    """최신 L return/material packet 기준 search candidate 문서를 doc_id identity로 표시한다."""

    doc_ids = [
        item.doc_id
        for item in document_material_items
        if item.was_search_candidate and item.doc_id
    ]
    if not doc_ids:
        doc_ids = _string_list(l_loop_return_summary.get("search_result_doc_ids"))
    return _read_doc_display_labels(_unique_strings(doc_ids))


def _accumulated_search_candidate_documents(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> list[str]:
    """L3 preserved frame 전체의 검색 후보를 doc_id identity 기준으로 모은다."""

    doc_ids: list[str] = []
    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not record.data_type.startswith("node_output:L3") or "preserved_info_frame" not in record.data_type:
            continue
        if not isinstance(record.payload, dict):
            continue
        candidates = record.payload.get("candidates")
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            doc_id = candidate.get("doc_id")
            if isinstance(doc_id, str) and doc_id.strip():
                doc_ids.append(doc_id.strip())
    return _read_doc_display_labels(_unique_strings(doc_ids))


def _runtime_tasks(
    movements: list[NodeMovement],
    assigned_model_by_node: dict[str, str],
) -> list[Node3BriefRuntimeTask]:
    tasks: list[Node3BriefRuntimeTask] = []
    for movement in sorted(movements, key=lambda item: item.step_index):
        tasks.append(
            Node3BriefRuntimeTask(
                step_index=movement.step_index,
                node_label=movement.node_id,
                mode=movement.mode or "unknown",
                status=movement.status,
                model_label=assigned_model_by_node.get(movement.node_id, "CODE/LOCAL_RUNTIME"),
                evidence_trace_count=len(
                    _unique_strings([*movement.input_trace_ids, *movement.output_trace_ids])
                ),
                evidence_data_count=len(
                    _unique_strings([*movement.input_data_ids, *movement.output_data_ids])
                ),
            )
        )
    return tasks


def _runtime_task_trace_ids(movements: list[NodeMovement]) -> list[str]:
    return _unique_strings(
        [
            trace_id
            for movement in movements
            for trace_id in [*movement.input_trace_ids, *movement.output_trace_ids]
        ]
    )


def _runtime_task_data_ids(movements: list[NodeMovement]) -> list[str]:
    return _unique_strings(
        [
            data_id
            for movement in movements
            for data_id in [*movement.input_data_ids, *movement.output_data_ids]
        ]
    )


def _count_records_with_type_prefix(
    data_store: DataStore,
    prefix: str,
    *,
    id_namespace: LRunIds | None,
) -> int:
    return sum(
        1
        for record in data_store.list_records()
        if record.data_type.startswith(prefix)
        and _record_in_namespace(record.data_id, id_namespace=id_namespace)
    )


def _count_records_by_type(data_store: DataStore, data_type: str) -> int:
    return sum(1 for record in data_store.list_records() if record.data_type == data_type)


def _document_extract_counts(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> dict[str, object]:
    raw_count = 0
    reportable_count = 0
    empty_count = 0
    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not _is_document_extract_record(record.data_type):
            continue
        raw_count += 1
        payload = record.payload if isinstance(record.payload, dict) else {}
        text = payload.get("text") if isinstance(payload, dict) else None
        if isinstance(text, str) and text.strip():
            reportable_count += 1
        else:
            empty_count += 1
    pack_payload = latest_document_context_pack_payload(
        data_store,
        id_namespace=id_namespace,
    )
    pack_frame_id = _text(pack_payload, "frame_id", fallback="")
    pack_included = _int(pack_payload, "included_document_count")
    pack_excluded = _int(pack_payload, "excluded_document_count")
    pack_cutoff_reason = _text(pack_payload, "cutoff_reason", fallback="")
    if pack_frame_id:
        reportable_count = pack_included
    return {
        "raw": raw_count,
        "reportable": reportable_count,
        "empty": empty_count,
        "pack_frame_id": pack_frame_id,
        "pack_included": pack_included,
        "pack_excluded": pack_excluded,
        "pack_cutoff_reason": pack_cutoff_reason,
    }


def _code_extract_counts(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> dict[str, int]:
    raw_count = 0
    reportable_count = 0
    empty_count = 0
    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not _is_code_extract_record(record.data_type):
            continue
        raw_count += 1
        payload = record.payload if isinstance(record.payload, dict) else {}
        text = payload.get("text") if isinstance(payload, dict) else None
        if payload.get("read_status") == "ok" and isinstance(text, str) and text.strip():
            reportable_count += 1
        else:
            empty_count += 1
    return {
        "raw": raw_count,
        "reportable": reportable_count,
        "empty": empty_count,
    }


def _blocked_same_turn_l_reroute_request_count(data_store: DataStore) -> int:
    count = 0
    for frame in _same_turn_l_reroute_controller_payloads(data_store):
        if frame.get("node1_route") != "L":
            continue
        if frame.get("controller_decision") != "close_route_2":
            continue
        count += 1
    return count


def _same_turn_l_reroute_controller_decisions(data_store: DataStore) -> list[str]:
    decisions: list[str] = []
    for frame in _same_turn_l_reroute_controller_payloads(data_store):
        decisions.append(
            "run="
            f"{frame.get('current_run_index', '?')} "
            f"node1_route={frame.get('node1_route', 'unknown')} "
            f"decision={frame.get('controller_decision', 'unknown')} "
            f"reason={frame.get('decision_reason', 'unknown')}"
        )
    return _unique_strings(decisions)


def _same_turn_l_reroute_controller_payloads(data_store: DataStore) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for record in data_store.list_records():
        if record.data_type != "node_output:same_turn_l_reroute_controller_frame":
            continue
        if isinstance(record.payload, dict):
            frames.append(record.payload)
    return frames


def _latest_l_loop_return_summary(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> tuple[str | None, dict[str, object]]:
    latest_id: str | None = None
    latest_payload: dict[str, object] = {}
    for record in data_store.list_records():
        if record.data_type != "node_output:l_loop_return_summary_frame":
            continue
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if isinstance(record.payload, dict):
            latest_id = record.data_id
            latest_payload = record.payload
    return latest_id, latest_payload


def _latest_document_material_packet(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> tuple[str | None, dict[str, object]]:
    latest_id: str | None = None
    latest_payload: dict[str, object] = {}
    for record in data_store.list_records():
        if record.data_type != "node_output:node0_document_material_packet_frame":
            continue
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if isinstance(record.payload, dict):
            latest_id = record.data_id
            latest_payload = record.payload
    return latest_id, latest_payload


def _actual_tool_read_doc_documents(
    *,
    data_store: DataStore,
    l_loop_return_summary: dict[str, object],
    id_namespace: LRunIds | None,
) -> list[str]:
    doc_ids: list[str] = []
    for doc_id in _string_list(l_loop_return_summary.get("read_doc_ids")):
        doc_ids.append(doc_id)

    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not _is_document_extract_record(record.data_type):
            continue
        if not isinstance(record.payload, dict):
            continue
        text = record.payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        doc_id = record.payload.get("doc_id")
        if isinstance(doc_id, str) and doc_id.strip():
            doc_ids.append(doc_id.strip())
        else:
            doc_ids.append(record.data_id)
    return _read_doc_display_labels(_unique_strings(doc_ids))


def _actual_tool_read_doc_count(
    *,
    data_store: DataStore,
    l_loop_return_summary: dict[str, object],
    id_namespace: LRunIds | None,
    document_names: list[str],
) -> int:
    if document_names:
        return len(document_names)
    summary_count = l_loop_return_summary.get("actual_read_doc_count")
    if isinstance(summary_count, int) and summary_count >= 0:
        return summary_count
    return sum(
        1
        for record in data_store.list_records()
        if _record_in_namespace(record.data_id, id_namespace=id_namespace)
        and _is_document_extract_record(record.data_type)
        and isinstance(record.payload, dict)
        and isinstance(record.payload.get("text"), str)
        and bool(str(record.payload.get("text") or "").strip())
    )


def _actual_tool_read_code_file_paths(
    *,
    data_store: DataStore,
    l_loop_return_summary: dict[str, object],
    id_namespace: LRunIds | None,
) -> list[str]:
    file_paths: list[str] = []
    for file_path in _string_list(l_loop_return_summary.get("read_code_file_paths")):
        file_paths.append(file_path)

    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not _is_code_extract_record(record.data_type):
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get("read_status") != "ok":
            continue
        text = record.payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        file_path = record.payload.get("file_path")
        if isinstance(file_path, str) and file_path.strip():
            file_paths.append(file_path.strip())
    return _unique_strings(file_paths)


def _supplied_source_code_context_count(
    *,
    data_store: DataStore,
    read_documents: list[Node3BriefDocument],
) -> int:
    count = 0
    for document in read_documents:
        record = data_store.get_record(document.source_data_id)
        if record is not None and _is_code_extract_record(record.data_type):
            count += 1
    return count


def _source_code_outlines(
    *,
    data_store: DataStore,
    read_documents: list[Node3BriefDocument],
) -> list[Node3SourceCodeOutline]:
    outlines: list[Node3SourceCodeOutline] = []
    for document in read_documents:
        record = data_store.get_record(document.source_data_id)
        if record is None or not _is_code_extract_record(record.data_type):
            continue
        payload = record.payload if isinstance(record.payload, dict) else {}
        if payload.get("read_status") != "ok":
            continue
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        file_path = payload.get("file_path")
        if not isinstance(file_path, str) or not file_path.strip():
            file_path = document.document_name
        outlines.append(
            _build_source_code_outline(
                file_path=file_path,
                text=text,
                source_data_id=record.data_id,
            )
        )
    return outlines


def _build_source_code_outline(
    *,
    file_path: str,
    text: str,
    source_data_id: str,
) -> Node3SourceCodeOutline:
    language = _source_code_language(file_path)
    if language != "python":
        return Node3SourceCodeOutline(
            file_path=file_path,
            language=language,
            parse_status="unsupported_language",
            source_data_id=source_data_id,
            top_level_symbol_count=0,
            public_symbol_count=0,
            public_function_names=[],
            top_level_symbols=[],
        )

    try:
        tree = ast.parse(text, filename=file_path)
    except SyntaxError as exc:
        return Node3SourceCodeOutline(
            file_path=file_path,
            language=language,
            parse_status="parse_failed",
            source_data_id=source_data_id,
            top_level_symbol_count=0,
            public_symbol_count=0,
            public_function_names=[],
            top_level_symbols=[],
            parse_error_type=type(exc).__name__,
        )

    symbols: list[Node3SourceCodeSymbol] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            symbols.append(_source_code_symbol(node.name, "function", node.lineno, ast.get_docstring(node) is not None))
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols.append(
                _source_code_symbol(
                    node.name,
                    "async_function",
                    node.lineno,
                    ast.get_docstring(node) is not None,
                )
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(_source_code_symbol(node.name, "class", node.lineno, ast.get_docstring(node) is not None))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for name in _assigned_uppercase_names(node):
                symbols.append(_source_code_symbol(name, "constant", node.lineno, False))

    public_function_names = [
        symbol.name
        for symbol in symbols
        if symbol.is_public and symbol.symbol_kind in {"function", "async_function"}
    ]
    return Node3SourceCodeOutline(
        file_path=file_path,
        language=language,
        parse_status="parsed",
        source_data_id=source_data_id,
        top_level_symbol_count=len(symbols),
        public_symbol_count=sum(1 for symbol in symbols if symbol.is_public),
        public_function_names=public_function_names,
        top_level_symbols=symbols,
    )


def _source_code_symbol(
    name: str,
    symbol_kind: str,
    line_number: int,
    docstring_present: bool,
) -> Node3SourceCodeSymbol:
    return Node3SourceCodeSymbol(
        name=name,
        symbol_kind=symbol_kind,
        line_number=line_number,
        is_public=not name.startswith("_"),
        docstring_present=docstring_present,
    )


def _assigned_uppercase_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]

    names: list[str] = []
    for target in targets:
        names.extend(_uppercase_names_from_target(target))
    return _unique_strings(names)


def _uppercase_names_from_target(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name) and target.id.isupper():
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_uppercase_names_from_target(element))
        return names
    return []


def _source_code_language(file_path: str) -> str:
    normalized = file_path.lower().strip()
    if normalized.endswith(".py"):
        return "python"
    return "unsupported"


def _l_loop_result_attitude_hint(payload: dict[str, object]) -> str:
    if not payload:
        return "not_recorded"
    task_status = _text(payload, "l_loop_task_status", fallback="unknown")
    failure_level = _text(payload, "failure_level", fallback="unknown")
    goal_match = _text(payload, "l3_goal_match_status", fallback="not_run")
    semantic_match = _text(payload, "l3_semantic_goal_match_status", fallback="not_run")
    if task_status == "achieved" and failure_level == "none":
        return "l_loop_achieved"
    if failure_level == "budget_exhausted":
        return "l_loop_budget_exhausted"
    if (
        task_status in {"partial", "failed", "unknown"}
        or goal_match in {"partial", "missing"}
        or semantic_match in {"partial", "missing"}
    ):
        return "l_loop_partial_or_failed"
    return "l_loop_missing_or_uncertain"


def _same_turn_l_reroute_controller_ids(data_store: DataStore) -> list[str]:
    return [
        record.data_id
        for record in data_store.list_records()
        if record.data_type == "node_output:same_turn_l_reroute_controller_frame"
    ]


def _count_l_internal_revision_records(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> int:
    revision_types = {
        "node_output:L2_revision_query_frame",
        "node_output:L3_revision_achievement_frame",
    }
    return sum(
        1
        for record in data_store.list_records()
        if record.data_type in revision_types
        and _record_in_namespace(record.data_id, id_namespace=id_namespace)
    )


def _has_legacy_or_typed_l_output(
    *,
    data_store: DataStore,
    l_loop_output_ids: list[str],
    legacy_id: str,
    type_fragment: str,
) -> bool:
    if legacy_id in l_loop_output_ids:
        return True
    for data_id in l_loop_output_ids:
        record = data_store.get_record(data_id)
        if record is not None and type_fragment in record.data_type:
            return True
    return False


def _is_document_extract_record(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_doc") or data_type.startswith("tool_result:read_artifact")


def _is_code_extract_record(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_code_file")


def _route_path(route_ids: list[str], *, actual_l_run_count: int) -> list[str]:
    path: list[str] = []
    l_route_seen = 0
    for route_id in route_ids:
        route = _route_value(route_id)
        if route == "L":
            l_route_seen += 1
            if l_route_seen <= actual_l_run_count:
                path.append("1:route=L")
                path.append("0:targeted_memory_supply")
                path.append(f"L:L1_L2_tools_L3(run={l_route_seen})")
                path.append("0:loop_return_summary")
            else:
                path.append("1:route=L_requested")
                path.append("L:top_level_reroute_blocked_by_controller")
        elif route == "2":
            path.append("1:route=2")
            path.append("0:final_trace_for_2")
        elif route == "R":
            path.append("1:route=R_experimental")
            path.append("0:r_loop_graph_guide_handoff")
            path.append("R:R1_R2_R3_experimental_skeleton")
            path.append("1:route=2_after_R_experimental")
            path.append("0:final_trace_for_2")
    return path


def _route_value(route_id: str) -> str | None:
    if route_id == "route:L" or route_id.endswith(":route:L"):
        return "L"
    if route_id == "route:2" or route_id.endswith(":route:2"):
        return "2"
    if route_id == "route:R" or route_id.endswith(":route:R"):
        return "R"
    return None


def _document_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "읽은 문서"
    normalized = value.replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] or "읽은 문서"


def _read_doc_display_labels(doc_ids: list[str]) -> list[str]:
    """같은 파일명이 여러 경로에 있으면 전체 doc_id로 구분해 표시한다."""

    name_counts: dict[str, int] = {}
    for doc_id in doc_ids:
        name = _document_name(doc_id)
        name_counts[name] = name_counts.get(name, 0) + 1

    labels: list[str] = []
    for doc_id in doc_ids:
        name = _document_name(doc_id)
        label = doc_id.replace("\\", "/").strip("/") if name_counts.get(name, 0) > 1 else name
        labels.append(label or name)
    return labels


def _payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    if not data_id:
        return {}
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return {}
    return record.payload


def _candidate_by_frame_id(packet_payload: dict[str, object]) -> dict[str, dict[str, object]]:
    candidates = packet_payload.get("relevance_candidate_frames")
    if not isinstance(candidates, list):
        return {}
    result: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        frame_id = candidate.get("frame_id")
        if isinstance(frame_id, str) and frame_id:
            result[frame_id] = candidate
    return result


def _raw_conversation_by_turn_id(
    recent_raw_conversation: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for entry in recent_raw_conversation:
        turn_id = _raw_conversation_text(entry, "turn_id")
        if turn_id:
            result[turn_id] = entry
    return result


def _raw_conversation_text(entry: dict[str, str], field_kind: str) -> str | None:
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
    for field_name in field_names_by_kind.get(field_kind, []):
        value = entry.get(field_name)
        if isinstance(value, str):
            return value
    return None


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _text(payload: dict[str, object], field_name: str, *, fallback: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def _int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    return value if isinstance(value, int) else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _current_namespace_ids(
    data_ids: list[str],
    *,
    id_namespace: LRunIds | None,
) -> list[str]:
    return [
        data_id
        for data_id in data_ids
        if _record_in_namespace(data_id, id_namespace=id_namespace)
    ]


def _record_in_namespace(data_id: str, *, id_namespace: LRunIds | None) -> bool:
    if id_namespace is None:
        return True
    return id_namespace.owns_data_id(data_id)


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
