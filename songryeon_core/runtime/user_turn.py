from __future__ import annotations

import os
from pathlib import Path

from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.runtime.defaults import (
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_QUERY_ATTEMPTS,
    DEFAULT_MAX_READ_DOC_CALLS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_SEARCH_TOP_K,
)
from songryeon_core.nodes.node_1_router import ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.replay import replay_run


def run_fake_user_turn(
    *,
    user_input: str,
    export_dir: str | Path | None = None,
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
    search_top_k: int = DEFAULT_SEARCH_TOP_K,
    max_query_attempts: int = DEFAULT_MAX_QUERY_ATTEMPTS,
    max_query_candidates: int | None = None,
    max_read_doc_calls: int = DEFAULT_MAX_READ_DOC_CALLS,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    include_data_records: bool = False,
    force_l_route: bool = False,
    same_turn_l_reroute_enabled: bool = False,
    max_l_runs_per_turn: int = 1,
) -> dict[str, object]:
    """Fake adapter로 전체 노드 흐름을 실행한다.

    학습/스모크용 진입점이다. Qwen 없이도 라우팅, L루프, 2/3/4 경계를
    재현할 수 있게 해준다.
    """

    adapter = SongRyeonAllNodesFakeLLMAdapter()
    result = run_dry_turn(
        user_input=user_input,
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        export_dir=str(export_dir) if export_dir is not None else None,
        max_tool_calls=max_tool_calls,
        search_top_k=search_top_k,
        max_query_attempts=max_query_attempts,
        max_query_candidates=max_query_candidates,
        max_read_doc_calls=max_read_doc_calls,
        max_input_chars=max_input_chars,
        force_l_route=force_l_route,
        same_turn_l_reroute_enabled=same_turn_l_reroute_enabled,
        max_l_runs_per_turn=max_l_runs_per_turn,
    )
    return _turn_response(
        status=_status_from_result(result),
        runtime={
            "mode": "fake",
            "model_id": adapter.model_id,
            "adapter_kind": "songryeon-all-nodes-fake-llm-adapter",
        },
        result=result,
        export_dir=export_dir,
        include_data_records=include_data_records,
    )


def run_qwen_user_turn(
    *,
    user_input: str,
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    export_dir: str | Path | None = None,
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
    search_top_k: int = DEFAULT_SEARCH_TOP_K,
    max_query_attempts: int = DEFAULT_MAX_QUERY_ATTEMPTS,
    max_query_candidates: int | None = None,
    max_read_doc_calls: int = DEFAULT_MAX_READ_DOC_CALLS,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    include_data_records: bool = False,
    force_l_route: bool = False,
    same_turn_l_reroute_enabled: bool = False,
    max_l_runs_per_turn: int = 1,
) -> dict[str, object]:
    """Qwen adapter로 사용자 턴을 실행한다.

    현재는 L2만이 아니라 1, L1, L2, L3, 2, 3, 4까지 같은 adapter를
    받을 수 있다. LLM 실패 시에는 구조 실패를 숨기지 않고 status로 돌려준다.
    """

    config = build_llm_runtime_config(
        mode="qwen",
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    runtime = llm_runtime_status(config)
    selected_endpoint = endpoint if endpoint is not None else os.environ.get("QWEN_LOCAL_ENDPOINT")
    adapter = build_llm_adapter(config, endpoint=selected_endpoint)
    if adapter is None:
        return {
            "status": "skipped",
            "reason": "adapter_missing",
            "runtime": runtime,
            "user_input": user_input,
        }

    try:
        result = run_dry_turn(
            user_input=user_input,
            node_1_router_adapter=adapter,
            l1_goal_adapter=adapter,
            l2_query_planner_adapter=adapter,
            l3_result_adapter=adapter,
            node_2_boundary_adapter=adapter,
            node_3_reporter_adapter=adapter,
            node_4_gatekeeper_adapter=adapter,
            export_dir=str(export_dir) if export_dir is not None else None,
            max_tool_calls=max_tool_calls,
            search_top_k=search_top_k,
            max_query_attempts=max_query_attempts,
            max_query_candidates=max_query_candidates,
            max_read_doc_calls=max_read_doc_calls,
            max_input_chars=max_input_chars,
            force_l_route=force_l_route,
            same_turn_l_reroute_enabled=same_turn_l_reroute_enabled,
            max_l_runs_per_turn=max_l_runs_per_turn,
            allow_node_1_router_fallback=False,
            node_1_router_fallback_policy=ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED,
        )
    except Exception as exc:
        return {
            "status": "structure_failed",
            "reason": exc.__class__.__name__,
            "error": str(exc),
            "runtime": runtime,
            "user_input": user_input,
        }

    status = _status_from_result(result)
    return _turn_response(
        status=status,
        runtime=runtime,
        result=result,
        export_dir=export_dir,
        include_data_records=include_data_records,
    )


def _turn_response(
    *,
    status: str,
    runtime: dict[str, object],
    result: dict[str, object],
    export_dir: str | Path | None,
    include_data_records: bool = False,
) -> dict[str, object]:
    """Build the JSON payload printed by fake-turn and qwen-turn."""

    data_ids = set(result.get("data_ids") or [])
    response: dict[str, object] = {
        "status": status,
        "runtime": runtime,
        "turn_id": result.get("turn_id"),
        "trace_count": result.get("trace_count"),
        "data_record_count": result.get("data_record_count"),
        "relative_info_count": result.get("relative_info_count"),
        "mixed_info_count": result.get("mixed_info_count"),
        "llm_call_count": result.get("llm_call_count"),
        "tool_result_count": result.get("tool_result_count"),
        "tool_distillation_count": result.get("tool_distillation_count"),
        "tool_budget_frame_count": result.get("tool_budget_frame_count"),
        "l_loop_budget_plan_count": result.get("l_loop_budget_plan_count"),
        "task_frame_count": result.get("task_frame_count"),
        "task_result_count": result.get("task_result_count"),
        "search_top_k": result.get("search_top_k"),
        "max_query_attempts": result.get("max_query_attempts"),
        "l2_query_source": result.get("l2_query_source"),
        "l2_query_plan_present": (
            "L2:query_plan_frame" in data_ids
            or _has_record_type(result, "node_output:L2_query_plan_frame")
        ),
        "l_loop_final_decision": result.get("l_loop_final_decision"),
        "l_loop_final_continuation_status": result.get("l_loop_final_continuation_status"),
        "l_loop_continuation_count": result.get("l_loop_continuation_count"),
        "l_loop_revision_query_count": result.get("l_loop_revision_query_count"),
        "l_loop_run_count": result.get("l_loop_run_count"),
        "same_turn_l_reroute_enabled": result.get("same_turn_l_reroute_enabled"),
        "max_l_runs_per_turn": result.get("max_l_runs_per_turn"),
        "effective_max_l_runs_per_turn": result.get("effective_max_l_runs_per_turn"),
        "same_turn_rerun_allowed": result.get("same_turn_rerun_allowed"),
        "rerun_block_reason": result.get("rerun_block_reason"),
        "planned_next_step": result.get("planned_next_step"),
        "reroute_controller_decision": result.get("reroute_controller_decision"),
        "reroute_controller_reason": result.get("reroute_controller_reason"),
        "node1_llm_routing_count": result.get("node1_llm_routing_count"),
        "node1_llm_routing_failed_count": result.get("node1_llm_routing_failed_count"),
        "node1_router_fallback_count": result.get("node1_router_fallback_count"),
        "node1_router_fallback_policy": result.get("node1_router_fallback_policy"),
        "l1_goal_generation_source": result.get("l1_goal_generation_source"),
        "l3_achievement_generation_source": result.get("l3_achievement_generation_source"),
        "node3_reporter_status": result.get("node3_reporter_status"),
        "node4_gate_status": result.get("node4_gate_status"),
        "export_dir": str(export_dir) if export_dir is not None else result.get("export_dir"),
        "report": result.get("report"),
    }
    if include_data_records:
        response["data_records"] = result.get("data_records", [])
    if export_dir is not None:
        replay_text = replay_run(export_dir)
        response["replay_has_llm_call"] = "llm_call:" in replay_text
        response["replay_has_tool_choice"] = "tool_choice:" in replay_text
        response["replay_has_controller"] = "controller:" in replay_text
        response["replay_has_budget"] = "budget:" in replay_text
    return response


def _status_from_result(result: dict[str, object]) -> str:
    if result.get("l2_query_source") == "llm_query_plan":
        return "ok"
    if result.get("l2_query_source") is None and result.get("tool_result_count") == 0:
        return "ok"
    return "model_fallback"


def _has_record_type(result: dict[str, object], data_type: str) -> bool:
    records = result.get("data_records")
    if not isinstance(records, list):
        return False
    return any(
        isinstance(record, dict) and record.get("data_type") == data_type
        for record in records
    )
