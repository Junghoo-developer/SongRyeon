from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    NodeMovement,
    Node2HandoffFrame,
    Node3BriefClaim,
    Node3BriefDocument,
    Node3InputBriefFrame,
    Node3BriefRuntimeTask,
    validate_node2_handoff_frame,
    validate_node3_input_brief_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds


NODE2_HANDOFF_FRAME_DATA_ID = "node_2:handoff_frame"
NODE3_INPUT_BRIEF_FRAME_DATA_ID = "node_3:input_brief_frame"


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
    reportable_document_count = document_counts["reportable"]
    raw_document_extract_record_count = document_counts["raw"]
    empty_document_extract_record_count = document_counts["empty"]
    read_doc_count = reportable_document_count
    actual_l_run_count = _count_records_by_type(data_store, "node_output:L_loop_run_frame")
    blocked_reroute_count = _blocked_same_turn_l_reroute_request_count(data_store)
    controller_decisions = _same_turn_l_reroute_controller_decisions(data_store)
    l_internal_revision_count = _count_l_internal_revision_records(
        data_store,
        id_namespace=id_namespace,
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
        if search_result_count < 1 and reportable_document_count < 1:
            insufficiency_reasons.append("missing_l_evidence_result")

    has_blocker = any(reason.startswith("missing_") for reason in insufficiency_reasons[:3])
    handoff_status = "blocked" if has_blocker else "insufficient" if insufficiency_reasons else "ready"
    source_data_ids = _unique_strings(
        [
            node2_input_frame_id,
            final_memory_packet_id,
            turn_outcome_id,
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
        read_doc_count=read_doc_count,
        actual_l_run_count=actual_l_run_count,
        blocked_same_turn_l_reroute_request_count=blocked_reroute_count,
        same_turn_l_reroute_controller_decisions=controller_decisions,
        l_internal_revision_count=l_internal_revision_count,
        brief_available=reportable_document_count > 0,
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
    search_candidate_documents = _search_candidate_documents(
        data_store,
        id_namespace=id_namespace,
    )
    runtime_tasks = _runtime_tasks(
        runtime_movements or [],
        assigned_model_by_node or {},
    )
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
    if not read_documents and not allowed_claims and not runtime_tasks:
        insufficiency_reasons.append("no_document_or_claim_material")

    runtime_trace_ids = _runtime_task_trace_ids(runtime_movements or [])
    runtime_data_ids = _runtime_task_data_ids(runtime_movements or [])
    frame = Node3InputBriefFrame(
        frame_id=brief_frame_id,
        turn_id=turn_id,
        user_question=user_question,
        brief_status="ready" if not insufficiency_reasons else "insufficient",
        handoff_frame_id=handoff_frame_id,
        read_documents=read_documents,
        search_candidate_count=len(search_candidate_documents),
        search_candidate_documents=search_candidate_documents,
        allowed_claims=allowed_claims,
        runtime_tasks=runtime_tasks,
        reporting_rules=[
            "사용자 질문에 직접 답한다.",
            "문서 재료가 있으면 문서나 데이터가 없다고 말하지 않는다.",
            "답변 첫머리의 '근거 기준:' 블록은 code가 Node3InputBriefFrame의 절대 count로 고정 생성한다.",
            "node_3 LLM은 읽은 문서 수, 검색 후보 문서 수, 현재 턴 실행 순서 자료 수를 직접 쓰지 않고 본문만 작성한다.",
            "검색 후보 문서는 원문을 읽은 문서가 아니다. 검색 후보만 보고 읽은 문서처럼 말하지 않는다.",
            "현재 턴 실행 순서 자료가 있으면 실행 순서와 작업 장부 설명의 근거로 사용할 수 있다.",
            "해석, 정의, 평가, 요약을 말할 때는 답변 안에 근거 기준을 짧게 밝히고, 문서/허용 주장/현재 턴 실행 순서 자료 중 무엇에 기대는지와 왜 그 근거로 말할 수 있는지 설명한다.",
            "너는 특정 내부 노드 그 자체가 아니라, 사용자에게 보고하는 송련의 최종 응답자 관점으로 말한다.",
            "node_0/node_1/node_2/node_3 같은 내부 역할명은 자기정체성으로 쓰지 않고, 필요할 때 실행 경로 설명에만 제한적으로 쓴다.",
            "내부 추적용 raw ID를 답변 본문에 쓰지 않는다.",
            "문서 내용의 최종 진실성은 단정하지 않는다.",
        ],
        insufficiency_reasons=insufficiency_reasons,
        source_trace_ids=_unique_strings([*input_trace_ids, *runtime_trace_ids]),
        source_data_ids=_unique_strings([handoff_frame_id, *source_data_ids, *runtime_data_ids]),
    )
    validate_node3_input_brief_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_2",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
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


def node3_brief_llm_payload(frame: Node3InputBriefFrame) -> dict[str, object]:
    """내부 ID를 제거한 node_3 LLM용 payload를 만든다."""

    return {
        "user_question": frame.user_question,
        "brief_status": frame.brief_status,
        "available_document_extract_count": len(frame.read_documents),
        "available_search_candidate_document_count": frame.search_candidate_count,
        "search_candidate_documents": list(frame.search_candidate_documents),
        "read_documents": [
            {
                "document_name": document.document_name,
                "char_count": document.char_count,
                "text": document.text,
            }
            for document in frame.read_documents
        ],
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
        "available_runtime_task_count": len(frame.runtime_tasks),
        "runtime_task_sequence_note": (
            "This sequence is captured before node_3 report generation. "
            "Later node_3 reporting and node_4 gatekeeping tasks may appear in the final runtime ledger."
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


def _read_documents(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> list[Node3BriefDocument]:
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
    return documents


def _search_candidate_documents(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> list[str]:
    """L3가 보존한 검색 후보 문서명을 node_3용 안전한 형태로 모은다."""

    names: list[str] = []
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
                names.append(_document_name(doc_id))
    return _unique_strings(names)


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
) -> dict[str, int]:
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
    return path


def _route_value(route_id: str) -> str | None:
    if route_id == "route:L" or route_id.endswith(":route:L"):
        return "L"
    if route_id == "route:2" or route_id.endswith(":route:2"):
        return "2"
    return None


def _document_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "읽은 문서"
    normalized = value.replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] or "읽은 문서"


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
