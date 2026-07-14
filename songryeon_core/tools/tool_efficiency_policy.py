from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.failure_signal_store import record_failure_signal
from songryeon_core.core.schemas import (
    CodeReadContinuationOption,
    CodeReadRangeRecord,
    ToolCacheStatusRecord,
    ToolUseBudgetFrame,
    validate_code_read_continuation_option,
    validate_code_read_range_record,
    validate_tool_use_budget_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds


class BudgetConsistencyError(ValueError):
    """ToolUseBudgetFrame 검증 실패를 구조화된 진단과 함께 올린다."""

    def __init__(self, message: str, *, diagnostics: dict[str, object]) -> None:
        super().__init__(message)
        self.budget_diagnostics = diagnostics


def tool_budget_data_id(
    turn_id: str,
    sequence_index: int,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    if id_namespace is None:
        return f"tool_budget:{turn_id}:{sequence_index:04d}"
    return id_namespace.tool_budget_data_id(turn_id, sequence_index)


def record_tool_use_budget_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    sequence_index: int,
    max_tool_calls: int,
    search_top_k: int,
    max_query_attempts: int,
    max_read_doc_calls: int,
    max_input_chars: int,
    tool_call_count: int,
    executed_queries: list[str],
    read_doc_ids: list[str],
    cache_statuses: list[ToolCacheStatusRecord],
    input_chars_used: int,
    stop_reason: str,
    reason: str,
    condition_flags: list[str] | None = None,
    source_trace_ids: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    duplicate_query_count: int = 0,
    duplicate_doc_count: int = 0,
    max_query_candidates: int | None = None,
    id_namespace: LRunIds | None = None,
    max_read_code_file_calls: int = 0,
    read_code_file_ranges: list[CodeReadRangeRecord] | None = None,
) -> tuple[str, str]:
    """현재 L루프 도구 사용 예산 상태를 trace와 DataStore에 저장한다."""

    budget_id = tool_budget_data_id(
        turn_id,
        sequence_index,
        id_namespace=id_namespace,
    )
    frame = ToolUseBudgetFrame(
        budget_id=budget_id,
        turn_id=turn_id,
        loop_id="L",
        sequence_index=sequence_index,
        max_tool_calls=max_tool_calls,
        search_top_k=search_top_k,
        max_query_attempts=max_query_attempts,
        max_query_candidates=max_query_candidates
        if max_query_candidates is not None
        else max_query_attempts,
        max_read_doc_calls=max_read_doc_calls,
        max_input_chars=max_input_chars,
        tool_call_count=tool_call_count,
        query_count=len(executed_queries),
        read_doc_count=len(read_doc_ids),
        input_chars_used=input_chars_used,
        max_read_code_file_calls=max_read_code_file_calls,
        read_code_file_count=len(read_code_file_ranges or []),
        read_code_file_ranges=list(read_code_file_ranges or []),
        executed_queries=list(executed_queries),
        read_doc_ids=list(read_doc_ids),
        cache_statuses=list(cache_statuses),
        duplicate_query_count=duplicate_query_count,
        duplicate_doc_count=duplicate_doc_count,
        stop_reason=stop_reason,
        reason=reason,
        condition_flags=condition_flags or [stop_reason],
        source_trace_ids=source_trace_ids or [],
        source_data_ids=source_data_ids or [],
    )
    try:
        validate_tool_use_budget_frame(frame)
    except (TypeError, ValueError) as exc:
        diagnostics = _budget_failure_diagnostics(
            frame=frame,
            reason=str(exc),
            id_namespace=id_namespace,
        )
        raise BudgetConsistencyError(str(exc), diagnostics=diagnostics) from exc
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="tool_efficiency_policy",
        event_type="node_output",
        input_ref=source_trace_ids or [],
        output_ref=[budget_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=budget_id,
        data_type="tool_use_budget",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, budget_id


def _budget_failure_diagnostics(
    *,
    frame: ToolUseBudgetFrame,
    reason: str,
    id_namespace: LRunIds | None,
) -> dict[str, object]:
    return {
        "budget_failure_type": _budget_failure_type(frame, reason=reason),
        "budget_failure_reason": reason,
        "budget_failure_frame_id": frame.budget_id,
        "budget_failure_source_data_ids": list(frame.source_data_ids),
        "budget_failure_route": "L",
        "budget_failure_l_run_id": _budget_failure_l_run_id(id_namespace),
        "budget_failure_query_count": frame.query_count,
        "budget_failure_max_query_attempts": frame.max_query_attempts,
        "budget_failure_tool_calls": frame.tool_call_count,
        "budget_failure_max_tool_calls": frame.max_tool_calls,
        "budget_failure_read_doc_count": frame.read_doc_count,
        "budget_failure_max_read_doc": frame.max_read_doc_calls,
        "budget_failure_read_code_file_count": frame.read_code_file_count,
        "budget_failure_max_read_code_file_calls": frame.max_read_code_file_calls,
        "budget_failure_stage": "record_tool_use_budget_frame:validate",
    }


def _budget_failure_type(frame: ToolUseBudgetFrame, *, reason: str) -> str:
    if frame.query_count > frame.max_query_attempts:
        return "query_count_exceeded_max_query_attempts"
    if frame.tool_call_count > frame.max_tool_calls:
        return "tool_call_count_exceeded_max_tool_calls"
    if frame.read_doc_count > frame.max_read_doc_calls:
        return "read_doc_count_exceeded_max_read_doc"
    if frame.read_code_file_count > frame.max_read_code_file_calls:
        return "read_code_file_count_exceeded_max_read_code_file_calls"
    if frame.max_query_candidates != frame.max_query_attempts:
        return "max_query_candidates_mismatch"
    if "must be positive" in reason:
        return "budget_limit_not_positive"
    if "must not be negative" in reason:
        return "budget_count_negative"
    return "budget_consistency_violation"


def _budget_failure_l_run_id(id_namespace: LRunIds | None) -> str:
    if id_namespace is None:
        return "unknown"
    return f"L:run:{id_namespace.run_index:04d}"


def record_duplicate_tool_use_signal(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    duplicate_kind: str,
    duplicate_value: str,
    source_trace_ids: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str]:
    """반복 query/doc 시도를 통제 신호로 기록한다."""

    if duplicate_kind not in {"query", "doc"}:
        raise ValueError("duplicate_kind must be query or doc")
    if not duplicate_value:
        raise ValueError("duplicate_value must not be empty")
    sequence_index = len(trace_store.list_events()) + 1
    if id_namespace is None:
        failure_id = (
            f"failure:tool_efficiency:{turn_id}:duplicate_{duplicate_kind}:"
            f"{sequence_index:04d}"
        )
    else:
        failure_id = id_namespace.tool_efficiency_failure_data_id(
            turn_id=turn_id,
            duplicate_kind=duplicate_kind,
            sequence_index=sequence_index,
        )
    event_id = record_failure_signal(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        failure_id=failure_id,
        type="tool_failed",
        severity="info",
        raised_by="tool_efficiency_policy",
        recoverable=True,
        source_trace_ids=source_trace_ids or [],
        source_data_ids=source_data_ids or [],
        message=f"duplicate_{duplicate_kind}: {duplicate_value}",
    )
    return event_id, failure_id


def cache_status_from_search_payload(payload: object) -> str:
    """search_docs payload에서 cache_status 절대정보를 꺼낸다."""

    if not isinstance(payload, dict):
        return "unknown"
    cache_status = payload.get("cache_status")
    if cache_status in {"hit", "miss"}:
        return str(cache_status)
    return "unknown"


def make_cache_status_record(
    *,
    tool_result_data_id: str,
    cache_status: str,
    query_text: str,
) -> ToolCacheStatusRecord:
    """ToolUseBudgetFrame에 들어갈 cache 상태 record를 만든다."""

    return ToolCacheStatusRecord(
        tool_result_data_id=tool_result_data_id,
        cache_status=cache_status if cache_status in {"hit", "miss"} else "unknown",
        query_text=query_text,
    )


def make_code_read_range_record(
    *,
    tool_result_data_id: str,
    payload: object,
) -> CodeReadRangeRecord:
    """read_code_file payload의 path/range/truncation 절대정보를 장부 행으로 복사한다."""

    if not isinstance(payload, dict):
        raise TypeError("read_code_file payload must be a dict")
    file_path = payload.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("read_code_file payload.file_path must not be empty")
    read_status = payload.get("read_status")
    if not isinstance(read_status, str) or not read_status:
        raise ValueError("read_code_file payload.read_status must not be empty")
    record = CodeReadRangeRecord(
        tool_result_data_id=tool_result_data_id,
        file_path=file_path,
        requested_start_char=_payload_int(payload, "requested_start_char"),
        range_start_char=_payload_int(payload, "range_start_char"),
        range_end_char_exclusive=_payload_int(payload, "range_end_char_exclusive"),
        returned_char_count=_payload_int(payload, "returned_char_count"),
        total_char_count=_payload_int(
            payload,
            "total_char_count",
            fallback_field="char_count",
        ),
        truncated_before=payload.get("truncated_before") is True,
        truncated_after=payload.get("truncated_after") is True,
        read_status=read_status,
    )
    validate_code_read_range_record(record)
    return record


def build_code_read_continuation_options(
    ranges: list[CodeReadRangeRecord],
) -> list[CodeReadContinuationOption]:
    """이미 읽은 range만 보고 아직 실행하지 않은 연속 시작점을 계산한다.

    이 함수는 파일 내용이나 이름의 의미를 보지 않는다. 성공한 range의 exclusive end가
    아직 같은 파일의 다른 성공 range start로 쓰이지 않았는지만 확인한다.
    """

    successful_starts: set[tuple[str, int]] = set()
    for record in ranges:
        validate_code_read_range_record(record)
        if record.read_status == "ok":
            successful_starts.add((record.file_path, record.range_start_char))

    options_by_key: dict[tuple[str, int], CodeReadContinuationOption] = {}
    for record in ranges:
        if record.read_status != "ok" or not record.truncated_after:
            continue
        start_char = record.range_end_char_exclusive
        key = (record.file_path, start_char)
        if key in successful_starts:
            continue
        option = CodeReadContinuationOption(
            file_path=record.file_path,
            start_char=start_char,
            previous_range_end_char_exclusive=record.range_end_char_exclusive,
            total_char_count=record.total_char_count,
            remaining_char_count=record.total_char_count - start_char,
            source_tool_result_data_id=record.tool_result_data_id,
        )
        validate_code_read_continuation_option(option)
        options_by_key[key] = option
    return list(options_by_key.values())


def _payload_int(
    payload: dict[str, object],
    field_name: str,
    *,
    fallback_field: str | None = None,
) -> int:
    value = payload.get(field_name)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if fallback_field is not None:
        fallback = payload.get(fallback_field)
        if isinstance(fallback, int) and not isinstance(fallback, bool):
            return fallback
    return 0


def distilled_input_size(payload: object) -> int:
    """distillation payload나 frame에서 입력 크기 추정값을 읽는다."""

    if hasattr(payload, "distilled_content_bytes"):
        value = getattr(payload, "distilled_content_bytes")
        return value if isinstance(value, int) else 0
    if isinstance(payload, dict):
        value = payload.get("distilled_content_bytes")
        return value if isinstance(value, int) else 0
    return 0
