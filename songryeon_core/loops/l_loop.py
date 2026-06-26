from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.failure_signal_store import record_failure_signal
from songryeon_core.core.schemas import (
    LLoopControlFrame,
    LLoopRunFrame,
    MemoryPacketFrom0,
    ZeroState,
    validate_l_loop_control_frame,
    validate_l_loop_run_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.loops.l_loop_budget import (
    record_l_loop_budget_plan,
)
from songryeon_core.loops.l_loop_continuation import record_l_loop_continuation_decision
from songryeon_core.loops.l_loop_namespace import (
    L_REROUTE_PLANNED_NEXT_STEP,
    L_REROUTE_REMAINING_BLOCK_REASON,
    LRunIds,
    build_l_run_ids,
)
from songryeon_core.runtime.same_turn_l_reroute import (
    SAME_TURN_L_REROUTE_ALLOWED_REASON,
    SAME_TURN_L_REROUTE_ENABLED_STEP,
)
from songryeon_core.loops.l_loop_revision_tool_attempt import run_l_loop_revision_tool_attempt
from songryeon_core.nodes.l1_goal_setter import run_l1_goal_setter
from songryeon_core.nodes.l2_revision_input import record_l2_revision_input_frame
from songryeon_core.nodes.l2_query_setter import (
    l2_revision_query_frame_data_id,
    l2_revision_query_plan_data_id,
    run_l2_query_planner,
    run_l2_query_setter,
    run_l2_revision_query_planner,
    run_l2_revision_query_setter,
    selected_query_from_plan,
    selected_target_tool_from_plan,
)
from songryeon_core.nodes.l3_result_keeper import (
    l3_revision_achievement_frame_data_id,
    l3_revision_preserved_frame_data_id,
    run_l3_result_keeper,
    run_l3_revision_result_keeper,
)
from songryeon_core.nodes.node_0_memory_supplier import (
    record_l3_continuation_summary_for_l2,
)
from songryeon_core.tools.tool_runner import (
    ToolRunResult,
    ToolRunner,
    build_document_tool_registry,
    record_tool_catalog,
    record_tool_choice,
    tool_catalog_data_id,
    tool_choice_data_id,
)
from songryeon_core.tools.tool_efficiency_policy import (
    cache_status_from_search_payload,
    distilled_input_size,
    make_cache_status_record,
    record_duplicate_tool_use_signal,
    record_tool_use_budget_frame,
)
from songryeon_core.tools.tool_result_distiller import record_tool_result_distillation


@dataclass
class LLoopResult:
    """L루프 드라이런 결과의 절대정보 중심 뼈대."""

    loop_id: str
    turn_id: str
    run_trace_id: str
    l1_trace_id: str
    l2_trace_id: str
    l3_trace_id: str
    run_data_ids: list[str] = field(default_factory=list)
    l2_plan_trace_ids: list[str] = field(default_factory=list)
    budget_plan_trace_ids: list[str] = field(default_factory=list)
    control_trace_ids: list[str] = field(default_factory=list)
    tool_trace_ids: list[str] = field(default_factory=list)
    budget_trace_ids: list[str] = field(default_factory=list)
    continuation_trace_ids: list[str] = field(default_factory=list)
    revision_trace_ids: list[str] = field(default_factory=list)
    failure_trace_ids: list[str] = field(default_factory=list)
    goal_data_ids: list[str] = field(default_factory=list)
    budget_plan_data_ids: list[str] = field(default_factory=list)
    tool_catalog_data_ids: list[str] = field(default_factory=list)
    tool_choice_data_ids: list[str] = field(default_factory=list)
    query_plan_data_ids: list[str] = field(default_factory=list)
    query_data_ids: list[str] = field(default_factory=list)
    control_data_ids: list[str] = field(default_factory=list)
    tool_result_data_ids: list[str] = field(default_factory=list)
    tool_distillation_data_ids: list[str] = field(default_factory=list)
    tool_budget_data_ids: list[str] = field(default_factory=list)
    continuation_data_ids: list[str] = field(default_factory=list)
    revision_input_data_ids: list[str] = field(default_factory=list)
    revision_query_plan_data_ids: list[str] = field(default_factory=list)
    revision_query_data_ids: list[str] = field(default_factory=list)
    failure_signal_data_ids: list[str] = field(default_factory=list)
    preserved_data_ids: list[str] = field(default_factory=list)
    achievement_data_ids: list[str] = field(default_factory=list)
    output_data_ids: list[str] = field(default_factory=list)
    source_trace_ids: list[str] = field(default_factory=list)
    final_control_data_id: str | None = None
    final_control_decision: str | None = None
    final_continuation_data_id: str | None = None
    final_continuation_status: str | None = None


def run_l_loop(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    memory_packet: MemoryPacketFrom0,
    search_query: str,
    memory_packet_data_ids: list[str] | None = None,
    zero_state: ZeroState | None = None,
    document_root: str | Path = "Administrative_Reform_1",
    l1_goal_adapter: LLMAdapter | None = None,
    l2_query_planner_adapter: LLMAdapter | None = None,
    l3_result_adapter: LLMAdapter | None = None,
    max_iterations: int = 3,
    max_tool_calls: int = 5,
    max_query_attempts: int = 3,
    search_top_k: int = 3,
    max_query_candidates: int | None = None,
    max_read_doc_calls: int = 1,
    max_input_chars: int = 6000,
    run_index: int = 1,
    same_turn_rerun_allowed: bool = False,
    rerun_block_reason: str = L_REROUTE_REMAINING_BLOCK_REASON,
    planned_next_step: str = L_REROUTE_PLANNED_NEXT_STEP,
) -> LLoopResult:
    """L1/L2/controller/tools/L3를 budget 안에서 실행한다."""

    continuation_zero_state = zero_state or ZeroState()

    if max_query_candidates is not None:
        max_query_attempts = max_query_candidates
    if max_iterations < 2:
        raise ValueError("max_iterations must be at least 2")
    if max_tool_calls < 1:
        raise ValueError("max_tool_calls must be at least 1")
    if max_query_attempts < 1:
        raise ValueError("max_query_attempts must be at least 1")
    if search_top_k < 1:
        raise ValueError("search_top_k must be at least 1")
    if max_read_doc_calls < 1:
        raise ValueError("max_read_doc_calls must be at least 1")
    if max_input_chars < 1:
        raise ValueError("max_input_chars must be at least 1")

    # L루프 전체 실행 단위의 ID 묶음이다.
    # run_index=1은 기존 고정 ID를 유지한다.
    # run_index>=2는 L 내부 주요 record 앞에 L:run:0002 같은 이름표를 붙인다.
    run_ids = build_l_run_ids(run_index=run_index)
    l1_goal_data_id = run_ids.l1_goal_data_id
    l2_query_plan_data_id = run_ids.l2_query_plan_data_id
    l2_query_data_id = run_ids.l2_query_data_id
    l3_preserved_data_id = run_ids.l3_preserved_data_id
    l3_achievement_data_id = run_ids.l3_achievement_data_id

    if same_turn_rerun_allowed:
        rerun_block_reason = SAME_TURN_L_REROUTE_ALLOWED_REASON
        planned_next_step = SAME_TURN_L_REROUTE_ENABLED_STEP

    run_trace_id, run_data_id = _record_l_loop_run_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        run_ids=run_ids,
        input_ref=memory_packet.trace_evidence_ids,
        source_data_ids=memory_packet_data_ids or [],
        same_turn_rerun_allowed=same_turn_rerun_allowed,
        rerun_block_reason=rerun_block_reason,
        planned_next_step=planned_next_step,
    )

    l1 = run_l1_goal_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        memory_packet=memory_packet,
        user_query=search_query,
        source_data_ids=memory_packet_data_ids or [],
        adapter=l1_goal_adapter,
        goal_frame_data_id=l1_goal_data_id,
    )
    budget_plan_trace_id, budget_plan_data_id, budget_plan_frame = record_l_loop_budget_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        l1_event=l1,
        goal_data_id=l1_goal_data_id,
        base_search_top_k=search_top_k,
        base_max_tool_calls=max_tool_calls,
        base_max_read_doc_calls=max_read_doc_calls,
        base_max_query_attempts=max_query_attempts,
        budget_plan_data_id=run_ids.budget_plan_data_id,
    )
    search_top_k = budget_plan_frame.approved_search_top_k
    max_tool_calls = budget_plan_frame.approved_max_tool_calls
    max_read_doc_calls = budget_plan_frame.approved_max_read_doc_calls
    max_query_attempts = budget_plan_frame.approved_max_query_attempts
    # 장기 과제: 지금은 read_doc 예산이 늘면 controller 반복 횟수도 v0 정책으로 같이 늘린다.
    # 나중에는 이것을 숨은 보정이 아니라 명시적인 controller-step 예산 필드로 승격해야 한다.
    max_iterations = max(max_iterations, max_read_doc_calls + 2)
    budget_plan_trace_ids = [budget_plan_trace_id]
    budget_plan_data_ids = [budget_plan_data_id]

    tool_registry = build_document_tool_registry(document_root)
    tool_catalog_trace_id = record_tool_catalog(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        registry=tool_registry,
        input_ref=[l1.event_id, budget_plan_trace_id],
        source_data_ids=[l1_goal_data_id, budget_plan_data_id],
        id_namespace=run_ids,
    )
    catalog_id = tool_catalog_data_id(turn_id, id_namespace=run_ids)
    catalog_record = data_store.require_record(catalog_id)
    catalog_payload = catalog_record.payload
    available_tools = (
        catalog_payload.get("tools")
        if isinstance(catalog_payload, dict) and isinstance(catalog_payload.get("tools"), list)
        else []
    )

    query_text = search_query
    query_source = "user_input_fallback"
    query_source_data_ids = [l1_goal_data_id, budget_plan_data_id]
    query_extra_trace_ids: list[str] = []
    query_plan_data_ids: list[str] = []
    l2_plan_trace_ids: list[str] = []
    selected_tool_name = "search_docs"
    if l2_query_planner_adapter is not None:
        try:
            plan_event = run_l2_query_planner(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                l1_event=l1,
                user_input=search_query,
                adapter=l2_query_planner_adapter,
                source_data_ids=[l1_goal_data_id, budget_plan_data_id, catalog_id],
                available_tools=available_tools,
                query_plan_frame_data_id=l2_query_plan_data_id,
            )
            plan_record = data_store.require_record(l2_query_plan_data_id)
            query_text = selected_query_from_plan(plan_record.payload)
            selected_tool_name = selected_target_tool_from_plan(plan_record.payload)
            query_source = "llm_query_plan"
            query_source_data_ids = [
                l1_goal_data_id,
                budget_plan_data_id,
                catalog_id,
                l2_query_plan_data_id,
            ]
            query_extra_trace_ids = [plan_event.event_id]
            query_plan_data_ids = [l2_query_plan_data_id]
            l2_plan_trace_ids = [plan_event.event_id]
        except Exception:
            # LLM query plan 실패 시 기존 사용자 입력 fallback 검색을 유지한다.
            query_text = search_query
            query_source = "user_input_fallback"

    l2 = run_l2_query_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        l1_event=l1,
        query_text=query_text,
        query_source=query_source,
        target_tool_name=selected_tool_name,
        source_data_ids=query_source_data_ids,
        extra_input_trace_ids=query_extra_trace_ids,
        query_frame_data_id=l2_query_data_id,
    )
    tool_choice_trace_id = record_tool_choice(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        registry=tool_registry,
        chooser_node_id="L2",
        tool_name=selected_tool_name,
        catalog_id=catalog_id,
        reason=f"CODE_STATUS:l2_query_frame_targets_{selected_tool_name}",
        expected_use="CODE_STATUS:run_selected_query_or_artifact_ref",
        tool_choice_policy_id="l2_query_frame_target_tool",
        expected_effect_label=f"CODE_STATUS:{selected_tool_name}_execution",
        input_ref=[tool_catalog_trace_id, l2.event_id],
        source_data_ids=[l2_query_data_id, budget_plan_data_id],
        id_namespace=run_ids,
    )
    tool_choice_ids = [
        tool_choice_data_id("L2", selected_tool_name, id_namespace=run_ids)
    ]
    tool_choice_trace_ids = [tool_choice_trace_id]

    l2_query_frame = data_store.require_record(l2_query_data_id)
    query_text = _read_query_text_from_l2_frame(l2_query_frame.payload)
    tool_runner = ToolRunner(tool_registry)

    control_trace_ids: list[str] = []
    control_data_ids: list[str] = []
    tool_call_trace_ids: list[str] = []
    distillation_trace_ids: list[str] = []
    budget_trace_ids: list[str] = []
    tool_result_data_ids: list[str] = []
    tool_distillation_data_ids: list[str] = []
    tool_budget_data_ids: list[str] = []
    failure_trace_ids: list[str] = []
    failure_signal_data_ids: list[str] = []
    used_queries: set[str] = set()
    executed_queries: list[str] = []
    read_doc_ids: set[str] = set()
    read_doc_id_list: list[str] = []
    cache_status_records = []
    current_query = query_text
    tool_call_count = 0
    input_chars_used = 0
    duplicate_query_count = 0
    duplicate_doc_count = 0
    budget_sequence_index = 1
    next_iteration_index = 1
    final_control_data_id: str | None = None
    final_control_decision: str | None = None
    final_continuation_data_id: str | None = None
    final_continuation_status: str | None = None
    continuation_trace_ids: list[str] = []
    continuation_data_ids: list[str] = []
    revision_trace_ids: list[str] = []
    revision_input_data_ids: list[str] = []
    revision_query_plan_data_ids: list[str] = []
    revision_query_data_ids: list[str] = []
    revision_preserved_data_ids: list[str] = []
    revision_achievement_data_ids: list[str] = []
    latest_search_result: ToolRunResult | None = None

    def record_budget(
        *,
        stop_reason: str,
        reason: str,
        condition_flags: list[str] | None = None,
        source_trace_ids: list[str] | None = None,
        source_data_ids: list[str] | None = None,
    ) -> tuple[str, str]:
        nonlocal budget_sequence_index

        event_id, data_id = record_tool_use_budget_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            sequence_index=budget_sequence_index,
            max_tool_calls=max_tool_calls,
            search_top_k=search_top_k,
            max_query_attempts=max_query_attempts,
            max_read_doc_calls=max_read_doc_calls,
            max_input_chars=max_input_chars,
            tool_call_count=tool_call_count,
            executed_queries=executed_queries,
            read_doc_ids=read_doc_id_list,
            cache_statuses=cache_status_records,
            input_chars_used=input_chars_used,
            stop_reason=stop_reason,
            reason=reason,
            condition_flags=condition_flags or [stop_reason],
            source_trace_ids=_unique_strings([budget_plan_trace_id, *(source_trace_ids or [])]),
            source_data_ids=_unique_strings([budget_plan_data_id, *(source_data_ids or [])]),
            duplicate_query_count=duplicate_query_count,
            duplicate_doc_count=duplicate_doc_count,
            id_namespace=run_ids,
        )
        budget_sequence_index += 1
        budget_trace_ids.append(event_id)
        tool_budget_data_ids.append(data_id)
        return event_id, data_id

    record_budget(
        stop_reason="within_budget",
        reason="CODE_STATUS:budget_initialized",
        condition_flags=["budget_initialized", "within_budget"],
        source_trace_ids=[l2.event_id, tool_choice_trace_id],
        source_data_ids=[l2_query_data_id, tool_choice_ids[0]],
    )

    while True:
        if next_iteration_index >= max_iterations:
            budget_trace_id, budget_data_id = record_budget(
                stop_reason="max_tool_calls_reached"
                if tool_call_count >= max_tool_calls
                else "within_budget",
                reason="CODE_STATUS:max_controller_iterations_reached",
                condition_flags=["max_controller_iterations_reached"],
                source_trace_ids=_unique_strings([l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings(
                    [
                        l2_query_data_id,
                        *tool_distillation_data_ids,
                        *tool_budget_data_ids,
                    ]
                ),
            )
            failure_trace_id, failure_id = _record_l_loop_budget_failure(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                source_trace_ids=_unique_strings([budget_trace_id, l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings(
                    [budget_data_id, l2_query_data_id, *tool_distillation_data_ids, *control_data_ids]
                ),
                message="CODE_STATUS:max_controller_iterations_before_stop",
                id_namespace=run_ids,
            )
            failure_trace_ids.append(failure_trace_id)
            failure_signal_data_ids.append(failure_id)
            control_trace_id, control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:max_controller_iterations_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=_unique_strings([failure_trace_id, budget_trace_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings([failure_id, budget_data_id, *tool_distillation_data_ids]),
                failure_signal_id=failure_id,
                id_namespace=run_ids,
            )
            control_trace_ids.append(control_trace_id)
            control_data_ids.append(control_data_id)
            final_control_data_id = control_data_id
            final_control_decision = "stop_failed"
            break

        if tool_call_count >= max_tool_calls:
            budget_trace_id, budget_data_id = record_budget(
                stop_reason="max_tool_calls_reached",
                reason="CODE_STATUS:max_tool_calls_reached",
                condition_flags=["max_tool_calls_reached"],
                source_trace_ids=_unique_strings([l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings(
                    [l2_query_data_id, *tool_distillation_data_ids, *tool_budget_data_ids]
                ),
            )
            failure_trace_id, failure_id = _record_l_loop_budget_failure(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                source_trace_ids=_unique_strings([budget_trace_id, l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings(
                    [budget_data_id, l2_query_data_id, *tool_distillation_data_ids, *control_data_ids]
                ),
                message="CODE_STATUS:max_tool_calls_exhausted",
                id_namespace=run_ids,
            )
            failure_trace_ids.append(failure_trace_id)
            failure_signal_data_ids.append(failure_id)
            control_trace_id, control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:max_tool_calls_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=_unique_strings([failure_trace_id, budget_trace_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings([failure_id, budget_data_id, *tool_distillation_data_ids]),
                failure_signal_id=failure_id,
                id_namespace=run_ids,
            )
            control_trace_ids.append(control_trace_id)
            control_data_ids.append(control_data_id)
            final_control_data_id = control_data_id
            final_control_decision = "stop_failed"
            break

        if current_query in used_queries:
            duplicate_query_count += 1
            duplicate_trace_id, duplicate_id = record_duplicate_tool_use_signal(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                duplicate_kind="query",
                duplicate_value=current_query,
                source_trace_ids=_unique_strings([l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings([l2_query_data_id, *tool_budget_data_ids]),
                id_namespace=run_ids,
            )
            failure_trace_ids.append(duplicate_trace_id)
            failure_signal_data_ids.append(duplicate_id)
            budget_trace_id, budget_data_id = record_budget(
                stop_reason="duplicate_query",
                reason="CODE_STATUS:duplicate_query_before_tool_call",
                condition_flags=["duplicate_query"],
                source_trace_ids=[duplicate_trace_id],
                source_data_ids=[duplicate_id],
            )
            control_trace_id, control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:duplicate_query_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=[duplicate_trace_id, budget_trace_id],
                source_data_ids=[duplicate_id, budget_data_id],
                failure_signal_id=duplicate_id,
                id_namespace=run_ids,
            )
            control_trace_ids.append(control_trace_id)
            control_data_ids.append(control_data_id)
            final_control_data_id = control_data_id
            final_control_decision = "stop_failed"
            break

        if len(executed_queries) >= max_query_attempts:
            budget_trace_id, budget_data_id = record_budget(
                stop_reason="max_query_attempts_reached",
                reason="CODE_STATUS:max_query_attempts_reached",
                condition_flags=["max_query_attempts_reached"],
                source_trace_ids=_unique_strings([l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings([l2_query_data_id, *tool_budget_data_ids]),
            )
            control_trace_id, control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:max_query_attempts_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=[budget_trace_id],
                source_data_ids=[budget_data_id],
                id_namespace=run_ids,
            )
            control_trace_ids.append(control_trace_id)
            control_data_ids.append(control_data_id)
            final_control_data_id = control_data_id
            final_control_decision = "stop_failed"
            break

        if input_chars_used + len(current_query) > max_input_chars:
            budget_trace_id, budget_data_id = record_budget(
                stop_reason="max_input_chars_reached",
                reason="CODE_STATUS:max_input_chars_before_query",
                condition_flags=["max_input_chars_reached"],
                source_trace_ids=_unique_strings([l2.event_id, *tool_call_trace_ids]),
                source_data_ids=_unique_strings([l2_query_data_id, *tool_budget_data_ids]),
            )
            control_trace_id, control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:max_input_chars_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=[budget_trace_id],
                source_data_ids=[budget_data_id],
                id_namespace=run_ids,
            )
            control_trace_ids.append(control_trace_id)
            control_data_ids.append(control_data_id)
            final_control_data_id = control_data_id
            final_control_decision = "stop_failed"
            break

        used_queries.add(current_query)
        executed_queries.append(current_query)
        budget_trace_id, budget_data_id = record_budget(
            stop_reason="within_budget",
            reason="CODE_STATUS:query_budget_checks_passed",
            condition_flags=["within_budget", "query_not_duplicate"],
            source_trace_ids=_unique_strings([l2.event_id, *tool_call_trace_ids]),
            source_data_ids=_unique_strings([l2_query_data_id, *tool_budget_data_ids]),
        )
        control_trace_id, control_data_id = _record_l_loop_control(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            iteration_index=next_iteration_index,
            decision="continue_read_artifact" if selected_tool_name == "read_artifact" else "continue_search",
            reason=(
                "CODE_STATUS:continue_read_artifact"
                if selected_tool_name == "read_artifact"
                else "CODE_STATUS:continue_search_docs"
            ),
            max_iterations=max_iterations,
            max_tool_calls=max_tool_calls,
            tool_call_count=tool_call_count,
            source_trace_ids=_unique_strings(
                [
                    run_trace_id,
                    l1.event_id,
                    tool_catalog_trace_id,
                    *l2_plan_trace_ids,
                    l2.event_id,
                    tool_choice_trace_id,
                    budget_trace_id,
                    *tool_call_trace_ids,
                ]
            ),
            source_data_ids=_unique_strings(
                [
                    l1_goal_data_id,
                    catalog_id,
                    *query_plan_data_ids,
                    l2_query_data_id,
                    tool_choice_ids[0],
                    budget_data_id,
                    *tool_distillation_data_ids,
                ]
            ),
            selected_tool_name=selected_tool_name,
            query_text=current_query,
            id_namespace=run_ids,
        )
        control_trace_ids.append(control_trace_id)
        control_data_ids.append(control_data_id)
        next_iteration_index += 1

        if selected_tool_name == "read_artifact":
            artifact_result = tool_runner.run(
                tool_name="read_artifact",
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                input_ref=[l2.event_id, tool_choice_trace_id, control_trace_id],
                id_namespace=run_ids,
                artifact_ref=current_query,
            )
            tool_call_count += 1
            tool_call_trace_ids.append(artifact_result.trace_event_id)
            tool_result_data_ids.append(artifact_result.data_ref.data_id)
            artifact_distillation = record_tool_result_distillation(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                tool_result=artifact_result,
                id_namespace=run_ids,
            )
            distillation_trace_ids.append(artifact_distillation.trace_event_id)
            tool_distillation_data_ids.append(artifact_distillation.data_id)
            input_chars_used += len(current_query) + distilled_input_size(artifact_distillation.frame)

            artifact_payload = artifact_result.payload if isinstance(artifact_result.payload, dict) else {}
            artifact_doc_id = str(
                artifact_payload.get("selected_doc_id")
                or artifact_payload.get("doc_id")
                or ""
            )
            artifact_match_status = str(artifact_payload.get("match_status") or "")
            if artifact_match_status == "unique" and artifact_doc_id:
                read_doc_ids.add(artifact_doc_id)
                read_doc_id_list.append(artifact_doc_id)
                completed_budget_trace_id, completed_budget_data_id = record_budget(
                    stop_reason="completed",
                    reason="CODE_STATUS:read_artifact_unique_document_extract_recorded",
                    condition_flags=["completed", "read_artifact_unique", "read_doc_recorded"],
                    source_trace_ids=[
                        artifact_result.trace_event_id,
                        artifact_distillation.trace_event_id,
                    ],
                    source_data_ids=[
                        artifact_result.data_ref.data_id,
                        artifact_distillation.data_id,
                    ],
                )
                stop_control_trace_id, stop_control_data_id = _record_l_loop_control(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    iteration_index=next_iteration_index,
                    decision="stop_success",
                    reason="CODE_STATUS:stop_success_read_artifact_unique_match",
                    max_iterations=max_iterations,
                    max_tool_calls=max_tool_calls,
                    tool_call_count=tool_call_count,
                    source_trace_ids=_unique_strings(
                        [
                            *control_trace_ids,
                            *tool_call_trace_ids,
                            *distillation_trace_ids,
                            *budget_trace_ids,
                            completed_budget_trace_id,
                        ]
                    ),
                    source_data_ids=_unique_strings(
                        [
                            *control_data_ids,
                            *tool_distillation_data_ids,
                            *tool_budget_data_ids,
                            completed_budget_data_id,
                        ]
                    ),
                    id_namespace=run_ids,
                )
                control_trace_ids.append(stop_control_trace_id)
                control_data_ids.append(stop_control_data_id)
                final_control_data_id = stop_control_data_id
                final_control_decision = "stop_success"
                break

            failure_trace_id, failure_id = _record_l_loop_budget_failure(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                source_trace_ids=[
                    artifact_result.trace_event_id,
                    artifact_distillation.trace_event_id,
                ],
                source_data_ids=[
                    artifact_result.data_ref.data_id,
                    artifact_distillation.data_id,
                ],
                message=f"CODE_STATUS:read_artifact_{artifact_match_status or 'not_found'}",
                id_namespace=run_ids,
            )
            failure_trace_ids.append(failure_trace_id)
            failure_signal_data_ids.append(failure_id)
            failed_budget_trace_id, failed_budget_data_id = record_budget(
                stop_reason="low_yield_stop",
                reason="CODE_STATUS:read_artifact_no_unique_document",
                condition_flags=["read_artifact_no_unique_document", artifact_match_status or "not_found"],
                source_trace_ids=[failure_trace_id],
                source_data_ids=[failure_id],
            )
            stop_control_trace_id, stop_control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:read_artifact_no_unique_document_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=[failure_trace_id, failed_budget_trace_id],
                source_data_ids=[failure_id, failed_budget_data_id],
                failure_signal_id=failure_id,
                id_namespace=run_ids,
            )
            control_trace_ids.append(stop_control_trace_id)
            control_data_ids.append(stop_control_data_id)
            final_control_data_id = stop_control_data_id
            final_control_decision = "stop_failed"
            break

        search_result = tool_runner.run(
            tool_name="search_docs",
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            input_ref=[l2.event_id, tool_choice_trace_id, control_trace_id],
            id_namespace=run_ids,
            query=current_query,
            top_k=search_top_k,
        )
        latest_search_result = search_result
        tool_call_count += 1
        tool_call_trace_ids.append(search_result.trace_event_id)
        tool_result_data_ids.append(search_result.data_ref.data_id)
        search_distillation = record_tool_result_distillation(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            tool_result=search_result,
            id_namespace=run_ids,
        )
        distillation_trace_ids.append(search_distillation.trace_event_id)
        tool_distillation_data_ids.append(search_distillation.data_id)
        cache_status_records.append(
            make_cache_status_record(
                tool_result_data_id=search_result.data_ref.data_id,
                cache_status=cache_status_from_search_payload(search_result.payload),
                query_text=current_query,
            )
        )
        input_chars_used += len(current_query) + distilled_input_size(search_distillation.frame)
        search_budget_trace_id, search_budget_data_id = record_budget(
            stop_reason="within_budget",
            reason="CODE_STATUS:search_docs_result_budget_recorded",
            condition_flags=["within_budget", "search_docs_recorded"],
            source_trace_ids=[
                search_result.trace_event_id,
                search_distillation.trace_event_id,
            ],
            source_data_ids=[
                search_result.data_ref.data_id,
                search_distillation.data_id,
            ],
        )

        result_count = _distilled_result_count(search_distillation.frame)
        if result_count > 0:
            # 장기 과제: 이 루프는 search_docs가 정렬한 후보를 순서대로 읽는다.
            # 사용자가 "무작위"라고 말해도 여기서는 진짜 랜덤 샘플링이 아니라 의미 검색 후보 열람이다.
            # 진짜 무작위 열람이나 L2의 명시적 읽기 전략이 필요해지면 별도 tool/read-plan frame으로 분리한다.
            candidate_doc_ids = _candidate_doc_ids_from_distillation(search_distillation.frame)
            for candidate_doc_id in candidate_doc_ids:
                can_read_doc = next_iteration_index < max_iterations
                if candidate_doc_id in read_doc_ids:
                    duplicate_doc_count += 1
                    duplicate_trace_id, duplicate_id = record_duplicate_tool_use_signal(
                        trace_store=trace_store,
                        data_store=data_store,
                        turn_id=turn_id,
                        duplicate_kind="doc",
                        duplicate_value=candidate_doc_id,
                        source_trace_ids=[
                            search_result.trace_event_id,
                            search_distillation.trace_event_id,
                        ],
                        source_data_ids=[search_distillation.data_id, *tool_budget_data_ids],
                        id_namespace=run_ids,
                    )
                    failure_trace_ids.append(duplicate_trace_id)
                    failure_signal_data_ids.append(duplicate_id)
                    record_budget(
                        stop_reason="duplicate_doc",
                        reason="CODE_STATUS:duplicate_doc_read_skipped",
                        condition_flags=["duplicate_doc"],
                        source_trace_ids=[duplicate_trace_id],
                        source_data_ids=[duplicate_id],
                    )
                    continue
                if tool_call_count >= max_tool_calls:
                    record_budget(
                        stop_reason="max_tool_calls_reached",
                        reason="CODE_STATUS:max_tool_calls_before_read_doc",
                        condition_flags=["max_tool_calls_reached"],
                        source_trace_ids=[
                            search_result.trace_event_id,
                            search_distillation.trace_event_id,
                        ],
                        source_data_ids=[search_distillation.data_id, *tool_budget_data_ids],
                    )
                    break
                if len(read_doc_id_list) >= max_read_doc_calls:
                    record_budget(
                        stop_reason="max_read_doc_calls_reached",
                        reason="CODE_STATUS:max_read_doc_calls_reached",
                        condition_flags=["max_read_doc_calls_reached"],
                        source_trace_ids=[
                            search_result.trace_event_id,
                            search_distillation.trace_event_id,
                        ],
                        source_data_ids=[search_distillation.data_id, *tool_budget_data_ids],
                    )
                    break
                if input_chars_used >= max_input_chars:
                    record_budget(
                        stop_reason="max_input_chars_reached",
                        reason="CODE_STATUS:max_input_chars_before_read_doc",
                        condition_flags=["max_input_chars_reached"],
                        source_trace_ids=[
                            search_result.trace_event_id,
                            search_distillation.trace_event_id,
                        ],
                        source_data_ids=[search_distillation.data_id, *tool_budget_data_ids],
                    )
                    break
                if not can_read_doc:
                    record_budget(
                        stop_reason="within_budget",
                        reason="CODE_STATUS:max_controller_iterations_before_read_doc",
                        condition_flags=["max_controller_iterations_reached"],
                        source_trace_ids=[
                            search_result.trace_event_id,
                            search_distillation.trace_event_id,
                        ],
                        source_data_ids=[search_distillation.data_id, *tool_budget_data_ids],
                    )
                    break

                read_doc_ids.add(candidate_doc_id)
                read_doc_id_list.append(candidate_doc_id)
                read_control_trace_id, read_control_data_id = _record_l_loop_control(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    iteration_index=next_iteration_index,
                    decision="read_document",
                    reason=(
                        "CODE_STATUS:read_top_search_result_document"
                        if len(read_doc_id_list) == 1
                        else "CODE_STATUS:read_next_unread_search_result_document"
                    ),
                    max_iterations=max_iterations,
                    max_tool_calls=max_tool_calls,
                    tool_call_count=tool_call_count,
                    source_trace_ids=_unique_strings(
                        [
                            control_trace_id,
                            search_result.trace_event_id,
                            search_distillation.trace_event_id,
                            search_budget_trace_id,
                        ]
                    ),
                    source_data_ids=_unique_strings(
                        [control_data_id, search_distillation.data_id, search_budget_data_id]
                    ),
                    selected_tool_name="read_doc",
                    doc_id=candidate_doc_id,
                    id_namespace=run_ids,
                )
                control_trace_ids.append(read_control_trace_id)
                control_data_ids.append(read_control_data_id)
                read_choice_trace_id = record_tool_choice(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    registry=tool_registry,
                    chooser_node_id=f"L_controller_{next_iteration_index:04d}",
                    tool_name="read_doc",
                    catalog_id=catalog_id,
                    reason="CODE_STATUS:l_loop_control_selected_read_doc",
                    expected_use="CODE_STATUS:read_selected_doc_id",
                    tool_choice_policy_id="l_loop_control_read_document",
                    expected_effect_label="CODE_STATUS:read_doc_execution",
                    input_ref=[tool_catalog_trace_id, read_control_trace_id],
                    source_data_ids=[read_control_data_id, search_distillation.data_id],
                    id_namespace=run_ids,
                )
                read_choice_id = tool_choice_data_id(
                    f"L_controller_{next_iteration_index:04d}",
                    "read_doc",
                    id_namespace=run_ids,
                )
                tool_choice_trace_ids.append(read_choice_trace_id)
                tool_choice_ids.append(read_choice_id)
                next_iteration_index += 1

                read_result = tool_runner.run(
                    tool_name="read_doc",
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    input_ref=[read_control_trace_id, read_choice_trace_id],
                    id_namespace=run_ids,
                    doc_id=candidate_doc_id,
                )
                tool_call_count += 1
                tool_call_trace_ids.append(read_result.trace_event_id)
                tool_result_data_ids.append(read_result.data_ref.data_id)
                read_distillation = record_tool_result_distillation(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    tool_result=read_result,
                    id_namespace=run_ids,
                )
                distillation_trace_ids.append(read_distillation.trace_event_id)
                tool_distillation_data_ids.append(read_distillation.data_id)
                input_chars_used += distilled_input_size(read_distillation.frame)
                record_budget(
                    stop_reason="within_budget"
                    if input_chars_used < max_input_chars
                    else "max_input_chars_reached",
                    reason="CODE_STATUS:read_doc_distillation_budget_recorded",
                    condition_flags=["read_doc_recorded"],
                    source_trace_ids=[
                        read_result.trace_event_id,
                        read_distillation.trace_event_id,
                    ],
                    source_data_ids=[
                        read_result.data_ref.data_id,
                        read_distillation.data_id,
                    ],
                )

            if not read_doc_id_list:
                no_read_trace_id, no_read_id = _record_l_loop_budget_failure(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    source_trace_ids=[
                        search_result.trace_event_id,
                        search_distillation.trace_event_id,
                    ],
                    source_data_ids=[search_distillation.data_id, *tool_budget_data_ids],
                    message="CODE_STATUS:no_candidate_document_read",
                    id_namespace=run_ids,
                )
                failure_trace_ids.append(no_read_trace_id)
                failure_signal_data_ids.append(no_read_id)
                record_budget(
                    stop_reason="low_yield_stop",
                    reason="CODE_STATUS:no_candidate_document_read",
                    condition_flags=["no_candidate_document_read"],
                    source_trace_ids=[no_read_trace_id],
                    source_data_ids=[no_read_id],
                )

            completed_budget_trace_id, completed_budget_data_id = record_budget(
                stop_reason="completed",
                reason="CODE_STATUS:l3_input_evidence_available",
                condition_flags=["completed", "candidate_count_positive"],
                source_trace_ids=[
                    *control_trace_ids,
                    *tool_call_trace_ids,
                    *distillation_trace_ids,
                    *budget_trace_ids,
                ],
                source_data_ids=[
                    *control_data_ids,
                    *tool_distillation_data_ids,
                    *tool_budget_data_ids,
                ],
            )
            stop_control_trace_id, stop_control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_success",
                reason="CODE_STATUS:stop_success_candidates_preserved",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=_unique_strings(
                    [
                        *control_trace_ids,
                        *tool_call_trace_ids,
                        *distillation_trace_ids,
                        *budget_trace_ids,
                        completed_budget_trace_id,
                    ]
                ),
                source_data_ids=_unique_strings(
                    [
                        *control_data_ids,
                        *tool_distillation_data_ids,
                        *tool_budget_data_ids,
                        completed_budget_data_id,
                    ]
                ),
                id_namespace=run_ids,
            )
            control_trace_ids.append(stop_control_trace_id)
            control_data_ids.append(stop_control_data_id)
            final_control_data_id = stop_control_data_id
            final_control_decision = "stop_success"
            break

        refined_query = _refine_search_query(current_query, attempt_count=len(used_queries) + 1)
        if refined_query in used_queries:
            failure_trace_id, failure_id = _record_l_loop_budget_failure(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                source_trace_ids=_unique_strings([search_result.trace_event_id]),
                source_data_ids=_unique_strings([search_distillation.data_id]),
                message="CODE_STATUS:no_results_no_new_query",
                id_namespace=run_ids,
            )
            failure_trace_ids.append(failure_trace_id)
            failure_signal_data_ids.append(failure_id)
            control_trace_id, control_data_id = _record_l_loop_control(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                iteration_index=next_iteration_index,
                decision="stop_failed",
                reason="CODE_STATUS:no_results_no_new_query_stop_failed",
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                tool_call_count=tool_call_count,
                source_trace_ids=_unique_strings(
                    [
                        failure_trace_id,
                        search_result.trace_event_id,
                        search_distillation.trace_event_id,
                    ]
                ),
                source_data_ids=_unique_strings([failure_id, search_distillation.data_id]),
                failure_signal_id=failure_id,
                id_namespace=run_ids,
            )
            control_trace_ids.append(control_trace_id)
            control_data_ids.append(control_data_id)
            final_control_data_id = control_data_id
            final_control_decision = "stop_failed"
            break
        current_query = refined_query

    l3_input_trace_ids = _unique_strings(
        [
            run_trace_id,
            *control_trace_ids,
            *tool_choice_trace_ids,
            *tool_call_trace_ids,
            *distillation_trace_ids,
            *budget_plan_trace_ids,
            *budget_trace_ids,
            *failure_trace_ids,
        ]
    )
    l3_input_data_ids = _unique_strings(
        [
            run_data_id,
            l1_goal_data_id,
            *budget_plan_data_ids,
            catalog_id,
            *query_plan_data_ids,
            l2_query_data_id,
            *tool_choice_ids,
            *control_data_ids,
            *tool_distillation_data_ids,
            *tool_budget_data_ids,
            *failure_signal_data_ids,
        ]
    )

    l3 = run_l3_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        l1_event=l1,
        l2_event=l2,
        extra_input_trace_ids=l3_input_trace_ids,
        extra_input_data_ids=l3_input_data_ids,
        final_control_data_id=final_control_data_id,
        user_query=search_query,
        adapter=l3_result_adapter,
        preserved_frame_data_id=l3_preserved_data_id,
        achievement_frame_data_id=l3_achievement_data_id,
        target_goal_data_id=l1_goal_data_id,
    )

    current_l3_trace_id = l3.event_id
    current_l3_achievement_id = l3_achievement_data_id
    current_l2_query_frame_id = l2_query_data_id
    continuation_attempt_index = 1
    if l2_query_planner_adapter is not None:
        while continuation_attempt_index <= max_iterations:
            continuation_trace_id, continuation_data_id, continuation_frame = (
                record_l_loop_continuation_decision(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    attempt_index=continuation_attempt_index,
                    max_attempts=max_iterations,
                    source_trace_ids=[current_l3_trace_id],
                    source_data_ids=[current_l3_achievement_id, current_l2_query_frame_id],
                    l3_achievement_data_id=current_l3_achievement_id,
                    l2_query_frame_data_id=current_l2_query_frame_id,
                    id_namespace=run_ids,
                )
            )
            continuation_trace_ids.append(continuation_trace_id)
            continuation_data_ids.append(continuation_data_id)
            final_continuation_data_id = continuation_data_id
            final_continuation_status = continuation_frame.continuation_status
            if continuation_frame.continuation_status != "continue":
                break

            memory_trace_id = record_l3_continuation_summary_for_l2(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                zero_state=continuation_zero_state,
                continuation_frame_id=continuation_data_id,
                input_ref=[continuation_trace_id],
                id_namespace=run_ids,
            )
            revision_trace_ids.append(memory_trace_id)

            revision_input_trace_id, revision_input_id, _ = record_l2_revision_input_frame(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                continuation_frame_id=continuation_data_id,
                l1_goal_data_id=l1_goal_data_id,
                id_namespace=run_ids,
            )
            revision_trace_ids.append(revision_input_trace_id)
            revision_input_data_ids.append(revision_input_id)

            try:
                revision_plan_event = run_l2_revision_query_planner(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    revision_input_data_id=revision_input_id,
                    adapter=l2_query_planner_adapter,
                    available_tools=available_tools,
                    id_namespace=run_ids,
                )
            except Exception:
                failure_trace_id, failure_id = _record_l_loop_budget_failure(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    source_trace_ids=[revision_input_trace_id],
                    source_data_ids=[revision_input_id, continuation_data_id],
                    message="CODE_STATUS:l2_revision_query_planner_failed",
                    id_namespace=run_ids,
                )
                failure_trace_ids.append(failure_trace_id)
                failure_signal_data_ids.append(failure_id)
                break

            revision_plan_id = l2_revision_query_plan_data_id(
                continuation_attempt_index,
                id_namespace=run_ids,
            )
            l2_plan_trace_ids.append(revision_plan_event.event_id)
            revision_trace_ids.append(revision_plan_event.event_id)
            revision_query_plan_data_ids.append(revision_plan_id)
            query_plan_data_ids.append(revision_plan_id)

            revision_query_event = run_l2_revision_query_setter(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                revision_query_plan_data_id=revision_plan_id,
                id_namespace=run_ids,
            )
            revision_query_id = l2_revision_query_frame_data_id(
                continuation_attempt_index,
                id_namespace=run_ids,
            )
            revision_trace_ids.append(revision_query_event.event_id)
            revision_query_data_ids.append(revision_query_id)

            revision_tool_result = run_l_loop_revision_tool_attempt(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                revision_query_frame_data_id=revision_query_id,
                document_root=document_root,
                search_top_k=search_top_k,
                max_tool_calls=max_tool_calls,
                max_query_attempts=max_query_attempts,
                max_read_doc_calls=max_read_doc_calls,
                max_input_chars=max_input_chars,
                id_namespace=run_ids,
            )
            revision_trace_ids.extend(revision_tool_result.source_trace_ids)
            tool_call_trace_ids.append(revision_tool_result.tool_trace_id)
            distillation_trace_ids.append(revision_tool_result.tool_distillation_trace_id)
            budget_trace_ids.append(revision_tool_result.tool_budget_trace_id)
            tool_choice_ids.append(revision_tool_result.tool_choice_data_id)
            tool_result_data_ids.append(revision_tool_result.tool_result_data_id)
            tool_distillation_data_ids.append(revision_tool_result.tool_distillation_data_id)
            tool_budget_data_ids.append(revision_tool_result.tool_budget_data_id)

            revision_l3_event = run_l3_revision_result_keeper(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                attempt_index=continuation_attempt_index,
                revision_query_frame_data_id=revision_query_id,
                revision_tool_source_trace_ids=revision_tool_result.source_trace_ids,
                revision_tool_source_data_ids=revision_tool_result.source_data_ids,
                user_query=search_query,
                l1_goal_data_id=l1_goal_data_id,
                id_namespace=run_ids,
            )
            revision_trace_ids.append(revision_l3_event.event_id)
            revision_preserved_id = l3_revision_preserved_frame_data_id(
                continuation_attempt_index,
                id_namespace=run_ids,
            )
            revision_achievement_id = l3_revision_achievement_frame_data_id(
                continuation_attempt_index,
                id_namespace=run_ids,
            )
            revision_preserved_data_ids.append(revision_preserved_id)
            revision_achievement_data_ids.append(revision_achievement_id)
            current_l3_trace_id = revision_l3_event.event_id
            current_l3_achievement_id = revision_achievement_id
            current_l2_query_frame_id = revision_query_id
            l3 = revision_l3_event
            continuation_attempt_index += 1

    source_trace_ids = _unique_strings(
        [
            run_trace_id,
            l1.event_id,
            *budget_plan_trace_ids,
            tool_catalog_trace_id,
            *l2_plan_trace_ids,
            l2.event_id,
            *tool_choice_trace_ids,
            *control_trace_ids,
            *tool_call_trace_ids,
            *distillation_trace_ids,
            *budget_trace_ids,
            *continuation_trace_ids,
            *revision_trace_ids,
            *failure_trace_ids,
            l3.event_id,
        ]
    )
    output_data_ids = _unique_strings(
        [
            run_data_id,
            l1_goal_data_id,
            *budget_plan_data_ids,
            catalog_id,
            *query_plan_data_ids,
            l2_query_data_id,
            *tool_choice_ids,
            *control_data_ids,
            *tool_result_data_ids,
            *tool_distillation_data_ids,
            *tool_budget_data_ids,
            *continuation_data_ids,
            *revision_input_data_ids,
            *revision_query_plan_data_ids,
            *revision_query_data_ids,
            *failure_signal_data_ids,
            l3_preserved_data_id,
            l3_achievement_data_id,
            *revision_preserved_data_ids,
            *revision_achievement_data_ids,
        ]
    )
    return LLoopResult(
        loop_id="L",
        turn_id=turn_id,
        run_trace_id=run_trace_id,
        l1_trace_id=l1.event_id,
        l2_trace_id=l2.event_id,
        l3_trace_id=l3.event_id,
        l2_plan_trace_ids=l2_plan_trace_ids,
        budget_plan_trace_ids=budget_plan_trace_ids,
        control_trace_ids=control_trace_ids,
        tool_trace_ids=_unique_strings(
            [tool_catalog_trace_id, *tool_choice_trace_ids, *tool_call_trace_ids]
        ),
        budget_trace_ids=budget_trace_ids,
        continuation_trace_ids=continuation_trace_ids,
        revision_trace_ids=revision_trace_ids,
        failure_trace_ids=failure_trace_ids,
        run_data_ids=[run_data_id],
        goal_data_ids=[l1_goal_data_id],
        budget_plan_data_ids=budget_plan_data_ids,
        tool_catalog_data_ids=[catalog_id],
        tool_choice_data_ids=tool_choice_ids,
        query_plan_data_ids=query_plan_data_ids,
        query_data_ids=[l2_query_data_id, *revision_query_data_ids],
        control_data_ids=control_data_ids,
        tool_result_data_ids=tool_result_data_ids,
        tool_distillation_data_ids=tool_distillation_data_ids,
        tool_budget_data_ids=tool_budget_data_ids,
        continuation_data_ids=continuation_data_ids,
        revision_input_data_ids=revision_input_data_ids,
        revision_query_plan_data_ids=revision_query_plan_data_ids,
        revision_query_data_ids=revision_query_data_ids,
        failure_signal_data_ids=failure_signal_data_ids,
        preserved_data_ids=[l3_preserved_data_id, *revision_preserved_data_ids],
        achievement_data_ids=[l3_achievement_data_id, *revision_achievement_data_ids],
        output_data_ids=output_data_ids,
        source_trace_ids=source_trace_ids,
        final_control_data_id=final_control_data_id,
        final_control_decision=final_control_decision,
        final_continuation_data_id=final_continuation_data_id,
        final_continuation_status=final_continuation_status,
    )


def _record_l_loop_run_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    run_ids: LRunIds,
    input_ref: list[str],
    source_data_ids: list[str],
    same_turn_rerun_allowed: bool = False,
    rerun_block_reason: str = L_REROUTE_REMAINING_BLOCK_REASON,
    planned_next_step: str = L_REROUTE_PLANNED_NEXT_STEP,
) -> tuple[str, str]:
    """L루프 전체 실행 1회를 기록한다.

    이 기록은 아직 상위 L 재라우팅을 열지 않는다. L 내부 ID와 복귀 route
    ID는 run_index 2부터 scoped 경로가 생겼지만, 같은 턴 재실행 controller
    정책과 런타임 흐름은 아직 명시적으로 열지 않았다.
    """

    frame = LLoopRunFrame(
        frame_id=run_ids.run_frame_data_id,
        turn_id=turn_id,
        loop_id="L",
        run_index=run_ids.run_index,
        namespace_policy=run_ids.namespace_policy,
        primary_ids_are_attempt_scoped=run_ids.run_index > 1,
        same_turn_rerun_allowed=same_turn_rerun_allowed,
        rerun_block_reason=rerun_block_reason,
        planned_next_step=planned_next_step,
        source_trace_ids=_unique_strings(input_ref),
        source_data_ids=_unique_strings(source_data_ids),
    )
    validate_l_loop_run_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L",
        event_type="node_output",
        input_ref=_unique_strings(input_ref),
        output_ref=[run_ids.run_frame_data_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=run_ids.run_frame_data_id,
        data_type="node_output:L_loop_run_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, run_ids.run_frame_data_id


def _record_l_loop_control(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    iteration_index: int,
    decision: str,
    reason: str,
    max_iterations: int,
    max_tool_calls: int,
    tool_call_count: int,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    selected_tool_name: str | None = None,
    query_text: str | None = None,
    doc_id: str | None = None,
    failure_signal_id: str | None = None,
    condition_flags: list[str] | None = None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str]:
    """controller 판단을 trace와 DataStore에 함께 남긴다."""

    control_id = (
        id_namespace.control_data_id(iteration_index)
        if id_namespace is not None
        else f"L:control:{iteration_index:04d}"
    )
    frame = LLoopControlFrame(
        control_id=control_id,
        turn_id=turn_id,
        loop_id="L",
        iteration_index=iteration_index,
        decision=decision,
        reason=reason,
        max_iterations=max_iterations,
        max_tool_calls=max_tool_calls,
        tool_call_count=tool_call_count,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        selected_tool_name=selected_tool_name,
        query_text=query_text,
        doc_id=doc_id,
        failure_signal_id=failure_signal_id,
        condition_flags=condition_flags or _control_condition_flags(
            decision=decision,
            selected_tool_name=selected_tool_name,
            failure_signal_id=failure_signal_id,
        ),
    )
    validate_l_loop_control_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L_controller",
        event_type="node_output",
        input_ref=source_trace_ids,
        output_ref=[control_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=control_id,
        data_type="node_output:L_loop_control_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, control_id


def _record_l_loop_budget_failure(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    message: str,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str]:
    """L루프 controller가 budget이나 검색 한계로 멈출 때 실패 신호를 남긴다."""

    signal_index = len(source_trace_ids) + len(source_data_ids)
    failure_id = (
        id_namespace.l_loop_failure_data_id(
            turn_id=turn_id,
            signal_index=signal_index,
        )
        if id_namespace is not None
        else f"failure:L_loop:{turn_id}:{signal_index:04d}"
    )
    failure_trace_id = record_failure_signal(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        failure_id=failure_id,
        type="tool_failed",
        severity="warning",
        raised_by="L_controller",
        recoverable=True,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        message=message,
    )
    return failure_trace_id, failure_id


def _control_condition_flags(
    *,
    decision: str,
    selected_tool_name: str | None,
    failure_signal_id: str | None,
) -> list[str]:
    flags = [decision]
    if selected_tool_name:
        flags.append(f"tool:{selected_tool_name}")
    if failure_signal_id:
        flags.append("has_failure_signal")
    return flags


def _read_query_text_from_l2_frame(payload: object) -> str:
    """DataStore에 저장된 L2 query frame payload에서 query_text를 꺼낸다."""

    if not isinstance(payload, dict):
        raise TypeError("L2 query frame payload must be a dict")
    query_text = payload.get("query_text")
    if not isinstance(query_text, str) or not query_text.strip():
        raise ValueError("L2 query frame query_text must be a non-empty string")
    return query_text


def _distilled_result_count(frame: object) -> int:
    """ToolResultDistillationFrame에서 search result item 개수를 읽는다."""

    items = getattr(frame, "items", [])
    return sum(1 for item in items if getattr(item, "item_kind", None) == "search_result")


def _top_doc_id_from_distillation(frame: object) -> str | None:
    """search_docs distillation의 첫 번째 doc_id를 읽는다."""

    items = getattr(frame, "items", [])
    for item in items:
        if getattr(item, "item_kind", None) != "search_result":
            continue
        doc_id = getattr(item, "doc_id", None)
        if isinstance(doc_id, str) and doc_id:
            return doc_id
    return None


def _candidate_doc_ids_from_distillation(frame: object) -> list[str]:
    """search_docs distillation에서 읽기 후보 doc_id를 순서대로 뽑는다."""

    items = getattr(frame, "items", [])
    doc_ids: list[str] = []
    seen: set[str] = set()
    for item in items:
        if getattr(item, "item_kind", None) != "search_result":
            continue
        doc_id = getattr(item, "doc_id", None)
        if not isinstance(doc_id, str) or not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        doc_ids.append(doc_id)
    return doc_ids


def _refine_search_query(query: str, *, attempt_count: int) -> str:
    """검색 결과가 없을 때 budget 안에서 한 번 더 시도할 query를 만든다."""

    suffixes = [
        " 내부 문서 발주서",
        " 구조화 에이전트 L루프",
        " 메타정보 trace DataStore",
    ]
    suffix = suffixes[min(attempt_count - 1, len(suffixes) - 1)]
    return f"{query}{suffix}"


def _unique_strings(values: list[str | None]) -> list[str]:
    """None과 중복을 제거하되 처음 등장한 순서를 보존한다."""

    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
