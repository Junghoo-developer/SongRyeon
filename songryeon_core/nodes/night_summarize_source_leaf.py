from __future__ import annotations

"""Night-government worker that summarizes changed raw source leaves one-to-one."""

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_source_ingest import (
    GRAPH_SOURCE_FILE_DATA_TYPE,
    GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE,
)
from songryeon_core.core.schemas import (
    GraphMemoryEdgeFrame,
    NightSourceLeafSummaryFrame,
    SourceObservationLedgerFrame,
    validate_graph_memory_edge_frame,
    validate_night_source_leaf_summary_frame,
    validate_source_observation_ledger_frame,
)
from songryeon_core.core.source_version_lineage import (
    SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID = "night_summarize_source_leaf"
NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF = (
    "songryeon_core/prompts/night_summarize_source_leaf_v0.md"
)
NIGHT_SUMMARIZE_SOURCE_LEAF_FRAME_DATA_TYPE = (
    "node_output:night_summarize_source_leaf_frame"
)
NIGHT_SUMMARIZE_SOURCE_LEAF_INPUT_DATA_TYPE = (
    "node_input:night_summarize_source_leaf_input"
)
NIGHT_SOURCE_LEAF_SUMMARY_BATCH_DATA_TYPE = (
    "node_output:night_summarize_changed_source_leaves_batch"
)
SUMMARIZABLE_SOURCE_OBSERVATION_STATUSES = {
    "new_source_version",
    "content_changed",
}


@dataclass(frozen=True)
class RecordedNightSourceLeafSummaryResult:
    frame: NightSourceLeafSummaryFrame
    trace_event_id: str
    frame_data_id: str
    summary_graph_node_data_id: str | None
    summary_edge_data_id: str | None
    created_data_ids: list[str]
    existing_data_ids: list[str]


@dataclass(frozen=True)
class RecordedNightChangedSourceLeafSummaryBatch:
    batch_data_id: str
    trace_event_id: str
    source_observation_ledger_frame_id: str
    summary_run_id: str
    selected_source_graph_node_ids: list[str]
    skipped_unchanged_source_graph_node_ids: list[str]
    results: list[RecordedNightSourceLeafSummaryResult]
    created_data_ids: list[str]
    existing_data_ids: list[str]


@dataclass(frozen=True)
class NightChangedSourceLeafSelection:
    source_observation_ledger_frame_id: str
    selected_source_graph_node_ids: list[str]
    skipped_unchanged_source_graph_node_ids: list[str]


def night_summarize_source_leaf_frame_id(
    raw_source_graph_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("raw_source_graph_node_id", raw_source_graph_node_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "night_summary:source_leaf:"
        f"{_stable_suffix(raw_source_graph_node_id)}:{_safe_id_part(summary_run_id)}"
    )


def night_summarize_source_leaf_graph_node_id(
    raw_source_graph_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("raw_source_graph_node_id", raw_source_graph_node_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "graph:summary:source_leaf:"
        f"{_stable_suffix(raw_source_graph_node_id)}:{_safe_id_part(summary_run_id)}"
    )


def night_summarize_changed_source_leaves_batch_id(
    source_observation_ledger_frame_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("source_observation_ledger_frame_id", source_observation_ledger_frame_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "night_summary:changed_source_leaves:"
        f"{_stable_suffix(source_observation_ledger_frame_id)}:"
        f"{_safe_id_part(summary_run_id)}"
    )


def run_night_summarize_changed_source_leaves(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    source_observation_ledger_frame_id: str,
    summary_run_id: str,
    adapter: LLMAdapter | None,
    max_retries: int = 0,
) -> RecordedNightChangedSourceLeafSummaryBatch:
    """Summarize only new or changed raw source leaves from one observation ledger."""

    selection = select_changed_source_leaf_summary_candidates(
        data_store=data_store,
        source_observation_ledger_frame_id=source_observation_ledger_frame_id,
    )
    ledger = _require_source_observation_ledger(
        data_store=data_store,
        source_observation_ledger_frame_id=source_observation_ledger_frame_id,
    )
    selected_source_graph_node_ids = selection.selected_source_graph_node_ids
    skipped_unchanged_source_graph_node_ids = (
        selection.skipped_unchanged_source_graph_node_ids
    )

    results = [
        run_night_summarize_source_leaf(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            raw_source_graph_node_id=source_graph_node_id,
            summary_run_id=summary_run_id,
            adapter=adapter,
            max_retries=max_retries,
        )
        for source_graph_node_id in selected_source_graph_node_ids
    ]

    batch_data_id = night_summarize_changed_source_leaves_batch_id(
        source_observation_ledger_frame_id,
        summary_run_id=summary_run_id,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID,
        event_type="node_output",
        input_ref=ledger.source_trace_ids,
        output_ref=[batch_data_id],
        schema_status="passed",
    )
    payload = {
        "batch_data_id": batch_data_id,
        "source_observation_ledger_frame_id": source_observation_ledger_frame_id,
        "summary_run_id": summary_run_id,
        "selected_source_graph_node_ids": selected_source_graph_node_ids,
        "skipped_unchanged_source_graph_node_ids": skipped_unchanged_source_graph_node_ids,
        "result_frame_ids": [result.frame.frame_id for result in results],
        "summary_graph_node_ids": [
            result.frame.summary_graph_node_id
            for result in results
            if result.summary_graph_node_data_id is not None
        ],
        "summary_status_counts": _count_result_statuses(results),
        "generated_by": "CODE:NIGHT_SUMMARIZE_CHANGED_SOURCE_LEAVES_BATCH",
        "info_class": "absolute",
        "semantic_judgement_status": "not_run",
    }
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=batch_data_id,
        data_type=NIGHT_SOURCE_LEAF_SUMMARY_BATCH_DATA_TYPE,
        payload=payload,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedNightChangedSourceLeafSummaryBatch(
        batch_data_id=batch_data_id,
        trace_event_id=event.event_id,
        source_observation_ledger_frame_id=source_observation_ledger_frame_id,
        summary_run_id=summary_run_id,
        selected_source_graph_node_ids=selected_source_graph_node_ids,
        skipped_unchanged_source_graph_node_ids=skipped_unchanged_source_graph_node_ids,
        results=results,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def select_changed_source_leaf_summary_candidates(
    *,
    data_store: DataStore,
    source_observation_ledger_frame_id: str,
) -> NightChangedSourceLeafSelection:
    """Select summarizable raw_source leaf ids using the observation ledger only."""

    ledger = _require_source_observation_ledger(
        data_store=data_store,
        source_observation_ledger_frame_id=source_observation_ledger_frame_id,
    )
    selected_source_graph_node_ids: list[str] = []
    skipped_unchanged_source_graph_node_ids: list[str] = []
    for record in ledger.observation_records:
        source_graph_node_id = _text(record.get("active_source_graph_node_id"))
        observation_status = _text(record.get("observation_status"))
        if not source_graph_node_id:
            continue
        if observation_status in SUMMARIZABLE_SOURCE_OBSERVATION_STATUSES:
            if source_graph_node_id not in selected_source_graph_node_ids:
                selected_source_graph_node_ids.append(source_graph_node_id)
        elif observation_status == "unchanged":
            if source_graph_node_id not in skipped_unchanged_source_graph_node_ids:
                skipped_unchanged_source_graph_node_ids.append(source_graph_node_id)
    return NightChangedSourceLeafSelection(
        source_observation_ledger_frame_id=source_observation_ledger_frame_id,
        selected_source_graph_node_ids=selected_source_graph_node_ids,
        skipped_unchanged_source_graph_node_ids=skipped_unchanged_source_graph_node_ids,
    )


def run_night_summarize_source_leaf(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    raw_source_graph_node_id: str,
    summary_run_id: str,
    adapter: LLMAdapter | None,
    max_retries: int = 0,
) -> RecordedNightSourceLeafSummaryResult:
    """Create an LLM summary graph node for exactly one raw_source graph leaf."""

    target_payload = _require_graph_node_payload(
        data_store=data_store,
        graph_node_id=raw_source_graph_node_id,
        expected_node_kind="raw_source",
    )
    source_file_record = _require_first_source_record(
        data_store=data_store,
        target_payload=target_payload,
        data_type=GRAPH_SOURCE_FILE_DATA_TYPE,
        record_name="source file metadata",
    )
    source_file_payload = _require_dict_payload(
        source_file_record.payload,
        record_name=source_file_record.data_id,
    )
    text_snapshot_record = _first_source_record(
        data_store=data_store,
        target_payload=target_payload,
        data_type=GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE,
    )
    text_snapshot_payload = (
        _require_dict_payload(text_snapshot_record.payload, record_name=text_snapshot_record.data_id)
        if text_snapshot_record is not None
        else None
    )
    frame_id = night_summarize_source_leaf_frame_id(
        raw_source_graph_node_id,
        summary_run_id=summary_run_id,
    )
    summary_graph_node_id = night_summarize_source_leaf_graph_node_id(
        raw_source_graph_node_id,
        summary_run_id=summary_run_id,
    )
    summary_created_at = datetime.now().isoformat(timespec="microseconds")
    base_source_data_ids = _unique_strings(
        [
            raw_source_graph_node_id,
            source_file_record.data_id,
            text_snapshot_record.data_id if text_snapshot_record is not None else None,
        ]
    )
    base_source_trace_ids = _unique_strings(
        [
            source_file_record.source_trace_id,
            text_snapshot_record.source_trace_id if text_snapshot_record is not None else None,
        ]
    )

    if text_snapshot_payload is None:
        frame = _skipped_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            target_payload=target_payload,
            source_file_data_id=source_file_record.data_id,
            source_file_payload=source_file_payload,
            text_snapshot_data_id=None,
            summary_status="skipped_no_text_snapshot",
            failure_type="no_text_snapshot",
            source_trace_ids=base_source_trace_ids,
            source_data_ids=base_source_data_ids,
            summary_run_id=summary_run_id,
            night_turn_id=turn_id,
            night_batch_id=summary_run_id,
            summary_created_at=summary_created_at,
        )
        return _record_failed_or_skipped_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    source_text = str(text_snapshot_payload.get("text") or "")
    if not source_text.strip():
        frame = _skipped_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            target_payload=target_payload,
            source_file_data_id=source_file_record.data_id,
            source_file_payload=source_file_payload,
            text_snapshot_data_id=text_snapshot_record.data_id,
            summary_status="skipped_empty_text",
            failure_type="empty_text",
            source_trace_ids=base_source_trace_ids,
            source_data_ids=base_source_data_ids,
            summary_run_id=summary_run_id,
            night_turn_id=turn_id,
            night_batch_id=summary_run_id,
            summary_created_at=summary_created_at,
        )
        return _record_failed_or_skipped_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    input_data_id = f"{frame_id}:input"
    input_payload = _input_payload(
        input_data_id=input_data_id,
        summary_run_id=summary_run_id,
        target_payload=target_payload,
        source_file_data_id=source_file_record.data_id,
        source_file_payload=source_file_payload,
        text_snapshot_data_id=text_snapshot_record.data_id,
        text_snapshot_payload=text_snapshot_payload,
        source_text=source_text,
        source_trace_ids=base_source_trace_ids,
        source_data_ids=base_source_data_ids,
    )
    input_trace_id = _record_input(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        input_data_id=input_data_id,
        input_payload=input_payload,
        source_trace_ids=base_source_trace_ids,
        source_data_ids=base_source_data_ids,
    )
    frame_source_trace_ids = _unique_strings([*base_source_trace_ids, input_trace_id])
    frame_base_source_data_ids = _unique_strings([*base_source_data_ids, input_data_id])

    if adapter is None:
        frame = _failed_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            target_payload=target_payload,
            source_file_data_id=source_file_record.data_id,
            source_file_payload=source_file_payload,
            text_snapshot_data_id=text_snapshot_record.data_id,
            model_id="adapter_missing",
            failure_type="adapter_missing",
            payload_parse_status="not_checked",
            source_trace_ids=frame_source_trace_ids,
            source_data_ids=frame_base_source_data_ids,
            summary_run_id=summary_run_id,
            night_turn_id=turn_id,
            night_batch_id=summary_run_id,
            summary_created_at=summary_created_at,
            llm_call_data_id=None,
            llm_trace_event_id=None,
        )
        return _record_failed_or_skipped_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )

    prompt = Path(NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id=NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID,
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF,
        input_ref=frame_source_trace_ids,
        source_data_ids=frame_base_source_data_ids,
        max_retries=max_retries,
        payload_validator=_validate_summary_payload,
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
            source_file_data_id=source_file_record.data_id,
            source_file_payload=source_file_payload,
            text_snapshot_data_id=text_snapshot_record.data_id,
            model_id=llm_result.model_id,
            failure_type=llm_result.failure_type,
            payload_parse_status=_payload_parse_status(llm_result.failure_type),
            source_trace_ids=source_trace_ids_after_llm,
            source_data_ids=source_data_ids_after_llm,
            summary_run_id=summary_run_id,
            night_turn_id=turn_id,
            night_batch_id=summary_run_id,
            summary_created_at=summary_created_at,
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
        )
        return _record_failed_or_skipped_frame(
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
        source_file_data_id=source_file_record.data_id,
        source_file_payload=source_file_payload,
        text_snapshot_data_id=text_snapshot_record.data_id,
        model_id=llm_result.model_id,
        source_trace_ids=source_trace_ids_after_llm,
        source_data_ids=source_data_ids_after_llm,
        summary_run_id=summary_run_id,
        night_turn_id=turn_id,
        night_batch_id=summary_run_id,
        summary_created_at=summary_created_at,
        llm_call_data_id=llm_result.call_data_id,
        llm_trace_event_id=llm_result.trace_event_id,
    )
    return _record_success_graph_summary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
    )


def _frame_from_payload(
    *,
    payload: dict[str, object],
    frame_id: str,
    summary_graph_node_id: str,
    target_payload: dict[str, object],
    source_file_data_id: str,
    source_file_payload: dict[str, object],
    text_snapshot_data_id: str,
    model_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    summary_run_id: str,
    night_turn_id: str,
    night_batch_id: str,
    summary_created_at: str,
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> NightSourceLeafSummaryFrame:
    frame = NightSourceLeafSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=_text(target_payload.get("node_id")),
        target_node_kind=_text(target_payload.get("node_kind")),
        source_kind=_text(source_file_payload.get("source_kind")),
        source_path=_text(source_file_payload.get("path")),
        source_file_data_id=source_file_data_id,
        content_sha1=_text(source_file_payload.get("content_sha1")),
        text_snapshot_data_id=text_snapshot_data_id,
        summary_text=str(payload.get("summary_text") or "").strip(),
        summary_status="ran",
        failure_type="none",
        payload_parse_status="passed",
        summary_run_id=summary_run_id,
        night_turn_id=night_turn_id,
        night_batch_id=night_batch_id,
        summary_created_at=summary_created_at,
        run_provenance_status="recorded",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        prompt_ref=NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF,
        source_graph_node_ids=[_text(target_payload.get("node_id"))],
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:night_summarize_source_leaf",
        info_class="relative",
        semantic_judgement_status="ran",
    )
    validate_night_source_leaf_summary_frame(frame)
    return frame


def _failed_frame(
    *,
    frame_id: str,
    summary_graph_node_id: str,
    target_payload: dict[str, object],
    source_file_data_id: str,
    source_file_payload: dict[str, object],
    text_snapshot_data_id: str,
    model_id: str,
    failure_type: str,
    payload_parse_status: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    summary_run_id: str,
    night_turn_id: str,
    night_batch_id: str,
    summary_created_at: str,
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> NightSourceLeafSummaryFrame:
    frame = NightSourceLeafSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=_text(target_payload.get("node_id")),
        target_node_kind=_text(target_payload.get("node_kind")),
        source_kind=_text(source_file_payload.get("source_kind")),
        source_path=_text(source_file_payload.get("path")),
        source_file_data_id=source_file_data_id,
        content_sha1=_text(source_file_payload.get("content_sha1")),
        text_snapshot_data_id=text_snapshot_data_id,
        summary_text="",
        summary_status="failed",
        failure_type=failure_type,
        payload_parse_status=payload_parse_status,
        summary_run_id=summary_run_id,
        night_turn_id=night_turn_id,
        night_batch_id=night_batch_id,
        summary_created_at=summary_created_at,
        run_provenance_status="recorded",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        prompt_ref=NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF,
        source_graph_node_ids=[_text(target_payload.get("node_id"))],
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:night_summarize_source_leaf",
        info_class="relative",
        semantic_judgement_status="failed",
    )
    validate_night_source_leaf_summary_frame(frame)
    return frame


def _skipped_frame(
    *,
    frame_id: str,
    summary_graph_node_id: str,
    target_payload: dict[str, object],
    source_file_data_id: str,
    source_file_payload: dict[str, object],
    text_snapshot_data_id: str | None,
    summary_status: str,
    failure_type: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    summary_run_id: str,
    night_turn_id: str,
    night_batch_id: str,
    summary_created_at: str,
) -> NightSourceLeafSummaryFrame:
    frame = NightSourceLeafSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=_text(target_payload.get("node_id")),
        target_node_kind=_text(target_payload.get("node_kind")),
        source_kind=_text(source_file_payload.get("source_kind")),
        source_path=_text(source_file_payload.get("path")),
        source_file_data_id=source_file_data_id,
        content_sha1=_text(source_file_payload.get("content_sha1")),
        text_snapshot_data_id=text_snapshot_data_id,
        summary_text="",
        summary_status=summary_status,
        failure_type=failure_type,
        payload_parse_status="not_checked",
        summary_run_id=summary_run_id,
        night_turn_id=night_turn_id,
        night_batch_id=night_batch_id,
        summary_created_at=summary_created_at,
        run_provenance_status="recorded",
        llm_call_data_id=None,
        llm_trace_event_id=None,
        prompt_ref=NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF,
        source_graph_node_ids=[_text(target_payload.get("node_id"))],
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by="CODE:NIGHT_SUMMARIZE_SOURCE_LEAF_SKIPPED",
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_night_source_leaf_summary_frame(frame)
    return frame


def _record_success_graph_summary(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: NightSourceLeafSummaryFrame,
) -> RecordedNightSourceLeafSummaryResult:
    validate_night_source_leaf_summary_frame(frame)
    edge = _summary_of_edge(frame)
    validate_graph_memory_edge_frame(edge)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID,
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
    return RecordedNightSourceLeafSummaryResult(
        frame=frame,
        trace_event_id=event.event_id,
        frame_data_id=frame.summary_graph_node_id,
        summary_graph_node_data_id=frame.summary_graph_node_id,
        summary_edge_data_id=edge.edge_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _record_failed_or_skipped_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: NightSourceLeafSummaryFrame,
) -> RecordedNightSourceLeafSummaryResult:
    validate_night_source_leaf_summary_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="failed" if frame.summary_status == "failed" else "passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame.frame_id,
        data_type=NIGHT_SUMMARIZE_SOURCE_LEAF_FRAME_DATA_TYPE,
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedNightSourceLeafSummaryResult(
        frame=frame,
        trace_event_id=event.event_id,
        frame_data_id=frame.frame_id,
        summary_graph_node_data_id=None,
        summary_edge_data_id=None,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _summary_of_edge(frame: NightSourceLeafSummaryFrame) -> GraphMemoryEdgeFrame:
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
        ],
        source_trace_ids=list(frame.source_trace_ids),
        source_data_ids=[
            frame.summary_graph_node_id,
            frame.target_graph_node_id,
        ],
    )


def _input_payload(
    *,
    input_data_id: str,
    summary_run_id: str,
    target_payload: dict[str, object],
    source_file_data_id: str,
    source_file_payload: dict[str, object],
    text_snapshot_data_id: str,
    text_snapshot_payload: dict[str, object],
    source_text: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> dict[str, object]:
    return {
        "input_data_id": input_data_id,
        "summary_run_id": summary_run_id,
        "target_raw_source_graph_node_id": _text(target_payload.get("node_id")),
        "target_raw_source_payload": dict(target_payload),
        "source_file_data_id": source_file_data_id,
        "source_file_payload": dict(source_file_payload),
        "text_snapshot_data_id": text_snapshot_data_id,
        "text_snapshot_metadata": {
            key: value
            for key, value in text_snapshot_payload.items()
            if key != "text"
        },
        "source_text": source_text,
        "expected_info_class": "relative",
        "classification_rule": (
            "a successful summary is relative because it is grounded in exactly "
            "one raw_source graph leaf"
        ),
        "source_trace_ids": source_trace_ids,
        "source_data_ids": source_data_ids,
        "generated_by": "CODE:NIGHT_SUMMARIZE_SOURCE_LEAF_INPUT_BUILDER",
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
        actor=NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID,
        event_type="node_input",
        input_ref=source_trace_ids,
        output_ref=[input_data_id],
        schema_status="not_checked",
    )
    data_store.create_record(
        data_id=input_data_id,
        data_type=NIGHT_SUMMARIZE_SOURCE_LEAF_INPUT_DATA_TYPE,
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


def _validate_summary_payload(payload: dict[str, object]) -> None:
    summary_text = str(payload.get("summary_text") or "").strip()
    if not summary_text:
        raise ValueError("summary_text must not be empty")
    supplied_info_class = payload.get("info_class")
    if supplied_info_class is not None and supplied_info_class != "relative":
        raise ValueError("source leaf summary info_class must be relative")
    supplied_source_ids = payload.get("source_graph_node_ids")
    if supplied_source_ids:
        raise ValueError("LLM must not supply source_graph_node_ids")


def _require_source_observation_ledger(
    *,
    data_store: DataStore,
    source_observation_ledger_frame_id: str,
) -> SourceObservationLedgerFrame:
    record = data_store.require_record(source_observation_ledger_frame_id)
    if record.data_type != SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE:
        raise ValueError(
            "source_observation_ledger_frame_id must point to source observation ledger"
        )
    if not isinstance(record.payload, dict):
        raise TypeError("source observation ledger payload must be dict")
    frame = SourceObservationLedgerFrame(**record.payload)
    validate_source_observation_ledger_frame(frame)
    return frame


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


def _require_first_source_record(
    *,
    data_store: DataStore,
    target_payload: dict[str, object],
    data_type: str,
    record_name: str,
):
    record = _first_source_record(
        data_store=data_store,
        target_payload=target_payload,
        data_type=data_type,
    )
    if record is None:
        raise ValueError(f"raw_source node is missing {record_name}")
    return record


def _first_source_record(
    *,
    data_store: DataStore,
    target_payload: dict[str, object],
    data_type: str,
):
    for data_id in _string_list(target_payload.get("source_data_ids")):
        record = data_store.get_record(data_id)
        if record is not None and record.data_type == data_type:
            return record
    return None


def _require_dict_payload(payload: object, *, record_name: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise TypeError(f"{record_name} payload must be dict")
    return dict(payload)


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
            raise ValueError(
                f"night source leaf summary data_id collision with different type: {data_id}"
            )
        if existing.payload != payload:
            raise ValueError(
                f"night source leaf summary data_id collision with different payload: {data_id}"
            )
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


def _count_result_statuses(
    results: list[RecordedNightSourceLeafSummaryResult],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.frame.summary_status] = counts.get(result.frame.summary_status, 0) + 1
    return counts


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
    "NIGHT_SOURCE_LEAF_SUMMARY_BATCH_DATA_TYPE",
    "NIGHT_SUMMARIZE_SOURCE_LEAF_FRAME_DATA_TYPE",
    "NIGHT_SUMMARIZE_SOURCE_LEAF_INPUT_DATA_TYPE",
    "NIGHT_SUMMARIZE_SOURCE_LEAF_NODE_ID",
    "NIGHT_SUMMARIZE_SOURCE_LEAF_PROMPT_REF",
    "SUMMARIZABLE_SOURCE_OBSERVATION_STATUSES",
    "RecordedNightChangedSourceLeafSummaryBatch",
    "RecordedNightSourceLeafSummaryResult",
    "NightChangedSourceLeafSelection",
    "night_summarize_changed_source_leaves_batch_id",
    "night_summarize_source_leaf_frame_id",
    "night_summarize_source_leaf_graph_node_id",
    "run_night_summarize_changed_source_leaves",
    "run_night_summarize_source_leaf",
    "select_changed_source_leaf_summary_candidates",
]
