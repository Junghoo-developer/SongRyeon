from __future__ import annotations

"""Night-government worker that summarizes one TimeBundle graph node."""

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    GraphMemoryEdgeFrame,
    NightTimeBundleSummaryFrame,
    validate_graph_memory_edge_frame,
    validate_night_time_bundle_summary_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID = "night_summarize_time_bundle"
NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF = (
    "songryeon_core/prompts/night_summarize_time_bundle_v0.md"
)
NIGHT_SUMMARIZE_TIME_BUNDLE_FRAME_DATA_TYPE = (
    "node_output:night_summarize_time_bundle_frame"
)
NIGHT_TIME_BUNDLE_SUMMARY_WORKER_NODE_ID = NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID
NIGHT_TIME_BUNDLE_SUMMARY_PROMPT_REF = NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF
NIGHT_TIME_BUNDLE_SUMMARY_FRAME_DATA_TYPE = NIGHT_SUMMARIZE_TIME_BUNDLE_FRAME_DATA_TYPE


@dataclass(frozen=True)
class RecordedNightTimeBundleSummaryResult:
    frame: NightTimeBundleSummaryFrame
    trace_event_id: str
    frame_data_id: str
    summary_graph_node_data_id: str | None
    summary_edge_data_id: str | None
    created_data_ids: list[str]
    existing_data_ids: list[str]


def night_summarize_time_bundle_frame_id(
    target_time_bundle_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("target_time_bundle_node_id", target_time_bundle_node_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "night_summary:time_bundle:"
        f"{_stable_suffix(target_time_bundle_node_id)}:{_safe_id_part(summary_run_id)}"
    )


def night_summarize_time_bundle_graph_node_id(
    target_time_bundle_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("target_time_bundle_node_id", target_time_bundle_node_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "graph:summary:time_bundle:"
        f"{_stable_suffix(target_time_bundle_node_id)}:{_safe_id_part(summary_run_id)}"
    )


def night_time_bundle_summary_frame_id(
    target_time_bundle_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    """Compatibility wrapper for night_summarize_time_bundle_frame_id."""

    return night_summarize_time_bundle_frame_id(
        target_time_bundle_node_id,
        summary_run_id=summary_run_id,
    )


def night_time_bundle_summary_graph_node_id(
    target_time_bundle_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    """Compatibility wrapper for night_summarize_time_bundle_graph_node_id."""

    return night_summarize_time_bundle_graph_node_id(
        target_time_bundle_node_id,
        summary_run_id=summary_run_id,
    )


def run_night_summarize_time_bundle(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    target_time_bundle_node_id: str,
    summary_run_id: str,
    adapter: LLMAdapter | None,
    max_retries: int = 0,
) -> RecordedNightTimeBundleSummaryResult:
    """Create an LLM summary graph node for one code-generated TimeBundle."""

    target_payload = _require_graph_node_payload(
        data_store=data_store,
        graph_node_id=target_time_bundle_node_id,
        expected_node_kind="time_bundle",
    )
    frame_id = night_summarize_time_bundle_frame_id(
        target_time_bundle_node_id,
        summary_run_id=summary_run_id,
    )
    summary_graph_node_id = night_summarize_time_bundle_graph_node_id(
        target_time_bundle_node_id,
        summary_run_id=summary_run_id,
    )
    source_graph_node_ids = _string_list(target_payload.get("source_graph_node_ids"))
    source_node_payloads = _source_node_payloads(
        data_store=data_store,
        source_graph_node_ids=source_graph_node_ids,
    )
    source_trace_ids = _unique_strings(
        [
            *_string_list(target_payload.get("source_trace_ids")),
            *[
                trace_id
                for payload in source_node_payloads
                for trace_id in _string_list(payload.get("source_trace_ids"))
            ],
        ]
    )
    base_source_data_ids = _unique_strings(
        [target_time_bundle_node_id, *source_graph_node_ids]
    )
    input_data_id = f"{frame_id}:input"
    input_payload = _input_payload(
        input_data_id=input_data_id,
        target_time_bundle_node_id=target_time_bundle_node_id,
        target_payload=target_payload,
        source_node_payloads=source_node_payloads,
        summary_run_id=summary_run_id,
        source_data_ids=base_source_data_ids,
        source_trace_ids=source_trace_ids,
    )
    input_trace_id = _record_input(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        input_data_id=input_data_id,
        input_payload=input_payload,
        source_trace_ids=source_trace_ids,
        source_data_ids=base_source_data_ids,
    )
    frame_source_trace_ids = _unique_strings([*source_trace_ids, input_trace_id])
    frame_base_source_data_ids = _unique_strings([*base_source_data_ids, input_data_id])

    if adapter is None:
        frame = _failed_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            target_payload=target_payload,
            source_graph_node_ids=source_graph_node_ids,
            source_node_payloads=source_node_payloads,
            model_id="adapter_missing",
            failure_type="adapter_missing",
            payload_parse_status="not_checked",
            source_trace_ids=frame_source_trace_ids,
            source_data_ids=frame_base_source_data_ids,
            llm_call_data_id=None,
            llm_trace_event_id=None,
        )
        return _record_failed_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    expected_info_class = _expected_info_class(
        source_graph_node_ids=source_graph_node_ids,
        source_leaf_count=_int(target_payload.get("source_leaf_count")),
        source_summary_count=_int(target_payload.get("source_summary_count")),
    )
    prompt = Path(NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id=NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID,
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF,
        input_ref=frame_source_trace_ids,
        source_data_ids=frame_base_source_data_ids,
        max_retries=max_retries,
        payload_validator=lambda payload: _validate_summary_payload(
            payload=payload,
            expected_info_class=expected_info_class,
            allowed_source_graph_node_ids=source_graph_node_ids,
        ),
    )
    source_trace_ids_after_llm = _unique_strings(
        [*frame_source_trace_ids, llm_result.trace_event_id]
    )
    source_data_ids_after_llm = _unique_strings(
        [*frame_base_source_data_ids, llm_result.call_data_id]
    )

    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        frame = _failed_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            target_payload=target_payload,
            source_graph_node_ids=source_graph_node_ids,
            source_node_payloads=source_node_payloads,
            model_id=llm_result.model_id,
            failure_type=llm_result.failure_type,
            payload_parse_status=_payload_parse_status(llm_result.failure_type),
            source_trace_ids=source_trace_ids_after_llm,
            source_data_ids=source_data_ids_after_llm,
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
        )
        return _record_failed_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    frame = _frame_from_payload(
        payload=llm_result.validation.payload,
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_payload=target_payload,
        source_graph_node_ids=source_graph_node_ids,
        source_node_payloads=source_node_payloads,
        model_id=llm_result.model_id,
        source_trace_ids=source_trace_ids_after_llm,
        source_data_ids=source_data_ids_after_llm,
        llm_call_data_id=llm_result.call_data_id,
        llm_trace_event_id=llm_result.trace_event_id,
    )
    return _record_success_graph_summary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
    )


def run_night_time_bundle_summary_worker(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    target_time_bundle_node_id: str,
    summary_run_id: str,
    adapter: LLMAdapter | None,
    max_retries: int = 0,
) -> RecordedNightTimeBundleSummaryResult:
    """Compatibility wrapper for the clearer run_night_summarize_time_bundle name."""

    return run_night_summarize_time_bundle(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        target_time_bundle_node_id=target_time_bundle_node_id,
        summary_run_id=summary_run_id,
        adapter=adapter,
        max_retries=max_retries,
    )


def _frame_from_payload(
    *,
    payload: dict[str, object],
    frame_id: str,
    summary_graph_node_id: str,
    target_payload: dict[str, object],
    source_graph_node_ids: list[str],
    source_node_payloads: list[dict[str, object]],
    model_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> NightTimeBundleSummaryFrame:
    source_leaf_count = _int(target_payload.get("source_leaf_count"))
    source_summary_count = _int(target_payload.get("source_summary_count"))
    info_class = _expected_info_class(
        source_graph_node_ids=source_graph_node_ids,
        source_leaf_count=source_leaf_count,
        source_summary_count=source_summary_count,
    )
    frame = NightTimeBundleSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=_text(target_payload.get("node_id")),
        target_node_kind=_text(target_payload.get("node_kind")),
        summary_text=str(payload.get("summary_text") or "").strip(),
        summary_status="ran",
        failure_type="none",
        payload_parse_status="passed",
        summary_depth=_summary_depth(source_node_payloads, target_payload),
        source_depth_min=_source_depth_min(source_node_payloads, target_payload),
        source_depth_max=_source_depth_max(source_node_payloads, target_payload),
        source_leaf_count=source_leaf_count,
        source_summary_count=source_summary_count,
        source_bundle_kind=_text(target_payload.get("source_bundle_kind")) or "time_bundle",
        validity_status="active",
        review_status="not_reviewed",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        prompt_ref=NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF,
        source_mode=_source_mode(info_class),
        claim_alignment=_claim_alignment(info_class),
        source_graph_node_ids=source_graph_node_ids,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:night_summarize_time_bundle",
        info_class=info_class,
        semantic_judgement_status="ran",
    )
    validate_night_time_bundle_summary_frame(frame)
    return frame


def _failed_frame(
    *,
    frame_id: str,
    summary_graph_node_id: str,
    target_payload: dict[str, object],
    source_graph_node_ids: list[str],
    source_node_payloads: list[dict[str, object]],
    model_id: str,
    failure_type: str,
    payload_parse_status: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> NightTimeBundleSummaryFrame:
    source_leaf_count = _int(target_payload.get("source_leaf_count"))
    source_summary_count = _int(target_payload.get("source_summary_count"))
    info_class = _expected_info_class(
        source_graph_node_ids=source_graph_node_ids,
        source_leaf_count=source_leaf_count,
        source_summary_count=source_summary_count,
    )
    frame = NightTimeBundleSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=_text(target_payload.get("node_id")),
        target_node_kind=_text(target_payload.get("node_kind")),
        summary_text="",
        summary_status="failed",
        failure_type=failure_type,
        payload_parse_status=payload_parse_status,
        summary_depth=_summary_depth(source_node_payloads, target_payload),
        source_depth_min=_source_depth_min(source_node_payloads, target_payload),
        source_depth_max=_source_depth_max(source_node_payloads, target_payload),
        source_leaf_count=source_leaf_count,
        source_summary_count=source_summary_count,
        source_bundle_kind=_text(target_payload.get("source_bundle_kind")) or "time_bundle",
        validity_status="active",
        review_status="not_reviewed",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        prompt_ref=NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF,
        source_mode=_source_mode(info_class),
        claim_alignment=_claim_alignment(info_class),
        source_graph_node_ids=source_graph_node_ids,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:night_summarize_time_bundle",
        info_class=info_class,
        semantic_judgement_status="failed",
    )
    validate_night_time_bundle_summary_frame(frame)
    return frame


def _record_success_graph_summary(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: NightTimeBundleSummaryFrame,
) -> RecordedNightTimeBundleSummaryResult:
    validate_night_time_bundle_summary_frame(frame)
    edge = _summary_of_edge(frame)
    validate_graph_memory_edge_frame(edge)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.summary_graph_node_id, edge.edge_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame.summary_graph_node_id,
        data_type="graph_memory:node:summary",
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=edge.edge_id,
        data_type="graph_memory:edge:SUMMARY_OF",
        payload=asdict(edge),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedNightTimeBundleSummaryResult(
        frame=frame,
        trace_event_id=event.event_id,
        frame_data_id=frame.summary_graph_node_id,
        summary_graph_node_data_id=frame.summary_graph_node_id,
        summary_edge_data_id=edge.edge_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _record_failed_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: NightTimeBundleSummaryFrame,
) -> RecordedNightTimeBundleSummaryResult:
    validate_night_time_bundle_summary_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="failed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame.frame_id,
        data_type=NIGHT_SUMMARIZE_TIME_BUNDLE_FRAME_DATA_TYPE,
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedNightTimeBundleSummaryResult(
        frame=frame,
        trace_event_id=event.event_id,
        frame_data_id=frame.frame_id,
        summary_graph_node_data_id=None,
        summary_edge_data_id=None,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _summary_of_edge(frame: NightTimeBundleSummaryFrame) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=(
            "graph:edge:summary_of:"
            f"{frame.summary_graph_node_id}:{frame.target_graph_node_id}"
        ),
        edge_kind="SUMMARY_OF",
        from_node_id=frame.summary_graph_node_id,
        to_node_id=frame.target_graph_node_id,
        source_graph_node_ids=[
            frame.summary_graph_node_id,
            frame.target_graph_node_id,
            *frame.source_graph_node_ids,
        ],
        source_trace_ids=list(frame.source_trace_ids),
        source_data_ids=[
            frame.summary_graph_node_id,
            frame.target_graph_node_id,
            *frame.source_graph_node_ids,
        ],
    )


def _input_payload(
    *,
    input_data_id: str,
    target_time_bundle_node_id: str,
    target_payload: dict[str, object],
    source_node_payloads: list[dict[str, object]],
    summary_run_id: str,
    source_data_ids: list[str],
    source_trace_ids: list[str],
) -> dict[str, object]:
    source_leaf_count = _int(target_payload.get("source_leaf_count"))
    source_summary_count = _int(target_payload.get("source_summary_count"))
    source_graph_node_ids = _string_list(target_payload.get("source_graph_node_ids"))
    return {
        "input_data_id": input_data_id,
        "summary_run_id": summary_run_id,
        "target_time_bundle_node_id": target_time_bundle_node_id,
        "target_time_bundle_payload": dict(target_payload),
        "source_graph_node_payloads": [dict(payload) for payload in source_node_payloads],
        "expected_info_class": _expected_info_class(
            source_graph_node_ids=source_graph_node_ids,
            source_leaf_count=source_leaf_count,
            source_summary_count=source_summary_count,
        ),
        "classification_rule": (
            "relative only when exactly one raw leaf source is summarized; "
            "otherwise mixed"
        ),
        "source_trace_ids": source_trace_ids,
        "source_data_ids": source_data_ids,
        "generated_by": "CODE:NIGHT_SUMMARIZE_TIME_BUNDLE_INPUT_BUILDER",
        "semantic_judgement_status": "not_run",
    }


def _record_input(
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
        actor=NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID,
        event_type="node_input",
        input_ref=source_trace_ids,
        output_ref=[input_data_id],
        schema_status="not_checked",
    )
    data_store.create_record(
        data_id=input_data_id,
        data_type="node_input:night_summarize_time_bundle_input",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload={
            **input_payload,
            "source_trace_ids": source_trace_ids,
            "source_data_ids": source_data_ids,
        },
    )
    return event.event_id


def _validate_summary_payload(
    *,
    payload: dict[str, object],
    expected_info_class: str,
    allowed_source_graph_node_ids: list[str],
) -> None:
    summary_text = str(payload.get("summary_text") or "").strip()
    if not summary_text:
        raise ValueError("summary_text must not be empty")
    supplied_info_class = payload.get("info_class")
    if supplied_info_class is not None and supplied_info_class != expected_info_class:
        raise ValueError("summary info_class does not match source cardinality")
    supplied_source_ids = _string_list(payload.get("source_graph_node_ids"))
    if supplied_source_ids and set(supplied_source_ids) != set(allowed_source_graph_node_ids):
        raise ValueError("summary source_graph_node_ids must match the target bundle")


def _require_graph_node_payload(
    *,
    data_store: DataStore,
    graph_node_id: str,
    expected_node_kind: str,
) -> dict[str, object]:
    record = data_store.require_record(graph_node_id)
    if not record.data_type.startswith("graph_memory:node:"):
        raise ValueError(f"expected graph memory node record: {graph_node_id}")
    if not isinstance(record.payload, dict):
        raise TypeError(f"graph node payload must be dict: {graph_node_id}")
    node_kind = _text(record.payload.get("node_kind"))
    if node_kind != expected_node_kind:
        raise ValueError(
            f"expected {expected_node_kind} graph node, got {node_kind}: {graph_node_id}"
        )
    return dict(record.payload)


def _source_node_payloads(
    *,
    data_store: DataStore,
    source_graph_node_ids: list[str],
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for graph_node_id in source_graph_node_ids:
        record = data_store.require_record(graph_node_id)
        if not record.data_type.startswith("graph_memory:node:"):
            raise ValueError(f"source graph id is not a graph node: {graph_node_id}")
        if not isinstance(record.payload, dict):
            raise TypeError(f"source graph node payload must be dict: {graph_node_id}")
        payloads.append(dict(record.payload))
    return payloads


def _record_payload_if_missing(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
    created_at: str,
    source_trace_id: str,
    created_data_ids: list[str],
    existing_data_ids: list[str],
) -> None:
    existing = data_store.get_record(data_id)
    if existing is not None:
        if existing.data_type != data_type:
            raise ValueError(f"night summary data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"night summary data_id collision with different payload: {data_id}")
        existing_data_ids.append(data_id)
        return
    data_store.create_record(
        data_id=data_id,
        data_type=data_type,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )
    created_data_ids.append(data_id)


def _summary_depth(
    source_node_payloads: list[dict[str, object]],
    target_payload: dict[str, object],
) -> int:
    source_depths = [_int(payload.get("summary_depth")) for payload in source_node_payloads]
    if source_depths:
        return max(source_depths) + 1
    return _int(target_payload.get("summary_depth")) + 1


def _source_depth_min(
    source_node_payloads: list[dict[str, object]],
    target_payload: dict[str, object],
) -> int:
    source_depths = [_int(payload.get("summary_depth")) for payload in source_node_payloads]
    if source_depths:
        return min(source_depths)
    return _int(target_payload.get("summary_depth"))


def _source_depth_max(
    source_node_payloads: list[dict[str, object]],
    target_payload: dict[str, object],
) -> int:
    source_depths = [_int(payload.get("summary_depth")) for payload in source_node_payloads]
    if source_depths:
        return max(source_depths)
    return _int(target_payload.get("summary_depth"))


def _expected_info_class(
    *,
    source_graph_node_ids: list[str],
    source_leaf_count: int,
    source_summary_count: int,
) -> str:
    if source_leaf_count == 1 and source_summary_count == 0 and len(source_graph_node_ids) == 1:
        return "relative"
    return "mixed"


def _source_mode(info_class: str) -> str:
    return "single_source" if info_class == "relative" else "source_bundle"


def _claim_alignment(info_class: str) -> str:
    return "single_absolute_record" if info_class == "relative" else "multi_source_bundle"


def _payload_parse_status(failure_type: str) -> str:
    if failure_type == "parse_failed":
        return "failed"
    if failure_type in {"adapter_failed", "adapter_missing"}:
        return "not_checked"
    return "passed"


def _require_text(field_name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


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
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _stable_suffix(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _safe_id_part(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        raise ValueError("safe id part must not be empty")
    return cleaned


__all__ = [
    "NIGHT_SUMMARIZE_TIME_BUNDLE_FRAME_DATA_TYPE",
    "NIGHT_SUMMARIZE_TIME_BUNDLE_NODE_ID",
    "NIGHT_SUMMARIZE_TIME_BUNDLE_PROMPT_REF",
    "NIGHT_TIME_BUNDLE_SUMMARY_FRAME_DATA_TYPE",
    "NIGHT_TIME_BUNDLE_SUMMARY_PROMPT_REF",
    "NIGHT_TIME_BUNDLE_SUMMARY_WORKER_NODE_ID",
    "RecordedNightTimeBundleSummaryResult",
    "night_summarize_time_bundle_frame_id",
    "night_summarize_time_bundle_graph_node_id",
    "night_time_bundle_summary_frame_id",
    "night_time_bundle_summary_graph_node_id",
    "run_night_summarize_time_bundle",
    "run_night_time_bundle_summary_worker",
]
