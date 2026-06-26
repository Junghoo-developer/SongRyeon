from __future__ import annotations

from dataclasses import asdict
import tempfile

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.registry import build_default_schema_registry
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    MemoryPacketFrom0,
    NodeMovement,
    Node2InputFrame,
    TurnOutcomeFrame,
    TurnStateCapsule,
    ZeroState,
    validate_node2_input_frame,
    validate_turn_outcome_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.fake import (
    BrokenJSONFakeLLMAdapter,
    ExactArtifactQueryPlannerFakeLLMAdapter,
    FakeLLMAdapter,
    MixedToolQueryPlannerFakeLLMAdapter,
    QueryPlannerFakeLLMAdapter,
    RevisionQueryPlannerFakeLLMAdapter,
    SongRyeonAllNodesFakeLLMAdapter,
)
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_continuation import record_l_loop_continuation_decision
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.loops.l_loop_namespace import (
    L_REROUTE_PLANNED_NEXT_STEP,
    L_REROUTE_REMAINING_BLOCK_REASON,
    build_l_run_ids,
)
from songryeon_core.loops.l_loop_revision_tool_attempt import run_l_loop_revision_tool_attempt
from songryeon_core.nodes.l2_revision_input import record_l2_revision_input_frame
from songryeon_core.nodes.l2_query_setter import (
    l2_revision_query_frame_data_id,
    l2_revision_query_plan_data_id,
    run_l2_revision_query_setter,
    run_l2_revision_query_planner,
    selected_query_from_plan,
)
from songryeon_core.nodes.l3_result_keeper import (
    l3_revision_achievement_frame_data_id,
    l3_revision_preserved_frame_data_id,
    run_l3_revision_result_keeper,
)
from songryeon_core.nodes.node_0_memory_supplier import (
    L3_CONTINUATION_SUMMARY_MODE,
    memory_packet_data_id,
    record_memory_packet,
    record_l3_continuation_summary_for_l2,
    record_l_loop_return_summary_for_node1,
)
from songryeon_core.nodes.node_1_router import (
    ROUTER_FALLBACK_POLICY_DEV_SMOKE,
    ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED,
    Node1RouterLLMFailure,
    record_routing,
    route_next,
)
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief, record_route2_handoff
from songryeon_core.nodes.node_2_metainfo_boundary import build_metainfo_boundary, record_boundary
from songryeon_core.nodes.node_3_reporter import record_report, render_report
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.l_loop_smoke import run_fake_llm_l_loop_smoke
from songryeon_core.runtime.same_turn_l_reroute import (
    SAME_TURN_L_REROUTE_ALLOWED_REASON,
    SAME_TURN_L_REROUTE_MAX_REACHED_REASON,
    SAME_TURN_L_REROUTE_NODE1_ROUTE2_REASON,
)
from songryeon_core.runtime.terminal_view import render_pretty_turn
from songryeon_core.runtime.user_turn import run_fake_user_turn
from songryeon_core.tools.document_memory_index import load_document_memory_index
from songryeon_core.tools.document_tools import list_docs, read_artifact, read_doc, search_docs
from songryeon_core.tools.tool_efficiency_policy import (
    record_duplicate_tool_use_signal,
    record_tool_use_budget_frame,
)


def run_smoke_tests() -> dict[str, object]:
    """MVP 구조가 깨졌는지 빠르게 확인하는 최소 smoke test."""

    result = run_dry_turn()
    data_ids = set(result["data_ids"])
    required_ids = {
        "L1:goal_frame",
        "L2:query_frame",
        "L3:achievement_frame",
        "L3:preserved_info_frame",
        "node_2:handoff_frame",
        "node_3:input_brief_frame",
        "report_dry_001",
        "L:run_frame:0001",
        "L:budget_plan_frame",
        "tool_catalog:turn_dry_001",
        "tool_choice:L2:search_docs",
        "tool_choice:L_controller_0002:read_doc",
        "L:return_summary_frame",
        "L:control:0001",
        "L:control:0002",
        "L:control:0003",
        "tool_budget:turn_dry_001:0001",
        "tool_budget:turn_dry_001:0002",
    }
    missing = sorted(required_ids - data_ids)
    if missing:
        raise AssertionError(f"missing data ids: {missing}")

    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    task_ledger_smoke = _check_task_ledger(result)
    l_loop_run_smoke = _check_l_loop_run_frame(records)
    l_loop_namespace_smoke = _check_l_loop_namespace_ids()
    l_loop_second_run_scope_smoke = _run_l_loop_second_run_scope_smoke()
    l_loop_return_reroute_scope_smoke = _run_l_loop_return_reroute_scope_smoke()
    l_loop_downstream_reroute_scope_smoke = _run_l_loop_downstream_reroute_scope_smoke()
    same_turn_l_reroute_smoke = _run_policy_guarded_same_turn_l_reroute_smoke()
    l3_sources = records["L3:preserved_info_frame"]["source_data_ids"]
    if "L1:goal_frame" not in l3_sources or "L2:query_frame" not in l3_sources:
        raise AssertionError("L3 source data is incomplete")

    achievement = records["L3:achievement_frame"]
    if not achievement["reason"]:
        raise AssertionError("L3 achievement reason is empty")
    if achievement["achievement_status"] not in {"achieved", "partial", "failed"}:
        raise AssertionError("L3 achievement status is invalid")
    _check_route2_handoff_and_brief(records)
    runtime_count_smoke = _run_runtime_count_consistency_smoke()
    return_summary_smoke = _check_l_loop_return_summary(records)
    _check_runtime_explanation_fields(records)
    runtime_label_smoke = _check_runtime_metainfo_labels(result)
    recent_capsule_smoke = _run_recent_turn_capsule_pre_route_smoke()
    recent_raw_alignment_smoke = _run_recent_raw_conversation_capsule_alignment_smoke()

    mixed_info_smoke = _check_mixed_info_boundary(records)
    relative_info_direct_field_smoke = _run_relative_info_direct_field_smoke()
    tool_smoke = _check_tool_catalog_and_choice(records)
    l_loop_control_smoke = _check_l_loop_controller(records)
    distillation_smoke = _check_tool_result_distillation(records)
    efficiency_smoke = _check_tool_efficiency_policy(records)
    budget_limit_smoke = _run_tool_budget_limit_smoke()
    search_budget_smoke = _run_search_budget_names_smoke()
    budget_consistency_smoke = _run_l_loop_budget_consistency_smoke()
    l1_requirement_budget_smoke = _run_l1_requirement_budget_smoke()
    read_artifact_smoke = _run_read_artifact_exact_ref_smoke()
    l3_goal_match_smoke = _run_l3_goal_match_guard_smoke()
    l3_semantic_goal_smoke = _run_l3_semantic_goal_guard_smoke()
    duplicate_signal_smoke = _run_duplicate_tool_use_signal_smoke()
    llm_smoke = _run_llm_call_smoke()
    router_fallback_smoke = _run_router_fallback_honesty_smoke()
    l2_planner_smoke = _run_l2_query_planner_smoke()
    llm_l_loop_smoke = _run_fake_llm_l_loop_export_replay_smoke()
    fake_turn_smoke = _run_fake_user_turn_smoke()
    remand_blocking_smoke = _run_node4_remand_blocking_smoke()
    grounding_count_guard_smoke = _run_node4_grounding_count_guard_smoke()
    gate_failed_honesty_smoke = _run_node4_gate_failed_honesty_smoke()
    continuation_controller_smoke = _run_l_loop_continuation_controller_smoke()
    continuation_memory_smoke = _run_l3_continuation_memory_packet_smoke()
    l2_revision_input_smoke = _run_l2_revision_input_frame_smoke()
    l2_revision_query_smoke = _run_l2_revision_query_planner_smoke()
    l2_revision_query_frame_smoke = _run_l2_revision_query_frame_smoke()
    l2_revision_tool_smoke = _run_l2_revision_tool_attempt_smoke()
    l3_revision_recheck_smoke = _run_l3_revision_recheck_smoke()
    live_continuation_smoke = _run_live_l_loop_continuation_smoke()

    search_result = search_docs(
        root="Administrative_Reform_1",
        query="L3PreservedInfoFrame",
        top_k=1,
    )
    if search_result["result_count"] < 1:
        raise AssertionError("search_docs returned no results")
    document_memory_smoke = _check_document_memory_index(records, search_result)

    return {
        "status": "SMOKE_TEST_OK",
        "trace_count": result["trace_count"],
        "data_record_count": result["data_record_count"],
        "task_frame_count": task_ledger_smoke["task_frame_count"],
        "task_result_count": task_ledger_smoke["task_result_count"],
        "l_loop_run_namespace_policy": l_loop_run_smoke["namespace_policy"],
        "l_loop_run_rerun_allowed": l_loop_run_smoke["same_turn_rerun_allowed"],
        "l_loop_run_block_reason": l_loop_run_smoke["rerun_block_reason"],
        "l_loop_second_run_l1_id": l_loop_namespace_smoke["second_run_l1_id"],
        "l_loop_second_run_control_id": l_loop_second_run_scope_smoke["control_id"],
        "l_loop_second_run_tool_catalog_id": l_loop_second_run_scope_smoke["tool_catalog_id"],
        "l_loop_second_run_tool_budget_id": l_loop_second_run_scope_smoke["tool_budget_id"],
        "l_loop_second_run_revision_query_id": l_loop_second_run_scope_smoke["revision_query_id"],
        "l_loop_second_run_return_summary_id": l_loop_return_reroute_scope_smoke["return_summary_id"],
        "l_loop_second_run_return_packet_id": l_loop_return_reroute_scope_smoke["return_packet_id"],
        "l_loop_second_run_return_route_id": l_loop_return_reroute_scope_smoke["route_id"],
        "l_loop_second_run_node2_input_id": l_loop_downstream_reroute_scope_smoke["node2_input_id"],
        "l_loop_second_run_handoff_id": l_loop_downstream_reroute_scope_smoke["handoff_id"],
        "l_loop_second_run_boundary_id": l_loop_downstream_reroute_scope_smoke["boundary_id"],
        "l_loop_second_run_brief_id": l_loop_downstream_reroute_scope_smoke["brief_id"],
        "l_loop_second_run_report_id": l_loop_downstream_reroute_scope_smoke["report_id"],
        "l_loop_second_run_gatekeeper_id": l_loop_downstream_reroute_scope_smoke["gatekeeper_id"],
        "same_turn_l_reroute_default_run_count": same_turn_l_reroute_smoke["default_run_count"],
        "same_turn_l_reroute_policy_run_count": same_turn_l_reroute_smoke["policy_run_count"],
        "same_turn_l_reroute_second_namespace": same_turn_l_reroute_smoke["second_namespace_policy"],
        "same_turn_l_reroute_final_reason": same_turn_l_reroute_smoke["final_reason"],
        "same_turn_l_reroute_third_run_blocked": same_turn_l_reroute_smoke["third_run_blocked"],
        "runtime_count_reportable_documents": runtime_count_smoke["reportable_document_count"],
        "runtime_count_raw_extract_records": runtime_count_smoke["raw_document_extract_record_count"],
        "runtime_count_empty_extract_records": runtime_count_smoke["empty_document_extract_record_count"],
        "llm_call_records": llm_smoke["llm_call_records"],
        "llm_retry_failure_type": llm_smoke["llm_retry_failure_type"],
        "node1_router_fallback_policy": router_fallback_smoke["fallback_policy"],
        "node1_router_fallback_failure_type": router_fallback_smoke["failure_type"],
        "node1_router_fallback_terminal_distinct": router_fallback_smoke["terminal_distinct"],
        "node1_router_strict_blocked": router_fallback_smoke["strict_blocked"],
        "tool_catalog_count": tool_smoke["tool_catalog_count"],
        "tool_choice": tool_smoke["tool_choice"],
        "l_loop_control_count": l_loop_control_smoke["control_count"],
        "l_loop_final_decision": l_loop_control_smoke["final_decision"],
        "l_loop_return_summary_status": return_summary_smoke["task_status"],
        "l_loop_return_summary_route_hint": return_summary_smoke["route_hint"],
        "l_loop_read_doc_used": l_loop_control_smoke["read_doc_used"],
        "tool_distillation_count": distillation_smoke["distillation_count"],
        "tool_distillation_sources_l3": distillation_smoke["l3_uses_distillation"],
        "relative_info_count": mixed_info_smoke["relative_info_count"],
        "mixed_info_count": mixed_info_smoke["mixed_info_count"],
        "semantic_info_count": mixed_info_smoke["semantic_info_count"],
        "relative_info_direct_field": relative_info_direct_field_smoke["relative_info_direct_field"],
        "relative_info_brief_preserved": relative_info_direct_field_smoke["brief_preserved"],
        "relative_info_report_preserved": relative_info_direct_field_smoke["report_preserved"],
        "mixed_info_excludes_code_l3_reason": mixed_info_smoke["excludes_code_l3_reason"],
        "mixed_info_excludes_code_tool_choice_reason": mixed_info_smoke["excludes_code_tool_choice_reason"],
        "tool_budget_frame_count": efficiency_smoke["budget_frame_count"],
        "tool_budget_cache_status": efficiency_smoke["cache_status"],
        "tool_budget_limit_stop_reason": budget_limit_smoke["stop_reason"],
        "search_top_k_smoke": search_budget_smoke["search_top_k"],
        "max_query_attempts_smoke": search_budget_smoke["max_query_attempts"],
        "budget_consistency_tool_calls": budget_consistency_smoke["approved_max_tool_calls"],
        "budget_consistency_read_doc": budget_consistency_smoke["approved_max_read_doc_calls"],
        "budget_consistency_actual_read_doc": budget_consistency_smoke["actual_read_doc_count"],
        "l1_requirement_budget_read_doc": l1_requirement_budget_smoke["approved_max_read_doc_calls"],
        "l1_requirement_budget_tool_calls": l1_requirement_budget_smoke["approved_max_tool_calls"],
        "read_artifact_doc_id": read_artifact_smoke["doc_id"],
        "read_artifact_l_loop_tool": read_artifact_smoke["l2_tool"],
        "l3_goal_match_status": l3_goal_match_smoke["goal_match_status"],
        "l3_goal_match_achievement_status": l3_goal_match_smoke["achievement_status"],
        "l3_semantic_goal_match_status": l3_semantic_goal_smoke["semantic_goal_match_status"],
        "l3_semantic_goal_achievement_status": l3_semantic_goal_smoke["achievement_status"],
        "duplicate_tool_signal": duplicate_signal_smoke["duplicate_signal"],
        "l2_query_plan_candidates": l2_planner_smoke["candidate_count"],
        "l2_query_plan_mixed_info": l2_planner_smoke["plan_mixed_info"],
        "l2_mixed_tool_plan_normalized": l2_planner_smoke["mixed_tool_plan_normalized"],
        "l2_broken_planner_fallback": l2_planner_smoke["broken_planner_fallback"],
        "fake_llm_l_loop_status": llm_l_loop_smoke["status"],
        "fake_llm_l_loop_replay_checked": llm_l_loop_smoke["replay_checked"],
        "fake_turn_status": fake_turn_smoke["status"],
        "fake_turn_query_source": fake_turn_smoke["query_source"],
        "node4_remand_blocked": remand_blocking_smoke["blocked"],
        "node4_remand_gate_status": remand_blocking_smoke["gate_status"],
        "node4_grounding_count_guard": grounding_count_guard_smoke["gate_status"],
        "node4_gate_failed_honest": gate_failed_honesty_smoke["honest_failure_message"],
        "l_loop_continuation_stop": continuation_controller_smoke["stop_status"],
        "l_loop_continuation_continue": continuation_controller_smoke["continue_status"],
        "l3_continuation_memory_mode": continuation_memory_smoke["mode"],
        "l3_continuation_memory_item_count": continuation_memory_smoke["item_count"],
        "l2_revision_input_attempt": l2_revision_input_smoke["attempt_index"],
        "l2_revision_input_previous_tool": l2_revision_input_smoke["previous_tool_name"],
        "l2_revision_query_plan_mode": l2_revision_query_smoke["planner_mode"],
        "l2_revision_query_plan_selected": l2_revision_query_smoke["selected_query"],
        "l2_revision_query_frame_source": l2_revision_query_frame_smoke["query_source"],
        "l2_revision_query_frame_tool": l2_revision_query_frame_smoke["target_tool_name"],
        "l2_revision_tool_attempt_tool": l2_revision_tool_smoke["tool_name"],
        "l2_revision_tool_attempt_budget": l2_revision_tool_smoke["budget_stop_reason"],
        "l3_revision_recheck_status": l3_revision_recheck_smoke["achievement_status"],
        "l3_revision_recheck_candidates": l3_revision_recheck_smoke["candidate_count"],
        "l3_revision_continuation": l3_revision_recheck_smoke["continuation_status"],
        "live_l_loop_continuation_count": live_continuation_smoke["continuation_count"],
        "live_l_loop_revision_query_count": live_continuation_smoke["revision_query_count"],
        "live_l_loop_final_continuation": live_continuation_smoke["final_continuation_status"],
        "document_memory_index_docs": document_memory_smoke["document_count"],
        "document_memory_index_has_order": document_memory_smoke["has_order"],
        "document_memory_index_l3_metadata": document_memory_smoke["l3_metadata"],
        "runtime_metainfo_label_count": runtime_label_smoke["metainfo_label_count"],
        "runtime_has_copied_from": runtime_label_smoke["has_copied_from"],
        "recent_capsule_read_window": recent_capsule_smoke["read_window"],
        "recent_capsules_read_count": recent_capsule_smoke["read_count"],
        "recent_capsule_item_type": recent_capsule_smoke["item_type"],
        "recent_capsule_trace_evidence_kept": recent_capsule_smoke["trace_evidence_kept"],
        "recent_capsule_llm_summary_status": recent_capsule_smoke["llm_summary_status"],
        "recent_raw_conversation_alignment_window": recent_raw_alignment_smoke["read_window"],
        "recent_raw_conversation_alignment_count": recent_raw_alignment_smoke["read_count"],
        "recent_raw_conversation_alignment_item_type": recent_raw_alignment_smoke["item_type"],
        "recent_raw_conversation_alignment_skips_mismatch": recent_raw_alignment_smoke["skips_mismatch"],
        "recent_raw_conversation_alignment_llm_summary_status": recent_raw_alignment_smoke["llm_summary_status"],
        "top_doc": search_result["results"][0]["doc_id"],
    }


def _check_task_ledger(result: dict[str, object]) -> dict[str, object]:
    records = result["data_records"]
    if not isinstance(records, list):
        raise AssertionError("data_records must be a list")
    task_frames = [
        item
        for item in records
        if isinstance(item, dict) and item.get("data_type") == "task_ledger:task_frame"
    ]
    task_results = [
        item
        for item in records
        if isinstance(item, dict) and item.get("data_type") == "task_ledger:task_result_frame"
    ]
    movement_count = result["movement_count"]
    if len(task_frames) != movement_count:
        raise AssertionError("task frame count must match movement_count")
    if len(task_results) != movement_count:
        raise AssertionError("task result count must match movement_count")
    if result.get("task_frame_count") != len(task_frames):
        raise AssertionError("result.task_frame_count is inconsistent")
    if result.get("task_result_count") != len(task_results):
        raise AssertionError("result.task_result_count is inconsistent")

    sorted_frames = sorted(
        [item["payload"] for item in task_frames if isinstance(item.get("payload"), dict)],
        key=lambda payload: payload["step_index"],
    )
    for index, payload in enumerate(sorted_frames, start=1):
        if payload.get("scheduling_policy") != "sequential_v0":
            raise AssertionError("task ledger v0 must use sequential_v0 policy")
        if payload.get("assigned_worker_id") != "local_sync_worker":
            raise AssertionError("task ledger v0 must use local_sync_worker")
        depends_on = payload.get("depends_on_task_ids")
        expected_dependency = [] if index == 1 else [f"task:{result['turn_id']}:{index - 1:03d}"]
        if depends_on != expected_dependency:
            raise AssertionError("task ledger dependency chain is broken")

    return {
        "task_frame_count": len(task_frames),
        "task_result_count": len(task_results),
    }


def _check_runtime_explanation_fields(records: dict[str, object]) -> None:
    """0/1/L1/L3의 런타임 설명 필드가 보존되는지 확인한다."""

    memory_packet = records["memory_packet:node_1:pre_route_report"]
    route_l = records["route:L"]
    l1_goal = records["L1:goal_frame"]
    l3_achievement = records["L3:achievement_frame"]
    for payload in (memory_packet, route_l, l1_goal, l3_achievement):
        if not isinstance(payload, dict):
            raise AssertionError("runtime explanation payload must be dict")

    if not memory_packet.get("compression_summary"):
        raise AssertionError("0 memory packet operation label is missing")
    if not str(memory_packet.get("compression_summary")).startswith("CODE_STATUS:"):
        raise AssertionError("0 memory packet compression_summary must be a code status label")
    if memory_packet.get("evidence_trace_count") != len(memory_packet.get("evidence_trace_ids") or []):
        raise AssertionError("0 memory packet evidence_trace_count is inconsistent")
    if memory_packet.get("generated_by") != "CODE:RULE_STUB":
        raise AssertionError("0 memory packet generated_by must reveal CODE:RULE_STUB")
    if memory_packet.get("llm_semantic_summary_status") != "not_run":
        raise AssertionError("0 memory packet must reveal LLM summary was not run")
    if not route_l.get("route_reason"):
        raise AssertionError("1 route_reason is missing")
    if not str(route_l.get("route_reason")).startswith("CODE_STATUS:"):
        raise AssertionError("1 route_reason must be a code status label before LLM router")
    if not route_l.get("route_rule_id"):
        raise AssertionError("1 route_rule_id is missing")
    if route_l.get("route_source") != "CODE:RULE_STUB":
        raise AssertionError("1 route source must reveal CODE:RULE_STUB")
    if route_l.get("llm_routing_status") != "not_run":
        raise AssertionError("1 route must reveal LLM routing was not run")
    if not l1_goal.get("macro_goal_reason") or not l1_goal.get("micro_goal_reason"):
        raise AssertionError("L1 goal reasons are missing")
    if not str(l1_goal.get("macro_goal_reason")).startswith("CODE_STATUS:"):
        raise AssertionError("L1 macro reason must be a code status label before LLM goal setter")
    if not str(l1_goal.get("micro_goal_reason")).startswith("CODE_STATUS:"):
        raise AssertionError("L1 micro reason must be a code status label before LLM goal setter")
    if l1_goal.get("goal_generation_source") != "RULE_STUB":
        raise AssertionError("L1 goal source must reveal RULE_STUB")
    if l1_goal.get("llm_goal_judgement_status") != "not_run":
        raise AssertionError("L1 goal must reveal LLM goal judgement was not run")
    if not l3_achievement.get("macro_achievement_reason"):
        raise AssertionError("L3 macro achievement reason is missing")
    if not l3_achievement.get("micro_achievement_reason"):
        raise AssertionError("L3 micro achievement reason is missing")
    if not str(l3_achievement.get("reason")).startswith("CODE_STATUS:"):
        raise AssertionError("L3 reason must be a code status label before LLM result keeper")
    if not str(l3_achievement.get("macro_achievement_reason")).startswith("CODE_STATUS:"):
        raise AssertionError("L3 macro reason must be a code status label before LLM result keeper")
    if not str(l3_achievement.get("micro_achievement_reason")).startswith("CODE_STATUS:"):
        raise AssertionError("L3 micro reason must be a code status label before LLM result keeper")
    if l3_achievement.get("achievement_generation_source") != "CODE:OPERATION_CHECK":
        raise AssertionError("L3 achievement source must reveal CODE:OPERATION_CHECK")
    if l3_achievement.get("llm_semantic_judgement_status") != "not_run":
        raise AssertionError("L3 achievement must reveal LLM semantic judgement was not run")


def _run_recent_turn_capsule_pre_route_smoke() -> dict[str, object]:
    """0 should copy only recent TurnStateCapsule index fields into pre-route memory."""

    previous_capsules = [
        _sample_previous_turn_capsule(index)
        for index in range(1, 5)
    ]
    result = run_dry_turn(previous_turn_capsules=previous_capsules)
    if result.get("recent_capsule_read_window") != 3:
        raise AssertionError("recent capsule read window must be N=3")
    if result.get("recent_capsules_read_count") != 3:
        raise AssertionError("recent capsule read count must be recorded as 3")

    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    packet = records.get("memory_packet:node_1:pre_route_report")
    if not isinstance(packet, dict):
        raise AssertionError("pre-route memory packet payload must be a dict")
    if packet.get("llm_semantic_summary_status") != "not_run":
        raise AssertionError("pre-route capsule index must not run semantic summary")

    items = packet.get("memory_items")
    if not isinstance(items, list):
        raise AssertionError("pre-route memory_items must be a list")
    item_types = [item.get("item_type") for item in items if isinstance(item, dict)]
    if "trace_evidence" not in item_types:
        raise AssertionError("existing trace_evidence memory item must be kept")

    capsule_items = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("item_type") == "previous_turn_capsule_index"
    ]
    if len(capsule_items) != 3:
        raise AssertionError("pre-route packet must include 3 previous capsule index items")

    expected_turn_indexes = [2, 3, 4]
    rendered_items = "\n".join(str(item.get("text", "")) for item in capsule_items)
    if "turn_prev_001" in rendered_items:
        raise AssertionError("pre-route capsule read must not include the 4th older capsule")
    for capsule_item, index in zip(capsule_items, expected_turn_indexes):
        expected_text = (
            "COPIED_FIELDS:"
            f"turn_id=turn_prev_{index:03d};"
            "trace_count=3;"
            "movement_count=1;"
            f"user_input_trace_id=trace_prev_{index:03d}_user;"
            f"final_response_trace_id=trace_prev_{index:03d}_final"
        )
        if capsule_item.get("text") != expected_text:
            raise AssertionError("previous_turn_capsule_index must copy only capsule fields")
        if capsule_item.get("source_trace_ids") != [
            f"trace_prev_{index:03d}_user",
            f"trace_prev_{index:03d}_final",
        ]:
            raise AssertionError("previous_turn_capsule_index source_trace_ids are wrong")
        if capsule_item.get("source_data_ids") != []:
            raise AssertionError("previous_turn_capsule_index source_data_ids must be empty")

    return {
        "read_window": result["recent_capsule_read_window"],
        "read_count": result["recent_capsules_read_count"],
        "item_type": "previous_turn_capsule_index",
        "trace_evidence_kept": True,
        "llm_summary_status": packet.get("llm_semantic_summary_status"),
    }


def _run_recent_raw_conversation_capsule_alignment_smoke() -> dict[str, object]:
    """0 should align recent raw conversation and capsules only by matching turn_id."""

    recent_raw_conversation = [
        _sample_recent_raw_conversation_entry(index)
        for index in range(1, 10)
    ]
    previous_capsules = [
        _sample_previous_turn_capsule(index)
        for index in range(1, 10)
    ]
    result = run_dry_turn(
        recent_raw_conversation=recent_raw_conversation,
        previous_turn_capsules=previous_capsules,
    )
    if result.get("recent_raw_conversation_alignment_window") != 8:
        raise AssertionError("recent raw conversation alignment window must be N=8")
    if result.get("recent_raw_conversation_alignment_count") != 8:
        raise AssertionError("recent raw conversation alignment count must be 8")

    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    packet = records.get("memory_packet:node_1:pre_route_report")
    if not isinstance(packet, dict):
        raise AssertionError("pre-route memory packet payload must be a dict")
    if packet.get("llm_semantic_summary_status") != "not_run":
        raise AssertionError("recent raw alignment must not run semantic summary")

    items = packet.get("memory_items")
    if not isinstance(items, list):
        raise AssertionError("pre-route memory_items must be a list")
    item_types = [item.get("item_type") for item in items if isinstance(item, dict)]
    if "trace_evidence" not in item_types:
        raise AssertionError("existing trace_evidence memory item must be kept")
    if "previous_turn_capsule_index" not in item_types:
        raise AssertionError("previous_turn_capsule_index memory item must be kept")

    alignment_items = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("item_type") == "recent_raw_conversation_capsule_alignment"
    ]
    if len(alignment_items) != 8:
        raise AssertionError("pre-route packet must include 8 raw-capsule alignment items")

    expected_turn_indexes = list(range(2, 10))
    rendered_items = "\n".join(str(item.get("text", "")) for item in alignment_items)
    if "turn_prev_001" in rendered_items:
        raise AssertionError("alignment read window must not include the 9th older raw turn")
    for alignment_item, index in zip(alignment_items, expected_turn_indexes):
        raw_entry = recent_raw_conversation[index - 1]
        capsule = previous_capsules[index - 1]
        expected_text = (
            "COPIED_FIELDS:"
            f"turn_id=turn_prev_{index:03d};"
            "raw_user_text_present=true;"
            "raw_assistant_text_present=true;"
            f"raw_user_text_chars={len(raw_entry['user_text'])};"
            f"raw_assistant_text_chars={len(raw_entry['assistant_text'])};"
            "capsule_trace_count=3;"
            "capsule_movement_count=1;"
            f"user_input_trace_id=trace_prev_{index:03d}_user;"
            f"final_response_trace_id=trace_prev_{index:03d}_final"
        )
        if alignment_item.get("text") != expected_text:
            raise AssertionError("alignment item must copy only raw/capsule fields")
        if not str(alignment_item.get("text", "")).startswith("COPIED_FIELDS:"):
            raise AssertionError("alignment item text must start with COPIED_FIELDS")
        if alignment_item.get("source_trace_ids") != [
            f"trace_prev_{index:03d}_user",
            f"trace_prev_{index:03d}_final",
        ]:
            raise AssertionError("alignment item source_trace_ids are wrong")
        for trace_id in alignment_item.get("source_trace_ids") or []:
            if trace_id not in capsule.trace_event_ids:
                raise AssertionError("alignment source_trace_ids must exist in capsule")
        if alignment_item.get("source_data_ids") != []:
            raise AssertionError("alignment item source_data_ids must be empty")

    mismatch_result = run_dry_turn(
        recent_raw_conversation=[
            _sample_recent_raw_conversation_entry(1),
            {
                "turn_id": "turn_without_capsule",
                "user_text": "raw user mismatch",
                "assistant_text": "raw assistant mismatch",
            },
        ],
        previous_turn_capsules=[
            _sample_previous_turn_capsule(1),
            _sample_previous_turn_capsule(2),
        ],
    )
    if mismatch_result.get("recent_raw_conversation_alignment_count") != 1:
        raise AssertionError("mismatched raw/capsule entries must not be force-aligned")
    mismatch_records = {
        item["data_id"]: item["payload"]
        for item in mismatch_result["data_records"]
    }
    mismatch_packet = mismatch_records.get("memory_packet:node_1:pre_route_report")
    if not isinstance(mismatch_packet, dict):
        raise AssertionError("mismatch pre-route memory packet payload must be a dict")
    mismatch_items = mismatch_packet.get("memory_items")
    if not isinstance(mismatch_items, list):
        raise AssertionError("mismatch pre-route memory_items must be a list")
    mismatch_alignment_text = "\n".join(
        str(item.get("text", ""))
        for item in mismatch_items
        if isinstance(item, dict)
        and item.get("item_type") == "recent_raw_conversation_capsule_alignment"
    )
    if "turn_without_capsule" in mismatch_alignment_text:
        raise AssertionError("raw turn without capsule must not be aligned")
    if "turn_prev_002" in mismatch_alignment_text:
        raise AssertionError("capsule turn without raw must not be aligned")

    return {
        "read_window": result["recent_raw_conversation_alignment_window"],
        "read_count": result["recent_raw_conversation_alignment_count"],
        "item_type": "recent_raw_conversation_capsule_alignment",
        "skips_mismatch": True,
        "llm_summary_status": packet.get("llm_semantic_summary_status"),
    }


def _sample_recent_raw_conversation_entry(index: int) -> dict[str, str]:
    return {
        "turn_id": f"turn_prev_{index:03d}",
        "user_text": f"raw user {index:03d}",
        "assistant_text": f"raw assistant {index:03d}",
    }


def _sample_previous_turn_capsule(index: int) -> TurnStateCapsule:
    turn_id = f"turn_prev_{index:03d}"
    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=[
            NodeMovement(
                movement_id=f"move_prev_{index:03d}_001",
                turn_id=turn_id,
                step_index=1,
                node_id="node_3",
                mode="report",
                input_trace_ids=[f"trace_prev_{index:03d}_user"],
                output_trace_ids=[f"trace_prev_{index:03d}_final"],
                status="completed",
            )
        ],
        trace_event_ids=[
            f"trace_prev_{index:03d}_user",
            f"trace_prev_{index:03d}_middle",
            f"trace_prev_{index:03d}_final",
        ],
        user_input_trace_id=f"trace_prev_{index:03d}_user",
        final_response_trace_id=f"trace_prev_{index:03d}_final",
    )


def _check_route2_handoff_and_brief(records: dict[str, object]) -> None:
    """route=2 handoff와 node_3용 브리프가 새 경계를 지키는지 확인한다."""

    handoff = records["node_2:handoff_frame"]
    brief = records["node_3:input_brief_frame"]
    if not isinstance(handoff, dict) or not isinstance(brief, dict):
        raise AssertionError("route2 handoff and node3 brief payloads must be dicts")
    if handoff.get("handoff_status") not in {"ready", "insufficient", "blocked"}:
        raise AssertionError("route2 handoff status is invalid")
    if "1:route=2" not in (handoff.get("route_path") or []):
        raise AssertionError("route2 handoff must preserve route=2 path")
    for field_name in (
        "reportable_document_count",
        "raw_document_extract_record_count",
        "empty_document_extract_record_count",
        "read_doc_count",
        "actual_l_run_count",
        "blocked_same_turn_l_reroute_request_count",
        "l_internal_revision_count",
    ):
        value = handoff.get(field_name)
        if not isinstance(value, int) or value < 0:
            raise AssertionError(f"route2 handoff {field_name} must be a non-negative integer")
    if handoff.get("read_doc_count") != handoff.get("reportable_document_count"):
        raise AssertionError("route2 handoff read_doc_count must mirror reportable_document_count")
    if handoff.get("raw_document_extract_record_count") < handoff.get("reportable_document_count"):
        raise AssertionError("route2 handoff raw extract count must cover reportable documents")
    controller_decisions = handoff.get("same_turn_l_reroute_controller_decisions")
    if not isinstance(controller_decisions, list):
        raise AssertionError("route2 handoff controller decisions must be a list")
    if brief.get("brief_status") not in {"ready", "insufficient"}:
        raise AssertionError("node3 brief status is invalid")
    if brief.get("handoff_frame_id") != "node_2:handoff_frame":
        raise AssertionError("node3 brief must point back to route2 handoff internally")
    read_documents = brief.get("read_documents")
    search_candidate_count = brief.get("search_candidate_count")
    search_candidate_documents = brief.get("search_candidate_documents")
    allowed_claims = brief.get("allowed_claims")
    runtime_tasks = brief.get("runtime_tasks")
    reporting_rules = brief.get("reporting_rules")
    if (
        not isinstance(read_documents, list)
        or not isinstance(search_candidate_documents, list)
        or not isinstance(allowed_claims, list)
        or not isinstance(runtime_tasks, list)
        or not isinstance(reporting_rules, list)
    ):
        raise AssertionError(
            "node3 brief documents/search candidates/claims/runtime_tasks/reporting_rules must be lists"
        )
    if not isinstance(search_candidate_count, int) or search_candidate_count < 0:
        raise AssertionError("node3 brief search_candidate_count must be a non-negative integer")
    if search_candidate_count != len(search_candidate_documents):
        raise AssertionError("node3 brief search_candidate_count must match search_candidate_documents")
    if not read_documents and not allowed_claims and not runtime_tasks:
        raise AssertionError("default dry run should provide node3 with at least one report material")
    for document in read_documents:
        if not isinstance(document, dict):
            raise AssertionError("node3 brief document must be dict")
        if "data_id" in document or "trace_id" in document or "boundary_id" in document:
            raise AssertionError("node3 brief document leaked internal id field names")
    if not runtime_tasks:
        raise AssertionError("node3 brief should include current runtime task sequence")
    if not any("근거 기준" in str(rule) for rule in reporting_rules):
        raise AssertionError("node3 brief should require an explicit grounding note")
    if not any("답변 첫머리" in str(rule) for rule in reporting_rules):
        raise AssertionError("node3 brief should require a first grounding block")
    if not any("최종 응답자 관점" in str(rule) for rule in reporting_rules):
        raise AssertionError("node3 brief should set final responder identity boundary")
    if not any("자기정체성" in str(rule) for rule in reporting_rules):
        raise AssertionError("node3 brief should forbid internal node names as self-identity")
    for candidate_document in search_candidate_documents:
        if not isinstance(candidate_document, str) or not candidate_document.strip():
            raise AssertionError("node3 search candidate document names must be non-empty strings")
        if "/" in candidate_document or "\\" in candidate_document:
            raise AssertionError("node3 search candidate documents should be sanitized names, not paths")
    for runtime_task in runtime_tasks:
        if not isinstance(runtime_task, dict):
            raise AssertionError("node3 runtime task must be dict")
        if "task_id" in runtime_task or "data_id" in runtime_task or "trace_id" in runtime_task:
            raise AssertionError("node3 runtime task leaked raw internal id field names")
    first_runtime_task = runtime_tasks[0]
    if first_runtime_task.get("node_label") != "node_0":
        raise AssertionError("node3 runtime task sequence should start from node_0")


def _run_runtime_count_consistency_smoke() -> dict[str, int]:
    """빈 extract record와 보고 가능한 문서를 같은 read_doc 숫자로 섞지 않는지 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_runtime_count_consistency"
    seed_event = trace_store.create_event(
        turn_id=turn_id,
        actor="smoke",
        event_type="node_output",
        output_ref=["node2_input:runtime_count_consistency"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="node2_input:runtime_count_consistency",
        data_type="node_output:node2_input_frame",
        source_trace_id=seed_event.event_id,
        payload={"frame_id": "node2_input:runtime_count_consistency"},
    )
    data_store.create_record(
        data_id="memory_packet:node_2:final_trace_for_2",
        data_type="node_output:memory_packet",
        source_trace_id=seed_event.event_id,
        payload={"packet_id": "memory_packet:node_2:final_trace_for_2"},
    )
    data_store.create_record(
        data_id="turn_outcome:runtime_count_consistency",
        data_type="node_output:turn_outcome",
        source_trace_id=seed_event.event_id,
        payload={"outcome_id": "turn_outcome:runtime_count_consistency"},
    )
    data_store.create_record(
        data_id="route:2",
        data_type="node_output:routing_decision",
        source_trace_id=seed_event.event_id,
        payload={"frame_id": "route:2", "route": "2"},
    )
    for index in range(1, 3):
        text = f"보고 가능한 문서 {index} 본문"
        data_store.create_record(
            data_id=f"tool_result:read_doc:runtime_count:{index:04d}",
            data_type="tool_result:read_doc",
            source_trace_id=seed_event.event_id,
            payload={
                "doc_id": f"doc_{index}.md",
                "char_count": len(text),
                "text": text,
            },
        )
    data_store.create_record(
        data_id="tool_result:read_artifact:runtime_count:empty",
        data_type="tool_result:read_artifact",
        source_trace_id=seed_event.event_id,
        payload={
            "doc_id": "empty_artifact.md",
            "char_count": 0,
            "text": "",
        },
    )

    handoff_trace_id, handoff_id = record_route2_handoff(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question="runtime count consistency smoke",
        node2_input_frame_id="node2_input:runtime_count_consistency",
        node2_input_trace_id=seed_event.event_id,
        final_memory_packet_id="memory_packet:node_2:final_trace_for_2",
        turn_outcome_id="turn_outcome:runtime_count_consistency",
        route_ids=["route:2"],
        l_loop_output_ids=[],
    )
    handoff_payload = data_store.require_record(handoff_id).payload
    if not isinstance(handoff_payload, dict):
        raise AssertionError("runtime count smoke handoff payload must be dict")
    if handoff_payload.get("reportable_document_count") != 2:
        raise AssertionError("handoff must count two reportable document extracts")
    if handoff_payload.get("read_doc_count") != 2:
        raise AssertionError("handoff compatibility read_doc_count must mean reportable documents")
    if handoff_payload.get("raw_document_extract_record_count") != 3:
        raise AssertionError("handoff must keep raw extract record count separate")
    if handoff_payload.get("empty_document_extract_record_count") != 1:
        raise AssertionError("handoff must count empty extract records separately")

    _, _, brief_frame = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question="runtime count consistency smoke",
        handoff_frame_id=handoff_id,
        boundary=MetainfoBoundary(),
        input_trace_ids=[handoff_trace_id],
        source_data_ids=[handoff_id],
    )
    if len(brief_frame.read_documents) != 2:
        raise AssertionError("node3 brief must expose only the two reportable documents")

    return {
        "reportable_document_count": handoff_payload["reportable_document_count"],
        "raw_document_extract_record_count": handoff_payload["raw_document_extract_record_count"],
        "empty_document_extract_record_count": handoff_payload["empty_document_extract_record_count"],
    }


def _check_l_loop_return_summary(records: dict[str, object]) -> dict[str, object]:
    """0이 node_1에게 L루프 결과 요약을 구조화해서 공급했는지 확인한다."""

    frame = records.get("L:return_summary_frame")
    if not isinstance(frame, dict):
        raise AssertionError("L loop return summary frame is missing")
    if frame.get("loop_id") != "L":
        raise AssertionError("L loop return summary must target loop L")
    if frame.get("l_loop_task_status") not in {"achieved", "partial", "failed", "unknown"}:
        raise AssertionError("L loop return summary task status is invalid")
    if frame.get("failure_level") not in {
        "none",
        "l2_retryable",
        "l1_replan_needed",
        "budget_exhausted",
        "give_up_recommended",
        "unknown",
    }:
        raise AssertionError("L loop return summary failure_level is invalid")
    if frame.get("recommended_next_route_for_node1") not in {"L", "2", "W_later", "none"}:
        raise AssertionError("L loop return summary route hint is invalid")
    if not isinstance(frame.get("actual_read_doc_count"), int):
        raise AssertionError("L loop return summary actual_read_doc_count must be int")
    if not isinstance(frame.get("search_candidate_count"), int):
        raise AssertionError("L loop return summary search_candidate_count must be int")

    packet = records.get("memory_packet:node_1:loop_return_summary")
    if not isinstance(packet, dict):
        raise AssertionError("node_1 loop_return_summary memory packet is missing")
    source_data_ids = packet.get("source_data_ids")
    if not isinstance(source_data_ids, list) or "L:return_summary_frame" not in source_data_ids:
        raise AssertionError("loop_return_summary packet must source L:return_summary_frame")
    memory_items = packet.get("memory_items")
    if not isinstance(memory_items, list):
        raise AssertionError("loop_return_summary packet memory_items must be a list")
    item_types = {
        item.get("item_type")
        for item in memory_items
        if isinstance(item, dict)
    }
    if "l_loop_return_status" not in item_types:
        raise AssertionError("loop_return_summary packet must include l_loop_return_status")
    if "l_loop_route_hint_for_node1" not in item_types:
        raise AssertionError("loop_return_summary packet must include node_1 route hint item")

    return {
        "task_status": frame.get("l_loop_task_status"),
        "route_hint": frame.get("recommended_next_route_for_node1"),
    }


def _check_l_loop_run_frame(records: dict[str, object]) -> dict[str, object]:
    """L루프 실행 단위와 현재 재실행 차단 사유가 명시됐는지 확인한다."""

    frame = records.get("L:run_frame:0001")
    if not isinstance(frame, dict):
        raise AssertionError("L loop run frame is missing")
    if frame.get("loop_id") != "L":
        raise AssertionError("L loop run frame must target loop L")
    if frame.get("run_index") != 1:
        raise AssertionError("first L loop run index must be 1")
    if frame.get("namespace_policy") != "fixed_primary_ids_v0":
        raise AssertionError("MVP L loop run frame should expose fixed primary ID policy")
    if frame.get("primary_ids_are_attempt_scoped") is not False:
        raise AssertionError("MVP primary L IDs should be marked as not attempt-scoped yet")
    if frame.get("same_turn_rerun_allowed") is not False:
        raise AssertionError("same-turn top-level L rerun must stay blocked until controller policy is enabled")
    block_reason = frame.get("rerun_block_reason")
    if block_reason != L_REROUTE_REMAINING_BLOCK_REASON:
        raise AssertionError("L loop run frame must name the current remaining reroute block")
    planned_next_step = frame.get("planned_next_step")
    if planned_next_step != L_REROUTE_PLANNED_NEXT_STEP:
        raise AssertionError("L loop run frame must name the next outer reroute ID step")

    return {
        "namespace_policy": frame.get("namespace_policy"),
        "same_turn_rerun_allowed": frame.get("same_turn_rerun_allowed"),
        "rerun_block_reason": block_reason,
    }


def _check_l_loop_namespace_ids() -> dict[str, object]:
    """LRunIds가 1회차 호환 ID와 2회차 scoped ID를 구분하는지 확인한다."""

    first = build_l_run_ids(run_index=1)
    second = build_l_run_ids(run_index=2)
    if first.l1_goal_data_id != "L1:goal_frame":
        raise AssertionError("first L run must keep legacy L1 goal ID")
    if second.l1_goal_data_id != "L:run:0002:L1:goal_frame":
        raise AssertionError("second L run must use scoped L1 goal ID")
    if second.l2_query_data_id != "L:run:0002:L2:query_frame":
        raise AssertionError("second L run must use scoped L2 query ID")
    if second.l3_achievement_data_id != "L:run:0002:L3:achievement_frame":
        raise AssertionError("second L run must use scoped L3 achievement ID")
    if first.namespace_policy != "fixed_primary_ids_v0":
        raise AssertionError("first L run namespace policy changed unexpectedly")
    if second.namespace_policy != "run_scoped_l_internal_return_and_downstream_ids_v1":
        raise AssertionError("second L run namespace policy must include downstream scoped IDs")
    if first.control_data_id(1) != "L:control:0001":
        raise AssertionError("first L run must keep legacy control ID")
    if first.tool_catalog_data_id("turn_dry_001") != "tool_catalog:turn_dry_001":
        raise AssertionError("first L run must keep legacy tool catalog ID")
    if first.tool_budget_data_id("turn_dry_001", 1) != "tool_budget:turn_dry_001:0001":
        raise AssertionError("first L run must keep legacy tool budget ID")
    if first.l2_revision_input_data_id(1) != "L2:revision_input:0001":
        raise AssertionError("first L run must keep legacy revision input ID")
    if first.return_summary_frame_id() != "L:return_summary_frame":
        raise AssertionError("first L run must keep legacy return summary ID")
    if first.loop_return_memory_packet_id() != "memory_packet:node_1:loop_return_summary":
        raise AssertionError("first L run must keep legacy loop return packet ID")
    if first.route_decision_id("2") != "route:2":
        raise AssertionError("first L run must keep legacy route decision ID")
    if second.control_data_id(1) != "L:run:0002:L:control:0001":
        raise AssertionError("second L run must use scoped control ID")
    if second.continuation_data_id(1) != "L:run:0002:L:continuation:0001":
        raise AssertionError("second L run must use scoped continuation ID")
    if second.l2_revision_input_data_id(1) != "L:run:0002:L2:revision_input:0001":
        raise AssertionError("second L run must use scoped revision input ID")
    if second.l2_revision_query_plan_data_id(1) != "L:run:0002:L2:revision_query_plan:0001":
        raise AssertionError("second L run must use scoped revision query plan ID")
    if second.l2_revision_query_frame_data_id(1) != "L:run:0002:L2:revision_query_frame:0001":
        raise AssertionError("second L run must use scoped revision query frame ID")
    if second.l3_revision_preserved_data_id(1) != "L:run:0002:L3:revision_preserved_info:0001":
        raise AssertionError("second L run must use scoped revision preserved ID")
    if second.l3_revision_achievement_data_id(1) != "L:run:0002:L3:revision_achievement:0001":
        raise AssertionError("second L run must use scoped revision achievement ID")
    if second.tool_catalog_data_id("turn_dry_001") != "L:run:0002:tool_catalog:turn_dry_001":
        raise AssertionError("second L run must use scoped tool catalog ID")
    if second.tool_choice_data_id("L2", "search_docs") != "L:run:0002:tool_choice:L2:search_docs":
        raise AssertionError("second L run must use scoped tool choice ID")
    if second.tool_budget_data_id("turn_dry_001", 1) != "L:run:0002:tool_budget:turn_dry_001:0001":
        raise AssertionError("second L run must use scoped tool budget ID")
    if second.return_summary_frame_id() != "L:run:0002:L:return_summary_frame":
        raise AssertionError("second L run must use scoped return summary ID")
    if second.loop_return_memory_packet_id() != "L:run:0002:memory_packet:node_1:loop_return_summary":
        raise AssertionError("second L run must use scoped loop return packet ID")
    if second.route_decision_id("2") != "L:run:0002:route:2":
        raise AssertionError("second L run must use scoped route decision ID")
    if second.node2_input_frame_id("turn_dry_001") != "L:run:0002:node2_input:turn_dry_001":
        raise AssertionError("second L run must be able to scope node2 input ID")

    return {
        "second_run_l1_id": second.l1_goal_data_id,
    }


def _run_l_loop_second_run_scope_smoke() -> dict[str, object]:
    """run_index=2 실제 L루프 기록이 L:run:0002 아래에 저장되는지 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_l_run_scope_002"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:l_run_scope_smoke",
        schema_status="not_checked",
    )
    memory_packet = MemoryPacketFrom0(
        target="L",
        trace_evidence_ids=[user_event.event_id],
    )
    first = build_l_run_ids(run_index=1)
    first_result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        search_query="내부 문서 근거를 먼저 찾는다",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        max_tool_calls=2,
        max_query_attempts=3,
        max_read_doc_calls=1,
        search_top_k=1,
        run_index=1,
    )
    if first_result.goal_data_ids != [first.l1_goal_data_id]:
        raise AssertionError("first L run scope smoke must keep legacy L1 ID")

    adapter = SongRyeonAllNodesFakeLLMAdapter()
    result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        search_query="내부 문서 근거를 찾고 부족하면 다시 검색해줘",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        l2_query_planner_adapter=adapter,
        l3_result_adapter=SemanticMismatchL3FakeAdapter(),
        max_tool_calls=3,
        max_query_attempts=3,
        max_read_doc_calls=1,
        search_top_k=1,
        run_index=2,
    )
    second = build_l_run_ids(run_index=2)
    records = {record.data_id: record.payload for record in data_store.list_records()}
    if first.control_data_id(1) not in records:
        raise AssertionError("first L run legacy control ID is missing after second run")
    if first.tool_catalog_data_id(turn_id) not in records:
        raise AssertionError("first L run legacy tool catalog ID is missing after second run")
    run_frame = records.get(second.run_frame_data_id)
    if not isinstance(run_frame, dict):
        raise AssertionError("second L run frame was not recorded")
    if run_frame.get("same_turn_rerun_allowed") is not False:
        raise AssertionError("second L run must still keep same_turn_rerun_allowed=false")
    if run_frame.get("rerun_block_reason") != L_REROUTE_REMAINING_BLOCK_REASON:
        raise AssertionError("second L run frame must expose the remaining controller/runtime-flow block")

    required_ids = [
        second.l1_goal_data_id,
        second.l2_query_plan_data_id,
        second.l2_query_data_id,
        second.l3_preserved_data_id,
        second.l3_achievement_data_id,
        second.budget_plan_data_id,
        second.control_data_id(1),
        second.tool_catalog_data_id(turn_id),
        second.tool_choice_data_id("L2", "search_docs"),
        second.tool_budget_data_id(turn_id, 1),
    ]
    missing = [data_id for data_id in required_ids if data_id not in records]
    if missing:
        raise AssertionError(f"second L run scoped IDs missing: {missing}")

    scoped_families = [
        *result.control_data_ids,
        *result.tool_catalog_data_ids,
        *result.tool_choice_data_ids,
        *result.tool_budget_data_ids,
        *result.tool_result_data_ids,
        *result.tool_distillation_data_ids,
        *result.continuation_data_ids,
        *result.revision_input_data_ids,
        *result.revision_query_plan_data_ids,
        *result.revision_query_data_ids,
        *result.preserved_data_ids,
        *result.achievement_data_ids,
    ]
    unscoped = [
        data_id
        for data_id in scoped_families
        if data_id
        and data_id != second.run_frame_data_id
        and not data_id.startswith(second.run_prefix + ":")
    ]
    if unscoped:
        raise AssertionError(f"second L run has unscoped internal IDs: {unscoped}")
    if not result.revision_query_data_ids:
        raise AssertionError("second L run scope smoke must exercise revision query IDs")

    revision_query_id = second.l2_revision_query_frame_data_id(1)
    if revision_query_id not in records:
        raise AssertionError("second L run revision query frame is not scoped")
    revision_achievement_id = second.l3_revision_achievement_data_id(1)
    if revision_achievement_id not in records:
        raise AssertionError("second L run revision achievement frame is not scoped")

    return {
        "control_id": second.control_data_id(1),
        "tool_catalog_id": second.tool_catalog_data_id(turn_id),
        "tool_budget_id": second.tool_budget_data_id(turn_id, 1),
        "revision_query_id": revision_query_id,
    }


def _run_l_loop_return_reroute_scope_smoke() -> dict[str, object]:
    """1회차와 2회차 L 복귀/재진입 기록이 같은 DataStore에서 충돌하지 않는지 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    schema_registry = build_default_schema_registry()
    turn_id = "turn_l_return_scope_002"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:l_return_scope_smoke",
        schema_status="not_checked",
    )
    memory_packet = MemoryPacketFrom0(
        target="L",
        trace_evidence_ids=[user_event.event_id],
    )
    first = build_l_run_ids(run_index=1)
    second = build_l_run_ids(run_index=2)

    first_result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        search_query="내부 문서 근거를 먼저 찾는다",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        max_tool_calls=2,
        max_query_attempts=2,
        max_read_doc_calls=1,
        search_top_k=1,
        run_index=1,
    )
    first_return_trace_id, first_packet_id, first_summary_id, first_packet = (
        record_l_loop_return_summary_for_node1(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
            input_ref=first_result.source_trace_ids,
            source_data_ids=first_result.output_data_ids,
            id_namespace=first,
        )
    )
    first_decision = route_next(
        user_input="보고",
        memory_packet=first_packet,
        schema_registry=schema_registry,
    )
    record_routing(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        decision=first_decision,
        input_ref=[first_return_trace_id],
        source_data_ids=[first_packet_id],
        id_namespace=first,
    )

    second_result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        search_query="내부 문서 근거를 두 번째로 찾는다",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        max_tool_calls=2,
        max_query_attempts=2,
        max_read_doc_calls=1,
        search_top_k=1,
        run_index=2,
    )
    second_return_trace_id, second_packet_id, second_summary_id, second_packet = (
        record_l_loop_return_summary_for_node1(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
            input_ref=second_result.source_trace_ids,
            source_data_ids=second_result.output_data_ids,
            id_namespace=second,
        )
    )
    second_decision = route_next(
        user_input="보고",
        memory_packet=second_packet,
        schema_registry=schema_registry,
    )
    record_routing(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        decision=second_decision,
        input_ref=[second_return_trace_id],
        source_data_ids=[second_packet_id],
        id_namespace=second,
    )

    records = {record.data_id: record.payload for record in data_store.list_records()}
    required_ids = [
        "L:return_summary_frame",
        "memory_packet:node_1:loop_return_summary",
        "route:2",
        second.return_summary_frame_id(),
        second.loop_return_memory_packet_id(),
        second.route_decision_id("2"),
    ]
    missing = [data_id for data_id in required_ids if data_id not in records]
    if missing:
        raise AssertionError(f"L return reroute scoped IDs missing: {missing}")
    if first_summary_id != "L:return_summary_frame":
        raise AssertionError("first L return summary must keep legacy ID")
    if first_packet_id != "memory_packet:node_1:loop_return_summary":
        raise AssertionError("first L return packet must keep legacy ID")
    if second_summary_id != second.return_summary_frame_id():
        raise AssertionError("second L return summary must use scoped ID")
    if second_packet_id != second.loop_return_memory_packet_id():
        raise AssertionError("second L return packet must use scoped ID")

    second_summary = records.get(second.return_summary_frame_id())
    if not isinstance(second_summary, dict):
        raise AssertionError("second L return summary payload is missing")
    if second_summary.get("frame_id") != second.return_summary_frame_id():
        raise AssertionError("second L return summary payload frame_id is not scoped")
    second_packet_payload = records.get(second.loop_return_memory_packet_id())
    if not isinstance(second_packet_payload, dict):
        raise AssertionError("second L return packet payload is missing")
    second_packet_sources = second_packet_payload.get("source_data_ids")
    if (
        not isinstance(second_packet_sources, list)
        or second.return_summary_frame_id() not in second_packet_sources
    ):
        raise AssertionError("second L return packet must source scoped return summary")
    second_route = records.get(second.route_decision_id("2"))
    if not isinstance(second_route, dict):
        raise AssertionError("second L return route payload is missing")
    if second_route.get("frame_id") != second.route_decision_id("2"):
        raise AssertionError("second L return route payload frame_id is not scoped")

    run_frame = records.get(second.run_frame_data_id)
    if not isinstance(run_frame, dict):
        raise AssertionError("second L run frame is missing in return scope smoke")
    if run_frame.get("same_turn_rerun_allowed") is not False:
        raise AssertionError("return scope smoke must keep same_turn_rerun_allowed=false")
    if run_frame.get("rerun_block_reason") != L_REROUTE_REMAINING_BLOCK_REASON:
        raise AssertionError("return scope smoke must expose the remaining controller/runtime-flow block")

    return {
        "return_summary_id": second.return_summary_frame_id(),
        "return_packet_id": second.loop_return_memory_packet_id(),
        "route_id": second.route_decision_id("2"),
    }


def _run_l_loop_downstream_reroute_scope_smoke() -> dict[str, object]:
    """1회차와 2회차 route=2 이후 downstream 기록이 같은 DataStore에서 충돌하지 않는지 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    schema_registry = build_default_schema_registry()
    turn_id = "turn_l_downstream_scope_002"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:l_downstream_scope_smoke",
        schema_status="not_checked",
    )
    memory_packet = MemoryPacketFrom0(
        target="L",
        trace_evidence_ids=[user_event.event_id],
    )
    first = build_l_run_ids(run_index=1)
    second = build_l_run_ids(run_index=2)

    first_result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        search_query="downstream scope first run",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        max_tool_calls=2,
        max_query_attempts=2,
        max_read_doc_calls=1,
        search_top_k=1,
        run_index=1,
    )
    first_ids = _record_downstream_after_l_run(
        trace_store=trace_store,
        data_store=data_store,
        schema_registry=schema_registry,
        turn_id=turn_id,
        user_question="downstream scope first run",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        l_result=first_result,
        run_ids=first,
    )

    second_result = run_l_loop(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        search_query="downstream scope second run",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        max_tool_calls=2,
        max_query_attempts=2,
        max_read_doc_calls=1,
        search_top_k=1,
        run_index=2,
    )
    second_ids = _record_downstream_after_l_run(
        trace_store=trace_store,
        data_store=data_store,
        schema_registry=schema_registry,
        turn_id=turn_id,
        user_question="downstream scope second run",
        zero_state=ZeroState(current_turn_trace_ids=[user_event.event_id]),
        l_result=second_result,
        run_ids=second,
    )

    records = {record.data_id: record.payload for record in data_store.list_records()}
    required_legacy_ids = [
        first.turn_outcome_id(turn_id),
        first.node2_input_frame_id(turn_id),
        first.route2_handoff_frame_id(),
        first.metainfo_boundary_id(),
        first.node3_input_brief_frame_id(),
        first.node3_report_id(),
        first.node4_gatekeeper_frame_id(),
    ]
    required_scoped_ids = [
        second.turn_outcome_id(turn_id),
        second.node2_input_frame_id(turn_id),
        second.route2_handoff_frame_id(),
        second.metainfo_boundary_id(),
        second.node3_input_brief_frame_id(),
        second.node3_report_id(),
        second.node4_gatekeeper_frame_id(),
    ]
    missing = [
        data_id
        for data_id in [*required_legacy_ids, *required_scoped_ids]
        if data_id not in records
    ]
    if missing:
        raise AssertionError(f"L downstream reroute scoped IDs missing: {missing}")

    for data_id in required_legacy_ids:
        if data_id.startswith(first.run_prefix + ":"):
            raise AssertionError(f"first downstream ID should stay legacy: {data_id}")
    for data_id in required_scoped_ids:
        if not data_id.startswith(second.run_prefix + ":"):
            raise AssertionError(f"second downstream ID should be run-scoped: {data_id}")

    second_node2_input = _require_payload(records, second.node2_input_frame_id(turn_id))
    if second_node2_input.get("frame_id") != second.node2_input_frame_id(turn_id):
        raise AssertionError("second Node2InputFrame.frame_id is not scoped")
    _assert_payload_sources_include(
        second_node2_input,
        [
            second.route_decision_id("2"),
            second.return_summary_frame_id(),
            second.loop_return_memory_packet_id(),
            second.l1_goal_data_id,
            second.l2_query_data_id,
            second.l3_preserved_data_id,
            second.l3_achievement_data_id,
        ],
        label="second Node2InputFrame.source_data_ids",
    )

    second_handoff = _require_payload(records, second.route2_handoff_frame_id())
    if second_handoff.get("frame_id") != second.route2_handoff_frame_id():
        raise AssertionError("second Node2HandoffFrame.frame_id is not scoped")
    _assert_payload_sources_include(
        second_handoff,
        [
            second.node2_input_frame_id(turn_id),
            second.memory_packet_data_id(target="node_2", mode="final_trace_for_2"),
            second.turn_outcome_id(turn_id),
        ],
        label="second Node2HandoffFrame.source_data_ids",
    )

    second_brief = _require_payload(records, second.node3_input_brief_frame_id())
    if second_brief.get("frame_id") != second.node3_input_brief_frame_id():
        raise AssertionError("second Node3InputBriefFrame.frame_id is not scoped")
    _assert_payload_sources_include(
        second_brief,
        [second.route2_handoff_frame_id(), second.metainfo_boundary_id()],
        label="second Node3InputBriefFrame.source_data_ids",
    )

    second_report = _require_payload(records, second.node3_report_id())
    if second_report.get("report_id") != second.node3_report_id():
        raise AssertionError("second ReportFrame.report_id is not scoped")
    second_gate = _require_payload(records, second.node4_gatekeeper_frame_id())
    if second_gate.get("gate_id") != second.node4_gatekeeper_frame_id():
        raise AssertionError("second Node4GatekeeperFrame.gate_id is not scoped")
    _assert_payload_sources_include(
        second_gate,
        [
            second.node3_report_id(),
            second.node3_input_brief_frame_id(),
            second.metainfo_boundary_id(),
        ],
        label="second Node4GatekeeperFrame.source_data_ids",
    )

    run_frame = _require_payload(records, second.run_frame_data_id)
    if run_frame.get("same_turn_rerun_allowed") is not False:
        raise AssertionError("downstream scope smoke must keep same_turn_rerun_allowed=false")
    if run_frame.get("rerun_block_reason") != L_REROUTE_REMAINING_BLOCK_REASON:
        raise AssertionError("downstream scope smoke must expose controller/runtime-flow block")
    if run_frame.get("planned_next_step") != L_REROUTE_PLANNED_NEXT_STEP:
        raise AssertionError("downstream scope smoke must expose controller/runtime-flow next step")

    scoped_result = {
        "status": "ok",
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "data_records": [
            asdict(record)
            for record in data_store.list_records()
            if record.data_id == second.run_frame_data_id
            or record.data_id.startswith(second.run_prefix + ":")
        ],
    }
    rendered = render_pretty_turn(
        scoped_result,
        user_input="downstream scoped runtime fallback smoke",
    )
    for marker in (
        "- route=2 handoff:",
        "- node_3 input brief:",
        "- node_3 report:",
        "- node_4 gatekeeper:",
    ):
        if marker not in rendered:
            raise AssertionError(f"runtime pretty fallback missed scoped marker: {marker}")

    return {
        "node2_input_id": second_ids["node2_input_id"],
        "handoff_id": second_ids["handoff_id"],
        "boundary_id": second_ids["boundary_id"],
        "brief_id": second_ids["brief_id"],
        "report_id": second_ids["report_id"],
        "gatekeeper_id": second_ids["gatekeeper_id"],
        "legacy_report_id": first_ids["report_id"],
        "same_turn_rerun_allowed": run_frame.get("same_turn_rerun_allowed"),
        "rerun_block_reason": run_frame.get("rerun_block_reason"),
    }


def _run_policy_guarded_same_turn_l_reroute_smoke() -> dict[str, object]:
    """Policy flag가 켜진 경우에만 같은 턴 L 2회차를 열고 3회차를 막는다."""

    default_result = run_dry_turn()
    if default_result.get("same_turn_l_reroute_enabled") is not False:
        raise AssertionError("default run_dry_turn must keep same_turn_l_reroute_enabled=false")
    if default_result.get("l_loop_run_count") != 1:
        raise AssertionError("default run_dry_turn must execute exactly one L run")
    if default_result.get("same_turn_rerun_allowed") is not False:
        raise AssertionError("default run_dry_turn must keep same_turn_rerun_allowed=false")
    default_reason = default_result.get("rerun_block_reason")
    if default_reason not in {
        SAME_TURN_L_REROUTE_NODE1_ROUTE2_REASON,
        "CODE_STATUS:same_turn_L_reroute_disabled_by_policy",
    }:
        raise AssertionError("default run_dry_turn rerun_block_reason must name a closed controller state")

    adapter = SameTurnLRerouteFakeAdapter()
    blocked_result = run_dry_turn(
        user_input="내부 문서를 검색하고 같은 턴 L을 다시 요청하지만 policy는 꺼 둔다",
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        same_turn_l_reroute_enabled=False,
    )
    blocked_records = {item["data_id"]: item["payload"] for item in blocked_result["data_records"]}
    blocked_handoff = _require_payload(blocked_records, "node_2:handoff_frame")
    blocked_path = blocked_handoff.get("route_path") or []
    if blocked_result.get("l_loop_run_count") != 1:
        raise AssertionError("policy-disabled L reroute request must not execute L run 2")
    if blocked_path.count("L:L1_L2_tools_L3(run=1)") != 1:
        raise AssertionError("blocked reroute path must show exactly one actual L execution")
    if any(item == "L:L1_L2_tools_L3(run=2)" for item in blocked_path):
        raise AssertionError("blocked reroute path must not show a second actual L execution")
    if "L:top_level_reroute_blocked_by_controller" not in blocked_path:
        raise AssertionError("blocked reroute path must label the blocked top-level L request")
    if blocked_handoff.get("actual_l_run_count") != 1:
        raise AssertionError("blocked reroute handoff must record one actual L run")
    if blocked_handoff.get("blocked_same_turn_l_reroute_request_count") != 1:
        raise AssertionError("blocked reroute handoff must count the blocked L request")

    policy_result = run_dry_turn(
        user_input="내부 문서를 검색하고 부족하면 같은 턴에서 한 번 더 L을 실행해줘",
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        max_tool_calls=4,
        max_query_attempts=2,
        max_read_doc_calls=2,
        same_turn_l_reroute_enabled=True,
        max_l_runs_per_turn=2,
    )
    records = {item["data_id"]: item["payload"] for item in policy_result["data_records"]}
    if policy_result.get("l_loop_run_count") != 2:
        raise AssertionError("policy-enabled same-turn reroute must execute L run 2")
    if "L:run_frame:0003" in records:
        raise AssertionError("policy-enabled same-turn reroute must not execute L run 3")
    if any(data_id.startswith("L:run:0003:") for data_id in records):
        raise AssertionError("policy-enabled same-turn reroute created run 3 scoped records")

    second = build_l_run_ids(run_index=2)
    second_run_frame = _require_payload(records, second.run_frame_data_id)
    if second_run_frame.get("same_turn_rerun_allowed") is not True:
        raise AssertionError("second L run frame must reveal policy-guarded rerun allowance")
    if second_run_frame.get("rerun_block_reason") != SAME_TURN_L_REROUTE_ALLOWED_REASON:
        raise AssertionError("second L run frame must name the policy guard allowance")
    if second_run_frame.get("namespace_policy") != "run_scoped_l_internal_return_and_downstream_ids_v1":
        raise AssertionError("second L run namespace policy is incorrect")

    required_scoped_ids = [
        second.l1_goal_data_id,
        second.l2_query_data_id,
        second.l3_preserved_data_id,
        second.l3_achievement_data_id,
        second.return_summary_frame_id(),
        second.loop_return_memory_packet_id(),
        second.route_decision_id("L"),
        second.route_decision_id("2"),
        second.turn_outcome_id(str(policy_result["turn_id"])),
        second.node2_input_frame_id(str(policy_result["turn_id"])),
        second.route2_handoff_frame_id(),
        second.metainfo_boundary_id(),
        second.node3_input_brief_frame_id(),
        second.node3_report_id(),
        second.node4_gatekeeper_frame_id(),
    ]
    missing = [data_id for data_id in required_scoped_ids if data_id not in records]
    if missing:
        raise AssertionError(f"policy-enabled same-turn reroute missing scoped IDs: {missing}")
    if "L:reroute:route:L" not in records:
        raise AssertionError("first L return route=L must avoid colliding with initial route:L")

    first_controller = _require_payload(records, "L:reroute_controller:0001")
    if first_controller.get("same_turn_rerun_allowed") is not True:
        raise AssertionError("first reroute controller must allow L run 2 under policy")
    if first_controller.get("decision_reason") != SAME_TURN_L_REROUTE_ALLOWED_REASON:
        raise AssertionError("first reroute controller must name the policy guard allowance")

    second_controller = _require_payload(records, second.reroute_controller_data_id())
    if second_controller.get("controller_decision") != "close_route_2":
        raise AssertionError("second reroute controller must close through route=2")
    if second_controller.get("decision_reason") != SAME_TURN_L_REROUTE_MAX_REACHED_REASON:
        raise AssertionError("second reroute controller must block run 3 by max runs")
    if policy_result.get("same_turn_rerun_allowed") is not False:
        raise AssertionError("final same_turn_rerun_allowed must be false after max close")
    if policy_result.get("rerun_block_reason") != SAME_TURN_L_REROUTE_MAX_REACHED_REASON:
        raise AssertionError("final rerun_block_reason must name max run closure")

    rendered = render_pretty_turn(
        policy_result,
        user_input="same-turn L reroute policy smoke",
    )
    runtime_view, answer = rendered.split("[answer]", 1)
    for marker in (
        "run=2",
        "- L same-turn reroute controller:",
        second.l1_goal_data_id,
        second.l3_achievement_data_id,
        second.route_decision_id("2"),
        second.node3_report_id(),
    ):
        if marker not in runtime_view:
            raise AssertionError(f"terminal view missed same-turn reroute marker: {marker}")
    if "L:run:" in answer:
        raise AssertionError("node_3 final answer must not expose internal L run IDs")

    return {
        "default_run_count": default_result.get("l_loop_run_count"),
        "policy_run_count": policy_result.get("l_loop_run_count"),
        "second_namespace_policy": second_run_frame.get("namespace_policy"),
        "final_reason": policy_result.get("rerun_block_reason"),
        "third_run_blocked": True,
    }


def _record_downstream_after_l_run(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    schema_registry,
    turn_id: str,
    user_question: str,
    zero_state: ZeroState,
    l_result,
    run_ids,
) -> dict[str, str]:
    return_trace_id, return_packet_id, return_summary_id, packet_after_l = (
        record_l_loop_return_summary_for_node1(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            zero_state=zero_state,
            input_ref=l_result.source_trace_ids,
            source_data_ids=l_result.output_data_ids,
            id_namespace=run_ids,
        )
    )
    decision = route_next(
        user_input="보고",
        memory_packet=packet_after_l,
        schema_registry=schema_registry,
    )
    route_trace_id = record_routing(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        decision=decision,
        input_ref=[return_trace_id],
        source_data_ids=[return_packet_id],
        id_namespace=run_ids,
    )
    route_data_id = run_ids.route_decision_id(decision.route)

    final_packet = MemoryPacketFrom0(
        target="node_2",
        trace_evidence_ids=[route_trace_id],
    )
    final_packet_trace_id = record_memory_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        packet=final_packet,
        mode="final_trace_for_2",
        input_ref=[route_trace_id],
        source_data_ids=[route_data_id],
        id_namespace=run_ids,
    )
    final_packet_id = run_ids.memory_packet_data_id(
        target="node_2",
        mode="final_trace_for_2",
    )

    outcome_id = run_ids.turn_outcome_id(turn_id)
    outcome = TurnOutcomeFrame(
        outcome_id=outcome_id,
        turn_id=turn_id,
        status="completed_without_llm_judgement",
        decided_by="node_0",
        source_trace_ids=[final_packet_trace_id],
        source_data_ids=[final_packet_id],
    )
    validate_turn_outcome_frame(outcome)
    outcome_trace = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="turn_outcome",
        input_ref=[final_packet_trace_id],
        output_ref=[outcome_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=outcome_id,
        data_type="node_output:turn_outcome",
        exists=True,
        created_at=outcome_trace.timestamp,
        source_trace_id=outcome_trace.event_id,
        payload=asdict(outcome),
    )

    node2_input_id = run_ids.node2_input_frame_id(turn_id)
    node2_source_data_ids = _unique_string_list(
        [
            *l_result.output_data_ids,
            return_summary_id,
            return_packet_id,
            route_data_id,
            final_packet_id,
            outcome_id,
        ]
    )
    node2_input = Node2InputFrame(
        frame_id=node2_input_id,
        turn_id=turn_id,
        final_memory_packet_id=final_packet_id,
        turn_outcome_id=outcome_id,
        route_ids=[route_data_id],
        l_loop_output_ids=list(l_result.output_data_ids),
        source_trace_ids=[event.event_id for event in trace_store.events_for_turn(turn_id)],
        source_data_ids=node2_source_data_ids,
    )
    validate_node2_input_frame(node2_input)
    node2_input_trace = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=[final_packet_trace_id, outcome_trace.event_id],
        output_ref=[node2_input_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=node2_input_id,
        data_type="node_output:node2_input_frame",
        exists=True,
        created_at=node2_input_trace.timestamp,
        source_trace_id=node2_input_trace.event_id,
        payload=asdict(node2_input),
    )

    handoff_trace_id, handoff_id = record_route2_handoff(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        node2_input_frame_id=node2_input_id,
        node2_input_trace_id=node2_input_trace.event_id,
        final_memory_packet_id=final_packet_id,
        turn_outcome_id=outcome_id,
        route_ids=[route_data_id],
        l_loop_output_ids=list(l_result.output_data_ids),
        id_namespace=run_ids,
    )
    boundary = build_metainfo_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        node2_input_frame_id=node2_input_id,
    )
    boundary_id = run_ids.metainfo_boundary_id()
    boundary_trace_id = record_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        boundary_id=boundary_id,
        boundary=boundary,
        input_ref=[node2_input_trace.event_id],
    )
    brief_trace_id, brief_id, brief_frame = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_question,
        handoff_frame_id=handoff_id,
        boundary=boundary,
        input_trace_ids=[handoff_trace_id, boundary_trace_id],
        source_data_ids=[node2_input_id, handoff_id, boundary_id],
        id_namespace=run_ids,
    )
    report_id = run_ids.node3_report_id()
    report = render_report(turn_id=turn_id, boundary=boundary)
    report_trace_id = record_report(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        report_id=report_id,
        rendered_markdown=report,
        allowed_info_ids=[data_ref.data_id for data_ref in boundary.absolute_info],
        allowed_relative_info_ids=[info_ref.info_id for info_ref in boundary.relative_info],
        allowed_mixed_info_ids=[info_ref.info_id for info_ref in boundary.mixed_info],
        input_ref=[brief_trace_id],
        source_data_ids=[brief_id, handoff_id, boundary_id, outcome_id, node2_input_id],
    )
    gatekeeper_trace_id = run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        report_id=report_id,
        boundary_id=boundary_id,
        brief_frame=brief_frame,
        rendered_markdown=report,
        adapter=SongRyeonAllNodesFakeLLMAdapter(),
        input_ref=[report_trace_id],
        source_data_ids=[report_id, brief_id, boundary_id],
        id_namespace=run_ids,
    )
    if not gatekeeper_trace_id:
        raise AssertionError("gatekeeper trace id must not be empty")

    return {
        "return_summary_id": return_summary_id,
        "return_packet_id": return_packet_id,
        "route_id": route_data_id,
        "final_packet_id": final_packet_id,
        "turn_outcome_id": outcome_id,
        "node2_input_id": node2_input_id,
        "handoff_id": handoff_id,
        "boundary_id": boundary_id,
        "brief_id": brief_id,
        "report_id": report_id,
        "gatekeeper_id": run_ids.node4_gatekeeper_frame_id(),
    }


def _require_payload(records: dict[str, object], data_id: str) -> dict[str, object]:
    payload = records.get(data_id)
    if not isinstance(payload, dict):
        raise AssertionError(f"payload is missing or not dict: {data_id}")
    return payload


def _assert_payload_sources_include(
    payload: dict[str, object],
    expected_ids: list[str],
    *,
    label: str,
) -> None:
    source_data_ids = payload.get("source_data_ids")
    if not isinstance(source_data_ids, list):
        raise AssertionError(f"{label} must be a list")
    missing = [data_id for data_id in expected_ids if data_id not in source_data_ids]
    if missing:
        raise AssertionError(f"{label} misses {missing}")


def _unique_string_list(values: list[str | None]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def _check_runtime_metainfo_labels(result: dict[str, object]) -> dict[str, object]:
    """pretty runtime 출력이 생성자/정보등급/출처/의미판단 라벨을 드러내는지 확인한다."""

    rendered = render_pretty_turn(result, user_input="smoke runtime metainfo labels")
    required_labels = (
        "generated_by:",
        "info_class:",
        "source_data_ids:",
        "semantic_judgement_status:",
    )
    for label in required_labels:
        if label not in rendered:
            raise AssertionError(f"runtime pretty output misses {label}")

    metainfo_label_count = rendered.count("generated_by:")
    if metainfo_label_count < 6:
        raise AssertionError("runtime pretty output has too few metainfo label blocks")

    required_sources = (
        "generated_by: CODE:RULE_STUB",
        "generated_by: RULE_STUB",
        "generated_by: TOOL:search_docs",
        "generated_by: TOOL:read_doc",
        "generated_by: CODE:OPERATION_CHECK",
        "generated_by: CODE/RENDERER",
    )
    for source_label in required_sources:
        if source_label not in rendered:
            raise AssertionError(f"runtime pretty output misses {source_label}")

    if "copied_from:" not in rendered:
        raise AssertionError("runtime pretty output must expose copied_from for document extracts")

    return {
        "metainfo_label_count": metainfo_label_count,
        "has_copied_from": True,
    }


def _check_mixed_info_boundary(records: dict[str, object]) -> dict[str, object]:
    """2가 근거 달린 상대/혼합 정보만 boundary와 보고서에 통과시키는지 확인한다."""

    boundary = records["boundary_dry_001"]
    report = records["report_dry_001"]
    if not isinstance(boundary, dict) or not isinstance(report, dict):
        raise AssertionError("boundary and report payloads must be dicts")

    relative_info = boundary.get("relative_info")
    if not isinstance(relative_info, list):
        raise AssertionError("MetainfoBoundary.relative_info must be a list")
    mixed_info = boundary.get("mixed_info")
    if not isinstance(mixed_info, list):
        raise AssertionError("MetainfoBoundary.mixed_info must be a list")

    seen_l3_reason = False
    seen_tool_choice_reason = False
    for item in relative_info:
        if not isinstance(item, dict):
            raise AssertionError("relative_info items must be dicts")
        _assert_semantic_info_has_evidence(item, info_class="relative")
        if item.get("info_kind") == "l3_achievement_reason" and item.get("field_path") == "reason":
            seen_l3_reason = True
        if item.get("info_kind") == "tool_choice_reason" and item.get("field_path") == "reason":
            seen_tool_choice_reason = True

    for item in mixed_info:
        if not isinstance(item, dict):
            raise AssertionError("mixed_info items must be dicts")
        _assert_semantic_info_has_evidence(item, info_class="mixed")
        if item.get("info_kind") == "l3_achievement_reason" and item.get("field_path") == "reason":
            seen_l3_reason = True
        if item.get("info_kind") == "tool_choice_reason" and item.get("field_path") == "reason":
            seen_tool_choice_reason = True

    if seen_l3_reason:
        raise AssertionError("mixed_info must not include code-generated L3 achievement reason")
    if seen_tool_choice_reason:
        raise AssertionError("mixed_info must not include code-generated tool choice reason")

    rendered_markdown = report.get("rendered_markdown")
    if not isinstance(rendered_markdown, str) or "## Relative Info" not in rendered_markdown:
        raise AssertionError("report did not render relative info")
    if "## Mixed Info" not in rendered_markdown:
        raise AssertionError("report did not render mixed info")
    allowed_relative_info_ids = report.get("allowed_relative_info_ids")
    if not isinstance(allowed_relative_info_ids, list):
        raise AssertionError("report did not record allowed_relative_info_ids")
    allowed_mixed_info_ids = report.get("allowed_mixed_info_ids")
    if not isinstance(allowed_mixed_info_ids, list):
        raise AssertionError("report did not record allowed_mixed_info_ids")
    relative_info_ids = [item["info_id"] for item in relative_info]
    if allowed_relative_info_ids != relative_info_ids:
        raise AssertionError("report allowed_relative_info_ids do not match boundary relative_info")
    mixed_info_ids = [item["info_id"] for item in mixed_info]
    if allowed_mixed_info_ids != mixed_info_ids:
        raise AssertionError("report allowed_mixed_info_ids do not match boundary mixed_info")

    return {
        "relative_info_count": len(relative_info),
        "mixed_info_count": len(mixed_info),
        "semantic_info_count": len(relative_info) + len(mixed_info),
        "excludes_code_l3_reason": not seen_l3_reason,
        "excludes_code_tool_choice_reason": not seen_tool_choice_reason,
    }


def _run_relative_info_direct_field_smoke() -> dict[str, object]:
    """하나의 source field에 직접 대응하는 LLM 의미 claim이 relative_info로 흐르는지 확인한다."""

    turn_id = "turn_relative_info_direct_field_smoke"
    trace_store = TraceStore()
    data_store = DataStore()
    source_data_id = "relative_smoke:l3_achievement_frame"
    source_event = trace_store.create_event(
        turn_id=turn_id,
        actor="L3",
        event_type="node_output",
        output_ref=[source_data_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=source_data_id,
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=source_event.timestamp,
        source_trace_id=source_event.event_id,
        payload={
            "schema_name": "L3AchievementFrame",
            "schema_version": "0.1",
            "frame_id": source_data_id,
            "turn_id": turn_id,
            "achievement_status": "partial",
            "reason": "단일 achievement frame의 reason field에 직접 대응하는 smoke용 의미 판단이다.",
            "achievement_generation_source": "LLM:relative-info-smoke",
            "llm_semantic_judgement_status": "ran",
            # 학습 메모: source_data_ids를 일부러 비워 둔다.
            # record 자체 외의 근거가 없을 때 direct-field relative_info가 되는지 보기 위한 fixture다.
        },
    )

    boundary = build_metainfo_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
    )
    if len(boundary.relative_info) != 1:
        raise AssertionError("direct-field semantic claim should become one relative_info item")
    if boundary.mixed_info:
        raise AssertionError("direct-field semantic claim must not become mixed_info")
    relative_info = boundary.relative_info[0]
    # 여기부터는 "분류 결과"뿐 아니라 node_3/report까지 라벨이 보존되는지도 확인한다.
    if relative_info.info_kind != "l3_achievement_reason":
        raise AssertionError("relative_info info_kind should preserve L3 achievement reason")
    if relative_info.source_data_id != source_data_id or relative_info.field_path != "reason":
        raise AssertionError("relative_info should point to the exact source record and field")
    if relative_info.source_mode != "direct_field":
        raise AssertionError("relative_info source_mode should be direct_field")
    if relative_info.claim_alignment != "one_to_one_field":
        raise AssertionError("relative_info claim_alignment should be one_to_one_field")

    brief_trace_id, brief_id, brief_frame = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question="relative info smoke",
        handoff_frame_id="relative_smoke:handoff_frame",
        boundary=boundary,
        input_trace_ids=[source_event.event_id],
        source_data_ids=["relative_smoke:handoff_frame", source_data_id],
    )
    if len(brief_frame.allowed_claims) != 1:
        raise AssertionError("node3 brief should receive the relative_info claim")
    brief_claim = brief_frame.allowed_claims[0]
    if brief_claim.info_class != "relative":
        raise AssertionError("node3 brief should preserve relative info_class")
    if brief_claim.source_mode != "direct_field":
        raise AssertionError("node3 brief should preserve relative source_mode")
    if brief_claim.claim_alignment != "one_to_one_field":
        raise AssertionError("node3 brief should preserve relative claim_alignment")

    rendered_markdown = render_report(turn_id=turn_id, boundary=boundary)
    if "## Relative Info" not in rendered_markdown:
        raise AssertionError("fallback report should render Relative Info section")
    if relative_info.info_id not in rendered_markdown:
        raise AssertionError("fallback report should render the relative_info id")

    report_id = "relative_smoke:report"
    record_report(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        report_id=report_id,
        rendered_markdown=rendered_markdown,
        allowed_info_ids=[data_ref.data_id for data_ref in boundary.absolute_info],
        allowed_relative_info_ids=[info_ref.info_id for info_ref in boundary.relative_info],
        allowed_mixed_info_ids=[info_ref.info_id for info_ref in boundary.mixed_info],
        input_ref=[brief_trace_id],
        source_data_ids=[brief_id, source_data_id],
    )
    report_payload = data_store.require_record(report_id).payload
    if not isinstance(report_payload, dict):
        raise AssertionError("relative smoke report payload must be a dict")
    if report_payload.get("allowed_relative_info_ids") != [relative_info.info_id]:
        raise AssertionError("report should preserve allowed_relative_info_ids")
    if report_payload.get("allowed_mixed_info_ids") != []:
        raise AssertionError("report should not invent allowed_mixed_info_ids")

    return {
        "relative_info_direct_field": True,
        "brief_preserved": True,
        "report_preserved": True,
    }


def _check_document_memory_index(
    records: dict[str, object],
    search_result: dict[str, object],
) -> dict[str, object]:
    """문서 검색 도구가 문서 메모리 인덱스 metadata를 보존하는지 확인한다."""

    index_id = search_result.get("document_memory_index_id")
    snapshot_id = search_result.get("snapshot_id")
    if not isinstance(index_id, str) or not index_id.startswith("document_memory_index:"):
        raise AssertionError("search_docs did not return document_memory_index_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("snapshot:"):
        raise AssertionError("search_docs did not return snapshot_id")

    document_count = search_result.get("document_count")
    chunk_count = search_result.get("chunk_count")
    if not isinstance(document_count, int) or document_count < 1:
        raise AssertionError("document memory index document_count is invalid")
    if not isinstance(chunk_count, int) or chunk_count < document_count:
        raise AssertionError("document memory index chunk_count is invalid")

    kind_counts = search_result.get("document_kind_counts")
    role_counts = search_result.get("source_role_counts")
    if not isinstance(kind_counts, dict) or "order" not in kind_counts:
        raise AssertionError("document memory index did not classify order documents")
    if not isinstance(role_counts, dict) or "generated_order" not in role_counts:
        raise AssertionError("document memory index did not classify generated orders")

    results = search_result.get("results")
    if not isinstance(results, list) or not results:
        raise AssertionError("search_docs results are missing")
    first_result = results[0]
    if not isinstance(first_result, dict):
        raise AssertionError("search_docs result item must be a dict")
    for field_name in (
        "document_memory_index_id",
        "content_hash",
        "chunk_count",
        "document_kind",
        "source_role",
    ):
        if not first_result.get(field_name):
            raise AssertionError(f"search_docs result misses {field_name}")

    listed_docs = list_docs(root="Administrative_Reform_1")
    order_doc = next(
        (
            item
            for item in listed_docs
            if item.get("doc_id") == "04_Orders/ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md"
        ),
        None,
    )
    if not isinstance(order_doc, dict):
        raise AssertionError("list_docs did not include ORDER_061")
    if order_doc.get("document_kind") != "order":
        raise AssertionError("list_docs did not classify ORDER_061 as order")
    if order_doc.get("source_role") != "generated_order":
        raise AssertionError("list_docs did not classify ORDER_061 as generated_order")

    read_payload = read_doc(
        root="Administrative_Reform_1",
        doc_id="04_Orders/ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md",
    )
    if read_payload.get("document_kind") != "order":
        raise AssertionError("read_doc did not preserve document_kind")
    if not read_payload.get("content_hash"):
        raise AssertionError("read_doc did not preserve content_hash")

    cached = load_document_memory_index(
        cache_dir=".songryeon_core_cache/document_memory_indexes",
        snapshot_id=snapshot_id,
    )
    if cached is None:
        raise AssertionError("document memory index cache was not saved")

    preserved = records["L3:preserved_info_frame"]
    if not isinstance(preserved, dict):
        raise AssertionError("L3 preserved payload must be a dict")
    candidates = preserved.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AssertionError("L3 candidates are missing")
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise AssertionError("L3 candidate must be a dict")
    l3_metadata = bool(
        first_candidate.get("document_kind")
        and first_candidate.get("source_role")
        and first_candidate.get("document_memory_index_id")
        and first_candidate.get("snapshot_id")
    )
    if not l3_metadata:
        raise AssertionError("L3 candidate did not preserve document memory metadata")

    return {
        "document_count": document_count,
        "has_order": True,
        "l3_metadata": True,
    }


def _assert_semantic_info_has_evidence(item: dict[str, object], *, info_class: str) -> None:
    """RelativeInfoRef/MixedInfoRef payload가 분류 근거와 근거 ID를 갖췄는지 확인한다."""

    for field_name in ("info_id", "source_data_id", "field_path", "info_kind", "text"):
        value = item.get(field_name)
        if not isinstance(value, str) or not value:
            raise AssertionError(f"{info_class}_info item misses {field_name}")

    source_mode = item.get("source_mode")
    claim_alignment = item.get("claim_alignment")
    if info_class == "relative":
        if source_mode != "direct_field":
            raise AssertionError("relative_info source_mode must be direct_field")
        if claim_alignment != "one_to_one_field":
            raise AssertionError("relative_info claim_alignment must be one_to_one_field")
    elif info_class == "mixed":
        if source_mode != "source_bundle":
            raise AssertionError("mixed_info source_mode must be source_bundle")
        if claim_alignment != "multi_source_bundle":
            raise AssertionError("mixed_info claim_alignment must be multi_source_bundle")
    else:
        raise AssertionError(f"unknown semantic info_class: {info_class}")

    source_trace_ids = item.get("source_trace_ids")
    source_data_ids = item.get("source_data_ids")
    if not isinstance(source_trace_ids, list) or not source_trace_ids:
        raise AssertionError(f"{info_class}_info source_trace_ids must not be empty")
    if not isinstance(source_data_ids, list) or not source_data_ids:
        raise AssertionError(f"{info_class}_info source_data_ids must not be empty")
    if item["source_data_id"] not in source_data_ids:
        raise AssertionError(f"{info_class}_info source_data_ids must include source_data_id")

    if not all(isinstance(trace_id, str) and trace_id for trace_id in source_trace_ids):
        raise AssertionError(f"{info_class}_info source_trace_ids contain empty values")
    if not all(isinstance(data_id, str) and data_id for data_id in source_data_ids):
        raise AssertionError(f"{info_class}_info source_data_ids contain empty values")


def _assert_mixed_info_has_evidence(item: dict[str, object]) -> None:
    """호환용 wrapper: MixedInfoRef payload의 분류 근거와 근거 ID를 확인한다."""

    _assert_semantic_info_has_evidence(item, info_class="mixed")


def _check_tool_catalog_and_choice(records: dict[str, object]) -> dict[str, object]:
    """기본 dry run이 tool catalog와 tool choice를 남겼는지 확인한다."""

    catalog = records["tool_catalog:turn_dry_001"]
    choice = records["tool_choice:L2:search_docs"]
    if not isinstance(catalog, dict) or not isinstance(choice, dict):
        raise AssertionError("tool catalog and choice payloads must be dicts")
    tools = catalog.get("tools")
    if not isinstance(tools, list):
        raise AssertionError("tool catalog tools must be a list")
    tool_names = {
        tool.get("tool_name") for tool in tools if isinstance(tool, dict)
    }
    expected_tools = {"list_docs", "read_artifact", "read_doc", "search_docs"}
    if not expected_tools.issubset(tool_names):
        raise AssertionError("tool catalog is missing document tools")
    if choice["tool_name"] != "search_docs":
        raise AssertionError("L2 tool choice must select search_docs")
    if choice["catalog_id"] != "tool_catalog:turn_dry_001":
        raise AssertionError("tool choice does not reference the turn tool catalog")
    source_data_ids = choice.get("source_data_ids")
    if not isinstance(source_data_ids, list) or "tool_catalog:turn_dry_001" not in source_data_ids:
        raise AssertionError("tool choice source data must include tool catalog")

    return {
        "tool_catalog_count": len(tools),
        "tool_choice": choice["tool_name"],
    }


def _check_l_loop_controller(records: dict[str, object]) -> dict[str, object]:
    """기본 dry run이 LLoopControlFrame으로 search/read/stop을 남겼는지 확인한다."""

    controls = [
        records["L:control:0001"],
        records["L:control:0002"],
        records["L:control:0003"],
    ]
    if not all(isinstance(control, dict) for control in controls):
        raise AssertionError("L loop controls must be dict payloads")
    decisions = [control["decision"] for control in controls]
    if decisions != ["continue_search", "read_document", "stop_success"]:
        raise AssertionError(f"unexpected L loop control decisions: {decisions}")
    if controls[0]["selected_tool_name"] != "search_docs":
        raise AssertionError("first L loop control must select search_docs")
    if controls[1]["selected_tool_name"] != "read_doc":
        raise AssertionError("second L loop control must select read_doc")
    if not controls[1].get("doc_id"):
        raise AssertionError("read_document control must include doc_id")
    if controls[2]["tool_call_count"] != 2:
        raise AssertionError("stop_success control must see two tool calls")

    read_doc_results = [
        data_id for data_id in records if data_id.startswith("tool_result:read_doc:")
    ]
    if not read_doc_results:
        raise AssertionError("L loop controller did not execute read_doc")

    achievement = records["L3:achievement_frame"]
    if not isinstance(achievement, dict):
        raise AssertionError("L3 achievement payload must be a dict")
    if achievement.get("controller_decision") != "stop_success":
        raise AssertionError("L3 achievement did not reflect final controller decision")
    if achievement.get("final_control_data_id") != "L:control:0003":
        raise AssertionError("L3 achievement did not reference final control frame")

    return {
        "control_count": len(controls),
        "final_decision": controls[-1]["decision"],
        "read_doc_used": True,
    }


def _check_tool_result_distillation(records: dict[str, object]) -> dict[str, object]:
    """도구 결과 distillation이 원본 링크와 L3 입력 우선권을 가지는지 확인한다."""

    search_id = _single_id_with_prefix(records, "tool_distillation:search_docs:")
    read_id = _single_id_with_prefix(records, "tool_distillation:read_doc:")
    search_distillation = records[search_id]
    read_distillation = records[read_id]
    if not isinstance(search_distillation, dict) or not isinstance(read_distillation, dict):
        raise AssertionError("tool distillation payloads must be dicts")
    if search_distillation["tool_name"] != "search_docs":
        raise AssertionError("search_docs distillation has wrong tool_name")
    if read_distillation["tool_name"] != "read_doc":
        raise AssertionError("read_doc distillation has wrong tool_name")
    if not str(search_distillation["original_tool_result_data_id"]).startswith("tool_result:search_docs:"):
        raise AssertionError("search_docs distillation lost original tool result link")
    if not str(read_distillation["original_tool_result_data_id"]).startswith("tool_result:read_doc:"):
        raise AssertionError("read_doc distillation lost original tool result link")
    if search_distillation["distilled_content_bytes"] >= search_distillation["original_payload_bytes"]:
        raise AssertionError("search_docs distillation did not reduce LLM content size")
    if read_distillation["distilled_content_bytes"] >= read_distillation["original_payload_bytes"]:
        raise AssertionError("read_doc distillation did not reduce LLM content size")

    search_items = search_distillation.get("items")
    read_items = read_distillation.get("items")
    if not isinstance(search_items, list) or not search_items:
        raise AssertionError("search_docs distillation items are missing")
    if not isinstance(read_items, list) or len(read_items) != 1:
        raise AssertionError("read_doc distillation item is missing")
    if search_items[0].get("item_kind") != "search_result":
        raise AssertionError("search_docs distillation first item must be search_result")
    if read_items[0].get("item_kind") != "read_doc_excerpt":
        raise AssertionError("read_doc distillation item must be read_doc_excerpt")

    preserved = records["L3:preserved_info_frame"]
    if not isinstance(preserved, dict):
        raise AssertionError("L3 preserved payload must be a dict")
    l3_sources = preserved.get("source_data_ids")
    if not isinstance(l3_sources, list):
        raise AssertionError("L3 source_data_ids must be a list")
    if search_id not in l3_sources or read_id not in l3_sources:
        raise AssertionError("L3 must receive tool distillation records")
    if any(str(data_id).startswith("tool_result:search_docs:") for data_id in l3_sources):
        raise AssertionError("L3 should prefer distillation over raw search_docs tool result")

    candidates = preserved.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AssertionError("L3 preserved candidates are missing")
    if candidates[0].get("source_data_id") != search_id:
        raise AssertionError("L3 candidates must reference search_docs distillation source")

    return {
        "distillation_count": 2,
        "l3_uses_distillation": True,
    }


def _check_tool_efficiency_policy(records: dict[str, object]) -> dict[str, object]:
    """기본 dry run이 ToolUseBudgetFrame과 cache_status를 남겼는지 확인한다."""

    budget_ids = sorted(data_id for data_id in records if data_id.startswith("tool_budget:"))
    if len(budget_ids) < 4:
        raise AssertionError("tool budget frames are missing")
    budget_payloads = [records[data_id] for data_id in budget_ids]
    if not all(isinstance(payload, dict) for payload in budget_payloads):
        raise AssertionError("tool budget payloads must be dicts")

    first = budget_payloads[0]
    if first["max_tool_calls"] != 5:
        raise AssertionError("default max_tool_calls budget is wrong")
    if first["search_top_k"] != 3:
        raise AssertionError("default search_top_k budget is wrong")
    if first["max_query_attempts"] != 3:
        raise AssertionError("default max_query_attempts budget is wrong")
    if first["max_query_candidates"] != first["max_query_attempts"]:
        raise AssertionError("max_query_candidates alias must mirror max_query_attempts")
    if first["max_read_doc_calls"] != 1:
        raise AssertionError("default max_read_doc_calls budget is wrong")
    if first["max_input_chars"] != 6000:
        raise AssertionError("default max_input_chars budget is wrong")

    cache_records = []
    for payload in budget_payloads:
        cache_statuses = payload.get("cache_statuses")
        if isinstance(cache_statuses, list):
            cache_records.extend(cache_statuses)
    if not cache_records:
        raise AssertionError("tool budget frames did not record cache_status")
    cache_status = cache_records[-1].get("cache_status")
    if cache_status not in {"hit", "miss", "unknown"}:
        raise AssertionError("invalid cache_status in tool budget frame")

    l3_sources = records["L3:preserved_info_frame"].get("source_data_ids")
    if not isinstance(l3_sources, list):
        raise AssertionError("L3 source_data_ids must be a list")
    if not any(str(data_id).startswith("tool_budget:") for data_id in l3_sources):
        raise AssertionError("L3 must receive tool budget frames")
    if "L:budget_plan_frame" not in l3_sources:
        raise AssertionError("L3 must receive L loop budget plan frame")
    if budget_payloads[-1]["stop_reason"] != "completed":
        raise AssertionError("default tool budget should end with completed")

    budget_plan = records.get("L:budget_plan_frame")
    if not isinstance(budget_plan, dict):
        raise AssertionError("L loop budget plan frame is missing")
    if budget_plan.get("approved_by") != "CODE:BUDGET_POLICY":
        raise AssertionError("L loop budget plan must be approved by code policy")
    if budget_plan.get("approved_search_top_k") != first["search_top_k"]:
        raise AssertionError("tool budget search_top_k must follow budget plan approval")
    if budget_plan.get("approved_max_tool_calls") != first["max_tool_calls"]:
        raise AssertionError("tool budget max_tool_calls must follow budget plan approval")
    if budget_plan.get("approved_max_read_doc_calls") != first["max_read_doc_calls"]:
        raise AssertionError("tool budget max_read_doc_calls must follow budget plan approval")
    if budget_plan.get("approved_max_query_attempts") != first["max_query_attempts"]:
        raise AssertionError("tool budget max_query_attempts must follow budget plan approval")

    return {
        "budget_frame_count": len(budget_ids),
        "cache_status": cache_status,
        "budget_plan_approval": budget_plan.get("approval_reason"),
    }


def _run_tool_budget_limit_smoke() -> dict[str, object]:
    """max_tool_calls가 낮을 때 read_doc을 생략하고 budget stop_reason을 남기는지 확인한다."""

    limited = run_dry_turn(max_tool_calls=1)
    records = {item["data_id"]: item["payload"] for item in limited["data_records"]}
    if any(data_id.startswith("tool_result:read_doc:") for data_id in records):
        raise AssertionError("read_doc should not run when max_tool_calls=1")

    budget_payloads = [
        payload
        for data_id, payload in records.items()
        if data_id.startswith("tool_budget:") and isinstance(payload, dict)
    ]
    stop_reasons = [payload.get("stop_reason") for payload in budget_payloads]
    if "max_tool_calls_reached" not in stop_reasons:
        raise AssertionError("tool budget limit did not record max_tool_calls_reached")

    return {"stop_reason": "max_tool_calls_reached"}


def _run_search_budget_names_smoke() -> dict[str, object]:
    """search_top_k와 max_query_attempts가 서로 다른 예산으로 기록되는지 확인한다."""

    result = run_dry_turn(search_top_k=5, max_query_attempts=2, max_tool_calls=1)
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    search_payloads = [
        payload
        for data_id, payload in records.items()
        if data_id.startswith("tool_result:search_docs:") and isinstance(payload, dict)
    ]
    if not search_payloads:
        raise AssertionError("search_top_k smoke did not run search_docs")
    if search_payloads[0].get("top_k") != 5:
        raise AssertionError("search_docs did not receive search_top_k=5")

    budget_payloads = [
        payload
        for data_id, payload in records.items()
        if data_id.startswith("tool_budget:") and isinstance(payload, dict)
    ]
    if not budget_payloads:
        raise AssertionError("search budget smoke did not record budget frames")
    latest = budget_payloads[-1]
    if latest.get("search_top_k") != 5:
        raise AssertionError("budget frame did not record search_top_k=5")
    if latest.get("max_query_attempts") != 2:
        raise AssertionError("budget frame did not record max_query_attempts=2")
    if latest.get("max_query_candidates") != 2:
        raise AssertionError("compat max_query_candidates did not mirror max_query_attempts")

    return {
        "search_top_k": latest.get("search_top_k"),
        "max_query_attempts": latest.get("max_query_attempts"),
    }


def _run_l_loop_budget_consistency_smoke() -> dict[str, object]:
    """read_doc 승인 수와 tool_call 승인 수가 서로 모순되지 않는지 확인한다."""

    adapter = LowToolCallBudgetFakeAdapter()
    result = run_dry_turn(
        user_input="여러 문서를 읽고 연관점을 파악해줘",
        force_l_route=True,
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        max_tool_calls=2,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    budget_plan = records.get("L:budget_plan_frame")
    if not isinstance(budget_plan, dict):
        raise AssertionError("budget consistency smoke did not record budget plan")
    if budget_plan.get("requested_max_tool_calls") != 2:
        raise AssertionError("budget consistency smoke should request tool_calls=2")
    if budget_plan.get("requested_max_read_doc_calls") != 2:
        raise AssertionError("budget consistency smoke should request read_doc=2")
    if budget_plan.get("approved_max_tool_calls") != 3:
        raise AssertionError("read_doc=2 should imply at least 3 total tool calls")
    if budget_plan.get("approved_max_read_doc_calls") != 2:
        raise AssertionError("budget consistency smoke should keep read_doc=2")
    approval_reason = str(budget_plan.get("approval_reason") or "")
    if "tool_calls_aligned_with_read_doc_budget" not in approval_reason:
        raise AssertionError("budget consistency smoke should record alignment reason")

    first_budget = records.get("tool_budget:turn_dry_001:0001")
    if not isinstance(first_budget, dict):
        raise AssertionError("budget consistency smoke did not record first tool budget")
    if first_budget.get("max_tool_calls") != 3:
        raise AssertionError("tool budget should use aligned max_tool_calls=3")
    if first_budget.get("max_read_doc_calls") != 2:
        raise AssertionError("tool budget should keep max_read_doc_calls=2")
    read_doc_result_count = sum(
        1 for data_id in records if data_id.startswith("tool_result:read_doc:")
    )
    if read_doc_result_count < 2:
        raise AssertionError("aligned budget should allow reading at least two documents")

    return {
        "approved_max_tool_calls": budget_plan.get("approved_max_tool_calls"),
        "approved_max_read_doc_calls": budget_plan.get("approved_max_read_doc_calls"),
        "actual_read_doc_count": read_doc_result_count,
    }


def _run_l1_requirement_budget_smoke() -> dict[str, object]:
    """L1이 숫자 예산을 빼먹어도 구조화 요구사항으로 다문서 예산을 승인하는지 확인한다."""

    adapter = RequirementOnlyMultiDocFakeAdapter()
    result = run_dry_turn(
        user_input="여러 문서를 무작위로 열람한 뒤에 그 문서들의 연관점을 파악해봐",
        force_l_route=True,
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    l1_goal = records.get("L1:goal_frame")
    if not isinstance(l1_goal, dict):
        raise AssertionError("L1 requirement budget smoke did not record L1 goal")
    if l1_goal.get("evidence_requirement_kind") != "multi_doc_relationship":
        raise AssertionError("L1 requirement smoke should declare multi_doc_relationship")
    if l1_goal.get("requested_max_read_doc_calls") != 0:
        raise AssertionError("L1 requirement smoke should omit numeric read_doc request")

    budget_plan = records.get("L:budget_plan_frame")
    if not isinstance(budget_plan, dict):
        raise AssertionError("L1 requirement budget smoke did not record budget plan")
    if budget_plan.get("approved_max_read_doc_calls") < 2:
        raise AssertionError("L1 evidence requirement should approve at least two read_doc calls")
    if budget_plan.get("approved_max_tool_calls") < 3:
        raise AssertionError("L1 evidence requirement should align tool_calls for two read_doc calls")
    approval_reason = str(budget_plan.get("approval_reason") or "")
    if "budget_expanded_from_l1_evidence_requirement" not in approval_reason:
        raise AssertionError("approval reason should mention L1 evidence requirement expansion")

    read_doc_result_count = sum(
        1 for data_id in records if data_id.startswith("tool_result:read_doc:")
    )
    if read_doc_result_count < 2:
        raise AssertionError("L1 evidence requirement should lead to multiple read_doc calls")

    return {
        "approved_max_tool_calls": budget_plan.get("approved_max_tool_calls"),
        "approved_max_read_doc_calls": budget_plan.get("approved_max_read_doc_calls"),
    }


def _run_read_artifact_exact_ref_smoke() -> dict[str, object]:
    """Explicit artifact references should use read_artifact, not semantic search ranking."""

    direct = read_artifact(root="Administrative_Reform_1", artifact_ref="CODE_STRUCTURE_MAP_v1")
    expected_doc_id = "03_Maps/02_Function_Maps/CODE_STRUCTURE_MAP_v1.md"
    if direct.get("match_status") != "unique":
        raise AssertionError("read_artifact did not resolve CODE_STRUCTURE_MAP_v1 uniquely")
    if direct.get("doc_id") != expected_doc_id:
        raise AssertionError("read_artifact resolved the wrong document")
    if "Code Structure Map v1" not in str(direct.get("text") or ""):
        raise AssertionError("read_artifact did not read the expected document text")

    result = run_dry_turn(
        user_input="read CODE_STRUCTURE_MAP_v1",
        force_l_route=True,
        l2_query_planner_adapter=ExactArtifactQueryPlannerFakeLLMAdapter(),
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    query_frame = records.get("L2:query_frame")
    if not isinstance(query_frame, dict):
        raise AssertionError("read_artifact smoke did not create L2 query frame")
    if query_frame.get("target_tool_name") != "read_artifact":
        raise AssertionError("L2 did not select read_artifact")
    if query_frame.get("query_mode") != "exact_artifact_ref":
        raise AssertionError("read_artifact L2 query mode should be exact_artifact_ref")

    artifact_result_ids = [
        data_id for data_id in records if data_id.startswith("tool_result:read_artifact:")
    ]
    if not artifact_result_ids:
        raise AssertionError("L loop did not execute read_artifact")
    artifact_payload = records[artifact_result_ids[0]]
    if not isinstance(artifact_payload, dict) or artifact_payload.get("doc_id") != expected_doc_id:
        raise AssertionError("read_artifact L loop result did not read CODE_STRUCTURE_MAP_v1")

    achievement = records.get("L3:achievement_frame")
    if not isinstance(achievement, dict):
        raise AssertionError("read_artifact smoke did not record L3 achievement")
    if achievement.get("goal_match_status") != "matched":
        raise AssertionError(
            "read_artifact should satisfy the explicit doc goal: "
            f"status={achievement.get('goal_match_status')} "
            f"hint={achievement.get('requested_doc_hint')} "
            f"read_doc_ids={achievement.get('read_doc_ids')}"
        )

    return {
        "doc_id": expected_doc_id,
        "l2_tool": query_frame.get("target_tool_name"),
    }


def _run_l3_goal_match_guard_smoke() -> dict[str, object]:
    """특정 문서를 요구했지만 read_doc까지 못 간 턴은 L3가 achieved로 확정하지 않는지 확인한다."""

    result = run_dry_turn(
        user_input="03_Maps/02_Function_Maps/CODE_STRUCTURE_MAP_v1을 찾아 읽어줘",
        force_l_route=True,
        max_tool_calls=1,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    achievement = records.get("L3:achievement_frame")
    if not isinstance(achievement, dict):
        raise AssertionError("L3 goal match smoke did not record achievement frame")

    hint = achievement.get("requested_doc_hint")
    if not isinstance(hint, str) or "CODE_STRUCTURE_MAP_v1" not in hint:
        raise AssertionError("L3 goal match smoke did not extract requested doc hint")
    if achievement.get("read_doc_ids"):
        raise AssertionError("L3 goal match smoke should not read a document with max_tool_calls=1")
    if achievement.get("goal_match_status") != "partial":
        raise AssertionError("L3 goal match guard should mark unread requested doc as partial")
    if achievement.get("achievement_status") != "partial":
        raise AssertionError("L3 goal match guard should downgrade achieved to partial")

    return {
        "goal_match_status": achievement.get("goal_match_status"),
        "achievement_status": achievement.get("achievement_status"),
    }


def _run_l3_semantic_goal_guard_smoke() -> dict[str, object]:
    """LLM semantic mismatch judgement should downgrade L3 without keyword heuristics."""

    adapter = SemanticMismatchL3FakeAdapter()
    result = run_dry_turn(
        user_input="사용자 목표와 읽은 문서가 의미적으로 맞는지 L3가 판단해줘",
        force_l_route=True,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    achievement = records.get("L3:achievement_frame")
    if not isinstance(achievement, dict):
        raise AssertionError("L3 semantic goal smoke did not record achievement frame")
    if achievement.get("semantic_goal_match_status") != "partial":
        raise AssertionError("L3 semantic goal smoke did not preserve LLM semantic partial status")
    if achievement.get("achievement_status") != "partial":
        raise AssertionError("L3 semantic goal guard should downgrade achieved to partial")
    generation_source = str(achievement.get("achievement_generation_source") or "")
    if "CODE:SEMANTIC_GOAL_GUARD" not in generation_source:
        raise AssertionError("L3 semantic goal guard source marker is missing")

    return {
        "semantic_goal_match_status": achievement.get("semantic_goal_match_status"),
        "achievement_status": achievement.get("achievement_status"),
    }


def _run_duplicate_tool_use_signal_smoke() -> dict[str, object]:
    """중복 query 시도가 failure signal과 budget frame으로 기록될 수 있는지 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "smoke_tool_efficiency_001"
    source_event = trace_store.create_event(
        turn_id=turn_id,
        actor="smoke",
        event_type="node_output",
        output_ref=["smoke:query"],
        schema_status="passed",
    )
    duplicate_trace_id, duplicate_id = record_duplicate_tool_use_signal(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        duplicate_kind="query",
        duplicate_value="repeat query",
        source_trace_ids=[source_event.event_id],
        source_data_ids=["smoke:query"],
    )
    record_tool_use_budget_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        sequence_index=1,
        max_tool_calls=2,
        search_top_k=3,
        max_query_attempts=2,
        max_read_doc_calls=1,
        max_input_chars=1000,
        tool_call_count=1,
        executed_queries=["repeat query"],
        read_doc_ids=[],
        cache_statuses=[],
        input_chars_used=12,
        stop_reason="duplicate_query",
        reason="CODE_STATUS:duplicate_query_smoke",
        condition_flags=["duplicate_query"],
        source_trace_ids=[duplicate_trace_id],
        source_data_ids=[duplicate_id],
        duplicate_query_count=1,
    )
    duplicate_payload = data_store.require_record(duplicate_id).payload
    budget_payload = data_store.require_record(f"tool_budget:{turn_id}:0001").payload
    if not isinstance(duplicate_payload, dict) or "duplicate_query" not in duplicate_payload.get("message", ""):
        raise AssertionError("duplicate query signal was not recorded")
    if not isinstance(budget_payload, dict) or budget_payload.get("stop_reason") != "duplicate_query":
        raise AssertionError("duplicate query budget frame was not recorded")

    return {"duplicate_signal": True}


def _run_llm_call_smoke() -> dict[str, object]:
    """FakeLLM 성공과 깨진 JSON 재시도 기록을 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "smoke_llm_001"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:smoke_llm",
        schema_status="not_checked",
    )

    success = LLMNodeExecutor(FakeLLMAdapter()).run(
        node_id="smoke_node",
        prompt="Return JSON only.",
        input_payload={"smoke": True},
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref="smoke:fake_prompt",
        input_ref=[user_event.event_id],
        source_data_ids=["smoke:input"],
    )
    if success.call_data_id is None:
        raise AssertionError("successful LLM smoke did not create call_data_id")
    success_payload = data_store.require_record(success.call_data_id).payload
    if not isinstance(success_payload, dict) or success_payload["failure_type"] != "none":
        raise AssertionError("successful LLM smoke did not record success")

    failed = LLMNodeExecutor(BrokenJSONFakeLLMAdapter()).run(
        node_id="broken_smoke_node",
        prompt="Return JSON only.",
        input_payload={"smoke": "broken"},
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref="smoke:broken_prompt",
        input_ref=[user_event.event_id],
        source_data_ids=["smoke:input"],
        max_retries=1,
    )
    if failed.call_data_id is None:
        raise AssertionError("failed LLM smoke did not create call_data_id")
    failed_payload = data_store.require_record(failed.call_data_id).payload
    if not isinstance(failed_payload, dict):
        raise AssertionError("failed LLM call payload is not a dict")
    if failed_payload["failure_type"] != "parse_failed":
        raise AssertionError("failed LLM smoke did not record parse_failed")
    if failed_payload["retry_count"] != 1:
        raise AssertionError("failed LLM smoke did not record retry_count=1")

    llm_call_records = [
        record for record in data_store.list_records() if record.data_type == "llm_call"
    ]
    if len(llm_call_records) != 3:
        raise AssertionError("LLM smoke should record one success and two retry attempts")

    return {
        "llm_call_records": len(llm_call_records),
        "llm_retry_failure_type": failed_payload["failure_type"],
    }


def _run_router_fallback_honesty_smoke() -> dict[str, object]:
    """node_1 LLM 실패 뒤 code fallback이 정직하게 구분되는지 확인한다."""

    user_input = "그냥 보고해줘"
    success = run_dry_turn(
        user_input=user_input,
        node_1_router_adapter=SongRyeonAllNodesFakeLLMAdapter(),
    )
    success_route = _first_routing_payload(success)
    if success_route.get("llm_routing_status") != "ran":
        raise AssertionError("node_1 LLM router success must record llm_routing_status=ran")
    if success_route.get("fallback_after_llm_failure") is not False:
        raise AssertionError("node_1 LLM router success must not look like fallback")

    fallback = run_dry_turn(
        user_input=user_input,
        node_1_router_adapter=BrokenJSONFakeLLMAdapter(),
    )
    fallback_route = _first_routing_payload(fallback)
    failure_data_id = fallback_route.get("router_llm_failure_data_id")
    failure_trace_id = fallback_route.get("router_llm_failure_trace_event_id")
    source_data_ids = fallback_route.get("source_data_ids")
    source_trace_ids = fallback_route.get("source_trace_ids")
    if fallback_route.get("llm_routing_status") != "failed":
        raise AssertionError("fallback route must record llm_routing_status=failed")
    if fallback_route.get("fallback_after_llm_failure") is not True:
        raise AssertionError("fallback route must record fallback_after_llm_failure=true")
    if fallback_route.get("fallback_policy") != ROUTER_FALLBACK_POLICY_DEV_SMOKE:
        raise AssertionError("fallback route must record the dev/smoke fallback policy")
    if fallback_route.get("fallback_allowed_by_runtime_policy") is not True:
        raise AssertionError("fallback route must record runtime policy allowance")
    if fallback_route.get("fallback_source_route_rule_id") != fallback_route.get("route_rule_id"):
        raise AssertionError("fallback route must preserve the code route rule id")
    if fallback_route.get("router_llm_failure_type") != "parse_failed":
        raise AssertionError("fallback route must preserve the LLM failure type")
    if not isinstance(failure_data_id, str) or not isinstance(source_data_ids, list):
        raise AssertionError("fallback route must cite the failed LLM call data id")
    if failure_data_id not in source_data_ids:
        raise AssertionError("fallback route source_data_ids must include failed LLM call id")
    if not isinstance(failure_trace_id, str) or not isinstance(source_trace_ids, list):
        raise AssertionError("fallback route must cite the failed LLM trace event id")
    if failure_trace_id not in source_trace_ids:
        raise AssertionError("fallback route source_trace_ids must include failed LLM trace id")

    code = run_dry_turn(user_input=user_input)
    code_terminal = render_pretty_turn(code, user_input=user_input)
    fallback_terminal = render_pretty_turn(fallback, user_input=user_input)
    if "node_1 router: CODE:RULE_STUB" not in code_terminal:
        raise AssertionError("terminal must show direct code router status")
    if "node_1 router: LLM failed -> CODE:RULE_STUB fallback" not in fallback_terminal:
        raise AssertionError("terminal must distinguish LLM failure fallback")

    strict_blocked = False
    try:
        run_dry_turn(
            user_input=user_input,
            node_1_router_adapter=BrokenJSONFakeLLMAdapter(),
            allow_node_1_router_fallback=False,
            node_1_router_fallback_policy=ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED,
        )
    except Node1RouterLLMFailure:
        strict_blocked = True
    if not strict_blocked:
        raise AssertionError("strict router policy must not silently allow fallback")

    return {
        "fallback_policy": fallback_route["fallback_policy"],
        "failure_type": fallback_route["router_llm_failure_type"],
        "terminal_distinct": True,
        "strict_blocked": strict_blocked,
    }


def _first_routing_payload(result: dict[str, object]) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        raise AssertionError("data_records must be a list")
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("data_type") != "node_output:routing_decision":
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            return payload
    raise AssertionError("routing decision payload not found")


def _run_l2_query_planner_smoke() -> dict[str, object]:
    """L2 query plan 성공과 실패 fallback을 확인한다."""

    planned = run_dry_turn(
        user_input="L2가 내부 문서를 알아서 검색하게 해줘",
        l2_query_planner_adapter=QueryPlannerFakeLLMAdapter(),
    )
    planned_records = {item["data_id"]: item["payload"] for item in planned["data_records"]}
    if "L2:query_plan_frame" not in planned_records:
        raise AssertionError("L2 query planner did not create L2:query_plan_frame")
    plan_payload = planned_records["L2:query_plan_frame"]
    query_payload = planned_records["L2:query_frame"]
    if not isinstance(plan_payload, dict) or not isinstance(query_payload, dict):
        raise AssertionError("L2 planner payloads must be dicts")
    candidates = plan_payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AssertionError("L2 query plan candidates are missing")
    if query_payload["query_source"] != "llm_query_plan":
        raise AssertionError("L2 query frame did not use llm_query_plan source")
    selected_query = _selected_query_from_payload(plan_payload)
    if query_payload["query_text"] != selected_query:
        raise AssertionError("L2 selected query did not flow into L2 query frame")
    boundary_payload = planned_records["boundary_dry_001"]
    if not isinstance(boundary_payload, dict):
        raise AssertionError("planned boundary payload must be a dict")
    plan_mixed_info = _has_l2_query_plan_mixed_info(boundary_payload)
    if not plan_mixed_info:
        raise AssertionError("L2 query plan purpose did not become mixed_info")

    mixed_tool = run_dry_turn(
        user_input="Qwen이 list_docs를 먼저 고르더라도 L2는 search_docs 후보를 써야 해",
        l2_query_planner_adapter=MixedToolQueryPlannerFakeLLMAdapter(),
    )
    mixed_tool_records = {item["data_id"]: item["payload"] for item in mixed_tool["data_records"]}
    mixed_tool_plan = mixed_tool_records["L2:query_plan_frame"]
    mixed_tool_query = mixed_tool_records["L2:query_frame"]
    if not isinstance(mixed_tool_plan, dict) or not isinstance(mixed_tool_query, dict):
        raise AssertionError("mixed tool L2 planner payloads must be dicts")
    mixed_tool_candidates = mixed_tool_plan.get("candidates")
    if not isinstance(mixed_tool_candidates, list) or len(mixed_tool_candidates) != 1:
        raise AssertionError("L2 mixed tool normalization should keep only search_docs candidates")
    if mixed_tool_candidates[0].get("target_tool_name") != "search_docs":
        raise AssertionError("L2 mixed tool normalization kept a non-search_docs candidate")
    if mixed_tool_plan.get("selected_candidate_id") != mixed_tool_candidates[0].get("candidate_id"):
        raise AssertionError("L2 mixed tool normalization did not reselect a valid candidate")
    if mixed_tool_query.get("query_source") != "llm_query_plan":
        raise AssertionError("L2 mixed tool normalization did not preserve LLM plan path")

    fallback = run_dry_turn(
        user_input="깨진 LLM이면 기존 검색으로 돌아가줘",
        l2_query_planner_adapter=BrokenJSONFakeLLMAdapter(),
    )
    fallback_records = {item["data_id"]: item["payload"] for item in fallback["data_records"]}
    fallback_query = fallback_records["L2:query_frame"]
    if not isinstance(fallback_query, dict):
        raise AssertionError("fallback L2 query payload must be a dict")
    if fallback_query["query_source"] != "user_input_fallback":
        raise AssertionError("broken L2 planner did not fall back to user input")

    return {
        "candidate_count": len(candidates),
        "plan_mixed_info": plan_mixed_info,
        "mixed_tool_plan_normalized": True,
        "broken_planner_fallback": True,
    }


def _run_fake_llm_l_loop_export_replay_smoke() -> dict[str, object]:
    """FakeLLM L루프 결과를 export하고 replay로 주요 흐름을 확인한다."""

    with tempfile.TemporaryDirectory(prefix="songryeon_fake_l_loop_") as temp_dir:
        result = run_fake_llm_l_loop_smoke(export_dir=temp_dir)
    if result["status"] != "FAKE_LLM_L_LOOP_OK":
        raise AssertionError("FakeLLM L loop smoke did not pass")
    if not result["replay_checked"]:
        raise AssertionError("FakeLLM L loop replay was not checked")
    if result["rule_query_source"] != "user_input_fallback":
        raise AssertionError("rule L loop query source changed unexpectedly")
    if result["llm_query_source"] != "llm_query_plan":
        raise AssertionError("FakeLLM L loop did not use llm_query_plan")
    if not result["l2_query_plan_present"]:
        raise AssertionError("FakeLLM L loop did not preserve query plan")
    return result


def _run_fake_user_turn_smoke() -> dict[str, object]:
    """직접 질문용 fake-turn entrypoint가 LLM 계획 경로로 닫히는지 확인한다."""

    result = run_fake_user_turn(user_input="송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘")
    if result["status"] != "ok":
        raise AssertionError("fake-turn did not finish with ok status")
    if result["l2_query_source"] != "llm_query_plan":
        raise AssertionError("fake-turn did not use llm_query_plan")
    if not result["l2_query_plan_present"]:
        raise AssertionError("fake-turn did not create L2 query plan")
    if result["l_loop_final_decision"] != "stop_success":
        raise AssertionError("fake-turn L loop did not finish with stop_success")
    if not result.get("report"):
        raise AssertionError("fake-turn did not return a report")
    return {
        "status": result["status"],
        "query_source": result["l2_query_source"],
    }


def _run_l_loop_continuation_controller_smoke() -> dict[str, object]:
    """ORDER 089 controller가 구조화 status와 예산만 보고 판단하는지 확인한다."""

    stop_store = DataStore.from_records(run_dry_turn()["data_records"])
    stop_trace_store = TraceStore()
    _, _, stop_frame = record_l_loop_continuation_decision(
        trace_store=stop_trace_store,
        data_store=stop_store,
        turn_id="turn_dry_001",
        attempt_index=1,
        max_attempts=3,
    )
    if stop_frame.continuation_status != "stop_achieved":
        raise AssertionError("achieved L3 result should stop continuation")
    if stop_frame.next_target_node != "loop_return_summary":
        raise AssertionError("stop continuation should target loop_return_summary")

    continue_store = DataStore()
    continue_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": "turn_continue",
            "query_text": "첫 검색어",
        },
    )
    continue_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": "turn_continue",
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    continue_store.create_record(
        data_id="tool_budget:turn_continue:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "turn_id": "turn_continue",
            "sequence_index": 1,
            "max_tool_calls": 3,
            "tool_call_count": 1,
            "max_query_attempts": 3,
            "query_count": 1,
            "max_read_doc_calls": 2,
            "read_doc_count": 1,
            "stop_reason": "within_budget",
        },
    )
    _, _, continue_frame = record_l_loop_continuation_decision(
        trace_store=TraceStore(),
        data_store=continue_store,
        turn_id="turn_continue",
        attempt_index=1,
        max_attempts=3,
    )
    if continue_frame.continuation_status != "continue":
        raise AssertionError("partial L3 result with remaining budget should continue")
    if continue_frame.next_target_node != "L2":
        raise AssertionError("continue continuation should target L2")
    if not continue_frame.continuation_reason_code.startswith("CODE_STATUS:"):
        raise AssertionError("continuation reason must remain a CODE_STATUS label")
    if continue_frame.unread_candidate_doc_ids != ["ORDER_002.md"]:
        raise AssertionError("continuation should preserve unread candidate doc ids")

    return {
        "stop_status": stop_frame.continuation_status,
        "continue_status": continue_frame.continuation_status,
    }


def _run_l3_continuation_memory_packet_smoke() -> dict[str, object]:
    """0 should copy L3 continuation facts into an L2-facing memory packet."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_continue_memory"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:continuation_memory_smoke",
        schema_status="not_checked",
    )
    zero_state = ZeroState(current_turn_trace_ids=[user_event.event_id])

    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": turn_id,
            "query_text": "first structured search",
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": turn_id,
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "reason": "COPIED_TEST_REASON",
            "macro_achievement_reason": "COPIED_MACRO_REASON",
            "micro_achievement_reason": "COPIED_MICRO_REASON",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    data_store.create_record(
        data_id="tool_budget:turn_continue_memory:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "turn_id": turn_id,
            "sequence_index": 1,
            "max_tool_calls": 3,
            "tool_call_count": 1,
            "max_query_attempts": 3,
            "query_count": 1,
            "max_read_doc_calls": 2,
            "read_doc_count": 1,
            "stop_reason": "within_budget",
        },
    )
    _, continuation_frame_id, _ = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        max_attempts=3,
        source_trace_ids=[user_event.event_id],
    )
    record_l3_continuation_summary_for_l2(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        continuation_frame_id=continuation_frame_id,
        input_ref=[user_event.event_id],
    )

    packet_id = memory_packet_data_id("L2", L3_CONTINUATION_SUMMARY_MODE, "0001")
    payload = data_store.require_record(packet_id).payload
    if not isinstance(payload, dict):
        raise AssertionError("L3 continuation memory packet payload must be a dict")
    if payload.get("target") != "L2":
        raise AssertionError("L3 continuation memory packet must target L2")
    if payload.get("mode") != L3_CONTINUATION_SUMMARY_MODE:
        raise AssertionError("L3 continuation memory packet mode is wrong")
    if payload.get("generated_by") != "CODE:RULE_STUB":
        raise AssertionError("0 continuation memory packet must reveal CODE:RULE_STUB")
    if payload.get("llm_semantic_summary_status") != "not_run":
        raise AssertionError("0 continuation memory packet must not pretend LLM summary ran")

    items = payload.get("memory_items")
    if not isinstance(items, list) or len(items) < 5:
        raise AssertionError("L3 continuation memory packet has too few memory items")
    item_types = {item.get("item_type") for item in items if isinstance(item, dict)}
    required_item_types = {
        "l_loop_continuation_status",
        "l3_goal_status_copy",
        "l3_feedback_text_copy",
        "previous_l2_query_copy",
        "tool_budget_status_copy",
        "read_and_unread_candidate_ids_copy",
    }
    if not required_item_types.issubset(item_types):
        raise AssertionError("L3 continuation memory packet missed required copied fields")
    rendered_items = "\n".join(
        str(item.get("text", "")) for item in items if isinstance(item, dict)
    )
    if "ORDER_002.md" not in rendered_items:
        raise AssertionError("L3 continuation memory packet missed unread candidate doc id")
    if "COPIED_TEST_REASON" not in rendered_items:
        raise AssertionError("L3 continuation memory packet missed copied L3 feedback")

    return {
        "mode": payload.get("mode"),
        "item_count": len(items),
    }


def _run_l2_revision_input_frame_smoke() -> dict[str, object]:
    """L2 revision input should be assembled from structured records only."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_revision_input"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:revision_input_smoke",
        schema_status="not_checked",
    )
    zero_state = ZeroState(current_turn_trace_ids=[user_event.event_id])

    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l1",
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": turn_id,
            "macro_goal": "find_requested_internal_document",
            "macro_goal_reason": "LLM_TEST_MACRO_REASON",
            "micro_goal": "revise_search_scope",
            "micro_goal_reason": "LLM_TEST_MICRO_REASON",
            "goal_source": "llm_l_route",
            "target_loop": "L",
            "goal_generation_source": "LLM:test",
            "llm_goal_judgement_status": "ran",
            "source_trace_ids": [user_event.event_id],
            "source_data_ids": [],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": turn_id,
            "query_text": "first structured search",
            "query_source": "llm_query_plan",
            "query_mode": "embedding_search",
            "target_tool_name": "search_docs",
            "source_trace_ids": ["trace_l1"],
            "source_data_ids": ["L1:goal_frame"],
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": turn_id,
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "reason": "COPIED_TEST_REASON",
            "macro_achievement_reason": "COPIED_MACRO_REASON",
            "micro_achievement_reason": "COPIED_MICRO_REASON",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    data_store.create_record(
        data_id="tool_budget:turn_revision_input:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "turn_id": turn_id,
            "sequence_index": 1,
            "max_tool_calls": 3,
            "tool_call_count": 1,
            "max_query_attempts": 3,
            "query_count": 1,
            "max_read_doc_calls": 2,
            "read_doc_count": 1,
            "stop_reason": "within_budget",
        },
    )
    _, continuation_frame_id, _ = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        max_attempts=3,
        source_trace_ids=[user_event.event_id],
    )
    record_l3_continuation_summary_for_l2(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        continuation_frame_id=continuation_frame_id,
        input_ref=[user_event.event_id],
    )
    _, revision_input_id, frame = record_l2_revision_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        continuation_frame_id=continuation_frame_id,
    )

    payload = data_store.require_record(revision_input_id).payload
    if not isinstance(payload, dict):
        raise AssertionError("L2 revision input payload must be a dict")
    if payload.get("frame_id") != "L2:revision_input:0001":
        raise AssertionError("L2 revision input frame_id is wrong")
    if payload.get("macro_goal") != "find_requested_internal_document":
        raise AssertionError("L2 revision input missed L1 macro goal")
    if payload.get("previous_query_text") != "first structured search":
        raise AssertionError("L2 revision input missed previous query")
    if payload.get("l3_goal_status") != "partial":
        raise AssertionError("L2 revision input missed L3 partial status")
    if payload.get("remaining_tool_calls") != 2:
        raise AssertionError("L2 revision input remaining tool calls are wrong")
    if payload.get("remaining_query_attempts") != 2:
        raise AssertionError("L2 revision input remaining query attempts are wrong")
    if payload.get("remaining_read_doc_calls") != 1:
        raise AssertionError("L2 revision input remaining read doc calls are wrong")
    if "ORDER_001.md" not in (payload.get("read_document_names") or []):
        raise AssertionError("L2 revision input missed read document name")
    summaries = payload.get("unread_candidate_summaries")
    if not isinstance(summaries, list) or not any("ORDER_002.md" in str(item) for item in summaries):
        raise AssertionError("L2 revision input missed unread candidate summary")
    source_data_ids = payload.get("source_data_ids")
    if not isinstance(source_data_ids, list):
        raise AssertionError("L2 revision input source_data_ids must be a list")
    required_sources = {
        "L1:goal_frame",
        "L2:query_frame",
        "L3:achievement_frame",
        "L:continuation:0001",
        "memory_packet:L2:l3_continuation_summary_for_L2:0001",
    }
    if not required_sources.issubset(set(source_data_ids)):
        raise AssertionError("L2 revision input source_data_ids are incomplete")

    return {
        "attempt_index": frame.attempt_index,
        "previous_tool_name": frame.previous_tool_name,
    }


def _run_l2_revision_query_planner_smoke() -> dict[str, object]:
    """L2 revision query planner should create an attempt-scoped query plan."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_revision_query"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:revision_query_smoke",
        schema_status="not_checked",
    )
    zero_state = ZeroState(current_turn_trace_ids=[user_event.event_id])

    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l1",
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": turn_id,
            "macro_goal": "find_requested_internal_document",
            "macro_goal_reason": "LLM_TEST_MACRO_REASON",
            "micro_goal": "revise_search_scope",
            "micro_goal_reason": "LLM_TEST_MICRO_REASON",
            "goal_source": "llm_l_route",
            "target_loop": "L",
            "goal_generation_source": "LLM:test",
            "llm_goal_judgement_status": "ran",
            "source_trace_ids": [user_event.event_id],
            "source_data_ids": [],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": turn_id,
            "query_text": "first structured search",
            "query_source": "llm_query_plan",
            "query_mode": "embedding_search",
            "target_tool_name": "search_docs",
            "source_trace_ids": ["trace_l1"],
            "source_data_ids": ["L1:goal_frame"],
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": turn_id,
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "reason": "COPIED_TEST_REASON",
            "macro_achievement_reason": "COPIED_MACRO_REASON",
            "micro_achievement_reason": "COPIED_MICRO_REASON",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    data_store.create_record(
        data_id="tool_budget:turn_revision_query:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "turn_id": turn_id,
            "sequence_index": 1,
            "max_tool_calls": 3,
            "tool_call_count": 1,
            "max_query_attempts": 3,
            "query_count": 1,
            "max_read_doc_calls": 2,
            "read_doc_count": 1,
            "stop_reason": "within_budget",
        },
    )
    _, continuation_frame_id, _ = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        max_attempts=3,
        source_trace_ids=[user_event.event_id],
    )
    record_l3_continuation_summary_for_l2(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        continuation_frame_id=continuation_frame_id,
        input_ref=[user_event.event_id],
    )
    _, revision_input_id, _ = record_l2_revision_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        continuation_frame_id=continuation_frame_id,
    )
    run_l2_revision_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_input_data_id=revision_input_id,
        adapter=RevisionQueryPlannerFakeLLMAdapter(),
    )

    plan_id = l2_revision_query_plan_data_id(1)
    payload = data_store.require_record(plan_id).payload
    if not isinstance(payload, dict):
        raise AssertionError("L2 revision query plan payload must be a dict")
    if payload.get("frame_id") != plan_id:
        raise AssertionError("L2 revision query plan frame_id is wrong")
    if payload.get("planner_mode") != "revision_llm":
        raise AssertionError("L2 revision query plan must use revision_llm mode")
    selected_query = selected_query_from_plan(payload)
    if selected_query == "first structured search":
        raise AssertionError("L2 revision query should not repeat the previous query in this smoke")
    source_data_ids = payload.get("source_data_ids")
    if not isinstance(source_data_ids, list) or revision_input_id not in source_data_ids:
        raise AssertionError("L2 revision query plan must cite revision input")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AssertionError("L2 revision query plan candidates are missing")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise AssertionError("L2 revision query candidate must be a dict")
        if candidate.get("target_tool_name") not in {"search_docs", "read_artifact"}:
            raise AssertionError("L2 revision query candidate selected a disallowed tool")
        candidate_sources = candidate.get("source_data_ids")
        if not isinstance(candidate_sources, list) or revision_input_id not in candidate_sources:
            raise AssertionError("L2 revision query candidate must cite revision input")

    return {
        "planner_mode": payload.get("planner_mode"),
        "selected_query": selected_query,
    }


def _run_l2_revision_query_frame_smoke() -> dict[str, object]:
    """Selected revision query plan candidate should become an L2QueryFrame."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_revision_query_frame"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:revision_query_frame_smoke",
        schema_status="not_checked",
    )
    zero_state = ZeroState(current_turn_trace_ids=[user_event.event_id])

    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l1",
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": turn_id,
            "macro_goal": "find_requested_internal_document",
            "macro_goal_reason": "LLM_TEST_MACRO_REASON",
            "micro_goal": "revise_search_scope",
            "micro_goal_reason": "LLM_TEST_MICRO_REASON",
            "goal_source": "llm_l_route",
            "target_loop": "L",
            "goal_generation_source": "LLM:test",
            "llm_goal_judgement_status": "ran",
            "source_trace_ids": [user_event.event_id],
            "source_data_ids": [],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": turn_id,
            "query_text": "first structured search",
            "query_source": "llm_query_plan",
            "query_mode": "embedding_search",
            "target_tool_name": "search_docs",
            "source_trace_ids": ["trace_l1"],
            "source_data_ids": ["L1:goal_frame"],
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": turn_id,
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "reason": "COPIED_TEST_REASON",
            "macro_achievement_reason": "COPIED_MACRO_REASON",
            "micro_achievement_reason": "COPIED_MICRO_REASON",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    data_store.create_record(
        data_id="tool_budget:turn_revision_query_frame:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "turn_id": turn_id,
            "sequence_index": 1,
            "max_tool_calls": 3,
            "tool_call_count": 1,
            "max_query_attempts": 3,
            "query_count": 1,
            "max_read_doc_calls": 2,
            "read_doc_count": 1,
            "stop_reason": "within_budget",
        },
    )
    _, continuation_frame_id, _ = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        max_attempts=3,
        source_trace_ids=[user_event.event_id],
    )
    record_l3_continuation_summary_for_l2(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        continuation_frame_id=continuation_frame_id,
        input_ref=[user_event.event_id],
    )
    _, revision_input_id, _ = record_l2_revision_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        continuation_frame_id=continuation_frame_id,
    )
    run_l2_revision_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_input_data_id=revision_input_id,
        adapter=RevisionQueryPlannerFakeLLMAdapter(),
    )
    plan_id = l2_revision_query_plan_data_id(1)
    run_l2_revision_query_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_query_plan_data_id=plan_id,
    )

    query_frame_id = l2_revision_query_frame_data_id(1)
    query_payload = data_store.require_record(query_frame_id).payload
    plan_payload = data_store.require_record(plan_id).payload
    if not isinstance(query_payload, dict) or not isinstance(plan_payload, dict):
        raise AssertionError("L2 revision query frame smoke payloads must be dicts")
    selected_query = selected_query_from_plan(plan_payload)
    if query_payload.get("frame_id") != query_frame_id:
        raise AssertionError("L2 revision query frame_id is wrong")
    if query_payload.get("query_text") != selected_query:
        raise AssertionError("L2 revision query frame did not copy selected query")
    if query_payload.get("query_source") != "revision_llm_query_plan":
        raise AssertionError("L2 revision query frame source is wrong")
    if query_payload.get("query_mode") != "embedding_search":
        raise AssertionError("L2 revision query frame mode is wrong")
    if query_payload.get("target_tool_name") != "search_docs":
        raise AssertionError("L2 revision query frame target tool is wrong")
    source_data_ids = query_payload.get("source_data_ids")
    if not isinstance(source_data_ids, list) or plan_id not in source_data_ids:
        raise AssertionError("L2 revision query frame must cite revision query plan")
    if revision_input_id not in source_data_ids:
        raise AssertionError("L2 revision query frame must preserve revision input source")

    return {
        "query_source": query_payload.get("query_source"),
        "target_tool_name": query_payload.get("target_tool_name"),
    }


def _run_l2_revision_tool_attempt_smoke() -> dict[str, object]:
    """Revision query frame should run one document tool and record budget."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_revision_tool_attempt"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:revision_tool_attempt_smoke",
        schema_status="not_checked",
    )
    zero_state = ZeroState(current_turn_trace_ids=[user_event.event_id])

    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l1",
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": turn_id,
            "macro_goal": "document memory index",
            "macro_goal_reason": "LLM_TEST_MACRO_REASON",
            "micro_goal": "revise_search_scope",
            "micro_goal_reason": "LLM_TEST_MICRO_REASON",
            "goal_source": "llm_l_route",
            "target_loop": "L",
            "goal_generation_source": "LLM:test",
            "llm_goal_judgement_status": "ran",
            "source_trace_ids": [user_event.event_id],
            "source_data_ids": [],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": turn_id,
            "query_text": "first structured search",
            "query_source": "llm_query_plan",
            "query_mode": "embedding_search",
            "target_tool_name": "search_docs",
            "source_trace_ids": ["trace_l1"],
            "source_data_ids": ["L1:goal_frame"],
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": turn_id,
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "reason": "COPIED_TEST_REASON",
            "macro_achievement_reason": "COPIED_MACRO_REASON",
            "micro_achievement_reason": "COPIED_MICRO_REASON",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    data_store.create_record(
        data_id="tool_budget:turn_revision_tool_attempt:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "budget_id": "tool_budget:turn_revision_tool_attempt:0001",
            "turn_id": turn_id,
            "loop_id": "L",
            "sequence_index": 1,
            "max_tool_calls": 3,
            "search_top_k": 1,
            "max_query_attempts": 3,
            "max_query_candidates": 3,
            "max_read_doc_calls": 2,
            "max_input_chars": 6000,
            "tool_call_count": 1,
            "query_count": 1,
            "read_doc_count": 1,
            "input_chars_used": 100,
            "executed_queries": ["first structured search"],
            "read_doc_ids": ["ORDER_001.md"],
            "cache_statuses": [],
            "duplicate_query_count": 0,
            "duplicate_doc_count": 0,
            "stop_reason": "within_budget",
            "reason": "CODE_STATUS:previous_attempt_budget",
            "condition_flags": ["within_budget"],
            "source_trace_ids": ["trace_l2"],
            "source_data_ids": ["L2:query_frame"],
        },
    )
    _, continuation_frame_id, _ = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        max_attempts=3,
        source_trace_ids=[user_event.event_id],
    )
    record_l3_continuation_summary_for_l2(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        continuation_frame_id=continuation_frame_id,
        input_ref=[user_event.event_id],
    )
    _, revision_input_id, _ = record_l2_revision_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        continuation_frame_id=continuation_frame_id,
    )
    run_l2_revision_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_input_data_id=revision_input_id,
        adapter=RevisionQueryPlannerFakeLLMAdapter(),
    )
    plan_id = l2_revision_query_plan_data_id(1)
    run_l2_revision_query_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_query_plan_data_id=plan_id,
    )
    query_frame_id = l2_revision_query_frame_data_id(1)
    result = run_l_loop_revision_tool_attempt(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_query_frame_data_id=query_frame_id,
        search_top_k=1,
        max_tool_calls=3,
        max_query_attempts=3,
        max_read_doc_calls=2,
        max_input_chars=6000,
    )

    if result.tool_name != "search_docs":
        raise AssertionError("revision tool attempt smoke should run search_docs")
    if not result.tool_choice_data_id.startswith("tool_choice:L2_revision_0001:"):
        raise AssertionError("revision tool attempt did not record L2 revision tool choice")
    tool_result_payload = data_store.require_record(result.tool_result_data_id).payload
    if not isinstance(tool_result_payload, dict):
        raise AssertionError("revision tool attempt result payload must be a dict")
    if tool_result_payload.get("result_count") != 1:
        raise AssertionError("revision search_docs should respect search_top_k=1")
    distillation_payload = data_store.require_record(result.tool_distillation_data_id).payload
    if not isinstance(distillation_payload, dict):
        raise AssertionError("revision tool attempt distillation payload must be a dict")
    if distillation_payload.get("tool_name") != "search_docs":
        raise AssertionError("revision tool attempt distillation should preserve tool name")
    budget_payload = data_store.require_record(result.tool_budget_data_id).payload
    if not isinstance(budget_payload, dict):
        raise AssertionError("revision tool attempt budget payload must be a dict")
    if budget_payload.get("sequence_index") != 2:
        raise AssertionError("revision tool attempt budget should continue sequence index")
    if budget_payload.get("tool_call_count") != 2:
        raise AssertionError("revision tool attempt budget should increment tool calls")
    if budget_payload.get("query_count") != 2:
        raise AssertionError("revision tool attempt budget should increment query count")
    if budget_payload.get("stop_reason") != "completed":
        raise AssertionError("revision tool attempt should complete when search returns results")
    source_data_ids = budget_payload.get("source_data_ids")
    if not isinstance(source_data_ids, list) or query_frame_id not in source_data_ids:
        raise AssertionError("revision tool attempt budget must cite revision query frame")

    return {
        "tool_name": result.tool_name,
        "budget_stop_reason": budget_payload.get("stop_reason"),
    }


def _run_l3_revision_recheck_smoke() -> dict[str, object]:
    """Revision tool output should be re-packaged into attempt-scoped L3 frames."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_l3_revision_recheck"
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:l3_revision_recheck_smoke",
        schema_status="not_checked",
    )
    zero_state = ZeroState(current_turn_trace_ids=[user_event.event_id])

    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l1",
        payload={
            "frame_id": "L1:goal_frame",
            "turn_id": turn_id,
            "macro_goal": "document memory index",
            "macro_goal_reason": "LLM_TEST_MACRO_REASON",
            "micro_goal": "revise_search_scope",
            "micro_goal_reason": "LLM_TEST_MICRO_REASON",
            "goal_source": "llm_l_route",
            "target_loop": "L",
            "goal_generation_source": "LLM:test",
            "llm_goal_judgement_status": "ran",
            "source_trace_ids": [user_event.event_id],
            "source_data_ids": [],
        },
    )
    data_store.create_record(
        data_id="L2:query_frame",
        data_type="node_output:L2_query_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l2",
        payload={
            "frame_id": "L2:query_frame",
            "turn_id": turn_id,
            "query_text": "first structured search",
            "query_source": "llm_query_plan",
            "query_mode": "embedding_search",
            "target_tool_name": "search_docs",
            "source_trace_ids": ["trace_l1"],
            "source_data_ids": ["L1:goal_frame"],
        },
    )
    data_store.create_record(
        data_id="L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
        exists=True,
        created_at=None,
        source_trace_id="trace_l3",
        payload={
            "frame_id": "L3:achievement_frame",
            "turn_id": turn_id,
            "achievement_status": "partial",
            "goal_match_status": "partial",
            "semantic_goal_match_status": "not_run",
            "reason": "COPIED_TEST_REASON",
            "macro_achievement_reason": "COPIED_MACRO_REASON",
            "micro_achievement_reason": "COPIED_MICRO_REASON",
            "read_doc_ids": ["ORDER_001.md"],
            "search_result_doc_ids": ["ORDER_001.md", "ORDER_002.md"],
        },
    )
    data_store.create_record(
        data_id="tool_budget:turn_l3_revision_recheck:0001",
        data_type="tool_use_budget",
        exists=True,
        created_at=None,
        source_trace_id="trace_budget",
        payload={
            "budget_id": "tool_budget:turn_l3_revision_recheck:0001",
            "turn_id": turn_id,
            "loop_id": "L",
            "sequence_index": 1,
            "max_tool_calls": 3,
            "search_top_k": 1,
            "max_query_attempts": 3,
            "max_query_candidates": 3,
            "max_read_doc_calls": 2,
            "max_input_chars": 6000,
            "tool_call_count": 1,
            "query_count": 1,
            "read_doc_count": 1,
            "input_chars_used": 100,
            "executed_queries": ["first structured search"],
            "read_doc_ids": ["ORDER_001.md"],
            "cache_statuses": [],
            "duplicate_query_count": 0,
            "duplicate_doc_count": 0,
            "stop_reason": "within_budget",
            "reason": "CODE_STATUS:previous_attempt_budget",
            "condition_flags": ["within_budget"],
            "source_trace_ids": ["trace_l2"],
            "source_data_ids": ["L2:query_frame"],
        },
    )
    _, continuation_frame_id, _ = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        max_attempts=3,
        source_trace_ids=[user_event.event_id],
    )
    record_l3_continuation_summary_for_l2(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        continuation_frame_id=continuation_frame_id,
        input_ref=[user_event.event_id],
    )
    _, revision_input_id, _ = record_l2_revision_input_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        continuation_frame_id=continuation_frame_id,
    )
    run_l2_revision_query_planner(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_input_data_id=revision_input_id,
        adapter=RevisionQueryPlannerFakeLLMAdapter(),
    )
    plan_id = l2_revision_query_plan_data_id(1)
    run_l2_revision_query_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_query_plan_data_id=plan_id,
    )
    query_frame_id = l2_revision_query_frame_data_id(1)
    revision_tool_result = run_l_loop_revision_tool_attempt(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        revision_query_frame_data_id=query_frame_id,
        search_top_k=1,
        max_tool_calls=3,
        max_query_attempts=3,
        max_read_doc_calls=2,
        max_input_chars=6000,
    )
    l3_event = run_l3_revision_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=1,
        revision_query_frame_data_id=query_frame_id,
        revision_tool_source_trace_ids=revision_tool_result.source_trace_ids,
        revision_tool_source_data_ids=revision_tool_result.source_data_ids,
        user_query="문서 메모리 인덱스를 근거로 설명해줘",
    )
    achievement_id = l3_revision_achievement_frame_data_id(1)
    preserved_id = l3_revision_preserved_frame_data_id(1)
    achievement_payload = data_store.require_record(achievement_id).payload
    preserved_payload = data_store.require_record(preserved_id).payload
    if not isinstance(achievement_payload, dict) or not isinstance(preserved_payload, dict):
        raise AssertionError("L3 revision recheck payloads must be dicts")
    if achievement_payload.get("preserved_info_frame_id") != preserved_id:
        raise AssertionError("L3 revision achievement must cite its attempt-scoped preserved frame")
    if achievement_payload.get("achievement_generation_source") != "CODE:OPERATION_CHECK":
        raise AssertionError("L3 revision recheck must reveal code-only operation checking")
    if achievement_payload.get("llm_semantic_judgement_status") != "not_run":
        raise AssertionError("L3 revision recheck must not pretend semantic LLM judgement ran")
    candidate_count = achievement_payload.get("candidate_count")
    if not isinstance(candidate_count, int) or candidate_count < 1:
        raise AssertionError("L3 revision recheck must preserve candidates from the revision tool result")
    if achievement_payload.get("achievement_status") != "partial":
        raise AssertionError("L3 revision recheck should remain partial before a new controller success")
    achievement_sources = achievement_payload.get("source_data_ids")
    if not isinstance(achievement_sources, list) or revision_tool_result.tool_distillation_data_id not in achievement_sources:
        raise AssertionError("L3 revision recheck must cite the revision tool distillation")

    _, second_continuation_id, second_continuation = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        attempt_index=2,
        max_attempts=3,
        source_trace_ids=[l3_event.event_id],
        source_data_ids=[
            achievement_id,
            query_frame_id,
            revision_tool_result.tool_budget_data_id,
        ],
        l3_achievement_data_id=achievement_id,
        l2_query_frame_data_id=query_frame_id,
    )
    continuation_payload = data_store.require_record(second_continuation_id).payload
    if not isinstance(continuation_payload, dict):
        raise AssertionError("L3 revision continuation payload must be a dict")
    if continuation_payload.get("source_l3_achievement_id") != achievement_id:
        raise AssertionError("second continuation must read the attempt-scoped L3 achievement")
    if continuation_payload.get("source_l2_query_frame_id") != query_frame_id:
        raise AssertionError("second continuation must read the revision query frame")
    if second_continuation.continuation_status != "continue":
        raise AssertionError("partial revision recheck with budget remaining should continue")

    return {
        "achievement_status": achievement_payload.get("achievement_status"),
        "candidate_count": candidate_count,
        "continuation_status": second_continuation.continuation_status,
    }


def _run_live_l_loop_continuation_smoke() -> dict[str, object]:
    """A partial L3 judgement in the live L loop should trigger one revision pass."""

    adapter = SongRyeonAllNodesFakeLLMAdapter()
    result = run_dry_turn(
        user_input="내부 문서에서 특정 근거를 찾고 부족하면 다시 검색해줘",
        node_1_router_adapter=adapter,
        l1_goal_adapter=None,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=SemanticMismatchL3FakeAdapter(),
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
        max_tool_calls=3,
        max_query_attempts=3,
        max_read_doc_calls=1,
        force_l_route=True,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    continuation_frames = [
        item
        for item in result["data_records"]
        if isinstance(item, dict) and item.get("data_type") == "node_output:L_loop_continuation_frame"
    ]
    revision_query_frames = [
        item
        for item in result["data_records"]
        if isinstance(item, dict) and item.get("data_type") == "node_output:L2_revision_query_frame"
    ]
    if result.get("l_loop_continuation_count", 0) < 2:
        raise AssertionError("live L loop should record initial and post-revision continuation frames")
    if result.get("l_loop_revision_query_count") != 1:
        raise AssertionError("live L loop should run exactly one revision query in this budget smoke")
    if "L2:revision_query_frame:0001" not in records:
        raise AssertionError("live L loop did not record revision query frame")
    if "L3:revision_achievement:0001" not in records:
        raise AssertionError("live L loop did not record revision L3 achievement frame")
    first_continuation = continuation_frames[0].get("payload")
    last_continuation = continuation_frames[-1].get("payload")
    if not isinstance(first_continuation, dict) or first_continuation.get("continuation_status") != "continue":
        raise AssertionError("first live continuation should continue after partial L3")
    if not isinstance(last_continuation, dict) or last_continuation.get("continuation_status") != "stop_budget_exhausted":
        raise AssertionError("live continuation should stop when the smoke budget is exhausted")
    if not revision_query_frames:
        raise AssertionError("live L loop revision query frame list is empty")

    return {
        "continuation_count": result.get("l_loop_continuation_count"),
        "revision_query_count": result.get("l_loop_revision_query_count"),
        "final_continuation_status": result.get("l_loop_final_continuation_status"),
    }


def _run_node4_remand_blocking_smoke() -> dict[str, object]:
    """node_4가 반려한 보고문이 사용자-facing answer로 그대로 나가지 않는지 확인한다."""

    adapter = RemandFakeLLMAdapter()
    result = run_dry_turn(
        user_input="node_4 반려 차단 smoke",
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    gate = records.get("node_4:gatekeeper_frame")
    if not isinstance(gate, dict):
        raise AssertionError("node_4 gatekeeper frame was not recorded")
    if gate.get("gate_status") != "needs_revision":
        raise AssertionError("remand smoke should produce needs_revision")

    rendered = render_pretty_turn(result, user_input="node_4 반려 차단 smoke")
    answer = rendered.split("[answer]", 1)[1] if "[answer]" in rendered else rendered
    if "FINAL_BLOCKED_BY_GATEKEEPER" not in answer:
        raise AssertionError("node_4 remand was not reflected in final answer")
    if "UNSUPPORTED_SECRET_CLAIM_SENTINEL" in answer:
        raise AssertionError("blocked node_3 report leaked into final answer")
    if "방금 생성된 답변이 최종 검사에서 반려됐어." not in answer:
        raise AssertionError("safe blocking answer is missing")

    return {
        "blocked": True,
        "gate_status": gate.get("gate_status"),
    }


def _run_node4_grounding_count_guard_smoke() -> dict[str, object]:
    """node_3 count는 code grounding block으로 고정되고 node_4 guard는 유지된다."""

    adapter = CountMismatchReporterFakeAdapter()
    result = run_dry_turn(
        user_input="여러 문서를 읽고 연관점을 파악해줘",
        force_l_route=True,
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=adapter,
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    gate = records.get("node_4:gatekeeper_frame")
    if not isinstance(gate, dict):
        raise AssertionError("node_4 count guard smoke did not record gatekeeper frame")
    if gate.get("gate_status") != "pass":
        raise AssertionError("code-generated grounding block should prevent count mismatch remand")
    reason = str(gate.get("reason") or "")
    if "grounding_count_mismatch" in reason:
        raise AssertionError("code-generated grounding block should not trigger count mismatch")
    contradictions = gate.get("contradictions")
    if not isinstance(contradictions, list) or contradictions:
        raise AssertionError("code-generated grounding block should leave no count contradictions")
    report = records.get("report_dry_001")
    if not isinstance(report, dict):
        raise AssertionError("node_3 report frame missing")
    rendered_markdown = str(report.get("rendered_markdown") or "")
    brief = records.get("node_3:input_brief_frame")
    if not isinstance(brief, dict):
        raise AssertionError("node3 brief missing")
    expected_doc_count = len(brief.get("read_documents") or [])
    expected_search_count = brief.get("search_candidate_count")
    expected_runtime_count = len(brief.get("runtime_tasks") or [])
    expected_lines = [
        "근거 기준:",
        f"- 읽은 문서: {expected_doc_count}개",
        f"- 검색 후보 문서: {expected_search_count}개",
        f"- 현재 턴 실행 순서 자료: {expected_runtime_count}개",
    ]
    for line in expected_lines:
        if line not in rendered_markdown:
            raise AssertionError(f"code grounding block missing expected line: {line}")
    if "- 읽은 문서: 0개" in rendered_markdown and expected_doc_count != 0:
        raise AssertionError("legacy LLM grounding count leaked into final report")
    answer = render_pretty_turn(result, user_input="count guard smoke")
    if "FINAL_BLOCKED_BY_GATEKEEPER" in answer:
        raise AssertionError("code-generated grounding block should avoid final answer blocking")
    return {"gate_status": gate.get("gate_status")}


def _run_node4_gate_failed_honesty_smoke() -> dict[str, object]:
    """node_4 호출 실패를 내용 반려처럼 말하지 않고 검사 실패로 표시하는지 확인한다."""

    adapter = SongRyeonAllNodesFakeLLMAdapter()
    result = run_dry_turn(
        user_input="node_4 failed honesty smoke",
        node_1_router_adapter=adapter,
        l1_goal_adapter=adapter,
        l2_query_planner_adapter=adapter,
        l3_result_adapter=adapter,
        node_2_boundary_adapter=adapter,
        node_3_reporter_adapter=adapter,
        node_4_gatekeeper_adapter=BrokenJSONFakeLLMAdapter(),
    )
    records = {item["data_id"]: item["payload"] for item in result["data_records"]}
    gate = records.get("node_4:gatekeeper_frame")
    if not isinstance(gate, dict):
        raise AssertionError("node_4 gate failure smoke did not record gatekeeper frame")
    if gate.get("gate_status") != "failed":
        raise AssertionError("node_4 gate failure smoke should produce failed gate_status")

    rendered = render_pretty_turn(result, user_input="node_4 failed honesty smoke")
    answer = rendered.split("[answer]", 1)[1] if "[answer]" in rendered else rendered
    if "최종 검사 자체가 실패" not in answer:
        raise AssertionError("node_4 failed gate answer must say the inspection failed")
    if "근거 밖 주장, 모순" in answer:
        raise AssertionError("node_4 failed gate answer must not look like a content remand")

    return {"honest_failure_message": True}


class RemandFakeLLMAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """node_3 문제 보고문과 node_4 반려를 함께 재현하는 smoke 전용 adapter."""

    model_id = "remand-fake-llm-adapter"

    def _node_3_payload(self, request) -> dict[str, object]:
        return {
            "rendered_markdown": (
                "UNSUPPORTED_SECRET_CLAIM_SENTINEL: 이 문장은 node_4가 반려해야 하는 "
                "근거 밖 주장이다."
            )
        }

    def _node_4_payload(self) -> dict[str, object]:
        return {
            "gate_status": "needs_revision",
            "reason": "report contains unsupported sentinel claim",
            "checked_claims": ["UNSUPPORTED_SECRET_CLAIM_SENTINEL"],
            "unsupported_claims": ["UNSUPPORTED_SECRET_CLAIM_SENTINEL"],
            "contradictions": [],
            "revision_targets": ["remove unsupported claim"],
        }


class SameTurnLRerouteFakeAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """same-turn L reroute controller smoke adapter."""

    model_id = "same-turn-l-reroute-fake-adapter"

    def _node_1_payload(self, request) -> dict[str, object]:
        route = "L"
        return {
            "route": route,
            "route_reason": "same-turn L reroute smoke intentionally keeps requesting L.",
            "expected_next_0_mode": "targeted_memory_supply",
            "route_confidence": 0.91,
            "needs_more_memory": False,
            "policy_flag": "same_turn_l_reroute_smoke",
        }


class SemanticMismatchL3FakeAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """L3 semantic goal guard smoke adapter."""

    model_id = "semantic-mismatch-l3-fake-adapter"

    def _l3_payload(self, request) -> dict[str, object]:
        payload = super()._l3_payload(request)
        payload.update(
            {
                "achievement_status": "achieved",
                "macro_achievement_status": "achieved",
                "micro_achievement_status": "achieved",
                "semantic_goal_match_status": "partial",
                "semantic_goal_match_reason": (
                    "The supplied read document evidence is only partially aligned with the user's actual goal."
                ),
            }
        )
        return payload


class LowToolCallBudgetFakeAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """read_doc 예산보다 총 tool call 예산을 낮게 요청하는 budget consistency smoke adapter."""

    model_id = "low-tool-call-budget-fake-adapter"

    def _l1_payload(self) -> dict[str, object]:
        payload = super()._l1_payload()
        payload.update(
            {
                "requested_search_top_k": 3,
                "requested_max_tool_calls": 2,
                "requested_max_read_doc_calls": 2,
                "requested_max_query_attempts": 1,
                "budget_request_reason": (
                    "문서 2개 열람을 요청하지만 총 tool_calls를 낮게 둔 예산 정합성 smoke."
                ),
            }
        )
        return payload


class RequirementOnlyMultiDocFakeAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """숫자 예산은 빠졌지만 구조화 근거 요구사항은 다문서라고 선언하는 smoke adapter."""

    model_id = "requirement-only-multi-doc-fake-adapter"

    def _l1_payload(self) -> dict[str, object]:
        payload = super()._l1_payload()
        payload.update(
            {
                "evidence_requirement_kind": "multi_doc_relationship",
                "minimum_read_documents": 2,
                "requires_cross_document_analysis": True,
                "randomness_mode": "semantic_exploration",
                "l_loop_success_condition": (
                    "최소 2개 이상의 읽은 문서 추출본이 있어야 문서 간 연관점 분석을 시도할 수 있다."
                ),
                "requested_search_top_k": 0,
                "requested_max_tool_calls": 1,
                "requested_max_read_doc_calls": 0,
                "requested_max_query_attempts": 1,
                "budget_request_reason": (
                    "의도적으로 숫자 read_doc 요청을 빠뜨리고 구조화 요구사항만 제공한다."
                ),
            }
        )
        return payload


class CountMismatchReporterFakeAdapter(SongRyeonAllNodesFakeLLMAdapter):
    """옛 node_3처럼 틀린 grounding count를 내는 smoke 전용 adapter."""

    model_id = "count-mismatch-reporter-fake-adapter"

    def _node_3_payload(self, request) -> dict[str, object]:
        return {
            "rendered_markdown": (
                "근거 기준:\n"
                "- 읽은 문서: 0개\n"
                "- 검색 후보 문서: 0개\n"
                "- 현재 턴 실행 순서 자료: 0개\n"
                "- 답변 한계: 일부러 brief count와 맞지 않는 smoke 보고문이다.\n\n"
                "이 본문은 LLM이 틀린 count 블록을 포함해도 code assembly가 제거해야 하는 smoke 본문이다."
            )
        }

    def _node_4_payload(self) -> dict[str, object]:
        return {
            "gate_status": "pass",
            "reason": "fake node_4 would pass unless code guard overrides it",
            "checked_claims": [],
            "unsupported_claims": [],
            "contradictions": [],
            "revision_targets": [],
        }


def _has_l2_query_plan_mixed_info(boundary_payload: dict[str, object]) -> bool:
    """boundary 안에 L2 query plan purpose 혼합 정보가 있는지 확인한다."""

    mixed_info = boundary_payload.get("mixed_info")
    if not isinstance(mixed_info, list):
        return False
    for item in mixed_info:
        if not isinstance(item, dict):
            continue
        if item.get("info_kind") != "l2_query_candidate_purpose":
            continue
        if item.get("source_data_id") != "L2:query_plan_frame":
            continue
        field_path = item.get("field_path")
        if not isinstance(field_path, str) or not field_path.startswith("candidates["):
            continue
        _assert_mixed_info_has_evidence(item)
        return True
    return False


def _selected_query_from_payload(plan_payload: dict[str, object]) -> str:
    selected_candidate_id = plan_payload.get("selected_candidate_id")
    candidates = plan_payload.get("candidates")
    if not isinstance(selected_candidate_id, str) or not isinstance(candidates, list):
        raise AssertionError("invalid L2 query plan payload")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("candidate_id") == selected_candidate_id:
            query_text = candidate.get("query_text")
            if isinstance(query_text, str):
                return query_text
    raise AssertionError("selected L2 query candidate not found")


def _single_id_with_prefix(records: dict[str, object], prefix: str) -> str:
    matches = sorted(data_id for data_id in records if data_id.startswith(prefix))
    if len(matches) != 1:
        raise AssertionError(f"expected one record with prefix {prefix}, got {matches}")
    return matches[0]
