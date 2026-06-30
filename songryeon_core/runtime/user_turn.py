from __future__ import annotations

import os
from pathlib import Path

from songryeon_core.core.schemas import TurnStateCapsule
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.llm.runtime import (
    build_llm_adapter,
    build_llm_runtime_config,
    llm_runtime_status,
)
from songryeon_core.runtime.defaults import (
    DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_QUERY_ATTEMPTS,
    DEFAULT_MAX_READ_DOC_CALLS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_SEARCH_TOP_K,
)
from songryeon_core.nodes.node_1_router import ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.live_trace import make_live_trace_sink
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
    max_document_context_chars: int = DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    include_data_records: bool = False,
    force_l_route: bool = False,
    same_turn_l_reroute_enabled: bool = False,
    max_l_runs_per_turn: int = 1,
    live_trace: bool = False,
    turn_id: str | None = None,
    previous_turn_capsules: list[TurnStateCapsule] | None = None,
    recent_raw_conversation: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Fake adapter로 전체 노드 흐름을 실행한다.

    학습/스모크용 진입점이다. Qwen 없이도 라우팅, L루프, 2/3/4 경계를
    재현할 수 있게 해준다.
    """

    adapter = SongRyeonAllNodesFakeLLMAdapter()
    result = run_dry_turn(
        user_input=user_input,
        turn_id=turn_id,
        node_1_router_adapter=adapter,
        memory_relevance_selector_adapter=adapter,
        l1_goal_adapter=adapter,
        l_tool_scope_adapter=adapter,
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
        max_document_context_chars=max_document_context_chars,
        force_l_route=force_l_route,
        same_turn_l_reroute_enabled=same_turn_l_reroute_enabled,
        max_l_runs_per_turn=max_l_runs_per_turn,
        previous_turn_capsules=previous_turn_capsules,
        recent_raw_conversation=recent_raw_conversation,
        live_trace_sink=make_live_trace_sink(enabled=live_trace),
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
    max_document_context_chars: int = DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    include_data_records: bool = False,
    force_l_route: bool = False,
    same_turn_l_reroute_enabled: bool = False,
    max_l_runs_per_turn: int = 1,
    live_trace: bool = False,
    turn_id: str | None = None,
    previous_turn_capsules: list[TurnStateCapsule] | None = None,
    recent_raw_conversation: list[dict[str, str]] | None = None,
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
            turn_id=turn_id,
            node_1_router_adapter=adapter,
            memory_relevance_selector_adapter=adapter,
            l1_goal_adapter=adapter,
            l_tool_scope_adapter=adapter,
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
            max_document_context_chars=max_document_context_chars,
            force_l_route=force_l_route,
            same_turn_l_reroute_enabled=same_turn_l_reroute_enabled,
            max_l_runs_per_turn=max_l_runs_per_turn,
            allow_node_1_router_fallback=False,
            node_1_router_fallback_policy=ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED,
            previous_turn_capsules=previous_turn_capsules,
            recent_raw_conversation=recent_raw_conversation,
            live_trace_sink=make_live_trace_sink(enabled=live_trace),
        )
    except Exception as exc:
        diagnostics = _structure_failure_diagnostics(exc)
        return {
            "status": "structure_failed",
            "reason": exc.__class__.__name__,
            "error": str(exc),
            **diagnostics,
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
        "max_document_context_chars": result.get("max_document_context_chars"),
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
        "recent_capsules_read_count": result.get("recent_capsules_read_count"),
        "recent_raw_conversation_alignment_count": result.get(
            "recent_raw_conversation_alignment_count"
        ),
        "recent_memory_relevance_candidate_count": result.get(
            "recent_memory_relevance_candidate_count"
        ),
        "recent_memory_relevance_selection_status": result.get(
            "recent_memory_relevance_selection_status"
        ),
        "recent_memory_relevance_selection_candidate_count": result.get(
            "recent_memory_relevance_selection_candidate_count"
        ),
        "recent_memory_relevance_selection_selected_count": result.get(
            "recent_memory_relevance_selection_selected_count"
        ),
        "selected_recent_memory_context_count": result.get(
            "selected_recent_memory_context_count"
        ),
        "missing_selected_memory_context_count": result.get(
            "missing_selected_memory_context_count"
        ),
        "raw_memory_compression_candidate_status": result.get(
            "raw_memory_compression_candidate_status"
        ),
        "raw_memory_compression_candidate_turn_ids": result.get(
            "raw_memory_compression_candidate_turn_ids"
        ),
        "raw_memory_retained_raw_turn_ids": result.get("raw_memory_retained_raw_turn_ids"),
        "older_unmanaged_raw_turn_count": result.get("older_unmanaged_raw_turn_count"),
        "l1_goal_generation_source": result.get("l1_goal_generation_source"),
        "l3_achievement_generation_source": result.get("l3_achievement_generation_source"),
        "node2_answer_basis_mode": result.get("node2_answer_basis_mode"),
        "node2_answer_basis_generated_by": result.get("node2_answer_basis_generated_by"),
        "node2_answer_basis_reason_codes": result.get("node2_answer_basis_reason_codes"),
        "node2_answer_basis_semantic_judgement_status": result.get(
            "node2_answer_basis_semantic_judgement_status"
        ),
        "node2_answer_basis_failure_type": result.get("node2_answer_basis_failure_type"),
        "node2_answer_basis_llm_call_data_id": result.get(
            "node2_answer_basis_llm_call_data_id"
        ),
        "node2_answer_basis_trace_event_id": result.get(
            "node2_answer_basis_trace_event_id"
        ),
        "node2_answer_basis_validation_error": result.get(
            "node2_answer_basis_validation_error"
        ),
        "node2_answer_basis_raw_text_present": result.get(
            "node2_answer_basis_raw_text_present"
        ),
        "node2_answer_basis_prompt_ref": result.get("node2_answer_basis_prompt_ref"),
        "node2_answer_basis_payload_parse_status": result.get(
            "node2_answer_basis_payload_parse_status"
        ),
        "node3_reporter_status": result.get("node3_reporter_status"),
        "node4_gate_status": result.get("node4_gate_status"),
        "node4_recent_memory_guard_status": result.get(
            "node4_recent_memory_guard_status"
        ),
        "node4_unsupported_recent_memory_claim_count": result.get(
            "node4_unsupported_recent_memory_claim_count"
        ),
        "turn_capsule": result.get("turn_capsule"),
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


def _structure_failure_diagnostics(exc: Exception) -> dict[str, object]:
    message = _short_diagnostic_text(str(exc) or exc.__class__.__name__)
    node = _infer_failure_node(message)
    diagnostics = {
        "structure_failure_stage": _infer_failure_stage(message, node=node),
        "structure_failure_reason": message or exc.__class__.__name__,
        "structure_failure_exception_type": exc.__class__.__name__,
        "structure_failure_llm_call_data_id": None,
        "structure_failure_trace_event_id": None,
        "structure_failure_node": node,
        "structure_failure_prompt_ref": _prompt_ref_for_node(node),
    }
    budget_diagnostics = getattr(exc, "budget_diagnostics", None)
    if isinstance(budget_diagnostics, dict):
        diagnostics.update(budget_diagnostics)
        diagnostics["structure_failure_stage"] = "run_dry_turn"
        diagnostics["structure_failure_node"] = "L"
    return diagnostics


def _infer_failure_node(message: str) -> str:
    lowered = message.lower()
    if "node_4" in lowered or "gatekeeper" in lowered:
        return "node_4"
    if "node_3" in lowered or "reporter" in lowered:
        return "node_3"
    if "answer_basis" in lowered or "node2 answer" in lowered or "node_2" in lowered:
        return "node_2"
    if "node_1" in lowered or "router" in lowered:
        return "node_1"
    if "toolusebudgetframe" in lowered or "tool use budget" in lowered:
        return "L"
    if "l3" in lowered:
        return "L3"
    if "l2" in lowered:
        return "L2"
    if "l1" in lowered:
        return "L1"
    return "unknown"


def _infer_failure_stage(message: str, *, node: str) -> str:
    lowered = message.lower()
    if "schema" in lowered:
        return f"{node}:schema_validation" if node != "unknown" else "schema_validation"
    if "parse" in lowered or "json" in lowered:
        return f"{node}:payload_parse" if node != "unknown" else "payload_parse"
    if node != "unknown":
        return f"{node}:run"
    return "run_dry_turn"


def _prompt_ref_for_node(node: str) -> str | None:
    prompt_refs = {
        "node_1": "songryeon_core/prompts/node_1_router_v0.md",
        "L1": "songryeon_core/prompts/l1_goal_setter_v0.md",
        "L2": "songryeon_core/prompts/l2_query_setter_v0.md",
        "L3": "songryeon_core/prompts/l3_result_keeper_v0.md",
        "node_2": "songryeon_core/prompts/node_2_answer_basis_selector_v0.md",
        "node_3": "songryeon_core/prompts/node_3_reporter_v0.md",
        "node_4": "songryeon_core/prompts/node_4_gatekeeper_v0.md",
    }
    return prompt_refs.get(node)


def _short_diagnostic_text(text: str, *, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


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
