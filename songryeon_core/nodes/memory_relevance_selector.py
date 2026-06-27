from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MemoryRelevanceSelectionFrame,
    validate_memory_relevance_selection_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


MEMORY_RELEVANCE_SELECTOR_PROMPT_REF = (
    "songryeon_core/prompts/memory_relevance_selector_v0.md"
)
MEMORY_RELEVANCE_SELECTOR_NODE_ID = "memory_relevance_selector"


def memory_relevance_selection_frame_data_id(source_memory_packet_id: str) -> str:
    """pre-route memory packet에 대응하는 selector 결과 frame ID를 만든다."""

    return f"{source_memory_packet_id}:memory_relevance_selection"


def memory_relevance_selector_input_data_id(selection_frame_id: str) -> str:
    return f"{selection_frame_id}:selector_input"


def run_recent_memory_relevance_selector(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    current_user_input: str,
    current_user_input_trace_id: str,
    source_memory_packet_id: str,
    selector_target_node: str,
    adapter: LLMAdapter | None,
    recent_raw_conversation: list[dict[str, str]] | None = None,
    max_retries: int = 0,
) -> tuple[str, str, MemoryRelevanceSelectionFrame]:
    """최근 memory relevance candidate frame을 LLM selector로 평가하고 저장한다."""

    packet = _memory_packet_payload(
        data_store=data_store,
        source_memory_packet_id=source_memory_packet_id,
    )
    candidate_frames = _dict_list(packet.get("relevance_candidate_frames"))
    memory_items = _dict_list(packet.get("memory_items"))
    frame_id = memory_relevance_selection_frame_data_id(source_memory_packet_id)
    candidate_frame_ids = _candidate_frame_ids(candidate_frames)
    source_memory_item_ids = _candidate_source_memory_item_ids(candidate_frames)
    source_trace_ids = _source_trace_ids(
        current_user_input_trace_id=current_user_input_trace_id,
        packet=packet,
        candidate_frames=candidate_frames,
        llm_trace_event_id=None,
    )

    if not candidate_frames:
        frame = MemoryRelevanceSelectionFrame(
            frame_id=frame_id,
            turn_id=turn_id,
            selector_target_node=selector_target_node,
            current_user_input_trace_id=current_user_input_trace_id,
            source_memory_packet_id=source_memory_packet_id,
            candidate_frame_ids=[],
            selected_candidate_turn_ids=[],
            selected_candidate_frame_ids=[],
            selection_status="none_selected",
            selection_reason="CODE_STATUS:no_memory_relevance_candidates",
            judged_by=None,
            generated_by="CODE:MEMORY_RELEVANCE_SELECTOR_GUARD",
            llm_call_data_id=None,
            llm_trace_event_id=None,
            source_trace_ids=source_trace_ids,
            source_data_ids=[source_memory_packet_id],
            source_memory_item_ids=[],
            info_class="absolute_status",
        )
        return _record_selection_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    if adapter is None:
        frame = MemoryRelevanceSelectionFrame(
            frame_id=frame_id,
            turn_id=turn_id,
            selector_target_node=selector_target_node,
            current_user_input_trace_id=current_user_input_trace_id,
            source_memory_packet_id=source_memory_packet_id,
            candidate_frame_ids=candidate_frame_ids,
            selected_candidate_turn_ids=[],
            selected_candidate_frame_ids=[],
            selection_status="failed",
            selection_reason="CODE_STATUS:memory_relevance_selector_adapter_missing",
            judged_by=None,
            generated_by="CODE:MEMORY_RELEVANCE_SELECTOR_FAILURE_RECORDER",
            llm_call_data_id=None,
            llm_trace_event_id=None,
            source_trace_ids=source_trace_ids,
            source_data_ids=[source_memory_packet_id],
            source_memory_item_ids=source_memory_item_ids,
            info_class="absolute_status",
        )
        return _record_selection_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    prompt = Path(MEMORY_RELEVANCE_SELECTOR_PROMPT_REF).read_text(encoding="utf-8")
    selector_input_data_id = memory_relevance_selector_input_data_id(frame_id)
    input_payload = {
        "current_user_input": current_user_input,
        "current_user_input_trace_id": current_user_input_trace_id,
        "selector_target_node": selector_target_node,
        "source_memory_packet_id": source_memory_packet_id,
        "memory_packet": _selector_memory_packet_view(packet),
        "relevance_candidate_frames": candidate_frames,
        "candidate_alignment_items": _candidate_alignment_items(
            candidate_frames=candidate_frames,
            memory_items=memory_items,
        ),
        "candidate_raw_conversation_items": _candidate_raw_conversation_items(
            candidate_frames=candidate_frames,
            recent_raw_conversation=recent_raw_conversation or [],
        ),
        "source_data_ids": [source_memory_packet_id],
    }
    selector_input_trace_id = _record_selector_input(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        input_data_id=selector_input_data_id,
        input_payload=input_payload,
        source_trace_ids=source_trace_ids,
        source_data_ids=[source_memory_packet_id],
    )
    llm_input_ref = _unique_strings([*source_trace_ids, selector_input_trace_id])
    llm_source_data_ids = _unique_strings([source_memory_packet_id, selector_input_data_id])
    llm_result = LLMNodeExecutor(adapter).run(
        node_id=MEMORY_RELEVANCE_SELECTOR_NODE_ID,
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=MEMORY_RELEVANCE_SELECTOR_PROMPT_REF,
        input_ref=llm_input_ref,
        source_data_ids=llm_source_data_ids,
        max_retries=max_retries,
        payload_validator=lambda payload: _validate_selector_payload(
            payload=payload,
            candidate_frames=candidate_frames,
        ),
    )

    frame_source_trace_ids = _source_trace_ids(
        current_user_input_trace_id=current_user_input_trace_id,
        packet=packet,
        candidate_frames=candidate_frames,
        llm_trace_event_id=llm_result.trace_event_id,
    )
    frame_source_trace_ids = _unique_strings(
        [*frame_source_trace_ids, selector_input_trace_id]
    )
    frame_source_data_ids = _unique_strings(
        [source_memory_packet_id, selector_input_data_id, llm_result.call_data_id]
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        frame = MemoryRelevanceSelectionFrame(
            frame_id=frame_id,
            turn_id=turn_id,
            selector_target_node=selector_target_node,
            current_user_input_trace_id=current_user_input_trace_id,
            source_memory_packet_id=source_memory_packet_id,
            candidate_frame_ids=candidate_frame_ids,
            selected_candidate_turn_ids=[],
            selected_candidate_frame_ids=[],
            selection_status="failed",
            selection_reason="CODE_STATUS:memory_relevance_selector_failed",
            judged_by=None,
            generated_by="CODE:MEMORY_RELEVANCE_SELECTOR_FAILURE_RECORDER",
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
            source_trace_ids=frame_source_trace_ids,
            source_data_ids=frame_source_data_ids,
            source_memory_item_ids=source_memory_item_ids,
            info_class="absolute_status",
        )
    else:
        frame = _selection_frame_from_llm_payload(
            payload=llm_result.validation.payload,
            frame_id=frame_id,
            turn_id=turn_id,
            selector_target_node=selector_target_node,
            current_user_input_trace_id=current_user_input_trace_id,
            source_memory_packet_id=source_memory_packet_id,
            candidate_frames=candidate_frames,
            model_id=llm_result.model_id,
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
            source_trace_ids=frame_source_trace_ids,
            source_data_ids=frame_source_data_ids,
        )

    return _record_selection_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
    )


def _record_selection_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: MemoryRelevanceSelectionFrame,
) -> tuple[str, str, MemoryRelevanceSelectionFrame]:
    validate_memory_relevance_selection_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=MEMORY_RELEVANCE_SELECTOR_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:memory_relevance_selection_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def _record_selector_input(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    input_data_id: str,
    input_payload: dict[str, object],
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> str:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=MEMORY_RELEVANCE_SELECTOR_NODE_ID,
        event_type="node_input",
        input_ref=source_trace_ids,
        output_ref=[input_data_id],
        schema_status="not_checked",
    )
    data_store.create_record(
        data_id=input_data_id,
        data_type="node_input:memory_relevance_selector_input",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload={
            **input_payload,
            "input_data_id": input_data_id,
            "source_trace_ids": source_trace_ids,
            "source_data_ids": source_data_ids,
            "generated_by": "CODE:MEMORY_RELEVANCE_SELECTOR_INPUT_BUILDER",
            "semantic_judgement_status": "not_run",
        },
    )
    return event.event_id


def _selection_frame_from_llm_payload(
    *,
    payload: dict[str, object],
    frame_id: str,
    turn_id: str,
    selector_target_node: str,
    current_user_input_trace_id: str,
    source_memory_packet_id: str,
    candidate_frames: list[dict[str, object]],
    model_id: str,
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> MemoryRelevanceSelectionFrame:
    candidate_frame_ids = _candidate_frame_ids(candidate_frames)
    return MemoryRelevanceSelectionFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        selector_target_node=selector_target_node,
        current_user_input_trace_id=current_user_input_trace_id,
        source_memory_packet_id=source_memory_packet_id,
        candidate_frame_ids=candidate_frame_ids,
        selected_candidate_turn_ids=_string_list(payload.get("selected_candidate_turn_ids")),
        selected_candidate_frame_ids=_string_list(payload.get("selected_candidate_frame_ids")),
        selection_status=str(payload.get("selection_status") or "").strip(),
        selection_reason=str(payload.get("selection_reason") or "").strip(),
        judged_by=f"LLM:{model_id}",
        generated_by=f"LLM:{model_id}:memory_relevance_selector",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        source_memory_item_ids=_candidate_source_memory_item_ids(candidate_frames),
        info_class="mixed",
        source_mode="source_bundle",
        claim_alignment="multi_source_bundle",
    )


def _validate_selector_payload(
    *,
    payload: dict[str, object],
    candidate_frames: list[dict[str, object]],
) -> None:
    candidate_by_frame_id = {
        str(candidate.get("frame_id")): candidate
        for candidate in candidate_frames
        if isinstance(candidate.get("frame_id"), str)
    }
    status = str(payload.get("selection_status") or "").strip()
    if status not in {"selected", "none_selected"}:
        raise ValueError("memory relevance selector status must be selected or none_selected")

    selected_frame_ids = _string_list(payload.get("selected_candidate_frame_ids"))
    selected_turn_ids = _string_list(payload.get("selected_candidate_turn_ids"))
    reason = str(payload.get("selection_reason") or "").strip()
    if not reason:
        raise ValueError("memory relevance selector selection_reason must not be empty")

    if len(selected_frame_ids) != len(set(selected_frame_ids)):
        raise ValueError("selected_candidate_frame_ids must not contain duplicates")
    if len(selected_turn_ids) != len(set(selected_turn_ids)):
        raise ValueError("selected_candidate_turn_ids must not contain duplicates")

    if status == "none_selected":
        if selected_frame_ids or selected_turn_ids:
            raise ValueError("none_selected selector output must not include selected candidates")
        return

    if not selected_frame_ids or not selected_turn_ids:
        raise ValueError("selected selector output must include selected candidates")
    if len(selected_frame_ids) != len(selected_turn_ids):
        raise ValueError("selected frame ids and turn ids must have the same length")
    for frame_id, turn_id in zip(selected_frame_ids, selected_turn_ids):
        candidate = candidate_by_frame_id.get(frame_id)
        if candidate is None:
            raise ValueError("selected candidate frame id is not in candidate_frame_ids")
        if candidate.get("candidate_turn_id") != turn_id:
            raise ValueError("selected candidate turn id does not match selected frame id")


def _memory_packet_payload(
    *,
    data_store: DataStore,
    source_memory_packet_id: str,
) -> dict[str, object]:
    record = data_store.require_record(source_memory_packet_id)
    if record.data_type != "node_output:memory_packet":
        raise ValueError("source_memory_packet_id must point to a memory packet record")
    if not isinstance(record.payload, dict):
        raise TypeError("memory packet payload must be a dict")
    return record.payload


def _selector_memory_packet_view(packet: dict[str, object]) -> dict[str, object]:
    return {
        "packet_id": packet.get("packet_id"),
        "turn_id": packet.get("turn_id"),
        "target": packet.get("target"),
        "mode": packet.get("mode"),
        "operation_label": packet.get("operation_label"),
        "llm_semantic_summary_status": packet.get("llm_semantic_summary_status"),
        "source_trace_ids": packet.get("source_trace_ids"),
        "source_data_ids": packet.get("source_data_ids"),
    }


def _candidate_alignment_items(
    *,
    candidate_frames: list[dict[str, object]],
    memory_items: list[dict[str, object]],
) -> list[dict[str, object]]:
    item_by_id = {
        item.get("item_id"): item
        for item in memory_items
        if isinstance(item.get("item_id"), str)
    }
    alignment_items: list[dict[str, object]] = []
    for candidate in candidate_frames:
        source_memory_item_id = candidate.get("source_memory_item_id")
        item = item_by_id.get(source_memory_item_id)
        if item is None:
            continue
        alignment_items.append(
            {
                "candidate_frame_id": candidate.get("frame_id"),
                "candidate_turn_id": candidate.get("candidate_turn_id"),
                "source_memory_item_id": source_memory_item_id,
                "item_type": item.get("item_type"),
                "text": item.get("text"),
                "source_trace_ids": item.get("source_trace_ids"),
                "source_data_ids": item.get("source_data_ids"),
            }
        )
    return alignment_items


def _candidate_raw_conversation_items(
    *,
    candidate_frames: list[dict[str, object]],
    recent_raw_conversation: list[dict[str, str]],
) -> list[dict[str, object]]:
    raw_by_turn_id = _raw_conversation_by_turn_id(recent_raw_conversation)
    items: list[dict[str, object]] = []
    for candidate in candidate_frames:
        frame_id = candidate.get("frame_id")
        candidate_turn_id = candidate.get("candidate_turn_id")
        if not isinstance(frame_id, str) or not isinstance(candidate_turn_id, str):
            continue
        raw_entry = raw_by_turn_id.get(candidate_turn_id)
        if raw_entry is None:
            continue
        raw_user_text = _raw_conversation_text(raw_entry, "user") or ""
        raw_assistant_text = _raw_conversation_text(raw_entry, "assistant") or ""
        copied_user_text, user_truncated = _truncate(raw_user_text, 800)
        copied_assistant_text, assistant_truncated = _truncate(raw_assistant_text, 1200)
        items.append(
            {
                "candidate_frame_id": frame_id,
                "candidate_turn_id": candidate_turn_id,
                "raw_user_text": copied_user_text,
                "raw_assistant_text": copied_assistant_text,
                "raw_user_text_chars": len(raw_user_text),
                "raw_assistant_text_chars": len(raw_assistant_text),
                "raw_user_text_truncated": user_truncated,
                "raw_assistant_text_truncated": assistant_truncated,
                "copied_from": (
                    "ZeroState.recent_raw_conversation"
                    f"[turn_id={candidate_turn_id}]"
                ),
            }
        )
    return items


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


def _candidate_frame_ids(candidate_frames: list[dict[str, object]]) -> list[str]:
    return _unique_strings(
        [
            str(candidate.get("frame_id"))
            for candidate in candidate_frames
            if isinstance(candidate.get("frame_id"), str)
        ]
    )


def _candidate_source_memory_item_ids(candidate_frames: list[dict[str, object]]) -> list[str]:
    return _unique_strings(
        [
            str(candidate.get("source_memory_item_id"))
            for candidate in candidate_frames
            if isinstance(candidate.get("source_memory_item_id"), str)
        ]
    )


def _source_trace_ids(
    *,
    current_user_input_trace_id: str,
    packet: dict[str, object],
    candidate_frames: list[dict[str, object]],
    llm_trace_event_id: str | None,
) -> list[str]:
    values: list[str | None] = [current_user_input_trace_id]
    values.extend(_string_list(packet.get("source_trace_ids")))
    values.extend(_string_list(packet.get("evidence_trace_ids")))
    for candidate in candidate_frames:
        values.extend(_string_list(candidate.get("source_trace_ids")))
    values.append(llm_trace_event_id)
    return _unique_strings(values)


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
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
