from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import CORE_EGO_ROOT_NODE_ID, record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.graph_vessel_neo4j import (
    graph_vessel_neo4j_config_from_env,
    record_graph_vessel_neo4j_write_result,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.songryeon_source_manifest import (
    record_songryeon_core_source_manifest_ingest,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.nodes.night_summarize_source_leaf import (
    RecordedNightSourceLeafSummaryResult,
    night_summarize_source_leaf_frame_id,
    night_summarize_source_leaf_graph_node_id,
    run_night_summarize_changed_source_leaves,
    run_night_summarize_source_leaf,
    select_changed_source_leaf_summary_candidates,
)


DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR = (
    ".songryeon_core_cache/night_changed_sources"
)
DEFAULT_NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_BATCH_ID = (
    "night_changed_sources_one_at_a_time_active"
)
NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_DATA_TYPE = (
    "runtime:night_changed_source_one_at_a_time_queue"
)
NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_GENERATOR = (
    "CODE:NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE"
)


class NightSourceSummaryFakeAdapter:
    """Deterministic adapter for command smoke tests."""

    model_id = "night-source-summary-fake-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        source_text = str(request.input_payload.get("source_text") or "").strip()
        source_file = request.input_payload.get("source_file_payload")
        path = ""
        if isinstance(source_file, dict):
            path = str(source_file.get("path") or "")
        payload = {
            "summary_text": (
                f"Fake source leaf summary for {Path(path).name or 'source'}: "
                f"{' '.join(source_text.split())[:160]}"
            )
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def run_night_changed_source_summary(
    *,
    root_path: str | Path = ".",
    store_dir: str | Path = DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR,
    batch_id: str | None = None,
    turn_id: str | None = None,
    llm_mode: str = "off",
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    write_vessel: bool = False,
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    allow_no_auth: bool = False,
    one_at_a_time: bool = False,
) -> dict[str, object]:
    """Manual opt-in source ingest and changed-leaf summary runner."""

    now = _now_iso()
    safe_batch_id = (
        batch_id
        or (
            DEFAULT_NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_BATCH_ID
            if one_at_a_time
            else f"night_changed_sources_{_safe_timestamp(now)}"
        )
    )
    safe_turn_id = turn_id or f"turn_{safe_batch_id}"
    root = Path(root_path).resolve()
    cache_dir = Path(store_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    trace_path = cache_dir / "trace_store.json"
    data_path = cache_dir / "data_store.json"
    trace_store = TraceStore.load_json(trace_path) if trace_path.exists() else TraceStore()
    data_store = DataStore.load_json(data_path) if data_path.exists() else DataStore()

    adapter = _build_summary_adapter(
        llm_mode=llm_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    summary_results: list[RecordedNightSourceLeafSummaryResult]
    one_at_a_time_state: dict[str, object] | None = None
    if one_at_a_time:
        queue_result = _run_one_at_a_time_source_summary_step(
            trace_store=trace_store,
            data_store=data_store,
            root=root,
            turn_id=safe_turn_id,
            batch_id=safe_batch_id,
            observed_at=now,
            adapter=adapter,
            trace_path=trace_path,
            data_path=data_path,
        )
        summary_results = list(queue_result["summary_results"])
        one_at_a_time_state = dict(queue_result["state"])
        source_manifest_frame_id = str(one_at_a_time_state.get("source_manifest_frame_id") or "")
        source_ingest_frame_id = str(one_at_a_time_state.get("source_ingest_frame_id") or "")
        source_observation_ledger_frame_id = str(
            one_at_a_time_state.get("source_observation_ledger_frame_id") or ""
        )
        source_kind_counts = _dict_value(one_at_a_time_state.get("source_kind_counts"))
        source_observation_status_counts = _dict_value(
            one_at_a_time_state.get("source_observation_status_counts")
        )
        selected_source_graph_node_ids = _string_list(
            one_at_a_time_state.get("selected_source_graph_node_ids")
        )
        skipped_unchanged_source_graph_node_ids = _string_list(
            one_at_a_time_state.get("skipped_unchanged_source_graph_node_ids")
        )
    else:
        _ensure_core_time_axis(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=safe_turn_id,
            batch_id=f"{safe_batch_id}:core",
        )
        manifest_result = record_songryeon_core_source_manifest_ingest(
            trace_store=trace_store,
            data_store=data_store,
            root_path=root,
            turn_id=safe_turn_id,
            batch_id=f"{safe_batch_id}:source_manifest",
            observed_at=now,
            ingested_at=now,
        )
        summary_batch = run_night_summarize_changed_source_leaves(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=safe_turn_id,
            source_observation_ledger_frame_id=(
                manifest_result.ingest_result.source_observation_ledger_frame_id
            ),
            summary_run_id=safe_batch_id,
            adapter=adapter,
        )
        summary_results = list(summary_batch.results)
        source_manifest_frame_id = manifest_result.manifest_data_id
        source_ingest_frame_id = manifest_result.ingest_result.frame_id
        source_observation_ledger_frame_id = (
            manifest_result.ingest_result.source_observation_ledger_frame_id
        )
        source_kind_counts = manifest_result.manifest.source_kind_counts
        source_observation_status_counts = (
            manifest_result.ingest_result.source_observation_status_counts
        )
        selected_source_graph_node_ids = summary_batch.selected_source_graph_node_ids
        skipped_unchanged_source_graph_node_ids = (
            summary_batch.skipped_unchanged_source_graph_node_ids
        )
    export_batch_id = f"{safe_batch_id}:export"
    if one_at_a_time:
        export_batch_id = f"{export_batch_id}:{_safe_timestamp(now)}"
    export_result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=safe_turn_id,
        batch_id=export_batch_id,
        created_at=now,
    )
    plan_result = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=safe_turn_id,
        export_packet_id=export_result.packet.packet_id,
        created_at=now,
    )
    write_result_payload: dict[str, object] | None = None
    if write_vessel:
        config = graph_vessel_neo4j_config_from_env(
            uri=uri,
            user=user,
            password=password,
            database=database,
            allow_no_auth=allow_no_auth,
        )
        write_result = record_graph_vessel_neo4j_write_result(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=safe_turn_id,
            plan_id=plan_result.plan.plan_id,
            config=config,
            created_at=now,
        )
        write_result_payload = asdict(write_result.result)

    trace_store.save_json(trace_path)
    data_store.save_json(data_path)

    summary_status_counts = _summary_status_counts(summary_results)
    result_payload = {
        "status": "NIGHT_CHANGED_SOURCE_SUMMARY_OK",
        "execution_mode": "one_at_a_time" if one_at_a_time else "all_at_once",
        "root_path": root.as_posix(),
        "store_dir": cache_dir.as_posix(),
        "batch_id": safe_batch_id,
        "turn_id": safe_turn_id,
        "llm_runtime": _llm_status_for_mode(
            llm_mode=llm_mode,
            endpoint=endpoint,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
        ),
        "source_manifest_frame_id": source_manifest_frame_id,
        "source_ingest_frame_id": source_ingest_frame_id,
        "source_observation_ledger_frame_id": source_observation_ledger_frame_id,
        "source_kind_counts": source_kind_counts,
        "source_observation_status_counts": source_observation_status_counts,
        "selected_source_leaf_count": len(selected_source_graph_node_ids),
        "skipped_unchanged_source_leaf_count": len(
            skipped_unchanged_source_graph_node_ids
        ),
        "summary_status_counts": summary_status_counts,
        "summary_success_count": summary_status_counts.get("ran", 0),
        "summary_failed_count": summary_status_counts.get("failed", 0),
        "summary_skipped_no_text_snapshot_count": summary_status_counts.get(
            "skipped_no_text_snapshot",
            0,
        ),
        "summary_skipped_empty_text_count": summary_status_counts.get(
            "skipped_empty_text",
            0,
        ),
        "summary_graph_node_ids": [
            result.summary_graph_node_data_id
            for result in summary_results
            if result.summary_graph_node_data_id is not None
        ],
        "summary_edge_ids": [
            result.summary_edge_data_id
            for result in summary_results
            if result.summary_edge_data_id is not None
        ],
        "export_packet_id": export_result.packet.packet_id,
        "write_plan_id": plan_result.plan.plan_id,
        "write_plan_status": plan_result.plan.plan_status,
        "write_vessel_requested": write_vessel,
        "write_result": write_result_payload,
        "trace_store_path": trace_path.as_posix(),
        "data_store_path": data_path.as_posix(),
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
    }
    if one_at_a_time_state is not None:
        result_payload.update(one_at_a_time_state)
    return result_payload


def _run_one_at_a_time_source_summary_step(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    root: Path,
    turn_id: str,
    batch_id: str,
    observed_at: str,
    adapter,
    trace_path: Path,
    data_path: Path,
) -> dict[str, object]:
    queue_id = _one_at_a_time_queue_id(batch_id)
    queue_payload = _load_one_at_a_time_queue(data_store=data_store, queue_id=queue_id)
    queue_status = "existing"
    if queue_payload is None:
        queue_status = "created"
        _ensure_core_time_axis(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            batch_id=f"{batch_id}:core",
        )
        manifest_result = record_songryeon_core_source_manifest_ingest(
            trace_store=trace_store,
            data_store=data_store,
            root_path=root,
            turn_id=turn_id,
            batch_id=f"{batch_id}:source_manifest",
            observed_at=observed_at,
            ingested_at=observed_at,
        )
        selection = select_changed_source_leaf_summary_candidates(
            data_store=data_store,
            source_observation_ledger_frame_id=(
                manifest_result.ingest_result.source_observation_ledger_frame_id
            ),
        )
        queue_payload = _record_one_at_a_time_queue(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            queue_id=queue_id,
            summary_run_id=batch_id,
            source_manifest_frame_id=manifest_result.manifest_data_id,
            source_ingest_frame_id=manifest_result.ingest_result.frame_id,
            source_observation_ledger_frame_id=(
                manifest_result.ingest_result.source_observation_ledger_frame_id
            ),
            source_kind_counts=manifest_result.manifest.source_kind_counts,
            source_observation_status_counts=(
                manifest_result.ingest_result.source_observation_status_counts
            ),
            selected_source_graph_node_ids=selection.selected_source_graph_node_ids,
            skipped_unchanged_source_graph_node_ids=(
                selection.skipped_unchanged_source_graph_node_ids
            ),
            input_trace_ids=[
                manifest_result.manifest_trace_event_id,
                manifest_result.ingest_result.trace_event_id,
            ],
        )
        trace_store.save_json(trace_path)
        data_store.save_json(data_path)

    selected_source_graph_node_ids = _string_list(
        queue_payload.get("selected_source_graph_node_ids")
    )
    processed_before = _processed_source_leaf_ids(
        data_store=data_store,
        source_graph_node_ids=selected_source_graph_node_ids,
        summary_run_id=batch_id,
    )
    pending_source_graph_node_ids = [
        source_graph_node_id
        for source_graph_node_id in selected_source_graph_node_ids
        if source_graph_node_id not in processed_before
    ]
    summary_results: list[RecordedNightSourceLeafSummaryResult] = []
    processed_source_graph_node_id: str | None = None
    if pending_source_graph_node_ids:
        processed_source_graph_node_id = pending_source_graph_node_ids[0]
        summary_results.append(
            run_night_summarize_source_leaf(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                raw_source_graph_node_id=processed_source_graph_node_id,
                summary_run_id=batch_id,
                adapter=adapter,
            )
        )
        trace_store.save_json(trace_path)
        data_store.save_json(data_path)

    processed_after = _processed_source_leaf_ids(
        data_store=data_store,
        source_graph_node_ids=selected_source_graph_node_ids,
        summary_run_id=batch_id,
    )
    pending_after = [
        source_graph_node_id
        for source_graph_node_id in selected_source_graph_node_ids
        if source_graph_node_id not in processed_after
    ]
    if not selected_source_graph_node_ids:
        completion_status = "no_candidates"
    elif pending_after:
        completion_status = "in_progress"
    else:
        completion_status = "complete"

    state = {
        **queue_payload,
        "one_at_a_time_queue_id": queue_id,
        "one_at_a_time_queue_status": queue_status,
        "one_at_a_time_completion_status": completion_status,
        "one_at_a_time_processed_this_run": len(summary_results),
        "one_at_a_time_processed_source_graph_node_id": processed_source_graph_node_id,
        "one_at_a_time_queue_total_count": len(selected_source_graph_node_ids),
        "one_at_a_time_queue_processed_count_before": len(processed_before),
        "one_at_a_time_queue_processed_count_after": len(processed_after),
        "one_at_a_time_queue_pending_count_after": len(pending_after),
        "one_at_a_time_next_source_graph_node_id": (
            pending_after[0] if pending_after else None
        ),
    }
    return {
        "summary_results": summary_results,
        "state": state,
    }


def _one_at_a_time_queue_id(summary_run_id: str) -> str:
    return f"night_summary:changed_source_one_at_a_time_queue:{_safe_id_part(summary_run_id)}"


def _load_one_at_a_time_queue(
    *,
    data_store: DataStore,
    queue_id: str,
) -> dict[str, object] | None:
    record = data_store.get_record(queue_id)
    if record is None:
        return None
    if record.data_type != NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_DATA_TYPE:
        raise ValueError(f"one-at-a-time queue data_id collision: {queue_id}")
    if not isinstance(record.payload, dict):
        raise TypeError("one-at-a-time queue payload must be dict")
    return dict(record.payload)


def _record_one_at_a_time_queue(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    queue_id: str,
    summary_run_id: str,
    source_manifest_frame_id: str,
    source_ingest_frame_id: str,
    source_observation_ledger_frame_id: str,
    source_kind_counts: dict[str, object],
    source_observation_status_counts: dict[str, object],
    selected_source_graph_node_ids: list[str],
    skipped_unchanged_source_graph_node_ids: list[str],
    input_trace_ids: list[str],
) -> dict[str, object]:
    payload = {
        "queue_id": queue_id,
        "summary_run_id": summary_run_id,
        "source_manifest_frame_id": source_manifest_frame_id,
        "source_ingest_frame_id": source_ingest_frame_id,
        "source_observation_ledger_frame_id": source_observation_ledger_frame_id,
        "source_kind_counts": dict(source_kind_counts),
        "source_observation_status_counts": dict(source_observation_status_counts),
        "selected_source_graph_node_ids": list(selected_source_graph_node_ids),
        "skipped_unchanged_source_graph_node_ids": list(
            skipped_unchanged_source_graph_node_ids
        ),
        "generated_by": NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_GENERATOR,
        "info_class": "absolute",
        "semantic_judgement_status": "not_run",
    }
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="night_changed_source_one_at_a_time_queue",
        event_type="node_output",
        input_ref=input_trace_ids,
        output_ref=[queue_id],
        schema_status="passed",
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=queue_id,
        data_type=NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_DATA_TYPE,
        payload=payload,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
    )
    return payload


def _processed_source_leaf_ids(
    *,
    data_store: DataStore,
    source_graph_node_ids: list[str],
    summary_run_id: str,
) -> list[str]:
    processed: list[str] = []
    for source_graph_node_id in source_graph_node_ids:
        summary_node_id = night_summarize_source_leaf_graph_node_id(
            source_graph_node_id,
            summary_run_id=summary_run_id,
        )
        frame_id = night_summarize_source_leaf_frame_id(
            source_graph_node_id,
            summary_run_id=summary_run_id,
        )
        if data_store.get_record(summary_node_id) is not None:
            processed.append(source_graph_node_id)
            continue
        if data_store.get_record(frame_id) is not None:
            processed.append(source_graph_node_id)
    return processed


def _record_payload_if_missing(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
    created_at: str,
    source_trace_id: str,
) -> None:
    existing = data_store.get_record(data_id)
    if existing is not None:
        if existing.data_type != data_type:
            raise ValueError(f"night changed source data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(
                f"night changed source data_id collision with different payload: {data_id}"
            )
        return
    data_store.create_record(
        data_id=data_id,
        data_type=data_type,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )


def _build_summary_adapter(
    *,
    llm_mode: str,
    endpoint: str | None,
    model_id: str | None,
    timeout_seconds: int | None,
):
    selected_mode = llm_mode.strip().lower()
    if selected_mode == "fake":
        return NightSourceSummaryFakeAdapter()
    config = build_llm_runtime_config(
        mode=selected_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    selected_endpoint = endpoint
    return build_llm_adapter(config, endpoint=selected_endpoint)


def _llm_status_for_mode(
    *,
    llm_mode: str,
    endpoint: str | None,
    model_id: str | None,
    timeout_seconds: int | None,
) -> dict[str, object]:
    selected_mode = llm_mode.strip().lower()
    if selected_mode == "fake":
        return {
            "mode": "fake",
            "enabled": True,
            "adapter_kind": "fake",
            "model_id": NightSourceSummaryFakeAdapter.model_id,
            "source": "arguments",
        }
    config = build_llm_runtime_config(
        mode=selected_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    return llm_runtime_status(config)


def _ensure_core_time_axis(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    batch_id: str,
) -> None:
    if data_store.get_record(CORE_EGO_ROOT_NODE_ID) is not None:
        return
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=batch_id,
        capsules=[_sample_capsule(turn_id=f"{turn_id}:bootstrap")],
    )


def _sample_capsule(turn_id: str) -> TurnStateCapsule:
    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=[
            NodeMovement(
                movement_id=f"move:{turn_id}:001",
                turn_id=turn_id,
                step_index=1,
                node_id="node_0",
                mode="night_changed_source_summary_bootstrap",
                input_trace_ids=[f"trace:{turn_id}:input"],
                output_trace_ids=[f"trace:{turn_id}:output"],
                status="completed",
            )
        ],
        trace_event_ids=[
            f"trace:{turn_id}:input",
            f"trace:{turn_id}:output",
            f"trace:{turn_id}:final",
        ],
        user_input_trace_id=f"trace:{turn_id}:input",
        final_response_trace_id=f"trace:{turn_id}:final",
    )


def _summary_status_counts(results: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        status = result.frame.summary_status
        counts[status] = counts.get(status, 0) + 1
    return counts


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def _safe_timestamp(timestamp: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in timestamp).strip("_")


def _safe_id_part(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        raise ValueError("safe id part must not be empty")
    return cleaned


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dict_value(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = [
    "DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR",
    "DEFAULT_NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_BATCH_ID",
    "NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_DATA_TYPE",
    "NightSourceSummaryFakeAdapter",
    "run_night_changed_source_summary",
]
