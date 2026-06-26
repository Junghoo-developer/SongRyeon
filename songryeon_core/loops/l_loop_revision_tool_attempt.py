from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataRecord, DataStore
from songryeon_core.core.schemas import ToolCacheStatusRecord
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.tools.tool_efficiency_policy import (
    cache_status_from_search_payload,
    distilled_input_size,
    make_cache_status_record,
    record_tool_use_budget_frame,
)
from songryeon_core.tools.tool_result_distiller import record_tool_result_distillation
from songryeon_core.tools.tool_runner import (
    ToolRunner,
    build_document_tool_registry,
    record_tool_catalog,
    record_tool_choice,
    tool_catalog_data_id,
    tool_choice_data_id,
)


@dataclass
class LLoopRevisionToolAttemptResult:
    """revision query frame 하나를 실제 도구 시도로 바꾼 결과."""

    attempt_index: int
    query_frame_data_id: str
    tool_name: str
    query_text: str
    tool_choice_data_id: str
    tool_result_data_id: str
    tool_distillation_data_id: str
    tool_budget_data_id: str
    tool_trace_id: str
    tool_distillation_trace_id: str
    tool_budget_trace_id: str
    source_trace_ids: list[str]
    source_data_ids: list[str]


def run_l_loop_revision_tool_attempt(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    revision_query_frame_data_id: str,
    document_root: str | Path = "Administrative_Reform_1",
    search_top_k: int = 3,
    max_tool_calls: int = 3,
    max_query_attempts: int = 3,
    max_read_doc_calls: int = 2,
    max_input_chars: int = 6000,
    id_namespace: LRunIds | None = None,
) -> LLoopRevisionToolAttemptResult:
    """L2 revision query frame을 읽어 실제 문서 도구를 1회 실행한다.

    이 함수는 L3를 다시 호출하지 않는다. 책임은 revision query frame이 가리키는
    도구를 실행하고, tool choice/result/distillation/budget record를 남기는
    것까지다.
    """

    query_record = data_store.require_record(revision_query_frame_data_id)
    query_payload = _require_dict_payload(query_record)
    attempt_index = _attempt_index_from_revision_query_frame_id(revision_query_frame_data_id)
    query_text = _required_text(query_payload, "query_text")
    tool_name = _required_text(query_payload, "target_tool_name")
    if tool_name not in {"search_docs", "read_artifact"}:
        raise ValueError(f"unsupported revision tool: {tool_name}")

    registry = build_document_tool_registry(document_root)
    catalog_trace_id, catalog_id = _ensure_tool_catalog(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        registry=registry,
        input_ref=_string_list(query_payload.get("source_trace_ids")),
        source_data_ids=[revision_query_frame_data_id],
        id_namespace=id_namespace,
    )
    chooser_node_id = f"L2_revision_{attempt_index:04d}"
    choice_trace_id = record_tool_choice(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        registry=registry,
        chooser_node_id=chooser_node_id,
        tool_name=tool_name,
        catalog_id=catalog_id,
        reason=f"CODE_STATUS:revision_query_frame_targets_{tool_name}",
        expected_use="CODE_STATUS:run_revision_query_frame_tool",
        tool_choice_policy_id="l2_revision_query_frame_target_tool",
        expected_effect_label=f"CODE_STATUS:{tool_name}_revision_execution",
        input_ref=_unique_strings([catalog_trace_id, query_record.source_trace_id]),
        source_data_ids=[revision_query_frame_data_id],
        id_namespace=id_namespace,
    )
    choice_id = tool_choice_data_id(
        chooser_node_id,
        tool_name,
        id_namespace=id_namespace,
    )

    runner = ToolRunner(registry)
    if tool_name == "search_docs":
        tool_result = runner.run(
            tool_name="search_docs",
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            input_ref=_unique_strings([query_record.source_trace_id, choice_trace_id]),
            id_namespace=id_namespace,
            query=query_text,
            top_k=search_top_k,
        )
    else:
        tool_result = runner.run(
            tool_name="read_artifact",
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            input_ref=_unique_strings([query_record.source_trace_id, choice_trace_id]),
            id_namespace=id_namespace,
            artifact_ref=query_text,
        )

    distillation = record_tool_result_distillation(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        tool_result=tool_result,
        id_namespace=id_namespace,
    )
    latest_budget = _latest_budget_record(
        data_store,
        turn_id,
        id_namespace=id_namespace,
    )
    latest_budget_payload = _require_dict_payload(latest_budget) if latest_budget is not None else {}
    executed_queries = _string_list(latest_budget_payload.get("executed_queries"))
    if query_text not in executed_queries:
        executed_queries.append(query_text)
    read_doc_ids = _string_list(latest_budget_payload.get("read_doc_ids"))
    read_doc_id = _read_doc_id_from_tool_payload(tool_name=tool_name, payload=tool_result.payload)
    if read_doc_id and read_doc_id not in read_doc_ids:
        read_doc_ids.append(read_doc_id)

    cache_statuses = _cache_status_records(latest_budget_payload.get("cache_statuses"))
    if tool_name == "search_docs":
        cache_statuses.append(
            make_cache_status_record(
                tool_result_data_id=tool_result.data_ref.data_id,
                cache_status=cache_status_from_search_payload(tool_result.payload),
                query_text=query_text,
            )
        )
    stop_reason = _tool_attempt_stop_reason(tool_name=tool_name, payload=tool_result.payload)
    budget_trace_id, budget_data_id = record_tool_use_budget_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        sequence_index=_next_budget_sequence_index(
            data_store=data_store,
            turn_id=turn_id,
            id_namespace=id_namespace,
        ),
        max_tool_calls=max_tool_calls,
        search_top_k=search_top_k,
        max_query_attempts=max_query_attempts,
        max_read_doc_calls=max_read_doc_calls,
        max_input_chars=max_input_chars,
        tool_call_count=_int(latest_budget_payload, "tool_call_count") + 1,
        executed_queries=executed_queries,
        read_doc_ids=read_doc_ids,
        cache_statuses=cache_statuses,
        input_chars_used=(
            _int(latest_budget_payload, "input_chars_used")
            + len(query_text)
            + distilled_input_size(distillation.frame)
        ),
        stop_reason=stop_reason,
        reason=f"CODE_STATUS:revision_{tool_name}_attempt_{stop_reason}",
        condition_flags=["revision_tool_attempt", tool_name, stop_reason],
        source_trace_ids=_unique_strings(
            [
                query_record.source_trace_id,
                choice_trace_id,
                tool_result.trace_event_id,
                distillation.trace_event_id,
            ]
        ),
        source_data_ids=_unique_strings(
            [
                revision_query_frame_data_id,
                choice_id,
                tool_result.data_ref.data_id,
                distillation.data_id,
            ]
        ),
        id_namespace=id_namespace,
    )

    return LLoopRevisionToolAttemptResult(
        attempt_index=attempt_index,
        query_frame_data_id=revision_query_frame_data_id,
        tool_name=tool_name,
        query_text=query_text,
        tool_choice_data_id=choice_id,
        tool_result_data_id=tool_result.data_ref.data_id,
        tool_distillation_data_id=distillation.data_id,
        tool_budget_data_id=budget_data_id,
        tool_trace_id=tool_result.trace_event_id,
        tool_distillation_trace_id=distillation.trace_event_id,
        tool_budget_trace_id=budget_trace_id,
        source_trace_ids=_unique_strings(
            [
                query_record.source_trace_id,
                choice_trace_id,
                tool_result.trace_event_id,
                distillation.trace_event_id,
                budget_trace_id,
            ]
        ),
        source_data_ids=_unique_strings(
            [
                revision_query_frame_data_id,
                choice_id,
                tool_result.data_ref.data_id,
                distillation.data_id,
                budget_data_id,
            ]
        ),
    )


def _ensure_tool_catalog(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    registry,
    input_ref: list[str],
    source_data_ids: list[str],
    id_namespace: LRunIds | None,
) -> tuple[str | None, str]:
    catalog_id = tool_catalog_data_id(turn_id, id_namespace=id_namespace)
    existing = data_store.get_record(catalog_id)
    if existing is not None:
        return existing.source_trace_id, catalog_id
    trace_id = record_tool_catalog(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        registry=registry,
        input_ref=input_ref,
        source_data_ids=source_data_ids,
        id_namespace=id_namespace,
    )
    return trace_id, catalog_id


def _require_dict_payload(record: DataRecord) -> dict[str, object]:
    if not isinstance(record.payload, dict):
        raise TypeError(f"{record.data_id} payload must be a dict")
    return record.payload


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str) and value.strip():
        return value
    raise ValueError(f"{field_name} must be a non-empty string")


def _attempt_index_from_revision_query_frame_id(data_id: str) -> int:
    marker = "L2:revision_query_frame:"
    if marker not in data_id:
        raise ValueError(f"not a revision query frame id: {data_id}")
    suffix = data_id.rsplit(marker, 1)[1]
    try:
        attempt_index = int(suffix)
    except ValueError as exc:
        raise ValueError(f"invalid revision query frame attempt suffix: {suffix}") from exc
    if attempt_index < 1:
        raise ValueError("revision query frame attempt index must be positive")
    return attempt_index


def _latest_budget_record(
    data_store: DataStore,
    turn_id: str,
    *,
    id_namespace: LRunIds | None,
) -> DataRecord | None:
    latest_record: DataRecord | None = None
    latest_sequence = -1
    for record in data_store.list_records():
        if record.data_type != "tool_use_budget":
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get("turn_id") != turn_id:
            continue
        if id_namespace is not None and not id_namespace.owns_data_id(record.data_id):
            continue
        sequence = record.payload.get("sequence_index")
        if isinstance(sequence, int) and sequence > latest_sequence:
            latest_record = record
            latest_sequence = sequence
    return latest_record


def _next_budget_sequence_index(
    *,
    data_store: DataStore,
    turn_id: str,
    id_namespace: LRunIds | None,
) -> int:
    latest = _latest_budget_record(
        data_store,
        turn_id,
        id_namespace=id_namespace,
    )
    if latest is None or not isinstance(latest.payload, dict):
        return 1
    sequence = latest.payload.get("sequence_index")
    if not isinstance(sequence, int):
        return 1
    return sequence + 1


def _read_doc_id_from_tool_payload(*, tool_name: str, payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    if tool_name == "read_artifact" and payload.get("match_status") == "unique":
        doc_id = payload.get("doc_id") or payload.get("selected_doc_id")
        return doc_id if isinstance(doc_id, str) and doc_id else None
    return None


def _tool_attempt_stop_reason(*, tool_name: str, payload: object) -> str:
    if not isinstance(payload, dict):
        return "low_yield_stop"
    if tool_name == "search_docs":
        result_count = payload.get("result_count")
        return "completed" if isinstance(result_count, int) and result_count > 0 else "low_yield_stop"
    if tool_name == "read_artifact":
        return "completed" if payload.get("match_status") == "unique" else "low_yield_stop"
    return "low_yield_stop"


def _int(payload: dict[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    return value if isinstance(value, int) else 0


def _cache_status_records(value: object) -> list[ToolCacheStatusRecord]:
    if not isinstance(value, list):
        return []
    records: list[ToolCacheStatusRecord] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool_result_data_id = item.get("tool_result_data_id")
        cache_status = item.get("cache_status")
        query_text = item.get("query_text")
        if not isinstance(tool_result_data_id, str) or not tool_result_data_id:
            continue
        if not isinstance(cache_status, str) or not cache_status:
            continue
        if not isinstance(query_text, str) or not query_text:
            continue
        records.append(
            ToolCacheStatusRecord(
                tool_result_data_id=tool_result_data_id,
                cache_status=cache_status,
                query_text=query_text,
            )
        )
    return records


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
    return result


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
