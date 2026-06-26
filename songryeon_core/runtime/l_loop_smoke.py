from __future__ import annotations

import os
from pathlib import Path

from songryeon_core.llm.fake import QueryPlannerFakeLLMAdapter
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.replay import replay_run


def run_fake_llm_l_loop_smoke(*, export_dir: str | Path | None = None) -> dict[str, object]:
    """FakeLLM L2 query planner가 붙은 L루프를 deterministic하게 검증한다."""

    user_input = "L2가 내부 문서를 알아서 검색하게 해줘"
    rule_result = run_dry_turn(user_input=user_input)
    llm_result = run_dry_turn(
        user_input=user_input,
        l2_query_planner_adapter=QueryPlannerFakeLLMAdapter(),
        export_dir=str(export_dir) if export_dir is not None else None,
    )
    llm_records = _records_by_id(llm_result)

    if "L2:query_plan_frame" not in llm_records:
        raise AssertionError("FakeLLM L loop did not create L2:query_plan_frame")
    if llm_result.get("llm_call_count") != 1:
        raise AssertionError("FakeLLM L loop should record exactly one LLM call")
    if llm_result.get("l2_query_source") != "llm_query_plan":
        raise AssertionError("FakeLLM L loop did not use llm_query_plan")
    if llm_result.get("l_loop_final_decision") != "stop_success":
        raise AssertionError("FakeLLM L loop did not finish with stop_success")

    replay_checks: dict[str, object] = {"replay_checked": False}
    if export_dir is not None:
        replay_text = replay_run(export_dir)
        required_fragments = [
            "llm_call:",
            "tool_choice:",
            "tool_result.search_docs:",
            "controller:",
            "budget:",
        ]
        missing_fragments = [
            fragment for fragment in required_fragments if fragment not in replay_text
        ]
        if missing_fragments:
            raise AssertionError(f"replay output is missing fragments: {missing_fragments}")
        replay_checks = {
            "replay_checked": True,
            "replay_has_llm_call": "llm_call:" in replay_text,
            "replay_has_tool_choice": "tool_choice:" in replay_text,
            "replay_has_controller": "controller:" in replay_text,
            "replay_has_budget": "budget:" in replay_text,
        }

    return {
        "status": "FAKE_LLM_L_LOOP_OK",
        "rule_query_source": rule_result.get("l2_query_source"),
        "llm_query_source": llm_result.get("l2_query_source"),
        "rule_data_record_count": rule_result.get("data_record_count"),
        "llm_data_record_count": llm_result.get("data_record_count"),
        "llm_call_count": llm_result.get("llm_call_count"),
        "l2_query_plan_present": "L2:query_plan_frame" in llm_records,
        "l_loop_final_decision": llm_result.get("l_loop_final_decision"),
        "artifact_exported": export_dir is not None,
        "export_dir": str(export_dir) if export_dir is not None else None,
        **replay_checks,
    }


def run_qwen_l_loop_smoke(
    *,
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    export_dir: str | Path | None = None,
) -> dict[str, object]:
    """Qwen endpoint가 있을 때만 L루프 통합 smoke를 시도한다."""

    config = build_llm_runtime_config(
        mode="qwen",
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    selected_endpoint = endpoint if endpoint is not None else os.environ.get("QWEN_LOCAL_ENDPOINT")
    adapter = build_llm_adapter(config, endpoint=selected_endpoint)
    if adapter is None:
        return {
            "status": "skipped",
            "reason": "adapter_missing",
            "runtime": llm_runtime_status(config),
        }

    try:
        result = run_dry_turn(
            user_input="Qwen으로 내부 문서 검색 query를 계획해줘",
            l2_query_planner_adapter=adapter,
            export_dir=str(export_dir) if export_dir is not None else None,
        )
    except Exception as exc:
        return {
            "status": "structure_failed",
            "reason": exc.__class__.__name__,
            "error": str(exc),
            "runtime": llm_runtime_status(config),
        }

    data_ids = set(result.get("data_ids") or [])
    query_source = result.get("l2_query_source")
    status = "ok" if query_source == "llm_query_plan" and "L2:query_plan_frame" in data_ids else "model_fallback"
    response: dict[str, object] = {
        "status": status,
        "runtime": llm_runtime_status(config),
        "query_source": query_source,
        "l2_query_plan_present": "L2:query_plan_frame" in data_ids,
        "llm_call_count": result.get("llm_call_count"),
        "l_loop_final_decision": result.get("l_loop_final_decision"),
        "trace_count": result.get("trace_count"),
        "data_record_count": result.get("data_record_count"),
        "export_dir": str(export_dir) if export_dir is not None else None,
    }
    if export_dir is not None:
        replay_text = replay_run(export_dir)
        response["replay_has_llm_call"] = "llm_call:" in replay_text
        response["replay_has_controller"] = "controller:" in replay_text
    return response


def _records_by_id(result: dict[str, object]) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}
    return {
        record["data_id"]: record["payload"]
        for record in records
        if isinstance(record, dict) and "data_id" in record
    }
