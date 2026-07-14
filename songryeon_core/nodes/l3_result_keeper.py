from __future__ import annotations

import re
from dataclasses import asdict, replace
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L3AchievementFrame,
    L3PerDocumentSummaryFrame,
    L3PreservedInfoFrame,
    L3PreservedSearchCandidate,
    TraceEvent,
    validate_l3_achievement_frame,
    validate_l3_per_document_summary_frame,
    validate_l3_preserved_info_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_namespace import LRunIds


L3_PRESERVED_FRAME_DATA_ID = "L3:preserved_info_frame"
L3_ACHIEVEMENT_FRAME_DATA_ID = "L3:achievement_frame"
L3_REVISION_PRESERVED_FRAME_DATA_ID_PREFIX = "L3:revision_preserved_info"
L3_REVISION_ACHIEVEMENT_FRAME_DATA_ID_PREFIX = "L3:revision_achievement"
L3_PER_DOCUMENT_SUMMARY_FRAME_DATA_ID_PREFIX = "L3:per_document_summary"
L3_PER_DOCUMENT_SUMMARY_PROMPT_REF = "songryeon_core/prompts/l3_per_document_summary_v0.md"
L3_PER_DOCUMENT_SUMMARY_MAX_SOURCE_CHARS = 12000


def l3_revision_preserved_frame_data_id(
    attempt_index: int,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    """Return the attempt-scoped L3 preserved-info frame id for a revision pass."""

    _validate_positive_attempt_index(attempt_index)
    legacy_id = f"{L3_REVISION_PRESERVED_FRAME_DATA_ID_PREFIX}:{attempt_index:04d}"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def l3_revision_achievement_frame_data_id(
    attempt_index: int,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    """Return the attempt-scoped L3 achievement frame id for a revision pass."""

    _validate_positive_attempt_index(attempt_index)
    legacy_id = f"{L3_REVISION_ACHIEVEMENT_FRAME_DATA_ID_PREFIX}:{attempt_index:04d}"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def run_l3_result_keeper(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    l1_event: TraceEvent,
    l2_event: TraceEvent,
    extra_input_trace_ids: list[str] | None = None,
    extra_input_data_ids: list[str] | None = None,
    final_control_data_id: str | None = None,
    user_query: str = "",
    adapter: LLMAdapter | None = None,
    preserved_frame_data_id: str = L3_PRESERVED_FRAME_DATA_ID,
    achievement_frame_data_id: str = L3_ACHIEVEMENT_FRAME_DATA_ID,
    target_goal_data_id: str = "L1:goal_frame",
) -> TraceEvent:
    """L3 보존, 코드 운영 판정, LLM 의미 적합성 판단을 기록한다.

    preserved_frame_data_id / achievement_frame_data_id / target_goal_data_id는
    L루프 실행 회차별 primary ID를 주입하기 위한 값이다. 같은 턴에서 L을 다시
    돌릴 때 L3가 기존 `L3:achievement_frame`을 덮지 않게 만드는 배관이다.
    """

    # 후보와 도구 결과는 코드가 보존한다. adapter가 있으면 LLM은 그 재료가
    # 사용자 요청에 의미상 맞는지만 판단하며, 운영 count와 상태는 다시 쓰지 않는다.
    input_ref = [l1_event.event_id, l2_event.event_id]
    input_ref.extend(extra_input_trace_ids or [])
    source_data_ids = extra_input_data_ids or []
    preserved_frame = _build_preserved_frame(
        frame_id=preserved_frame_data_id,
        turn_id=turn_id,
        input_trace_ids=input_ref,
        input_data_ids=source_data_ids,
        data_store=data_store,
    )
    validate_l3_preserved_info_frame(preserved_frame)
    if adapter is not None and data_store is not None:
        try:
            # LLM 의미 판단 경로와 fallback 코드 판정 경로가 같은 achievement_frame_data_id를 써야 한다.
            # 그래야 LLM 실패가 발생해도 scoped ID 계약이 깨지지 않는다.
            achievement_frame = _build_llm_achievement_frame(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                preserved_frame=preserved_frame,
                input_trace_ids=input_ref,
                input_data_ids=source_data_ids,
                final_control_data_id=final_control_data_id,
                user_query=user_query,
                adapter=adapter,
                achievement_frame_data_id=achievement_frame_data_id,
                target_goal_data_id=target_goal_data_id,
            )
        except Exception:
            achievement_frame = _build_achievement_frame(
                frame_id=achievement_frame_data_id,
                turn_id=turn_id,
                preserved_frame=preserved_frame,
                input_trace_ids=input_ref,
                input_data_ids=source_data_ids,
                data_store=data_store,
                final_control_data_id=final_control_data_id,
                user_query=user_query,
                target_goal_data_id=target_goal_data_id,
            )
    else:
        achievement_frame = _build_achievement_frame(
            frame_id=achievement_frame_data_id,
            turn_id=turn_id,
            preserved_frame=preserved_frame,
            input_trace_ids=input_ref,
            input_data_ids=source_data_ids,
            data_store=data_store,
            final_control_data_id=final_control_data_id,
            user_query=user_query,
            target_goal_data_id=target_goal_data_id,
        )
    validate_l3_achievement_frame(achievement_frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L3",
        event_type="node_output",
        input_ref=input_ref,
        output_ref=[preserved_frame_data_id, achievement_frame_data_id],
        schema_status="passed",
    )
    if data_store is not None:
        data_store.create_record(
            data_id=preserved_frame_data_id,
            data_type="node_output:L3_preserved_info_frame",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(preserved_frame),
        )
        data_store.create_record(
            data_id=achievement_frame_data_id,
            data_type="node_output:L3_achievement_frame",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(achievement_frame),
        )
        if adapter is not None:
            record_l3_per_document_summary_frames(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                input_trace_ids=input_ref,
                input_data_ids=source_data_ids,
                user_query=user_query,
                adapter=adapter,
                preserved_frame_data_id=preserved_frame_data_id,
                target_goal_data_id=target_goal_data_id,
                frame_id_prefix=f"{preserved_frame_data_id}:per_document_summary",
            )
    return event


def run_l3_revision_result_keeper(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    attempt_index: int,
    revision_query_frame_data_id: str,
    revision_tool_source_trace_ids: list[str],
    revision_tool_source_data_ids: list[str],
    user_query: str = "",
    final_control_data_id: str | None = None,
    l1_goal_data_id: str = "L1:goal_frame",
    adapter: LLMAdapter | None = None,
    id_namespace: LRunIds | None = None,
) -> TraceEvent:
    """Re-run the L3 preservation/achievement check after one revision tool attempt.

    이 함수는 L3의 의미 판단을 새로 만들지 않는다. revision tool attempt가 남긴
    tool result/distillation/budget 같은 구조화 기록만 모아, 다음 continuation
    controller가 읽을 수 있는 attempt별 L3 프레임으로 다시 포장한다.
    """

    preserved_frame_id = l3_revision_preserved_frame_data_id(
        attempt_index,
        id_namespace=id_namespace,
    )
    achievement_frame_id = l3_revision_achievement_frame_data_id(
        attempt_index,
        id_namespace=id_namespace,
    )
    input_trace_ids = _unique_strings(revision_tool_source_trace_ids)
    input_data_ids = _unique_strings(
        [
            l1_goal_data_id,
            revision_query_frame_data_id,
            *revision_tool_source_data_ids,
        ]
    )

    preserved_frame = _build_preserved_frame(
        frame_id=preserved_frame_id,
        turn_id=turn_id,
        input_trace_ids=input_trace_ids,
        input_data_ids=input_data_ids,
        data_store=data_store,
    )
    validate_l3_preserved_info_frame(preserved_frame)
    achievement_frame = _build_achievement_frame(
        frame_id=achievement_frame_id,
        turn_id=turn_id,
        preserved_frame=preserved_frame,
        input_trace_ids=input_trace_ids,
        input_data_ids=input_data_ids,
        data_store=data_store,
        final_control_data_id=final_control_data_id,
        user_query=user_query,
        target_goal_data_id=l1_goal_data_id,
    )
    validate_l3_achievement_frame(achievement_frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L3",
        event_type="node_output",
        input_ref=input_trace_ids,
        output_ref=[preserved_frame_id, achievement_frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=preserved_frame_id,
        data_type="node_output:L3_revision_preserved_info_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(preserved_frame),
    )
    data_store.create_record(
        data_id=achievement_frame_id,
        data_type="node_output:L3_revision_achievement_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(achievement_frame),
    )
    if adapter is not None:
        record_l3_per_document_summary_frames(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            input_trace_ids=input_trace_ids,
            input_data_ids=input_data_ids,
            user_query=user_query,
            adapter=adapter,
            preserved_frame_data_id=preserved_frame_id,
            target_goal_data_id=l1_goal_data_id,
            frame_id_prefix=f"{preserved_frame_id}:per_document_summary",
        )
    return event


def record_l3_per_document_summary_frames(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    input_trace_ids: list[str],
    input_data_ids: list[str],
    user_query: str,
    adapter: LLMAdapter,
    preserved_frame_data_id: str,
    target_goal_data_id: str,
    frame_id_prefix: str = L3_PER_DOCUMENT_SUMMARY_FRAME_DATA_ID_PREFIX,
) -> list[str]:
    """실제 document extract record마다 L3 문서별 요약 frame을 기록한다."""

    source_documents = _document_extract_records_for_ids(
        data_store=data_store,
        input_data_ids=input_data_ids,
    )
    created_frame_ids: list[str] = []
    for index, source_document in enumerate(source_documents, start=1):
        frame_id = f"{frame_id_prefix}:{index:04d}"
        frame = _build_l3_per_document_summary_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame_id=frame_id,
            source_document=source_document,
            input_trace_ids=input_trace_ids,
            user_query=user_query,
            adapter=adapter,
            preserved_frame_data_id=preserved_frame_data_id,
            target_goal_data_id=target_goal_data_id,
        )
        validate_l3_per_document_summary_frame(frame)
        event = trace_store.create_event(
            turn_id=turn_id,
            actor="L3",
            event_type="node_output",
            input_ref=frame.source_trace_ids,
            output_ref=[frame_id],
            schema_status="passed" if frame.summary_status == "ran" else "failed",
        )
        data_store.create_record(
            data_id=frame_id,
            data_type="node_output:L3_per_document_summary_frame",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
        created_frame_ids.append(frame_id)
    return created_frame_ids


def _build_l3_per_document_summary_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame_id: str,
    source_document: dict[str, object],
    input_trace_ids: list[str],
    user_query: str,
    adapter: LLMAdapter,
    preserved_frame_data_id: str,
    target_goal_data_id: str,
) -> L3PerDocumentSummaryFrame:
    source_document_data_id = str(source_document["source_data_id"])
    source_doc_id = str(source_document["doc_id"])
    source_text = str(source_document.get("text") or "")
    source_trace_id = source_document.get("source_trace_id")
    source_document_name = _document_name_from_doc_id(source_doc_id)
    source_char_count = int(source_document.get("char_count") or len(source_text))
    task_source_data_ids = _unique_strings(
        [source_document_data_id, target_goal_data_id, preserved_frame_data_id]
    )
    source_text_for_llm = source_text[:L3_PER_DOCUMENT_SUMMARY_MAX_SOURCE_CHARS]
    source_text_truncated = len(source_text) > len(source_text_for_llm)
    l1_goal = _read_l1_goal_frame(
        data_store=data_store,
        input_data_ids=[target_goal_data_id],
    )
    prompt = Path(L3_PER_DOCUMENT_SUMMARY_PROMPT_REF).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="L3_document_summary",
        prompt=prompt,
        input_payload={
            "user_query": user_query,
            "l1_goal": l1_goal,
            "source_document": {
                "document_name": source_document_name,
                "char_count": source_char_count,
                "text": source_text_for_llm,
                "text_truncated": source_text_truncated,
            },
            "summary_contract": {
                "plain_document_summary_info_class": "relative",
                "plain_document_summary_source_mode": "direct_record",
                "task_relevant_summary_info_class": "mixed",
                "task_relevant_summary_source_mode": "source_bundle",
            },
        },
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=L3_PER_DOCUMENT_SUMMARY_PROMPT_REF,
        input_ref=_unique_strings(
            [
                *input_trace_ids,
                source_trace_id if isinstance(source_trace_id, str) else None,
            ]
        ),
        source_data_ids=task_source_data_ids,
        payload_validator=_validate_l3_per_document_summary_payload,
    )

    frame_source_trace_ids = _unique_strings(
        [
            *input_trace_ids,
            source_trace_id if isinstance(source_trace_id, str) else None,
            llm_result.trace_event_id,
        ]
    )
    frame_source_data_ids = _unique_strings(
        [
            *task_source_data_ids,
            llm_result.call_data_id,
        ]
    )
    generated_by = f"LLM:{llm_result.model_id}"
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        return L3PerDocumentSummaryFrame(
            frame_id=frame_id,
            turn_id=turn_id,
            source_document_data_id=source_document_data_id,
            source_doc_id=source_doc_id,
            source_document_name=source_document_name,
            source_char_count=source_char_count,
            summary_status="failed",
            plain_summary_source_data_id=source_document_data_id,
            task_relevant_summary_source_data_ids=task_source_data_ids,
            generated_by=generated_by,
            semantic_judgement_status="failed",
            summary_failure_type=llm_result.failure_type or "unknown",
            llm_call_data_id=llm_result.call_data_id,
            prompt_ref=L3_PER_DOCUMENT_SUMMARY_PROMPT_REF,
            source_trace_ids=frame_source_trace_ids,
            source_data_ids=frame_source_data_ids,
        )

    payload = llm_result.validation.payload
    summary_limit_note = str(payload.get("summary_limit_note") or "").strip()
    if source_text_truncated and not summary_limit_note:
        summary_limit_note = "원문이 L3 요약 입력 한도에서 잘려 요약 범위에 한계가 있다."

    return L3PerDocumentSummaryFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        source_document_data_id=source_document_data_id,
        source_doc_id=source_doc_id,
        source_document_name=source_document_name,
        source_char_count=source_char_count,
        summary_status="ran",
        plain_document_summary=str(payload.get("plain_document_summary") or "").strip(),
        plain_summary_source_data_id=source_document_data_id,
        task_relevant_summary=str(payload.get("task_relevant_summary") or "").strip(),
        task_relevant_summary_source_data_ids=task_source_data_ids,
        summary_limit_note=summary_limit_note,
        generated_by=generated_by,
        semantic_judgement_status="ran",
        summary_failure_type="none",
        llm_call_data_id=llm_result.call_data_id,
        prompt_ref=L3_PER_DOCUMENT_SUMMARY_PROMPT_REF,
        source_trace_ids=frame_source_trace_ids,
        source_data_ids=frame_source_data_ids,
    )


def _validate_l3_per_document_summary_payload(payload: dict[str, object]) -> None:
    for field_name in ("plain_document_summary", "task_relevant_summary"):
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"L3 document summary payload {field_name} must not be empty")
    limit_note = payload.get("summary_limit_note")
    if limit_note is not None and not isinstance(limit_note, str):
        raise TypeError("L3 document summary payload summary_limit_note must be a string")


def _document_extract_records_for_ids(
    *,
    data_store: DataStore,
    input_data_ids: list[str],
) -> list[dict[str, object]]:
    documents: list[dict[str, object]] = []
    seen_data_ids: set[str] = set()
    for data_id in input_data_ids:
        if data_id in seen_data_ids:
            continue
        seen_data_ids.add(data_id)
        record = data_store.get_record(data_id)
        if record is None or not _is_document_extract_record(record.data_type):
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        text = payload.get("text")
        doc_id = payload.get("doc_id")
        if not isinstance(text, str) or not text.strip():
            continue
        if not isinstance(doc_id, str) or not doc_id.strip():
            continue
        char_count = payload.get("char_count")
        documents.append(
            {
                "source_data_id": record.data_id,
                "source_trace_id": record.source_trace_id,
                "doc_id": doc_id.strip(),
                "text": text,
                "char_count": char_count if isinstance(char_count, int) else len(text),
            }
        )
    return documents


def _document_name_from_doc_id(doc_id: str) -> str:
    normalized = doc_id.replace("\\", "/").strip()
    return normalized.rsplit("/", 1)[-1] if normalized else doc_id


def _build_preserved_frame(
    *,
    frame_id: str,
    turn_id: str,
    input_trace_ids: list[str],
    input_data_ids: list[str],
    data_store: DataStore | None,
) -> L3PreservedInfoFrame:
    """L3가 다음 흐름에 넘길 스키마 기반 보존 프레임을 만든다."""

    candidates: list[L3PreservedSearchCandidate] = []
    if data_store is not None:
        for data_id in input_data_ids:
            record = data_store.get_record(data_id)
            if record is None:
                continue
            candidates.extend(
                _extract_search_candidates(
                    source_data_id=record.data_id,
                    source_trace_id=record.source_trace_id,
                    payload=record.payload,
                    existing_count=len(candidates),
                )
            )

    return L3PreservedInfoFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        source_trace_ids=input_trace_ids,
        source_data_ids=input_data_ids,
        judgement_status="not_judged",
        candidates=candidates,
    )


def _build_achievement_frame(
    *,
    frame_id: str,
    turn_id: str,
    preserved_frame: L3PreservedInfoFrame,
    input_trace_ids: list[str],
    input_data_ids: list[str],
    data_store: DataStore | None,
    final_control_data_id: str | None,
    user_query: str,
    target_goal_data_id: str,
) -> L3AchievementFrame:
    """L3의 검색/보존 운영 목표 달성 여부를 제한된 규칙으로 판정한다."""

    candidate_count = len(preserved_frame.candidates)
    controller_decision = _read_controller_decision(
        data_store=data_store,
        final_control_data_id=final_control_data_id,
    )
    l1_goal = _read_l1_goal_frame(data_store=data_store, input_data_ids=input_data_ids)
    target_macro_goal = str(l1_goal.get("macro_goal") or "")
    target_micro_goal = str(l1_goal.get("micro_goal") or "")
    has_query_frame = _has_l2_query_frame(input_data_ids)
    goal_match = _build_goal_match_context(
        user_query=user_query,
        preserved_frame=preserved_frame,
        data_store=data_store,
    )
    actual_read_doc_count = len(goal_match["read_doc_ids"])
    actual_read_code_file_count = len(goal_match["read_code_file_paths"])
    original_material_count = actual_read_doc_count + actual_read_code_file_count
    evidence_acquisition_status = _evidence_acquisition_status(
        candidate_count=candidate_count,
        original_material_count=original_material_count,
    )
    required_count_value = l1_goal.get("minimum_read_documents")
    original_material_required_count = (
        required_count_value
        if isinstance(required_count_value, int)
        and not isinstance(required_count_value, bool)
        and required_count_value >= 0
        else 0
    )
    original_material_requirement_status = _original_material_requirement_status(
        required_count=original_material_required_count,
        original_material_count=original_material_count,
    )

    if controller_decision == "stop_failed":
        achievement_status = "failed"
    elif controller_decision == "stop_success" and original_material_count > 0:
        achievement_status = "achieved"
    elif candidate_count > 0 or original_material_count > 0:
        achievement_status = "partial"
    else:
        achievement_status = "failed"

    if achievement_status == "achieved":
        reason = "CODE_STATUS:original_material_acquired_and_controller_stop_success"
    elif achievement_status == "partial":
        reason = (
            "CODE_STATUS:candidates_only_without_original_material"
            if evidence_acquisition_status == "candidates_only"
            else "CODE_STATUS:original_material_acquired_without_controller_stop_success"
        )
    else:
        reason = "CODE_STATUS:no_preserved_candidates_or_controller_stop_failed"

    macro_status = achievement_status
    if achievement_status == "achieved":
        macro_reason = "CODE_STATUS:macro_operation_original_material_and_stop_success"
    elif achievement_status == "partial":
        macro_reason = (
            "CODE_STATUS:macro_operation_candidates_only"
            if evidence_acquisition_status == "candidates_only"
            else "CODE_STATUS:macro_operation_original_material_without_stop_success"
        )
    else:
        macro_reason = "CODE_STATUS:macro_operation_no_candidates_or_stop_failed"

    if has_query_frame and (candidate_count > 0 or original_material_count > 0):
        micro_status = "achieved"
        micro_reason = "CODE_STATUS:micro_operation_query_frame_and_candidates_present"
    elif has_query_frame:
        micro_status = "partial"
        micro_reason = "CODE_STATUS:micro_operation_query_frame_without_candidates"
    else:
        micro_status = "failed"
        micro_reason = "CODE_STATUS:micro_operation_query_frame_missing"

    original_status = achievement_status
    (
        achievement_status,
        reason,
        macro_status,
        macro_reason,
        micro_status,
        micro_reason,
    ) = _apply_goal_match_guard(
        achievement_status=achievement_status,
        reason=reason,
        macro_status=macro_status,
        macro_reason=macro_reason,
        micro_status=micro_status,
        micro_reason=micro_reason,
        goal_match=goal_match,
    )
    generation_source = "CODE:OPERATION_CHECK"
    if achievement_status != original_status:
        generation_source = f"{generation_source}+CODE:GOAL_MATCH_GUARD"

    status_before_l1_requirement_guard = achievement_status
    (
        achievement_status,
        reason,
        macro_status,
        macro_reason,
        micro_status,
        micro_reason,
    ) = _apply_l1_requirement_count_guard(
        achievement_status=achievement_status,
        reason=reason,
        macro_status=macro_status,
        macro_reason=macro_reason,
        micro_status=micro_status,
        micro_reason=micro_reason,
        l1_goal=l1_goal,
        read_document_count=len(goal_match["read_doc_ids"]),
        read_code_file_count=len(goal_match["read_code_file_paths"]),
        source_code_evidence_expected=_source_code_evidence_expected(
            l1_goal=l1_goal,
            data_store=data_store,
            input_data_ids=input_data_ids,
        ),
    )
    if achievement_status != status_before_l1_requirement_guard:
        generation_source = f"{generation_source}+CODE:L1_REQUIREMENT_COUNT_GUARD"

    evidence_data_ids = _unique_strings(
        [
            *input_data_ids,
            preserved_frame.frame_id,
            final_control_data_id,
        ]
    )
    return L3AchievementFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        achievement_status=achievement_status,
        reason=reason,
        target_goal_data_id=target_goal_data_id,
        preserved_info_frame_id=preserved_frame.frame_id,
        candidate_count=candidate_count,
        evidence_trace_ids=input_trace_ids,
        evidence_data_ids=evidence_data_ids,
        source_trace_ids=input_trace_ids,
        source_data_ids=evidence_data_ids,
        final_control_data_id=final_control_data_id,
        controller_decision=controller_decision,
        achievement_generation_source=generation_source,
        llm_semantic_judgement_status="not_run",
        target_macro_goal=target_macro_goal,
        target_micro_goal=target_micro_goal,
        macro_achievement_status=macro_status,
        macro_achievement_reason=macro_reason,
        micro_achievement_status=micro_status,
        micro_achievement_reason=micro_reason,
        requested_doc_hint=str(goal_match["requested_doc_hint"]),
        read_doc_ids=list(goal_match["read_doc_ids"]),
        read_code_file_paths=list(goal_match["read_code_file_paths"]),
        actual_read_code_file_count=actual_read_code_file_count,
        search_result_doc_ids=list(goal_match["search_result_doc_ids"]),
        goal_match_status=str(goal_match["goal_match_status"]),
        goal_match_reason=str(goal_match["goal_match_reason"]),
        semantic_goal_match_status="not_run",
        semantic_goal_match_reason="CODE_STATUS:llm_semantic_goal_match_not_run",
        actual_read_doc_count=actual_read_doc_count,
        original_material_count=original_material_count,
        evidence_acquisition_status=evidence_acquisition_status,
        original_material_required_count=original_material_required_count,
        original_material_requirement_status=original_material_requirement_status,
    )


def _build_llm_achievement_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    preserved_frame: L3PreservedInfoFrame,
    input_trace_ids: list[str],
    input_data_ids: list[str],
    final_control_data_id: str | None,
    user_query: str,
    adapter: LLMAdapter,
    achievement_frame_data_id: str,
    target_goal_data_id: str,
) -> L3AchievementFrame:
    """코드 운영 판정에 LLM의 의미 적합성 판단만 결합한다."""

    prompt_ref = "songryeon_core/prompts/l3_result_keeper_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    l1_goal = _read_l1_goal_frame(data_store=data_store, input_data_ids=input_data_ids)
    goal_match = _build_goal_match_context(
        user_query=user_query,
        preserved_frame=preserved_frame,
        data_store=data_store,
    )
    read_doc_ids = list(goal_match["read_doc_ids"])
    read_code_file_paths = list(goal_match["read_code_file_paths"])
    search_result_doc_ids = list(goal_match["search_result_doc_ids"])
    operation_frame = _build_achievement_frame(
        frame_id=achievement_frame_data_id,
        turn_id=turn_id,
        preserved_frame=preserved_frame,
        input_trace_ids=input_trace_ids,
        input_data_ids=input_data_ids,
        data_store=data_store,
        final_control_data_id=final_control_data_id,
        user_query=user_query,
        target_goal_data_id=target_goal_data_id,
    )
    input_payload = {
        "user_query": user_query,
        "l1_goal": _l1_semantic_goal_payload(l1_goal),
        "l3_judgement_contract": _l3_judgement_contract(l1_goal),
        "code_operation_status": {
            "achievement_status": operation_frame.achievement_status,
            "macro_achievement_status": operation_frame.macro_achievement_status,
            "micro_achievement_status": operation_frame.micro_achievement_status,
            "goal_match_status": operation_frame.goal_match_status,
            "has_read_document_material": bool(read_doc_ids),
            "has_read_code_material": bool(read_code_file_paths),
            "has_search_candidates": bool(search_result_doc_ids),
            "evidence_acquisition_status": operation_frame.evidence_acquisition_status,
            "original_material_count": operation_frame.original_material_count,
            "original_material_requirement_status": (
                operation_frame.original_material_requirement_status
            ),
        },
        "specific_document_request": _l3_specific_request_semantic_payload(goal_match),
        "read_document_previews": [
            {
                "doc_id": preview.get("doc_id"),
                "text_preview": preview.get("text_preview"),
            }
            for preview in _read_doc_previews_from_data_store(data_store)
        ],
        "read_code_file_previews": [
            {
                "file_path": preview.get("file_path"),
                "text_preview": preview.get("text_preview"),
            }
            for preview in _read_code_file_previews_from_data_store(data_store)
        ],
        "candidate_previews": [
            {
                "doc_id": candidate.doc_id,
                "text_preview": candidate.text_preview,
            }
            for candidate in preserved_frame.candidates[:5]
        ],
    }
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="L3",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=input_trace_ids,
        source_data_ids=input_data_ids,
        payload_validator=_validate_l3_semantic_payload,
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        raise ValueError(f"L3 LLM result keeper failed: {llm_result.failure_type}")

    payload = llm_result.validation.payload
    frame_source_trace_ids = list(input_trace_ids)
    if llm_result.trace_event_id:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = _unique_strings(
        [
            *input_data_ids,
            preserved_frame.frame_id,
            final_control_data_id,
            llm_result.call_data_id,
        ]
    )
    semantic_goal_match_status = str(payload.get("semantic_goal_match_status") or "not_run").strip()
    semantic_goal_match_reason = str(
        payload.get("semantic_goal_match_reason") or "CODE_STATUS:llm_semantic_goal_match_not_run"
    ).strip()
    achievement_status = operation_frame.achievement_status
    reason = operation_frame.reason
    macro_status = operation_frame.macro_achievement_status
    macro_reason = operation_frame.macro_achievement_reason
    micro_status = operation_frame.micro_achievement_status
    micro_reason = operation_frame.micro_achievement_reason
    status_before_semantic_guard = achievement_status
    (
        achievement_status,
        reason,
        macro_status,
        macro_reason,
        micro_status,
        micro_reason,
    ) = _apply_semantic_goal_match_guard(
        achievement_status=achievement_status,
        reason=reason,
        macro_status=macro_status,
        macro_reason=macro_reason,
        micro_status=micro_status,
        micro_reason=micro_reason,
        semantic_goal_match_status=semantic_goal_match_status,
        semantic_goal_match_reason=semantic_goal_match_reason,
    )
    generation_source = (
        f"{operation_frame.achievement_generation_source}"
        f"+LLM:{llm_result.model_id}:SEMANTIC_GOAL_MATCH"
    )
    if achievement_status != status_before_semantic_guard:
        generation_source = f"{generation_source}+CODE:SEMANTIC_GOAL_GUARD"

    return replace(
        operation_frame,
        achievement_status=achievement_status,
        reason=reason,
        evidence_trace_ids=_unique_strings(frame_source_trace_ids),
        evidence_data_ids=frame_source_data_ids,
        source_trace_ids=_unique_strings(frame_source_trace_ids),
        source_data_ids=frame_source_data_ids,
        achievement_generation_source=generation_source,
        llm_semantic_judgement_status="ran",
        macro_achievement_status=macro_status,
        macro_achievement_reason=macro_reason,
        micro_achievement_status=micro_status,
        micro_achievement_reason=micro_reason,
        semantic_goal_match_status=semantic_goal_match_status,
        semantic_goal_match_reason=semantic_goal_match_reason,
    )


def _l1_semantic_goal_payload(l1_goal: dict[str, object]) -> dict[str, object]:
    """L3 의미 판단에 필요한 목표 문장만 넘기고 예산 숫자는 제외한다."""

    return {
        "macro_goal": str(l1_goal.get("macro_goal") or ""),
        "micro_goal": str(l1_goal.get("micro_goal") or ""),
        "evidence_requirement_kind": str(
            l1_goal.get("evidence_requirement_kind") or "unspecified"
        ),
        "requires_cross_document_analysis": bool(
            l1_goal.get("requires_cross_document_analysis")
        ),
        "randomness_mode": str(l1_goal.get("randomness_mode") or "not_random"),
        "l_loop_success_condition": str(
            l1_goal.get("l_loop_success_condition") or ""
        ),
    }


def _l3_specific_request_semantic_payload(
    goal_match: dict[str, object],
) -> dict[str, object]:
    """특정 문서 대응의 code 상태와 사람이 읽을 이름만 의미 판단에 제공한다."""

    return {
        "requested_doc_hint": str(goal_match.get("requested_doc_hint") or ""),
        "requested_doc_hint_source": str(
            goal_match.get("requested_doc_hint_source") or "none"
        ),
        "goal_match_status": str(
            goal_match.get("goal_match_status") or "not_applicable"
        ),
        "goal_match_reason": str(goal_match.get("goal_match_reason") or ""),
        "read_doc_ids": list(goal_match.get("read_doc_ids") or []),
        "read_code_file_paths": list(goal_match.get("read_code_file_paths") or []),
    }


def _l3_judgement_contract(l1_goal: dict[str, object]) -> list[str]:
    """LLM L3에게 전달할 판정 계약. 판단 기준을 숨은 지식이 아니라 입력에 둔다."""

    evidence_kind = str(l1_goal.get("evidence_requirement_kind") or "unspecified")
    contract = [
        "Judge the current user_query and L1 success condition, not whether a read document describes some implementation success.",
        "Use read_document_count and read_doc_ids as proof that original Markdown/document text was read.",
        "Use read_code_file_count and read_code_file_paths as proof that original source/config code text was read.",
        "Do not rename source-code evidence into read_doc evidence; keep document evidence and source-code evidence separate.",
        "If the evidence kind is exploratory or multi-document, judge whether the read documents can support cross-document relationship analysis.",
    ]
    if evidence_kind in {"exploratory_multi_doc", "multi_doc_relationship"}:
        contract.append(
            "For this evidence kind, do not mark semantic_goal_match_status as matched merely because the read documents are internally coherent; they must visibly help the user's requested multi-document relationship/exploration task."
        )
    return contract


def _validate_l3_semantic_payload(payload: dict[str, object]) -> None:
    """Qwen L3가 생성할 수 있는 의미 적합성 필드만 검증한다."""

    status = str(payload.get("semantic_goal_match_status") or "").strip()
    reason = str(payload.get("semantic_goal_match_reason") or "").strip()
    if status not in {"matched", "partial", "missing", "not_run"}:
        raise ValueError("unknown L3 semantic_goal_match_status")
    if status != "not_run" and not reason:
        raise ValueError("L3 semantic_goal_match_reason must not be empty")


def _extract_search_candidates(
    *,
    source_data_id: str,
    source_trace_id: str | None,
    payload: object,
    existing_count: int,
) -> list[L3PreservedSearchCandidate]:
    """search_docs payload에서 보존 후보 목록을 꺼낸다."""

    if not isinstance(payload, dict):
        return []

    distilled_items = payload.get("items")
    if isinstance(distilled_items, list):
        return _extract_distilled_search_candidates(
            source_data_id=source_data_id,
            source_trace_id=source_trace_id,
            items=distilled_items,
            existing_count=existing_count,
        )

    results = payload.get("results")
    if not isinstance(results, list):
        return []

    candidates: list[L3PreservedSearchCandidate] = []
    for index, item in enumerate(results, start=existing_count + 1):
        if not isinstance(item, dict):
            continue
        candidates.append(
            L3PreservedSearchCandidate(
                candidate_id=f"L3:candidate_{index:04d}",
                source_data_id=source_data_id,
                source_trace_id=source_trace_id,
                result_id=str(item.get("result_id") or ""),
                doc_id=str(item.get("doc_id") or ""),
                chunk_id=str(item.get("chunk_id") or ""),
                score=float(item.get("score") or 0.0),
                embedding_model_id=str(item.get("embedding_model_id") or ""),
                text_preview=str(item.get("text_preview") or ""),
                document_kind=_optional_text(item.get("document_kind")),
                source_role=_optional_text(item.get("source_role")),
                document_memory_index_id=_optional_text(item.get("document_memory_index_id")),
                snapshot_id=_optional_text(item.get("snapshot_id")),
            )
        )

    return candidates


def _extract_distilled_search_candidates(
    *,
    source_data_id: str,
    source_trace_id: str | None,
    items: list[object],
    existing_count: int,
) -> list[L3PreservedSearchCandidate]:
    """ToolResultDistillationFrame items에서 search result 후보를 꺼낸다."""

    candidates: list[L3PreservedSearchCandidate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_kind = item.get("item_kind")
        if item_kind == "search_result":
            candidates.append(
                L3PreservedSearchCandidate(
                    candidate_id=f"L3:candidate_{existing_count + len(candidates) + 1:04d}",
                    source_data_id=source_data_id,
                    source_trace_id=source_trace_id,
                    result_id=str(item.get("result_id") or ""),
                    doc_id=str(item.get("doc_id") or ""),
                    chunk_id=str(item.get("chunk_id") or ""),
                    score=float(item.get("score") or 0.0),
                    embedding_model_id=str(item.get("embedding_model_id") or ""),
                    text_preview=str(item.get("text_preview") or ""),
                    document_kind=_optional_text(item.get("document_kind")),
                    source_role=_optional_text(item.get("source_role")),
                    document_memory_index_id=_optional_text(item.get("document_memory_index_id")),
                    snapshot_id=_optional_text(item.get("snapshot_id")),
                )
            )
        elif item_kind == "read_doc_excerpt":
            doc_id = str(item.get("doc_id") or "")
            if not doc_id:
                continue
            candidates.append(
                L3PreservedSearchCandidate(
                    candidate_id=f"L3:candidate_{existing_count + len(candidates) + 1:04d}",
                    source_data_id=source_data_id,
                    source_trace_id=source_trace_id,
                    result_id=str(item.get("item_id") or "document_extract"),
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}#document_extract",
                    score=1.0,
                    embedding_model_id="document-extract",
                    text_preview=str(item.get("text_preview") or ""),
                    document_kind=_optional_text(item.get("document_kind")),
                    source_role=_optional_text(item.get("source_role")),
                    document_memory_index_id=_optional_text(item.get("document_memory_index_id")),
                    snapshot_id=_optional_text(item.get("snapshot_id")),
                )
            )
    return candidates


def _build_goal_match_context(
    *,
    user_query: str,
    preserved_frame: L3PreservedInfoFrame,
    data_store: DataStore | None,
) -> dict[str, object]:
    """사용자가 특정 문서를 요구했는지와 실제 L루프 산출이 맞았는지 코드로 대조한다."""

    explicit_artifact_hint = _explicit_artifact_requested_doc_hint(data_store)
    requested_doc_hint = explicit_artifact_hint or _extract_requested_doc_hint(user_query)
    requested_doc_hint_source = (
        "explicit_artifact_reference_frame"
        if explicit_artifact_hint
        else "user_query_syntax"
        if requested_doc_hint
        else "none"
    )
    read_doc_ids = _read_doc_ids_from_data_store(data_store)
    read_code_file_paths = _read_code_file_paths_from_data_store(data_store)
    search_result_doc_ids = _unique_strings(
        [candidate.doc_id for candidate in preserved_frame.candidates if candidate.doc_id]
    )

    if not requested_doc_hint:
        return {
            "requested_doc_hint": "",
            "requested_doc_hint_source": requested_doc_hint_source,
            "read_doc_ids": read_doc_ids,
            "read_code_file_paths": read_code_file_paths,
            "search_result_doc_ids": search_result_doc_ids,
            "goal_match_status": "not_applicable",
            "goal_match_reason": "CODE_STATUS:no_specific_doc_hint_detected",
        }

    if any(_doc_matches_hint(doc_id, requested_doc_hint) for doc_id in read_doc_ids):
        return {
            "requested_doc_hint": requested_doc_hint,
            "requested_doc_hint_source": requested_doc_hint_source,
            "read_doc_ids": read_doc_ids,
            "read_code_file_paths": read_code_file_paths,
            "search_result_doc_ids": search_result_doc_ids,
            "goal_match_status": "matched",
            "goal_match_reason": "CODE_STATUS:requested_doc_read_doc_matched",
        }

    if any(_doc_matches_hint(file_path, requested_doc_hint) for file_path in read_code_file_paths):
        return {
            "requested_doc_hint": requested_doc_hint,
            "requested_doc_hint_source": requested_doc_hint_source,
            "read_doc_ids": read_doc_ids,
            "read_code_file_paths": read_code_file_paths,
            "search_result_doc_ids": search_result_doc_ids,
            "goal_match_status": "matched",
            "goal_match_reason": "CODE_STATUS:requested_source_code_file_read_code_file_matched",
        }

    if any(_doc_matches_hint(doc_id, requested_doc_hint) for doc_id in search_result_doc_ids):
        return {
            "requested_doc_hint": requested_doc_hint,
            "requested_doc_hint_source": requested_doc_hint_source,
            "read_doc_ids": read_doc_ids,
            "read_code_file_paths": read_code_file_paths,
            "search_result_doc_ids": search_result_doc_ids,
            "goal_match_status": "partial",
            "goal_match_reason": "CODE_STATUS:requested_doc_found_in_search_results_but_not_read",
        }

    if read_doc_ids or read_code_file_paths or search_result_doc_ids:
        return {
            "requested_doc_hint": requested_doc_hint,
            "requested_doc_hint_source": requested_doc_hint_source,
            "read_doc_ids": read_doc_ids,
            "read_code_file_paths": read_code_file_paths,
            "search_result_doc_ids": search_result_doc_ids,
            "goal_match_status": "partial",
            "goal_match_reason": "CODE_STATUS:requested_doc_not_matched_but_l_loop_has_other_evidence",
        }

    return {
        "requested_doc_hint": requested_doc_hint,
        "requested_doc_hint_source": requested_doc_hint_source,
        "read_doc_ids": read_doc_ids,
        "read_code_file_paths": read_code_file_paths,
        "search_result_doc_ids": search_result_doc_ids,
        "goal_match_status": "missing",
        "goal_match_reason": "CODE_STATUS:requested_doc_not_matched_and_no_l_loop_evidence",
    }


def _apply_goal_match_guard(
    *,
    achievement_status: str,
    reason: str,
    macro_status: str,
    macro_reason: str,
    micro_status: str,
    micro_reason: str,
    goal_match: dict[str, object],
) -> tuple[str, str, str, str, str, str]:
    """특정 문서 요청을 못 맞춘 경우 L3가 achieved로 확정하지 못하게 낮춘다."""

    goal_match_status = str(goal_match.get("goal_match_status") or "not_applicable")
    if goal_match_status in {"not_applicable", "matched"}:
        return (
            achievement_status,
            reason,
            macro_status,
            macro_reason,
            micro_status,
            micro_reason,
        )

    guarded_status = "failed" if goal_match_status == "missing" else "partial"
    guarded_reason = str(goal_match.get("goal_match_reason") or "CODE_STATUS:goal_match_guarded")
    reason = _append_guard_reason(reason, guarded_reason)
    macro_reason = _append_guard_reason(macro_reason, guarded_reason)
    micro_reason = _append_guard_reason(micro_reason, guarded_reason)

    return (
        _downgrade_achievement_status(achievement_status, guarded_status),
        reason,
        _downgrade_achievement_status(macro_status, guarded_status),
        macro_reason,
        _downgrade_achievement_status(micro_status, guarded_status),
        micro_reason,
    )


def _apply_semantic_goal_match_guard(
    *,
    achievement_status: str,
    reason: str,
    macro_status: str,
    macro_reason: str,
    micro_status: str,
    micro_reason: str,
    semantic_goal_match_status: str,
    semantic_goal_match_reason: str,
) -> tuple[str, str, str, str, str, str]:
    """LLM semantic judgement can downgrade achievement; code does not invent semantic labels."""

    if semantic_goal_match_status in {"not_run", "matched"}:
        return (
            achievement_status,
            reason,
            macro_status,
            macro_reason,
            micro_status,
            micro_reason,
        )

    guarded_status = "failed" if semantic_goal_match_status == "missing" else "partial"
    guarded_reason = semantic_goal_match_reason or "LLM_SEMANTIC_GOAL:semantic_mismatch"
    reason = _append_guard_reason(reason, guarded_reason)
    macro_reason = _append_guard_reason(macro_reason, guarded_reason)
    micro_reason = _append_guard_reason(micro_reason, guarded_reason)
    return (
        _downgrade_achievement_status(achievement_status, guarded_status),
        reason,
        _downgrade_achievement_status(macro_status, guarded_status),
        macro_reason,
        _downgrade_achievement_status(micro_status, guarded_status),
        micro_reason,
    )


def _apply_l1_requirement_count_guard(
    *,
    achievement_status: str,
    reason: str,
    macro_status: str,
    macro_reason: str,
    micro_status: str,
    micro_reason: str,
    l1_goal: dict[str, object],
    read_document_count: int,
    read_code_file_count: int,
    source_code_evidence_expected: bool,
) -> tuple[str, str, str, str, str, str]:
    """L1의 최소 원문 열람 요구보다 실제 source evidence 수가 적으면 achieved를 낮춘다."""

    minimum_read_documents = l1_goal.get("minimum_read_documents")
    if not isinstance(minimum_read_documents, int) or minimum_read_documents <= 0:
        return (
            achievement_status,
            reason,
            macro_status,
            macro_reason,
            micro_status,
            micro_reason,
        )
    actual_evidence_count = read_document_count
    if source_code_evidence_expected:
        actual_evidence_count += read_code_file_count
    if actual_evidence_count >= minimum_read_documents:
        return (
            achievement_status,
            reason,
            macro_status,
            macro_reason,
            micro_status,
            micro_reason,
        )

    guard_reason = (
        "CODE_STATUS:l1_minimum_read_documents_not_met"
        f":required_{minimum_read_documents}_actual_{actual_evidence_count}"
    )
    reason = _append_guard_reason(reason, guard_reason)
    macro_reason = _append_guard_reason(macro_reason, guard_reason)
    micro_reason = _append_guard_reason(micro_reason, guard_reason)
    return (
        _downgrade_achievement_status(achievement_status, "partial"),
        reason,
        _downgrade_achievement_status(macro_status, "partial"),
        macro_reason,
        _downgrade_achievement_status(micro_status, "partial"),
        micro_reason,
    )


def _downgrade_achievement_status(current_status: str, guarded_status: str) -> str:
    """achieved는 partial/failed로 낮추고, 이미 더 낮은 판정은 유지한다."""

    if current_status == "achieved":
        return guarded_status
    if guarded_status == "failed" and current_status == "partial":
        return "failed"
    return current_status or guarded_status


def _append_guard_reason(reason: str, guard_reason: str) -> str:
    if not reason:
        return guard_reason
    if guard_reason in reason:
        return reason
    return f"{reason} | {guard_reason}"


def _extract_requested_doc_hint(text: str) -> str:
    """사용자 입력에서 파일 경로/문서명처럼 보이는 최소 힌트만 뽑는다."""

    if not text:
        return ""

    for candidate in re.findall(r"`([^`]+)`", text):
        candidate = _clean_doc_hint(candidate)
        if _looks_like_doc_hint(candidate):
            return candidate

    path_match = re.search(r"([A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)+(?:\.md)?)(?=$|[^A-Za-z0-9_.-])", text)
    if path_match:
        return _clean_doc_hint(path_match.group(1))

    token_match = re.search(
        r"(?<![A-Za-z0-9_.-])([A-Za-z0-9][A-Za-z0-9_.-]*(?:_[A-Za-z0-9][A-Za-z0-9_.-]*){2,}(?:\.md)?)(?=$|[^A-Za-z0-9_.-])",
        text,
    )
    if token_match:
        return _clean_doc_hint(token_match.group(1))

    return ""


def _explicit_artifact_requested_doc_hint(data_store: DataStore | None) -> str:
    """명시 문서 resolver가 남긴 절대 좌표를 L3 목표 대조에 재사용한다."""

    if data_store is None:
        return ""

    for record in reversed(data_store.list_records()):
        if record.data_type != "node_output:explicit_artifact_reference_frame":
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        resolved_references = payload.get("resolved_references")
        if not isinstance(resolved_references, list):
            continue
        for item in resolved_references:
            if not isinstance(item, dict):
                continue
            selected_doc_id = item.get("selected_doc_id")
            if item.get("resolve_status") == "unique" and isinstance(selected_doc_id, str) and selected_doc_id:
                return selected_doc_id
            for key in ("normalized_ref", "raw_ref"):
                value = item.get(key)
                if isinstance(value, str) and value:
                    return value
    return ""


def _looks_like_doc_hint(value: str) -> bool:
    return (
        "/" in value
        or "\\" in value
        or value.endswith(".md")
        or value.count("_") >= 2
    )


def _clean_doc_hint(value: str) -> str:
    return value.strip().strip("`'\"").rstrip(".,:;)]}")


def _read_doc_ids_from_data_store(data_store: DataStore | None) -> list[str]:
    if data_store is None:
        return []

    doc_ids: list[str] = []
    for record in data_store.list_records():
        if not _is_document_extract_record(record.data_type):
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        doc_id = payload.get("doc_id")
        if isinstance(doc_id, str) and doc_id:
            doc_ids.append(doc_id)
    return _unique_strings(doc_ids)


def _evidence_acquisition_status(
    *,
    candidate_count: int,
    original_material_count: int,
) -> str:
    """후보 존재와 실제 비어 있지 않은 원문 존재를 절대 count로만 구분한다."""

    if original_material_count > 0:
        return "original_material_acquired"
    if candidate_count > 0:
        return "candidates_only"
    return "none"


def _original_material_requirement_status(
    *,
    required_count: int,
    original_material_count: int,
) -> str:
    if required_count <= 0:
        return "not_required"
    if original_material_count >= required_count:
        return "satisfied"
    return "unsatisfied"


def _read_code_file_paths_from_data_store(data_store: DataStore | None) -> list[str]:
    if data_store is None:
        return []

    paths: list[str] = []
    for record in data_store.list_records():
        if not _is_code_extract_record(record.data_type):
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        if payload.get("read_status") != "ok":
            continue
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        file_path = payload.get("file_path")
        if isinstance(file_path, str) and file_path:
            paths.append(file_path)
    return _unique_strings(paths)


def _read_doc_previews_from_data_store(
    data_store: DataStore | None,
    *,
    max_docs: int = 3,
    max_text_chars: int = 1200,
) -> list[dict[str, object]]:
    """Package read_doc outputs for L3 LLM judgement without adding semantic interpretation."""

    if data_store is None:
        return []

    previews: list[dict[str, object]] = []
    for record in data_store.list_records():
        if not _is_document_extract_record(record.data_type):
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        doc_id = payload.get("doc_id")
        text = payload.get("text")
        if not isinstance(doc_id, str) or not doc_id:
            continue
        if not isinstance(text, str):
            text = ""
        previews.append(
            {
                "source_data_id": record.data_id,
                "doc_id": doc_id,
                "char_count": payload.get("char_count"),
                "text_preview": text[:max_text_chars],
            }
        )
        if len(previews) >= max_docs:
            break
    return previews


def _read_code_file_previews_from_data_store(
    data_store: DataStore | None,
    *,
    max_files: int = 3,
    max_text_chars: int = 1200,
) -> list[dict[str, object]]:
    """Package read_code_file outputs for L3 LLM judgement without interpretation."""

    if data_store is None:
        return []

    previews: list[dict[str, object]] = []
    for record in data_store.list_records():
        if not _is_code_extract_record(record.data_type):
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        if payload.get("read_status") != "ok":
            continue
        file_path = payload.get("file_path")
        text = payload.get("text")
        if not isinstance(file_path, str) or not file_path:
            continue
        if not isinstance(text, str):
            text = ""
        previews.append(
            {
                "source_data_id": record.data_id,
                "file_path": file_path,
                "char_count": payload.get("char_count"),
                "line_count": payload.get("line_count"),
                "text_preview": text[:max_text_chars],
            }
        )
        if len(previews) >= max_files:
            break
    return previews


def _is_document_extract_record(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_doc") or data_type.startswith("tool_result:read_artifact")


def _is_code_extract_record(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_code_file")


def _source_code_evidence_expected(
    *,
    l1_goal: dict[str, object],
    data_store: DataStore | None,
    input_data_ids: list[str],
) -> bool:
    if _string_in_list(l1_goal.get("required_materials"), "source_code_file"):
        return True
    if data_store is None:
        return False
    for data_id in input_data_ids:
        record = data_store.get_record(data_id)
        if record is None or record.data_type != "node_output:L_tool_scope_frame":
            continue
        payload = record.payload
        if not isinstance(payload, dict):
            continue
        if payload.get("tool_scope_mode") in {"code_only", "document_and_code", "mixed_evidence"}:
            return True
        if _string_in_list(payload.get("required_materials"), "source_code_file"):
            return True
    return False


def _string_in_list(value: object, expected: str) -> bool:
    return isinstance(value, list) and any(item == expected for item in value)


def _doc_matches_hint(doc_id: str, hint: str) -> bool:
    normalized_doc_id = _normalize_doc_token(doc_id)
    normalized_hint = _normalize_doc_token(hint)
    if not normalized_doc_id or not normalized_hint:
        return False

    doc_name = normalized_doc_id.rsplit("/", 1)[-1]
    hint_name = normalized_hint.rsplit("/", 1)[-1]
    return (
        normalized_hint == normalized_doc_id
        or normalized_hint == doc_name
        or hint_name == doc_name
        or normalized_hint in normalized_doc_id
        or normalized_doc_id in normalized_hint
    )


def _normalize_doc_token(value: str) -> str:
    normalized = value.strip().strip("`'\"").replace("\\", "/").lower()
    normalized = re.sub(r"\.md$", "", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _optional_text(value: object) -> str | None:
    """문자열이면 보존하고 아니면 optional metadata를 비워 둔다."""

    if not isinstance(value, str) or not value:
        return None
    return value


def _unique_strings(values: list[str]) -> list[str]:
    """중복을 제거하되 처음 등장한 순서를 보존한다."""

    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value is None:
            continue
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def _read_controller_decision(
    *,
    data_store: DataStore | None,
    final_control_data_id: str | None,
) -> str | None:
    """최종 LLoopControlFrame payload에서 controller decision만 안전하게 읽는다."""

    if data_store is None or final_control_data_id is None:
        return None
    record = data_store.get_record(final_control_data_id)
    if record is None or not isinstance(record.payload, dict):
        return None
    decision = record.payload.get("decision")
    return decision if isinstance(decision, str) else None


def _read_l1_goal_frame(
    *,
    data_store: DataStore | None,
    input_data_ids: list[str],
) -> dict[str, object]:
    """L3가 기준으로 삼은 L1 목표 payload를 읽는다."""

    if data_store is None:
        return {}
    for data_id in input_data_ids:
        record = data_store.get_record(data_id)
        if record is None or record.data_type != "node_output:L1_goal_frame":
            continue
        if isinstance(record.payload, dict):
            return record.payload
    return {}


def _has_data_id(input_data_ids: list[str], target_data_id: str) -> bool:
    return target_data_id in input_data_ids


def _has_l2_query_frame(input_data_ids: list[str]) -> bool:
    """Treat both the first L2 query and later revision queries as L2 query evidence."""

    if any(data_id.endswith("L2:query_frame") for data_id in input_data_ids):
        return True
    return any(
        data_id.startswith("L2:revision_query_frame:")
        or ":L2:revision_query_frame:" in data_id
        for data_id in input_data_ids
    )


def _validate_positive_attempt_index(attempt_index: int) -> None:
    if not isinstance(attempt_index, int):
        raise TypeError("attempt_index must be an integer")
    if attempt_index < 1:
        raise ValueError("attempt_index must be positive")
