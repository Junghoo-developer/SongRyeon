from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.graph_vessel_neo4j import (
    graph_vessel_neo4j_config_from_env,
    record_graph_vessel_neo4j_write_result,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.nodes.night_summarize_token_budget_bundle import (
    TokenBudgetSummaryBundleSpec,
    build_token_budget_summary_bundle_specs,
    collect_active_source_leaf_summary_graph_node_ids,
    night_summarize_token_budget_bundle_frame_id,
    night_summarize_token_budget_bundle_graph_node_id,
    run_night_summarize_token_budget_bundle,
)
from songryeon_core.runtime.night_changed_source_summary import (
    DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR,
)


DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_BATCH_ID = "night_token_budget_layer_active"
DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_MAX_BUNDLE_CHARS = 8000
DEFAULT_NIGHT_TOKEN_BUDGET_TARGET_CONTEXT_CHARS = 12000
DEFAULT_NIGHT_TOKEN_BUDGET_MAX_LAYER_DEPTH = 5
DEFAULT_NIGHT_TOKEN_BUDGET_MAX_STEPS = 5
DEFAULT_NIGHT_TOKEN_BUDGET_PROGRESS_JSONL = "night_token_layer_progress.jsonl"
NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE = "runtime:night_token_budget_layer_queue"
NIGHT_TOKEN_BUDGET_LAYER_QUEUE_GENERATOR = "CODE:NIGHT_TOKEN_BUDGET_LAYER_QUEUE"
NIGHT_TOKEN_BUDGET_VESSEL_WRITE_MODES = {"none", "every-step", "at-end"}


class NightTokenBudgetLayerFakeAdapter:
    """Deterministic adapter for token-layer command tests."""

    model_id = "night-token-budget-layer-fake-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        source_summaries = request.input_payload.get("source_summary_payloads")
        count = len(source_summaries) if isinstance(source_summaries, list) else 0
        payload = {
            "summary_text": (
                "Fake token-budget bundle summary over "
                f"{count} supplied source summaries."
            )
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def run_night_token_budget_layer_summary(
    *,
    store_dir: str | Path = DEFAULT_NIGHT_CHANGED_SOURCE_STORE_DIR,
    batch_id: str | None = None,
    turn_id: str | None = None,
    max_bundle_chars: int = DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_MAX_BUNDLE_CHARS,
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
    until_context_budget: bool = False,
    target_context_chars: int = DEFAULT_NIGHT_TOKEN_BUDGET_TARGET_CONTEXT_CHARS,
    max_layer_depth: int = DEFAULT_NIGHT_TOKEN_BUDGET_MAX_LAYER_DEPTH,
    max_steps: int = 1,
    source_summary_graph_node_ids: list[str] | None = None,
    max_runtime_minutes: float | None = None,
    progress_jsonl: str | Path | None = None,
    vessel_write_mode: str | None = None,
    stop_on_failure: bool = True,
) -> dict[str, object]:
    """Run one step of the source-summary token-budget layer summarizer."""

    if max_bundle_chars <= 0:
        raise ValueError("max_bundle_chars must be positive")
    if target_context_chars <= 0:
        raise ValueError("target_context_chars must be positive")
    if max_layer_depth < 2:
        raise ValueError("max_layer_depth must be at least 2")
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if max_runtime_minutes is not None and max_runtime_minutes <= 0:
        raise ValueError("max_runtime_minutes must be positive when set")
    effective_vessel_write_mode = _effective_vessel_write_mode(
        write_vessel=write_vessel,
        vessel_write_mode=vessel_write_mode,
    )
    write_vessel = effective_vessel_write_mode == "every-step"
    if until_context_budget:
        return _run_auto_reduce_until_context_budget(
            store_dir=store_dir,
            batch_id=batch_id,
            turn_id=turn_id,
            max_bundle_chars=max_bundle_chars,
            target_context_chars=target_context_chars,
            max_layer_depth=max_layer_depth,
            max_steps=max_steps,
            max_runtime_minutes=max_runtime_minutes,
            progress_jsonl=progress_jsonl,
            vessel_write_mode=effective_vessel_write_mode,
            stop_on_failure=stop_on_failure,
            llm_mode=llm_mode,
            endpoint=endpoint,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            uri=uri,
            user=user,
            password=password,
            database=database,
            allow_no_auth=allow_no_auth,
        )

    now = _now_iso()
    safe_batch_id = batch_id or DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_BATCH_ID
    safe_turn_id = turn_id or f"turn_{safe_batch_id}"
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

    queue_payload = _load_or_create_queue(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=safe_turn_id,
        batch_id=safe_batch_id,
        max_bundle_chars=max_bundle_chars,
        source_summary_graph_node_ids=source_summary_graph_node_ids,
    )
    specs = [
        TokenBudgetSummaryBundleSpec(
            bundle_index=_int(item.get("bundle_index")),
            bundle_graph_node_id=_text(item.get("bundle_graph_node_id")),
            source_summary_graph_node_ids=_string_list(
                item.get("source_summary_graph_node_ids")
            ),
            source_summary_char_count=_int(item.get("source_summary_char_count")),
            char_budget=_int(item.get("char_budget")),
            char_budget_status=_text(item.get("char_budget_status")),
        )
        for item in _dict_list(queue_payload.get("bundle_specs"))
    ]
    processed_before = _processed_bundle_ids(
        data_store=data_store,
        specs=specs,
        summary_run_id=safe_batch_id,
    )
    pending_specs = [
        spec for spec in specs if spec.bundle_graph_node_id not in processed_before
    ]
    processed_result = None
    if pending_specs:
        processed_result = run_night_summarize_token_budget_bundle(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=safe_turn_id,
            spec=pending_specs[0],
            summary_run_id=safe_batch_id,
            adapter=adapter,
        )
        trace_store.save_json(trace_path)
        data_store.save_json(data_path)

    processed_after = _processed_bundle_ids(
        data_store=data_store,
        specs=specs,
        summary_run_id=safe_batch_id,
    )
    pending_after = [
        spec for spec in specs if spec.bundle_graph_node_id not in processed_after
    ]
    if not specs:
        completion_status = "no_candidates"
    elif pending_after:
        completion_status = "in_progress"
    else:
        completion_status = "complete"

    export_packet_id: str | None = None
    write_plan_id: str | None = None
    write_plan_status = "not_run"
    write_result_payload: dict[str, object] | None = None
    if _has_exportable_graph_records(data_store):
        export_batch_id = f"{safe_batch_id}:token_layer_export:{_safe_timestamp(now)}"
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
        export_packet_id = export_result.packet.packet_id
        write_plan_id = plan_result.plan.plan_id
        write_plan_status = plan_result.plan.plan_status
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

    return {
        "status": "NIGHT_TOKEN_BUDGET_LAYER_SUMMARY_OK",
        "execution_mode": "one_bundle_at_a_time",
        "store_dir": cache_dir.as_posix(),
        "batch_id": safe_batch_id,
        "turn_id": safe_turn_id,
        "llm_runtime": _llm_status_for_mode(
            llm_mode=llm_mode,
            endpoint=endpoint,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
        ),
        "queue_id": queue_payload["queue_id"],
        "queue_status": queue_payload["queue_status"],
        "budget_unit": queue_payload["budget_unit"],
        "max_bundle_chars": queue_payload["max_bundle_chars"],
        "source_summary_count": queue_payload["source_summary_count"],
        "bundle_count": len(specs),
        "processed_this_run": 1 if processed_result is not None else 0,
        "processed_bundle_graph_node_id": (
            processed_result.target_bundle_graph_node_id
            if processed_result is not None
            else None
        ),
        "processed_count_before": len(processed_before),
        "processed_count_after": len(processed_after),
        "pending_count_after": len(pending_after),
        "next_bundle_graph_node_id": (
            pending_after[0].bundle_graph_node_id if pending_after else None
        ),
        "completion_status": completion_status,
        "summary_status": (
            processed_result.frame.summary_status if processed_result is not None else None
        ),
        "summary_graph_node_id": (
            processed_result.summary_graph_node_data_id
            if processed_result is not None
            else None
        ),
        "target_bundle_graph_node_id": (
            processed_result.target_bundle_graph_node_id
            if processed_result is not None
            else None
        ),
        "export_packet_id": export_packet_id,
        "write_plan_id": write_plan_id,
        "write_plan_status": write_plan_status,
        "write_vessel_requested": write_vessel,
        "write_result": write_result_payload,
        "trace_store_path": trace_path.as_posix(),
        "data_store_path": data_path.as_posix(),
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
    }


def _run_auto_reduce_until_context_budget(
    *,
    store_dir: str | Path,
    batch_id: str | None,
    turn_id: str | None,
    max_bundle_chars: int,
    target_context_chars: int,
    max_layer_depth: int,
    max_steps: int,
    max_runtime_minutes: float | None,
    progress_jsonl: str | Path | None,
    vessel_write_mode: str,
    stop_on_failure: bool,
    llm_mode: str,
    endpoint: str | None,
    model_id: str | None,
    timeout_seconds: int | None,
    uri: str | None,
    user: str | None,
    password: str | None,
    database: str | None,
    allow_no_auth: bool,
) -> dict[str, object]:
    safe_batch_id = batch_id or DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_BATCH_ID
    safe_turn_id = turn_id or f"turn_{safe_batch_id}:auto_reduce"
    cache_dir = Path(store_dir).resolve()
    progress_path = (
        Path(progress_jsonl).resolve()
        if progress_jsonl is not None
        else cache_dir / DEFAULT_NIGHT_TOKEN_BUDGET_PROGRESS_JSONL
    )
    started = time.monotonic()
    steps: list[dict[str, object]] = []
    auto_status = "max_steps_reached"
    final_layer_depth = 1
    final_summary_count = 0
    final_summary_char_count = 0
    last_result: dict[str, object] | None = None

    for step_index in range(1, max_steps + 1):
        elapsed_seconds = time.monotonic() - started
        if (
            max_runtime_minutes is not None
            and elapsed_seconds >= max_runtime_minutes * 60
        ):
            auto_status = "max_runtime_reached"
            event = {
                "event_type": "auto_reduce_stop",
                "step_index": step_index,
                "auto_reduce_status": auto_status,
                "elapsed_seconds": round(elapsed_seconds, 3),
            }
            steps.append({**event, "processed_this_step": 0})
            _append_progress_jsonl(progress_path, event)
            break
        data_store = _load_data_store(cache_dir)
        decision = _next_auto_reduce_decision(
            data_store=data_store,
            base_batch_id=safe_batch_id,
            target_context_chars=target_context_chars,
            max_layer_depth=max_layer_depth,
        )
        final_layer_depth = _int(decision.get("current_layer_depth"))
        final_summary_count = _int(decision.get("current_summary_count"))
        final_summary_char_count = _int(decision.get("current_summary_char_count"))
        if decision["action"] != "process_step":
            auto_status = _text(decision.get("action"))
            event = {
                "event_type": "auto_reduce_stop",
                "step_index": step_index,
                **decision,
                "processed_this_step": 0,
                "auto_reduce_status": auto_status,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
            steps.append(event)
            _append_progress_jsonl(progress_path, event)
            break

        layer_depth = _int(decision.get("target_layer_depth"))
        layer_batch_id = _text(decision.get("target_batch_id"))
        source_ids = _string_list(decision.get("source_summary_graph_node_ids"))
        last_result = run_night_token_budget_layer_summary(
            store_dir=cache_dir,
            batch_id=layer_batch_id,
            turn_id=f"{safe_turn_id}:step_{step_index:04d}:layer_{layer_depth:02d}",
            max_bundle_chars=max_bundle_chars,
            llm_mode=llm_mode,
            endpoint=endpoint,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            write_vessel=vessel_write_mode == "every-step",
            uri=uri,
            user=user,
            password=password,
            database=database,
            allow_no_auth=allow_no_auth,
            until_context_budget=False,
            target_context_chars=target_context_chars,
            max_layer_depth=max_layer_depth,
            max_steps=1,
            source_summary_graph_node_ids=source_ids,
        )
        step_event = {
            "event_type": "auto_reduce_step",
            "step_index": step_index,
            **decision,
            "processed_this_step": last_result.get("processed_this_run"),
            "step_completion_status": last_result.get("completion_status"),
            "step_summary_status": last_result.get("summary_status"),
            "step_summary_graph_node_id": last_result.get("summary_graph_node_id"),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        steps.append(step_event)
        _append_progress_jsonl(progress_path, step_event)
        if last_result.get("processed_this_run") != 1:
            auto_status = "blocked_no_progress"
            break
        if stop_on_failure and last_result.get("summary_status") != "ran":
            auto_status = "stopped_on_failure"
            break
    else:
        data_store = _load_data_store(cache_dir)
        decision = _next_auto_reduce_decision(
            data_store=data_store,
            base_batch_id=safe_batch_id,
            target_context_chars=target_context_chars,
            max_layer_depth=max_layer_depth,
        )
        final_layer_depth = _int(decision.get("current_layer_depth"))
        final_summary_count = _int(decision.get("current_summary_count"))
        final_summary_char_count = _int(decision.get("current_summary_char_count"))
        if decision["action"] != "process_step":
            auto_status = _text(decision.get("action"))

    final_write_result: dict[str, object] | None = None
    if vessel_write_mode == "at-end":
        final_write_result = _record_final_vessel_write(
            cache_dir=cache_dir,
            turn_id=f"{safe_turn_id}:final_vessel_write",
            batch_id=f"{safe_batch_id}:checkpointed_final",
            uri=uri,
            user=user,
            password=password,
            database=database,
            allow_no_auth=allow_no_auth,
        )
        _append_progress_jsonl(
            progress_path,
            {
                "event_type": "auto_reduce_final_vessel_write",
                "auto_reduce_status": auto_status,
                "write_status": final_write_result.get("write_status"),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            },
        )

    return {
        "status": "NIGHT_TOKEN_BUDGET_AUTO_REDUCE_OK",
        "execution_mode": "auto_reduce_until_context_budget",
        "store_dir": cache_dir.as_posix(),
        "batch_id": safe_batch_id,
        "turn_id": safe_turn_id,
        "budget_unit": "characters",
        "max_bundle_chars": max_bundle_chars,
        "target_context_chars": target_context_chars,
        "max_layer_depth": max_layer_depth,
        "max_steps": max_steps,
        "max_runtime_minutes": max_runtime_minutes,
        "progress_jsonl_path": progress_path.as_posix(),
        "vessel_write_mode": vessel_write_mode,
        "stop_on_failure": stop_on_failure,
        "step_count": len(steps),
        "auto_reduce_status": auto_status,
        "final_layer_depth": final_layer_depth,
        "final_summary_count": final_summary_count,
        "final_summary_char_count": final_summary_char_count,
        "last_step_result": last_result,
        "final_write_result": final_write_result,
        "steps": steps,
    }


def _next_auto_reduce_decision(
    *,
    data_store: DataStore,
    base_batch_id: str,
    target_context_chars: int,
    max_layer_depth: int,
) -> dict[str, object]:
    leaf_ids = collect_active_source_leaf_summary_graph_node_ids(data_store)
    leaf_chars = _summary_text_char_count(
        data_store=data_store,
        summary_graph_node_ids=leaf_ids,
    )
    if not leaf_ids:
        return {
            "action": "no_candidates",
            "current_layer_depth": 1,
            "current_summary_count": 0,
            "current_summary_char_count": 0,
        }
    if leaf_chars <= target_context_chars:
        return {
            "action": "target_context_reached",
            "current_layer_depth": 1,
            "current_summary_count": len(leaf_ids),
            "current_summary_char_count": leaf_chars,
        }

    previous_layer_summary_ids = leaf_ids
    previous_layer_chars = leaf_chars
    previous_layer_depth = 1
    for target_layer_depth in range(2, max_layer_depth + 1):
        layer_batch_id = _layer_batch_id(base_batch_id, target_layer_depth)
        queue = _load_queue_payload(data_store=data_store, batch_id=layer_batch_id)
        if queue is None:
            return {
                "action": "process_step",
                "current_layer_depth": previous_layer_depth,
                "current_summary_count": len(previous_layer_summary_ids),
                "current_summary_char_count": previous_layer_chars,
                "target_layer_depth": target_layer_depth,
                "target_batch_id": layer_batch_id,
                "source_summary_graph_node_ids": previous_layer_summary_ids,
                "queue_status": "missing_create_next",
            }

        specs = _specs_from_queue(queue)
        processed_ids = _processed_bundle_ids(
            data_store=data_store,
            specs=specs,
            summary_run_id=layer_batch_id,
        )
        if len(processed_ids) < len(specs):
            return {
                "action": "process_step",
                "current_layer_depth": previous_layer_depth,
                "current_summary_count": len(previous_layer_summary_ids),
                "current_summary_char_count": previous_layer_chars,
                "target_layer_depth": target_layer_depth,
                "target_batch_id": layer_batch_id,
                "source_summary_graph_node_ids": _string_list(
                    queue.get("source_summary_graph_node_ids")
                ),
                "queue_status": "existing_incomplete",
                "queue_bundle_count": len(specs),
                "queue_processed_count": len(processed_ids),
                "queue_pending_count": len(specs) - len(processed_ids),
            }

        current_layer_summary_ids = _successful_summary_ids_for_specs(
            data_store=data_store,
            specs=specs,
            summary_run_id=layer_batch_id,
        )
        current_layer_chars = _summary_text_char_count(
            data_store=data_store,
            summary_graph_node_ids=current_layer_summary_ids,
        )
        if not current_layer_summary_ids:
            return {
                "action": "blocked_no_successful_summaries",
                "current_layer_depth": target_layer_depth,
                "current_summary_count": 0,
                "current_summary_char_count": 0,
                "target_batch_id": layer_batch_id,
            }
        if current_layer_chars <= target_context_chars:
            return {
                "action": "target_context_reached",
                "current_layer_depth": target_layer_depth,
                "current_summary_count": len(current_layer_summary_ids),
                "current_summary_char_count": current_layer_chars,
                "target_batch_id": layer_batch_id,
            }
        if target_layer_depth == max_layer_depth:
            return {
                "action": "max_layer_depth_reached",
                "current_layer_depth": target_layer_depth,
                "current_summary_count": len(current_layer_summary_ids),
                "current_summary_char_count": current_layer_chars,
                "target_batch_id": layer_batch_id,
            }
        previous_layer_summary_ids = current_layer_summary_ids
        previous_layer_chars = current_layer_chars
        previous_layer_depth = target_layer_depth

    return {
        "action": "max_layer_depth_reached",
        "current_layer_depth": previous_layer_depth,
        "current_summary_count": len(previous_layer_summary_ids),
        "current_summary_char_count": previous_layer_chars,
    }


def _load_or_create_queue(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    batch_id: str,
    max_bundle_chars: int,
    source_summary_graph_node_ids: list[str] | None = None,
) -> dict[str, object]:
    queue_id = _queue_id(batch_id)
    existing = data_store.get_record(queue_id)
    if existing is not None:
        if existing.data_type != NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE:
            raise ValueError(f"night token layer queue data_id collision: {queue_id}")
        if not isinstance(existing.payload, dict):
            raise TypeError("night token layer queue payload must be dict")
        return {**existing.payload, "queue_status": "existing"}

    selected_source_summary_graph_node_ids = (
        list(source_summary_graph_node_ids)
        if source_summary_graph_node_ids is not None
        else collect_active_source_leaf_summary_graph_node_ids(data_store)
    )
    specs = build_token_budget_summary_bundle_specs(
        data_store=data_store,
        summary_run_id=batch_id,
        source_summary_graph_node_ids=selected_source_summary_graph_node_ids,
        max_bundle_chars=max_bundle_chars,
    )
    payload = {
        "queue_id": queue_id,
        "summary_run_id": batch_id,
        "queue_status": "created",
        "budget_unit": "characters",
        "max_bundle_chars": max_bundle_chars,
        "source_summary_count": len(selected_source_summary_graph_node_ids),
        "source_summary_graph_node_ids": selected_source_summary_graph_node_ids,
        "source_summary_char_count": _summary_text_char_count(
            data_store=data_store,
            summary_graph_node_ids=selected_source_summary_graph_node_ids,
        ),
        "bundle_specs": [asdict(spec) for spec in specs],
        "generated_by": NIGHT_TOKEN_BUDGET_LAYER_QUEUE_GENERATOR,
        "info_class": "absolute",
        "semantic_judgement_status": "not_run",
    }
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="night_token_budget_layer_queue",
        event_type="node_output",
        output_ref=[queue_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=queue_id,
        data_type=NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=payload,
    )
    return payload


def _processed_bundle_ids(
    *,
    data_store: DataStore,
    specs: list[TokenBudgetSummaryBundleSpec],
    summary_run_id: str,
) -> list[str]:
    processed: list[str] = []
    for spec in specs:
        summary_node_id = night_summarize_token_budget_bundle_graph_node_id(
            spec.bundle_graph_node_id,
            summary_run_id=summary_run_id,
        )
        frame_id = night_summarize_token_budget_bundle_frame_id(
            spec.bundle_graph_node_id,
            summary_run_id=summary_run_id,
        )
        if data_store.get_record(summary_node_id) is not None:
            processed.append(spec.bundle_graph_node_id)
            continue
        if data_store.get_record(frame_id) is not None:
            processed.append(spec.bundle_graph_node_id)
    return processed


def _load_data_store(cache_dir: Path) -> DataStore:
    data_path = cache_dir / "data_store.json"
    return DataStore.load_json(data_path) if data_path.exists() else DataStore()


def _load_queue_payload(
    *,
    data_store: DataStore,
    batch_id: str,
) -> dict[str, object] | None:
    record = data_store.get_record(_queue_id(batch_id))
    if record is None:
        return None
    if record.data_type != NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE:
        raise ValueError(f"night token layer queue data_id collision: {record.data_id}")
    if not isinstance(record.payload, dict):
        raise TypeError("night token layer queue payload must be dict")
    return dict(record.payload)


def _specs_from_queue(queue_payload: dict[str, object]) -> list[TokenBudgetSummaryBundleSpec]:
    return [
        TokenBudgetSummaryBundleSpec(
            bundle_index=_int(item.get("bundle_index")),
            bundle_graph_node_id=_text(item.get("bundle_graph_node_id")),
            source_summary_graph_node_ids=_string_list(
                item.get("source_summary_graph_node_ids")
            ),
            source_summary_char_count=_int(item.get("source_summary_char_count")),
            char_budget=_int(item.get("char_budget")),
            char_budget_status=_text(item.get("char_budget_status")),
        )
        for item in _dict_list(queue_payload.get("bundle_specs"))
    ]


def _successful_summary_ids_for_specs(
    *,
    data_store: DataStore,
    specs: list[TokenBudgetSummaryBundleSpec],
    summary_run_id: str,
) -> list[str]:
    result: list[str] = []
    for spec in specs:
        summary_node_id = night_summarize_token_budget_bundle_graph_node_id(
            spec.bundle_graph_node_id,
            summary_run_id=summary_run_id,
        )
        record = data_store.get_record(summary_node_id)
        if record is None or record.data_type != "graph_memory:node:summary":
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get("summary_status") != "ran":
            continue
        if record.payload.get("validity_status") != "active":
            continue
        result.append(summary_node_id)
    return result


def _summary_text_char_count(
    *,
    data_store: DataStore,
    summary_graph_node_ids: list[str],
) -> int:
    total = 0
    for summary_graph_node_id in summary_graph_node_ids:
        record = data_store.get_record(summary_graph_node_id)
        if record is None or not isinstance(record.payload, dict):
            continue
        total += len(_text(record.payload.get("summary_text")))
    return total


def _layer_batch_id(base_batch_id: str, layer_depth: int) -> str:
    if layer_depth < 2:
        raise ValueError("layer_depth must be at least 2")
    if layer_depth == 2:
        return base_batch_id
    return f"{base_batch_id}:layer_{layer_depth:02d}"


def _has_exportable_graph_records(data_store: DataStore) -> bool:
    for record in data_store.list_records():
        if record.data_type.startswith("graph_memory:"):
            return True
        if record.data_type.startswith("graph_source:"):
            return True
    return False


def _effective_vessel_write_mode(
    *,
    write_vessel: bool,
    vessel_write_mode: str | None,
) -> str:
    if vessel_write_mode is None:
        return "every-step" if write_vessel else "none"
    normalized = vessel_write_mode.strip().lower().replace("_", "-")
    if normalized not in NIGHT_TOKEN_BUDGET_VESSEL_WRITE_MODES:
        allowed = ", ".join(sorted(NIGHT_TOKEN_BUDGET_VESSEL_WRITE_MODES))
        raise ValueError(f"unknown vessel_write_mode: {vessel_write_mode}; allowed: {allowed}")
    return normalized


def _append_progress_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "created_at": _now_iso(),
        **payload,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _record_final_vessel_write(
    *,
    cache_dir: Path,
    turn_id: str,
    batch_id: str,
    uri: str | None,
    user: str | None,
    password: str | None,
    database: str | None,
    allow_no_auth: bool,
) -> dict[str, object]:
    trace_path = cache_dir / "trace_store.json"
    data_path = cache_dir / "data_store.json"
    trace_store = TraceStore.load_json(trace_path) if trace_path.exists() else TraceStore()
    data_store = DataStore.load_json(data_path) if data_path.exists() else DataStore()
    if not _has_exportable_graph_records(data_store):
        return {
            "write_status": "not_run",
            "failure_type": "no_exportable_graph_records",
            "failure_reason": "No graph_memory or graph_source records were available.",
        }

    now = _now_iso()
    export_result = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=f"{batch_id}:export:{_safe_timestamp(now)}",
        created_at=now,
    )
    plan_result = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        export_packet_id=export_result.packet.packet_id,
        created_at=now,
    )
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
        turn_id=turn_id,
        plan_id=plan_result.plan.plan_id,
        config=config,
        created_at=now,
    )
    trace_store.save_json(trace_path)
    data_store.save_json(data_path)
    payload = asdict(write_result.result)
    payload["export_packet_id"] = export_result.packet.packet_id
    payload["write_plan_id"] = plan_result.plan.plan_id
    return payload


def _build_summary_adapter(
    *,
    llm_mode: str,
    endpoint: str | None,
    model_id: str | None,
    timeout_seconds: int | None,
):
    selected_mode = llm_mode.strip().lower()
    if selected_mode == "fake":
        return NightTokenBudgetLayerFakeAdapter()
    config = build_llm_runtime_config(
        mode=selected_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    return build_llm_adapter(config, endpoint=endpoint)


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
            "model_id": NightTokenBudgetLayerFakeAdapter.model_id,
            "source": "arguments",
        }
    config = build_llm_runtime_config(
        mode=selected_mode,
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    return llm_runtime_status(config)


def _queue_id(batch_id: str) -> str:
    return f"night_summary:token_budget_layer_queue:{_safe_id_part(batch_id)}"


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


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


__all__ = [
    "DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_BATCH_ID",
    "DEFAULT_NIGHT_TOKEN_BUDGET_LAYER_MAX_BUNDLE_CHARS",
    "DEFAULT_NIGHT_TOKEN_BUDGET_MAX_LAYER_DEPTH",
    "DEFAULT_NIGHT_TOKEN_BUDGET_MAX_STEPS",
    "DEFAULT_NIGHT_TOKEN_BUDGET_TARGET_CONTEXT_CHARS",
    "NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE",
    "NightTokenBudgetLayerFakeAdapter",
    "run_night_token_budget_layer_summary",
]
