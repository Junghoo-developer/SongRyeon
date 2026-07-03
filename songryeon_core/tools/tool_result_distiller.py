from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    ToolResultDistillationFrame,
    ToolResultDistilledItem,
    validate_tool_result_distillation_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.tools.tool_runner import ToolRunResult


@dataclass
class ToolResultDistillationResult:
    """도구 결과 distillation 저장 결과."""

    trace_event_id: str
    data_id: str
    frame: ToolResultDistillationFrame


def record_tool_result_distillation(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    tool_result: ToolRunResult,
    max_search_preview_chars: int = 120,
    max_read_preview_chars: int = 420,
    id_namespace: LRunIds | None = None,
) -> ToolResultDistillationResult:
    """도구 결과 원본을 작은 distillation frame으로 바꿔 trace/data에 저장한다."""

    frame = _build_distillation_frame(
        turn_id=turn_id,
        tool_result=tool_result,
        max_search_preview_chars=max_search_preview_chars,
        max_read_preview_chars=max_read_preview_chars,
        id_namespace=id_namespace,
    )
    validate_tool_result_distillation_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="tool_distiller",
        event_type="node_output",
        input_ref=[tool_result.trace_event_id],
        output_ref=[frame.distillation_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.distillation_id,
        data_type=f"tool_result_distillation:{tool_result.tool_name}",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return ToolResultDistillationResult(
        trace_event_id=event.event_id,
        data_id=frame.distillation_id,
        frame=frame,
    )


def _build_distillation_frame(
    *,
    turn_id: str,
    tool_result: ToolRunResult,
    max_search_preview_chars: int,
    max_read_preview_chars: int,
    id_namespace: LRunIds | None,
) -> ToolResultDistillationFrame:
    distillation_id = _distillation_data_id(
        tool_name=tool_result.tool_name,
        original_trace_id=tool_result.trace_event_id,
        id_namespace=id_namespace,
    )
    limits: list[str] = []
    if tool_result.tool_name == "search_docs":
        items = _distill_search_docs(
            payload=tool_result.payload,
            max_preview_chars=max_search_preview_chars,
            limits=limits,
        )
    elif tool_result.tool_name == "list_code_files":
        items = _distill_list_code_files(
            payload=tool_result.payload,
            max_preview_chars=max_search_preview_chars,
            limits=limits,
        )
    elif tool_result.tool_name == "search_code":
        items = _distill_search_code(
            payload=tool_result.payload,
            max_preview_chars=max_search_preview_chars,
            limits=limits,
        )
    elif tool_result.tool_name in {"read_doc", "read_artifact"}:
        items = _distill_document_extract(
            payload=tool_result.payload,
            max_preview_chars=max_read_preview_chars,
            limits=limits,
        )
    elif tool_result.tool_name == "read_code_file":
        items = _distill_read_code_file(
            payload=tool_result.payload,
            max_preview_chars=max_read_preview_chars,
            limits=limits,
        )
    else:
        raise ValueError(f"unsupported distillation tool: {tool_result.tool_name}")

    distilled_content = {
        "items": [asdict(item) for item in items],
        "limits": limits,
    }
    return ToolResultDistillationFrame(
        distillation_id=distillation_id,
        turn_id=turn_id,
        tool_name=tool_result.tool_name,
        original_tool_result_data_id=tool_result.data_ref.data_id,
        original_tool_trace_id=tool_result.trace_event_id,
        original_payload_bytes=_json_size(tool_result.payload),
        distilled_content_bytes=_json_size(distilled_content),
        items=items,
        limits=limits,
        source_trace_ids=[tool_result.trace_event_id],
        source_data_ids=[tool_result.data_ref.data_id],
    )


def _distill_search_docs(
    *,
    payload: object,
    max_preview_chars: int,
    limits: list[str],
) -> list[ToolResultDistilledItem]:
    if not isinstance(payload, dict):
        limits.append("search_docs payload가 dict가 아니어서 결과를 추출하지 못했다.")
        return []

    results = payload.get("results")
    if not isinstance(results, list):
        limits.append("search_docs payload에 results 목록이 없어서 결과를 추출하지 못했다.")
        return []

    items: list[ToolResultDistilledItem] = []
    for index, raw_item in enumerate(results, start=1):
        if not isinstance(raw_item, dict):
            continue
        preview = _shorten(str(raw_item.get("text_preview") or ""), max_preview_chars)
        if len(str(raw_item.get("text_preview") or "")) > len(preview):
            limits.append(f"results[{index - 1}].text_preview를 {max_preview_chars}자로 잘랐다.")
        items.append(
            ToolResultDistilledItem(
                item_id=f"distilled_search_result_{index:04d}",
                item_kind="search_result",
                source_field_path=f"results[{index - 1}]",
                doc_id=str(raw_item.get("doc_id") or ""),
                chunk_id=str(raw_item.get("chunk_id") or ""),
                result_id=str(raw_item.get("result_id") or ""),
                score=float(raw_item.get("score") or 0.0),
                embedding_model_id=str(raw_item.get("embedding_model_id") or ""),
                text_preview=preview,
                document_kind=_optional_text(raw_item.get("document_kind")),
                source_role=_optional_text(raw_item.get("source_role")),
                document_memory_index_id=_optional_text(raw_item.get("document_memory_index_id")),
                snapshot_id=_optional_text(raw_item.get("snapshot_id")),
            )
        )

    if not items:
        limits.append("search_docs 결과 후보가 없어서 distillation item이 비어 있다.")
    return items


def _distill_document_extract(
    *,
    payload: object,
    max_preview_chars: int,
    limits: list[str],
) -> list[ToolResultDistilledItem]:
    if not isinstance(payload, dict):
        limits.append("read_doc payload가 dict가 아니어서 원문 발췌를 만들지 못했다.")
        return []

    text = str(payload.get("text") or "")
    doc_id = str(payload.get("doc_id") or "")
    match_status = str(payload.get("match_status") or "")
    if not doc_id or not text:
        if match_status:
            limits.append(f"document extract has no unique readable document: {match_status}")
        else:
            limits.append("document extract has no readable text.")
        return []
    char_count = payload.get("char_count")
    if not isinstance(char_count, int):
        char_count = len(text)
    preview = _shorten(" ".join(text.split()), max_preview_chars)
    if len(text) > len(preview):
        limits.append(f"read_doc 원문을 {max_preview_chars}자 미리보기로 줄였다.")

    return [
        ToolResultDistilledItem(
            item_id="distilled_read_doc_0001",
            item_kind="read_doc_excerpt",
            source_field_path="text",
            doc_id=doc_id,
            char_count=char_count,
            text_preview=preview,
            document_kind=_optional_text(payload.get("document_kind")),
            source_role=_optional_text(payload.get("source_role")),
            document_memory_index_id=_optional_text(payload.get("document_memory_index_id")),
            snapshot_id=_optional_text(payload.get("snapshot_id")),
        )
    ]


def _distill_list_code_files(
    *,
    payload: object,
    max_preview_chars: int,
    limits: list[str],
) -> list[ToolResultDistilledItem]:
    if not isinstance(payload, dict):
        limits.append("list_code_files payload가 dict가 아니어서 결과를 추출하지 못했다.")
        return []

    files = payload.get("files")
    if not isinstance(files, list):
        limits.append("list_code_files payload에 files 목록이 없어서 결과를 추출하지 못했다.")
        return []

    items: list[ToolResultDistilledItem] = []
    for index, raw_item in enumerate(files, start=1):
        if not isinstance(raw_item, dict):
            continue
        file_path = str(raw_item.get("file_path") or "")
        if not file_path:
            continue
        preview = _shorten(
            (
                f"{file_path} "
                f"extension={raw_item.get('extension')}; "
                f"line_count={raw_item.get('line_count')}; "
                f"size_bytes={raw_item.get('size_bytes')}"
            ),
            max_preview_chars,
        )
        items.append(
            ToolResultDistilledItem(
                item_id=f"distilled_code_file_{index:04d}",
                item_kind="search_result",
                source_field_path=f"files[{index - 1}]",
                doc_id=file_path,
                chunk_id=f"{file_path}#file_listing",
                result_id=f"code_file_{index:04d}",
                score=1.0,
                embedding_model_id="code-file-list",
                text_preview=preview,
                document_kind="source_code",
                source_role="codebase_file_listing",
            )
        )

    if payload.get("truncated") is True:
        limits.append("list_code_files 결과가 max_files 제한으로 잘렸다.")
    if not items:
        limits.append("list_code_files 결과 파일이 없어서 distillation item이 비어 있다.")
    return items


def _distill_search_code(
    *,
    payload: object,
    max_preview_chars: int,
    limits: list[str],
) -> list[ToolResultDistilledItem]:
    if not isinstance(payload, dict):
        limits.append("search_code payload가 dict가 아니어서 결과를 추출하지 못했다.")
        return []

    results = payload.get("results")
    if not isinstance(results, list):
        limits.append("search_code payload에 results 목록이 없어서 결과를 추출하지 못했다.")
        return []

    items: list[ToolResultDistilledItem] = []
    for index, raw_item in enumerate(results, start=1):
        if not isinstance(raw_item, dict):
            continue
        file_path = str(raw_item.get("file_path") or "")
        if not file_path:
            continue
        line_number = raw_item.get("line_number")
        line_text = str(raw_item.get("line_text") or "")
        preview = _shorten(
            f"{file_path}:{line_number}: {line_text}",
            max_preview_chars,
        )
        items.append(
            ToolResultDistilledItem(
                item_id=f"distilled_code_match_{index:04d}",
                item_kind="search_result",
                source_field_path=f"results[{index - 1}]",
                doc_id=file_path,
                chunk_id=f"{file_path}#L{line_number}",
                result_id=str(raw_item.get("result_id") or f"code_match_{index:04d}"),
                score=1.0,
                embedding_model_id="code-substring-search",
                text_preview=preview,
                document_kind="source_code",
                source_role="code_search_match",
            )
        )

    if payload.get("truncated") is True:
        limits.append("search_code 결과가 max_results 제한으로 잘렸다.")
    if not items:
        limits.append("search_code 결과 후보가 없어서 distillation item이 비어 있다.")
    return items


def _distill_read_code_file(
    *,
    payload: object,
    max_preview_chars: int,
    limits: list[str],
) -> list[ToolResultDistilledItem]:
    if not isinstance(payload, dict):
        limits.append("read_code_file payload가 dict가 아니어서 원문 발췌를 만들지 못했다.")
        return []

    file_path = str(payload.get("file_path") or "")
    read_status = str(payload.get("read_status") or "")
    text = str(payload.get("text") or "")
    if read_status != "ok" or not file_path or not text:
        limits.append(f"read_code_file has no readable source text: {read_status or 'unknown'}")
        return []
    char_count = payload.get("char_count")
    if not isinstance(char_count, int):
        char_count = len(text)
    preview = _shorten(" ".join(text.split()), max_preview_chars)
    if payload.get("truncated") is True:
        limits.append("read_code_file 원문이 max_chars 제한으로 잘렸다.")

    return [
        ToolResultDistilledItem(
            item_id="distilled_read_code_file_0001",
            item_kind="read_doc_excerpt",
            source_field_path="text",
            doc_id=file_path,
            char_count=char_count,
            text_preview=preview,
            document_kind="source_code",
            source_role="code_file_extract",
        )
    ]


def _distillation_data_id(
    *,
    tool_name: str,
    original_trace_id: str,
    id_namespace: LRunIds | None = None,
) -> str:
    if id_namespace is None:
        return f"tool_distillation:{tool_name}:{original_trace_id}"
    return id_namespace.tool_distillation_data_id(
        tool_name=tool_name,
        original_trace_id=original_trace_id,
    )


def _json_size(payload: object) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _shorten(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value
