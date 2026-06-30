from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.schemas import (
    Node2InputFrame,
    TurnOutcomeFrame,
    TurnStateCapsule,
    ZeroState,
    validate_node2_input_frame,
    validate_turn_outcome_frame,
)
from songryeon_core.core.trace_store import TraceEventSink, TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.fake import MemoryRelevanceNoneSelectedFakeLLMAdapter
from songryeon_core.runtime.artifact_export import export_runtime_artifacts
from songryeon_core.runtime.defaults import (
    DEFAULT_DOCUMENT_ROOT,
    DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_QUERY_ATTEMPTS,
    DEFAULT_MAX_READ_DOC_CALLS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_SEARCH_TOP_K,
    DEFAULT_TURN_ID,
)
from songryeon_core.runtime.task_ledger import record_task_ledger_from_movements, task_ledger_counts
from songryeon_core.runtime.same_turn_l_reroute import (
    SAME_TURN_L_REROUTE_DISABLED_REASON,
    SAME_TURN_L_REROUTE_DISABLED_STEP,
    SAME_TURN_L_REROUTE_WAITING_STEP,
    SameTurnLRerouteDecision,
    SameTurnLReroutePolicy,
    run_same_turn_l_reroute_controller,
)
from songryeon_core.state.unified_state import (
    create_unified_state,
    enter_loop,
    exit_loop,
    set_active_schema,
    set_current_route,
    set_metainfo_boundary_id,
    sync_trace_ids_from_store,
)
from songryeon_core.state.zero_state import (
    add_capsule_to_zero_state,
    build_turn_capsule,
    make_node_movement,
    set_current_turn_trace_ids,
)
from songryeon_core.core.registry import build_default_prompt_registry, build_default_schema_registry
from songryeon_core.nodes.node_0_memory_supplier import (
    RAW_MEMORY_COMPRESSION_BATCH_SIZE,
    RAW_MEMORY_POST_COMPRESSION_KEEP,
    RECENT_RAW_CONVERSATION_MAX_WINDOW,
    RECENT_RAW_CONVERSATION_MIN_GUARANTEE,
    RECENT_MEMORY_RELEVANCE_CANDIDATE_WINDOW,
    RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW,
    RECENT_TURN_CAPSULE_READ_WINDOW,
    build_pre_route_memory_items,
    build_recent_raw_conversation_compression_candidate,
    build_recent_memory_relevance_candidate_frames,
    document_material_packet_frame_data_id,
    memory_packet_data_id,
    record_l_loop_return_summary_for_node1,
    record_r_loop_memory_handoff_packet,
    record_memory_packet,
    supply_memory,
)
from songryeon_core.nodes.memory_relevance_selector import (
    run_recent_memory_relevance_selector,
)
from songryeon_core.nodes.node_1_router import (
    ROUTER_FALLBACK_POLICY_DEV_SMOKE,
    record_routing,
    route_next,
    route_next_with_llm_or_policy_fallback,
)
from songryeon_core.loops.l_loop import run_l_loop
from songryeon_core.loops.l_loop_namespace import build_l_run_ids
from songryeon_core.loops.r_loop_dry_run import run_r_loop_dry_run_skeleton
from songryeon_core.nodes.node_2_metainfo_boundary import (
    build_metainfo_boundary,
    record_boundary,
    run_node2_answer_basis_selection,
    run_node2_boundary_review,
)
from songryeon_core.nodes.node_2_handoff import (
    record_node3_input_brief,
    record_route2_handoff,
    record_selected_recent_memory_context,
)
from songryeon_core.nodes.node_3_reporter import record_report, render_report, render_report_with_llm
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


def run_dry_turn(
    user_input: str = "내부 문서 기억 검색 후 보고해줘",
    *,
    turn_id: str | None = None,
    export_dir: str | None = None,
    node_1_router_adapter: LLMAdapter | None = None,
    memory_relevance_selector_adapter: LLMAdapter | None = None,
    l1_goal_adapter: LLMAdapter | None = None,
    l_tool_scope_adapter: LLMAdapter | None = None,
    l2_query_planner_adapter: LLMAdapter | None = None,
    l3_result_adapter: LLMAdapter | None = None,
    node_2_boundary_adapter: LLMAdapter | None = None,
    node_3_reporter_adapter: LLMAdapter | None = None,
    node_4_gatekeeper_adapter: LLMAdapter | None = None,
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
    search_top_k: int = DEFAULT_SEARCH_TOP_K,
    max_query_attempts: int = DEFAULT_MAX_QUERY_ATTEMPTS,
    max_query_candidates: int | None = None,
    max_read_doc_calls: int = DEFAULT_MAX_READ_DOC_CALLS,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    max_document_context_chars: int = DEFAULT_MAX_DOCUMENT_CONTEXT_CHARS,
    force_l_route: bool = False,
    same_turn_l_reroute_enabled: bool = False,
    max_l_runs_per_turn: int = 1,
    allow_node_1_router_fallback: bool = True,
    node_1_router_fallback_policy: str = ROUTER_FALLBACK_POLICY_DEV_SMOKE,
    previous_turn_capsules: list[TurnStateCapsule] | None = None,
    recent_raw_conversation: list[dict[str, str]] | None = None,
    live_trace_sink: TraceEventSink | None = None,
    enable_r_route_dry_run: bool = False,
    r_route_dry_run_force_budget_exhausted: bool = False,
) -> dict[str, object]:
    """한 턴의 구조 흐름을 trace/data로 실행한다.

    이름은 dry_run으로 남아 있지만, adapter를 넘기면 Qwen/fake LLM 노드도 함께 돈다.
    그래서 이 함수는 현재 MVP의 중앙 배선도에 가깝다.
    """

    turn_id = turn_id or DEFAULT_TURN_ID
    trace_store = TraceStore(on_event=live_trace_sink)
    data_store = DataStore()
    zero_state = ZeroState(
        recent_raw_conversation=list(recent_raw_conversation or []),
        previous_turn_capsules=list(previous_turn_capsules or []),
    )
    unified_state = create_unified_state(turn_id, user_input)
    prompt_registry = build_default_prompt_registry()
    schema_registry = build_default_schema_registry()

    movements = []
    route_data_ids: list[str] = []
    l_loop_output_ids: list[str] = []
    node0_l_data_ids: list[str] = []
    node0_return_data_id: str | None = None
    node0_return_data_ids: list[str] = []
    l_return_summary_data_ids: list[str] = []
    document_material_data_ids: list[str] = []
    l_run_ids = None
    l_results = []
    last_l_result = None
    reroute_controller_data_ids: list[str] = []
    final_reroute_controller: SameTurnLRerouteDecision | None = None
    policy = SameTurnLReroutePolicy(
        enabled=same_turn_l_reroute_enabled,
        max_l_runs_per_turn=max_l_runs_per_turn,
    )
    policy.effective_max_l_runs_per_turn

    # 1. 사용자 입력 trace 기록.
    user_event = trace_store.create_event(
        turn_id=turn_id,
        actor="user",
        event_type="user_input",
        raw_content_ref="inline:user_input",
        schema_status="not_checked",
    )

    # 2. 0이 1에게 줄 사전 기억 패킷 생성.
    # 학습 메모: supply_memory()는 packet의 trace 근거 뼈대를 만들고,
    # build_pre_route_memory_items()가 사람이 읽기 쉬운 item 목록을 붙인다.
    set_current_turn_trace_ids(zero_state, trace_store, turn_id)
    packet_for_1 = supply_memory(
        target="node_1",
        mode="pre_route_report",
        zero_state=zero_state,
        trace_store=trace_store,
        turn_id=turn_id,
    )
    node0_pre_data_id = memory_packet_data_id("node_1", "pre_route_report")
    node0_pre_memory_items = build_pre_route_memory_items(
        zero_state=zero_state,
        packet_id=node0_pre_data_id,
        packet=packet_for_1,
    )
    node0_pre_relevance_candidate_frames = build_recent_memory_relevance_candidate_frames(
        zero_state=zero_state,
        packet_id=node0_pre_data_id,
        turn_id=turn_id,
    )
    node0_pre_compression_candidate_frame = build_recent_raw_conversation_compression_candidate(
        zero_state=zero_state,
        packet_id=node0_pre_data_id,
        turn_id=turn_id,
    )
    previous_turn_capsules_read_count = sum(
        1
        for item in node0_pre_memory_items
        if item.item_type == "previous_turn_capsule_index"
    )
    recent_raw_conversation_alignment_count = sum(
        1
        for item in node0_pre_memory_items
        if item.item_type == "recent_raw_conversation_capsule_alignment"
    )
    node0_pre_trace_id = record_memory_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        packet=packet_for_1,
        mode="pre_route_report",
        input_ref=[user_event.event_id],
        memory_items=node0_pre_memory_items,
        relevance_candidate_frames=node0_pre_relevance_candidate_frames,
        compression_candidate_frames=[node0_pre_compression_candidate_frame],
    )
    movements.append(
        make_node_movement(
            movement_id="move_001",
            turn_id=turn_id,
            step_index=1,
            node_id="node_0",
            mode="pre_route_report",
            input_trace_ids=[user_event.event_id],
            output_trace_ids=[node0_pre_trace_id],
            status="completed",
        )
    )

    selector_adapter = memory_relevance_selector_adapter
    if selector_adapter is None and node0_pre_relevance_candidate_frames:
        selector_adapter = MemoryRelevanceNoneSelectedFakeLLMAdapter()
    (
        memory_relevance_selection_trace_id,
        memory_relevance_selection_data_id,
        memory_relevance_selection_frame,
    ) = run_recent_memory_relevance_selector(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        current_user_input=user_input,
        current_user_input_trace_id=user_event.event_id,
        source_memory_packet_id=node0_pre_data_id,
        selector_target_node="node_1",
        adapter=selector_adapter,
        recent_raw_conversation=zero_state.recent_raw_conversation,
    )
    movements.append(
        make_node_movement(
            movement_id="move_002",
            turn_id=turn_id,
            step_index=2,
            node_id="memory_relevance_selector",
            mode="recent_memory_relevance_selection",
            input_trace_ids=[node0_pre_trace_id],
            output_trace_ids=[memory_relevance_selection_trace_id],
            input_data_ids=[node0_pre_data_id],
            output_data_ids=[memory_relevance_selection_data_id],
            status="completed",
        )
    )
    (
        selected_memory_context_trace_id,
        selected_memory_context_data_id,
        selected_memory_context_frame,
    ) = record_selected_recent_memory_context(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        zero_state=zero_state,
        selection_frame_id=memory_relevance_selection_data_id,
    )

    # 3. 1이 route를 고른다.
    node1_route_input_refs = _unique_strings(
        [
            node0_pre_trace_id,
            memory_relevance_selection_trace_id,
            selected_memory_context_trace_id,
        ]
    )
    node1_route_source_data_ids = _unique_strings(
        [
            node0_pre_data_id,
            memory_relevance_selection_data_id,
            selected_memory_context_data_id,
        ]
    )
    if node_1_router_adapter is not None and not force_l_route:
        decision = route_next_with_llm_or_policy_fallback(
            user_input=user_input,
            memory_packet=packet_for_1,
            schema_registry=schema_registry,
            adapter=node_1_router_adapter,
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            input_ref=node1_route_input_refs,
            source_data_ids=node1_route_source_data_ids,
            force_l_route=force_l_route,
            fallback_policy=node_1_router_fallback_policy,
            fallback_allowed_by_runtime_policy=allow_node_1_router_fallback,
        )
    else:
        decision = route_next(
            user_input=user_input,
            memory_packet=packet_for_1,
            schema_registry=schema_registry,
            force_l_route=force_l_route,
        )
    route_input_ref = _unique_strings([*node1_route_input_refs, decision.llm_trace_event_id])
    route_source_data_ids = _unique_strings([*node1_route_source_data_ids, decision.llm_call_data_id])
    route_trace_id = record_routing(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        decision=decision,
        input_ref=route_input_ref,
        source_data_ids=route_source_data_ids,
    )
    route_data_id = f"route:{decision.route}"
    route_data_ids.append(route_data_id)
    set_current_route(unified_state, decision.route)
    set_active_schema(unified_state, decision.required_schema)
    movements.append(
        make_node_movement(
            movement_id="move_003",
            turn_id=turn_id,
            step_index=3,
            node_id="node_1",
            mode="routing",
            input_trace_ids=route_input_ref,
            output_trace_ids=[route_trace_id],
            status="completed",
        )
    )

    next_step_index = 4

    def append_movement(
        *,
        node_id: str,
        mode: str,
        input_trace_ids: list[str],
        output_trace_ids: list[str],
        input_data_ids: list[str] | None = None,
        output_data_ids: list[str] | None = None,
        node_type: str = "node",
    ) -> None:
        nonlocal next_step_index

        movements.append(
            make_node_movement(
                movement_id=f"move_{next_step_index:03d}",
                turn_id=turn_id,
                step_index=next_step_index,
                node_id=node_id,
                node_type=node_type,
                mode=mode,
                input_trace_ids=input_trace_ids,
                output_trace_ids=output_trace_ids,
                input_data_ids=input_data_ids or [],
                output_data_ids=output_data_ids or [],
                status="completed",
            )
        )
        next_step_index += 1

    # 4. route가 L이면 policy-guarded controller 아래에서 최대 2회차까지 다시 열 수 있다.
    if decision.route == "L":
        current_run_index = 1
        current_l_input_trace_ids = [route_trace_id]
        current_l_source_data_ids = [route_data_id]

        while decision.route == "L":
            l_run_ids = build_l_run_ids(run_index=current_run_index)
            packet_for_l = supply_memory(
                target="L",
                mode=decision.expected_next_0_mode,
                zero_state=zero_state,
                trace_store=trace_store,
                turn_id=turn_id,
            )
            node0_l_trace_id = record_memory_packet(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                packet=packet_for_l,
                mode=decision.expected_next_0_mode,
                input_ref=current_l_input_trace_ids,
                source_data_ids=current_l_source_data_ids,
                id_namespace=l_run_ids,
            )
            node0_l_data_id = l_run_ids.memory_packet_data_id(
                target="L",
                mode=decision.expected_next_0_mode,
            )
            node0_l_data_ids.append(node0_l_data_id)
            append_movement(
                node_id="node_0",
                mode=decision.expected_next_0_mode,
                input_trace_ids=current_l_input_trace_ids,
                output_trace_ids=[node0_l_trace_id],
                input_data_ids=current_l_source_data_ids,
                output_data_ids=[node0_l_data_id],
            )

            enter_loop(unified_state, "L")
            l_result = run_l_loop(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                memory_packet=packet_for_l,
                search_query=user_input,
                memory_packet_data_ids=[node0_l_data_id],
                zero_state=zero_state,
                document_root=DEFAULT_DOCUMENT_ROOT,
                l1_goal_adapter=l1_goal_adapter,
                l_tool_scope_adapter=l_tool_scope_adapter,
                l2_query_planner_adapter=l2_query_planner_adapter,
                l3_result_adapter=l3_result_adapter,
                max_tool_calls=max_tool_calls,
                search_top_k=search_top_k,
                max_query_attempts=max_query_attempts,
                max_query_candidates=max_query_candidates,
                max_read_doc_calls=max_read_doc_calls,
                max_input_chars=max_input_chars,
                max_document_context_chars=max_document_context_chars,
                run_index=current_run_index,
                same_turn_rerun_allowed=(
                    current_run_index > 1 and same_turn_l_reroute_enabled
                ),
                rerun_block_reason=(
                    SAME_TURN_L_REROUTE_DISABLED_REASON
                    if not same_turn_l_reroute_enabled
                    else "CODE_STATUS:same_turn_L_reroute_policy_guard_available"
                ),
                planned_next_step=(
                    SAME_TURN_L_REROUTE_DISABLED_STEP
                    if not same_turn_l_reroute_enabled
                    else SAME_TURN_L_REROUTE_WAITING_STEP
                ),
            )
            exit_loop(unified_state, "L")
            l_results.append(l_result)
            last_l_result = l_result
            l_loop_output_ids.extend(l_result.output_data_ids)
            append_movement(
                node_id="L",
                node_type="loop",
                mode=f"L_loop_run_{current_run_index:04d}",
                input_trace_ids=[node0_l_trace_id],
                output_trace_ids=l_result.source_trace_ids,
                input_data_ids=[node0_l_data_id],
                output_data_ids=l_result.output_data_ids,
            )

            (
                node0_return_trace_id,
                node0_return_data_id,
                l_return_summary_data_id,
                packet_after_l,
            ) = record_l_loop_return_summary_for_node1(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                zero_state=zero_state,
                input_ref=l_result.source_trace_ids,
                source_data_ids=l_result.output_data_ids,
                id_namespace=l_run_ids,
            )
            node0_return_data_ids.append(node0_return_data_id)
            l_return_summary_data_ids.append(l_return_summary_data_id)
            document_material_data_ids.append(
                document_material_packet_frame_data_id(id_namespace=l_run_ids)
            )
            append_movement(
                node_id="node_0",
                mode="loop_return_summary",
                input_trace_ids=l_result.source_trace_ids,
                output_trace_ids=[node0_return_trace_id],
                input_data_ids=l_result.output_data_ids,
                output_data_ids=[
                    node0_return_data_id,
                    l_return_summary_data_id,
                    document_material_data_ids[-1],
                ],
            )

            if node_1_router_adapter is not None:
                decision = route_next_with_llm_or_policy_fallback(
                    user_input="L루프가 끝났다. 최종 메타정보 경계와 보고 단계로 갈지 판단해줘.",
                    memory_packet=packet_after_l,
                    schema_registry=schema_registry,
                    adapter=node_1_router_adapter,
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    input_ref=[node0_return_trace_id],
                    source_data_ids=[node0_return_data_id, l_return_summary_data_id],
                    fallback_user_input="보고",
                    fallback_policy=node_1_router_fallback_policy,
                    fallback_allowed_by_runtime_policy=allow_node_1_router_fallback,
                )
            else:
                decision = route_next(
                    user_input="보고",
                    memory_packet=packet_after_l,
                    schema_registry=schema_registry,
                )
            return_route_input_ref = _unique_strings([node0_return_trace_id, decision.llm_trace_event_id])
            return_route_source_data_ids = _unique_strings(
                [node0_return_data_id, l_return_summary_data_id, decision.llm_call_data_id]
            )
            return_route_trace_id = record_routing(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                decision=decision,
                input_ref=return_route_input_ref,
                source_data_ids=return_route_source_data_ids,
                id_namespace=l_run_ids,
                route_context="l_return",
            )
            return_route_data_id = l_run_ids.return_route_decision_id(decision.route)
            route_data_ids.append(return_route_data_id)
            set_current_route(unified_state, decision.route)
            set_active_schema(unified_state, decision.required_schema)
            append_movement(
                node_id="node_1",
                mode="routing_after_l_return",
                input_trace_ids=return_route_input_ref,
                output_trace_ids=[return_route_trace_id],
                input_data_ids=return_route_source_data_ids,
                output_data_ids=[return_route_data_id],
            )

            controller_trace_id, controller_data_id, controller_frame = (
                run_same_turn_l_reroute_controller(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    run_ids=l_run_ids,
                    policy=policy,
                    node1_route=decision.route,
                    route_data_id=return_route_data_id,
                    return_summary_data_id=l_return_summary_data_id,
                    return_packet_data_id=node0_return_data_id,
                    source_trace_ids=[node0_return_trace_id, return_route_trace_id],
                    source_data_ids=[
                        node0_return_data_id,
                        l_return_summary_data_id,
                        return_route_data_id,
                    ],
                )
            )
            reroute_controller_data_ids.append(controller_data_id)
            final_reroute_controller = controller_frame
            append_movement(
                node_id="L_reroute_controller",
                mode="same_turn_l_reroute_policy",
                input_trace_ids=[node0_return_trace_id, return_route_trace_id],
                output_trace_ids=[controller_trace_id],
                input_data_ids=[node0_return_data_id, l_return_summary_data_id, return_route_data_id],
                output_data_ids=[controller_data_id],
            )

            if controller_frame.controller_decision == "rerun_L":
                current_run_index = controller_frame.next_run_index or (current_run_index + 1)
                current_l_input_trace_ids = [return_route_trace_id, controller_trace_id]
                current_l_source_data_ids = [return_route_data_id, controller_data_id]
                continue

            if decision.route == "2":
                route2_trace_id = return_route_trace_id
                route2_data_id = return_route_data_id
            else:
                close_decision = route_next(
                    user_input="보고",
                    memory_packet=packet_after_l,
                    schema_registry=schema_registry,
                )
                route2_input_ref = [controller_trace_id]
                route2_source_data_ids = [
                    controller_data_id,
                    node0_return_data_id,
                    l_return_summary_data_id,
                    return_route_data_id,
                ]
                route2_trace_id = record_routing(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    decision=close_decision,
                    input_ref=route2_input_ref,
                    source_data_ids=route2_source_data_ids,
                    id_namespace=l_run_ids,
                    route_context="l_return",
                )
                route2_data_id = l_run_ids.return_route_decision_id(close_decision.route)
                route_data_ids.append(route2_data_id)
                set_current_route(unified_state, close_decision.route)
                set_active_schema(unified_state, close_decision.required_schema)
                append_movement(
                    node_id="node_1",
                    mode="routing_policy_close_to_2",
                    input_trace_ids=route2_input_ref,
                    output_trace_ids=[route2_trace_id],
                    input_data_ids=route2_source_data_ids,
                    output_data_ids=[route2_data_id],
                )
            break
    else:
        route2_trace_id = route_trace_id
        route2_data_id = route_data_id

    # 5. 1 -> 2 직전 0이 최종 trace 패킷을 준다.
    packet_for_2 = supply_memory(
        target="node_2",
        mode="final_trace_for_2",
        zero_state=zero_state,
        trace_store=trace_store,
        turn_id=turn_id,
    )
    node0_final_trace_id = record_memory_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        packet=packet_for_2,
        mode="final_trace_for_2",
        input_ref=[route2_trace_id],
        source_data_ids=[route2_data_id],
        id_namespace=l_run_ids,
    )
    node0_final_data_id = (
        l_run_ids.memory_packet_data_id(target="node_2", mode="final_trace_for_2")
        if l_run_ids is not None
        else memory_packet_data_id("node_2", "final_trace_for_2")
    )
    append_movement(
        node_id="node_0",
        mode="final_trace_for_2",
        input_trace_ids=[route2_trace_id],
        output_trace_ids=[node0_final_trace_id],
        input_data_ids=[route2_data_id],
        output_data_ids=[node0_final_data_id],
    )

    # 6. 0이 이번 턴의 규칙 기반 종료 상태를 남긴다.
    outcome_id = (
        l_run_ids.turn_outcome_id(turn_id)
        if l_run_ids is not None
        else f"turn_outcome:{turn_id}"
    )
    outcome = TurnOutcomeFrame(
        outcome_id=outcome_id,
        turn_id=turn_id,
        status="completed_without_llm_judgement",
        decided_by="node_0",
        source_trace_ids=[node0_final_trace_id],
        source_data_ids=[node0_final_data_id],
    )
    validate_turn_outcome_frame(outcome)
    outcome_trace = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="turn_outcome",
        input_ref=[node0_final_trace_id],
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
    append_movement(
        node_id="node_0",
        mode="turn_outcome",
        input_trace_ids=[node0_final_trace_id],
        output_trace_ids=[outcome_trace.event_id],
        input_data_ids=[node0_final_data_id],
        output_data_ids=[outcome_id],
    )

    # 7. 0이 2가 읽을 입력 범위를 명시한 프레임을 만든다.
    node2_input_id = (
        l_run_ids.node2_input_frame_id(turn_id)
        if l_run_ids is not None
        else f"node2_input:{turn_id}"
    )
    node2_source_data_ids = _unique_strings(
        [
            node0_pre_data_id,
            memory_relevance_selection_data_id,
            selected_memory_context_data_id,
            *route_data_ids,
            *node0_l_data_ids,
            *l_loop_output_ids,
            *node0_return_data_ids,
            *l_return_summary_data_ids,
            *document_material_data_ids,
            *reroute_controller_data_ids,
            node0_final_data_id,
            outcome_id,
        ]
    )
    node2_input_frame = Node2InputFrame(
        frame_id=node2_input_id,
        turn_id=turn_id,
        final_memory_packet_id=node0_final_data_id,
        turn_outcome_id=outcome_id,
        route_ids=_unique_strings(route_data_ids),
        l_loop_output_ids=_unique_strings(l_loop_output_ids),
        source_trace_ids=[event.event_id for event in trace_store.events_for_turn(turn_id)],
        source_data_ids=node2_source_data_ids,
    )
    validate_node2_input_frame(node2_input_frame)
    node2_input_trace = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=[node0_final_trace_id, outcome_trace.event_id],
        output_ref=[node2_input_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=node2_input_id,
        data_type="node_output:node2_input_frame",
        exists=True,
        created_at=node2_input_trace.timestamp,
        source_trace_id=node2_input_trace.event_id,
        payload=asdict(node2_input_frame),
    )
    append_movement(
        node_id="node_0",
        mode="node2_input_frame",
        input_trace_ids=[node0_final_trace_id, outcome_trace.event_id],
        output_trace_ids=[node2_input_trace.event_id],
        input_data_ids=[node0_final_data_id, outcome_id],
        output_data_ids=[node2_input_id],
    )

    # 8. route=2 진입 조건을 0/code 권한으로 검사하고 2에게 넘길 handoff를 기록한다.
    handoff_trace_id, handoff_data_id = record_route2_handoff(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_input,
        node2_input_frame_id=node2_input_id,
        node2_input_trace_id=node2_input_trace.event_id,
        final_memory_packet_id=node0_final_data_id,
        turn_outcome_id=outcome_id,
        route_ids=_unique_strings(route_data_ids),
        l_loop_output_ids=_unique_strings(l_loop_output_ids),
        memory_relevance_selection_frame_id=memory_relevance_selection_data_id,
        selected_recent_memory_context_frame_id=selected_memory_context_data_id,
        id_namespace=l_run_ids,
    )
    append_movement(
        node_id="node_0",
        mode="route2_handoff",
        input_trace_ids=[node2_input_trace.event_id],
        output_trace_ids=[handoff_trace_id],
        input_data_ids=[node2_input_id, memory_relevance_selection_data_id, selected_memory_context_data_id],
        output_data_ids=[handoff_data_id],
    )

    # 9. 2가 Node2InputFrame 기준으로 절대정보 경계를 만든다.
    boundary = build_metainfo_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        node2_input_frame_id=node2_input_id,
    )
    boundary_id = (
        l_run_ids.metainfo_boundary_id()
        if l_run_ids is not None
        else "boundary_dry_001"
    )
    boundary_trace_id = record_boundary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        boundary_id=boundary_id,
        boundary=boundary,
        input_ref=[node2_input_trace.event_id],
    )
    node2_review_trace_id: str | None = None
    node2_review_data_id: str | None = None
    if node_2_boundary_adapter is not None:
        node2_review_trace_id = run_node2_boundary_review(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            boundary_id=boundary_id,
            boundary=boundary,
            adapter=node_2_boundary_adapter,
            input_ref=[boundary_trace_id],
            source_data_ids=[boundary_id, node2_input_id, handoff_data_id, selected_memory_context_data_id],
        )
        node2_review_data_id = "node_2:boundary_review"
    set_metainfo_boundary_id(unified_state, boundary_id)
    answer_basis_trace_id, answer_basis_data_id, answer_basis_frame = (
        run_node2_answer_basis_selection(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            user_question=user_input,
            boundary_id=boundary_id,
            boundary=boundary,
            handoff_frame_id=handoff_data_id,
            adapter=node_2_boundary_adapter,
            input_ref=_unique_strings([boundary_trace_id, node2_review_trace_id, handoff_trace_id]),
            source_data_ids=_unique_strings(
                [
                    node2_input_id,
                    handoff_data_id,
                    boundary_id,
                    node2_review_data_id,
                    selected_memory_context_data_id,
                ]
            ),
            id_namespace=l_run_ids,
        )
    )
    assigned_model_by_node = _assigned_model_by_node(
        node_1_router_adapter=node_1_router_adapter,
        memory_relevance_selector_label=memory_relevance_selection_frame.generated_by,
        l1_goal_adapter=l1_goal_adapter,
        l_tool_scope_adapter=l_tool_scope_adapter,
        l2_query_planner_adapter=l2_query_planner_adapter,
        l3_result_adapter=l3_result_adapter,
        node_2_boundary_adapter=node_2_boundary_adapter,
        node_3_reporter_adapter=node_3_reporter_adapter,
        node_4_gatekeeper_adapter=node_4_gatekeeper_adapter,
    )
    node2_brief_preview_movement = make_node_movement(
        movement_id=f"move_{next_step_index:03d}_preview",
        turn_id=turn_id,
        step_index=next_step_index,
        node_id="node_2",
        mode="metainfo_boundary_answer_basis_and_node3_brief",
        input_trace_ids=_unique_strings([handoff_trace_id, node2_input_trace.event_id]),
        output_trace_ids=_unique_strings([boundary_trace_id, node2_review_trace_id, answer_basis_trace_id]),
        input_data_ids=_unique_strings([handoff_data_id, node2_input_id]),
        output_data_ids=_unique_strings([boundary_id, node2_review_data_id, answer_basis_data_id]),
        status="completed",
    )
    brief_trace_id, brief_data_id, brief_frame = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question=user_input,
        handoff_frame_id=handoff_data_id,
        boundary=boundary,
        input_trace_ids=_unique_strings(
            [handoff_trace_id, boundary_trace_id, node2_review_trace_id, answer_basis_trace_id]
        ),
        source_data_ids=_unique_strings(
            [
                node2_input_id,
                handoff_data_id,
                boundary_id,
                node2_review_data_id,
                answer_basis_data_id,
                selected_memory_context_data_id,
            ]
        ),
        answer_basis_frame=answer_basis_frame,
        runtime_movements=[*movements, node2_brief_preview_movement],
        assigned_model_by_node=assigned_model_by_node,
        id_namespace=l_run_ids,
    )
    append_movement(
        node_id="node_2",
        mode="metainfo_boundary_answer_basis_and_node3_brief",
        input_trace_ids=_unique_strings([handoff_trace_id, node2_input_trace.event_id]),
        output_trace_ids=_unique_strings(
            [boundary_trace_id, node2_review_trace_id, answer_basis_trace_id, brief_trace_id]
        ),
        input_data_ids=_unique_strings([handoff_data_id, node2_input_id]),
        output_data_ids=_unique_strings(
            [boundary_id, node2_review_data_id, answer_basis_data_id, brief_data_id]
        ),
    )

    # 10. 3이 내부 ID를 제거한 node_3용 브리프를 보고 답변한다.
    report_source_trace_ids = [brief_trace_id]
    report_source_data_ids = _unique_strings([brief_data_id, handoff_data_id, boundary_id, answer_basis_data_id, outcome_id, node2_input_id, node2_review_data_id, selected_memory_context_data_id])
    report_generation_source = "CODE/RENDERER"
    llm_reporter_status = "not_run"
    if node_3_reporter_adapter is not None:
        try:
            report_draft = render_report_with_llm(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                brief_frame=brief_frame,
                adapter=node_3_reporter_adapter,
                input_ref=_unique_strings([brief_trace_id, node2_review_trace_id]),
                source_data_ids=report_source_data_ids,
            )
            report = report_draft.rendered_markdown
            report_source_trace_ids = report_draft.source_trace_ids
            report_source_data_ids = report_draft.source_data_ids
            report_generation_source = report_draft.generation_source
            llm_reporter_status = report_draft.llm_reporter_status
        except Exception:
            report = render_report(turn_id=turn_id, boundary=boundary)
    else:
        report = render_report(turn_id=turn_id, boundary=boundary)
    report_id = (
        l_run_ids.node3_report_id()
        if l_run_ids is not None
        else "report_dry_001"
    )
    report_trace_id = record_report(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        report_id=report_id,
        rendered_markdown=report,
        allowed_info_ids=[data_ref.data_id for data_ref in boundary.absolute_info],
        allowed_relative_info_ids=[info_ref.info_id for info_ref in boundary.relative_info],
        allowed_mixed_info_ids=[info_ref.info_id for info_ref in boundary.mixed_info],
        input_ref=report_source_trace_ids,
        source_data_ids=report_source_data_ids,
        report_generation_source=report_generation_source,
        llm_reporter_status=llm_reporter_status,
    )
    append_movement(
        node_id="node_3",
        mode="report",
        input_trace_ids=report_source_trace_ids,
        output_trace_ids=[report_trace_id],
        input_data_ids=report_source_data_ids,
        output_data_ids=[report_id],
    )

    node4_gate_trace_id: str | None = None
    node4_gate_data_id: str | None = None
    if node_4_gatekeeper_adapter is not None:
        node4_gate_trace_id = run_node4_gatekeeper(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            report_id=report_id,
            boundary_id=boundary_id,
            brief_frame=brief_frame,
            rendered_markdown=report,
            adapter=node_4_gatekeeper_adapter,
            input_ref=[report_trace_id],
            source_data_ids=[report_id, brief_data_id, boundary_id, answer_basis_data_id],
            id_namespace=l_run_ids,
        )
        node4_gate_data_id = (
            l_run_ids.node4_gatekeeper_frame_id()
            if l_run_ids is not None
            else "node_4:gatekeeper_frame"
        )
        append_movement(
            node_id="node_4",
            mode="gatekeeper",
            input_trace_ids=[report_trace_id],
            output_trace_ids=[node4_gate_trace_id],
            input_data_ids=[report_id],
            output_data_ids=[node4_gate_data_id],
        )

    # 11. 현재 순차 동선을 task 장부로 기록한다.
    task_ledger_trace_id, task_ledger_data_ids = record_task_ledger_from_movements(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        movements=movements,
        assigned_model_by_node=assigned_model_by_node,
    )

    # 12. trace를 state와 capsule에 반영한다.
    sync_trace_ids_from_store(unified_state, trace_store)
    set_current_turn_trace_ids(zero_state, trace_store, turn_id)
    capsule = build_turn_capsule(
        trace_store,
        turn_id,
        node_movements=movements,
        final_response_trace_id=node4_gate_trace_id or report_trace_id,
    )
    add_capsule_to_zero_state(zero_state, capsule)
    graph_memory_record = record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        capsules=zero_state.previous_turn_capsules,
        batch_id=turn_id,
    )

    # prompt_registry는 지금 실제 실행에 쓰이지 않지만, 드라이런에 구성품이 있음을 확인한다.
    prompt_registry.get("node_0")
    task_counts = task_ledger_counts(data_store)
    graph_snapshot = graph_memory_record.build.snapshot
    graph_guide = graph_memory_record.build.guide_packet
    (
        r_loop_memory_handoff_trace_id,
        r_loop_memory_handoff_data_id,
        r_loop_memory_handoff_frame,
    ) = record_r_loop_memory_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        guide_packet=graph_guide,
        input_ref=[graph_memory_record.trace_event_id],
        source_data_ids=[graph_snapshot.snapshot_id, graph_guide.packet_id],
        semantic_hint_status=graph_guide.recommended_traversal_hints_status,
    )
    r_loop_dry_run_result = None
    if enable_r_route_dry_run:
        r_loop_dry_run_result = run_r_loop_dry_run_skeleton(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            handoff_packet=r_loop_memory_handoff_frame,
            input_ref=[r_loop_memory_handoff_trace_id],
            force_budget_exhausted=r_route_dry_run_force_budget_exhausted,
        )

    result = {
        "turn_id": turn_id,
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "relative_info_count": len(boundary.relative_info),
        "mixed_info_count": len(boundary.mixed_info),
        "data_ids": [record.data_id for record in data_store.list_records()],
        "data_records": data_store.to_records(),
        "movement_count": len(movements),
        "task_ledger_trace_id": task_ledger_trace_id,
        "task_ledger_data_ids": task_ledger_data_ids,
        "task_frame_count": task_counts["task_frame_count"],
        "task_result_count": task_counts["task_result_count"],
        "current_route": unified_state.current_route,
        "capsule_trace_count": len(capsule.trace_event_ids),
        "turn_capsule": asdict(capsule),
        "recent_capsule_read_window": RECENT_TURN_CAPSULE_READ_WINDOW,
        "recent_capsules_read_count": previous_turn_capsules_read_count,
        "recent_raw_conversation_alignment_window": RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW,
        "recent_raw_conversation_alignment_count": recent_raw_conversation_alignment_count,
        "recent_raw_conversation_max_window": RECENT_RAW_CONVERSATION_MAX_WINDOW,
        "recent_raw_conversation_min_guarantee": RECENT_RAW_CONVERSATION_MIN_GUARANTEE,
        "raw_memory_post_compression_keep": RAW_MEMORY_POST_COMPRESSION_KEEP,
        "raw_memory_compression_batch_size": RAW_MEMORY_COMPRESSION_BATCH_SIZE,
        "raw_memory_compression_candidate_frame_id": (
            node0_pre_compression_candidate_frame.frame_id
        ),
        "raw_memory_compression_candidate_status": (
            node0_pre_compression_candidate_frame.candidate_status
        ),
        "raw_memory_compression_candidate_turn_ids": (
            node0_pre_compression_candidate_frame.candidate_turn_ids
        ),
        "raw_memory_retained_raw_turn_ids": (
            node0_pre_compression_candidate_frame.retained_raw_turn_ids
        ),
        "older_unmanaged_raw_turn_count": (
            node0_pre_compression_candidate_frame.older_unmanaged_raw_turn_count
        ),
        "recent_memory_relevance_candidate_window": RECENT_MEMORY_RELEVANCE_CANDIDATE_WINDOW,
        "recent_memory_relevance_candidate_count": len(node0_pre_relevance_candidate_frames),
        "recent_memory_relevance_selection_frame_id": memory_relevance_selection_data_id,
        "recent_memory_relevance_selection_status": memory_relevance_selection_frame.selection_status,
        "recent_memory_relevance_selection_candidate_count": len(
            memory_relevance_selection_frame.candidate_frame_ids
        ),
        "recent_memory_relevance_selection_selected_count": len(
            memory_relevance_selection_frame.selected_candidate_frame_ids
        ),
        "recent_memory_relevance_selection_llm_call_data_id": (
            memory_relevance_selection_frame.llm_call_data_id
        ),
        "selected_recent_memory_context_frame_id": selected_memory_context_data_id,
        "selected_recent_memory_context_count": (
            selected_memory_context_frame.selected_turn_count
        ),
        "missing_selected_memory_context_count": (
            selected_memory_context_frame.missing_selected_memory_context_count
        ),
        "graph_memory_snapshot_id": graph_snapshot.snapshot_id,
        "graph_memory_node_count": len(graph_snapshot.graph_node_ids),
        "graph_memory_edge_count": len(graph_snapshot.graph_edge_ids),
        "graph_memory_node_kind_counts": graph_snapshot.node_kind_counts,
        "graph_memory_data_kind_counts": graph_snapshot.data_kind_counts,
        "graph_memory_raw_capsule_node_count": graph_snapshot.node_kind_counts.get(
            "raw_capsule",
            0,
        ),
        "graph_memory_time_bundle_count": graph_snapshot.node_kind_counts.get(
            "time_bundle",
            0,
        ),
        "graph_memory_record_trace_id": graph_memory_record.trace_event_id,
        "graph_memory_created_data_ids": graph_memory_record.created_data_ids,
        "graph_memory_existing_data_ids": graph_memory_record.existing_data_ids,
        "rloop_graph_guide_packet_id": graph_guide.packet_id,
        "rloop_graph_guide_target_consumer": graph_guide.target_consumer,
        "rloop_graph_guide_entry_node_count": len(graph_guide.available_entry_nodes),
        "rloop_graph_guide_available_entry_nodes": graph_guide.available_entry_nodes,
        "rloop_graph_guide_summary_depth_range": graph_guide.summary_depth_range,
        "rloop_graph_guide_source_leaf_count_range": graph_guide.source_leaf_count_range,
        "rloop_graph_guide_risky_or_unreviewed_node_count": len(
            graph_guide.risky_or_unreviewed_node_ids
        ),
        "rloop_graph_guide_generated_by": graph_guide.generated_by,
        "rloop_graph_guide_info_class": graph_guide.info_class,
        "rloop_graph_guide_semantic_judgement_status": (
            graph_guide.semantic_judgement_status
        ),
        "rloop_graph_guide_hints_status": graph_guide.recommended_traversal_hints_status,
        "r_loop_memory_handoff_trace_id": r_loop_memory_handoff_trace_id,
        "r_loop_memory_handoff_packet_id": r_loop_memory_handoff_data_id,
        "r_loop_memory_handoff_status": r_loop_memory_handoff_frame.packet_status,
        "r_loop_memory_handoff_target": r_loop_memory_handoff_frame.target,
        "r_loop_memory_handoff_mode": r_loop_memory_handoff_frame.mode,
        "r_loop_memory_handoff_guide_packet_id": (
            r_loop_memory_handoff_frame.r_loop_graph_guide_packet_id
        ),
        "r_loop_memory_handoff_entry_node_count": len(
            r_loop_memory_handoff_frame.available_entry_node_ids
        ),
        "r_loop_memory_handoff_source_graph_node_count": len(
            r_loop_memory_handoff_frame.source_graph_node_ids
        ),
        "r_loop_memory_handoff_summary_depth_range": (
            r_loop_memory_handoff_frame.summary_depth_range
        ),
        "r_loop_memory_handoff_semantic_hint_status": (
            r_loop_memory_handoff_frame.semantic_hint_status
        ),
        "r_loop_memory_handoff_generated_by": r_loop_memory_handoff_frame.generated_by,
        "r_loop_memory_handoff_info_class": r_loop_memory_handoff_frame.info_class,
        "r_loop_memory_handoff_semantic_judgement_status": (
            r_loop_memory_handoff_frame.semantic_judgement_status
        ),
        "r_route_dry_run_enabled": enable_r_route_dry_run,
        "r_route_dry_run_status": (
            r_loop_dry_run_result.return_summary.r_loop_task_status
            if r_loop_dry_run_result is not None
            else "not_run"
        ),
        "r_route_dry_run_continuation_status": (
            r_loop_dry_run_result.continuation.continuation_status
            if r_loop_dry_run_result is not None
            else "not_run"
        ),
        "r_route_dry_run_next_target_node": (
            r_loop_dry_run_result.continuation.next_target_node
            if r_loop_dry_run_result is not None
            else "not_run"
        ),
        "r_route_dry_run_output_data_ids": (
            r_loop_dry_run_result.output_data_ids
            if r_loop_dry_run_result is not None
            else []
        ),
        "r_route_dry_run_trace_event_ids": (
            r_loop_dry_run_result.trace_event_ids
            if r_loop_dry_run_result is not None
            else []
        ),
        "r_route_dry_run_selected_entry_node_ids": (
            r_loop_dry_run_result.return_summary.selected_entry_node_ids
            if r_loop_dry_run_result is not None
            else []
        ),
        "r_route_dry_run_inspected_graph_node_ids": (
            r_loop_dry_run_result.return_summary.inspected_graph_node_ids
            if r_loop_dry_run_result is not None
            else []
        ),
        "r_route_dry_run_budget_status": (
            r_loop_dry_run_result.return_summary.budget_status
            if r_loop_dry_run_result is not None
            else "not_run"
        ),
        "llm_call_count": _count_records_by_type(data_store, "llm_call"),
        "tool_choice_count": _count_records_by_type(data_store, "tool_choice"),
        "tool_result_count": _count_records_with_type_prefix(data_store, "tool_result:"),
        "tool_distillation_count": _count_records_with_type_prefix(
            data_store,
            "tool_result_distillation:",
        ),
        "tool_budget_frame_count": _count_records_by_type(data_store, "tool_use_budget"),
        "l_loop_budget_plan_count": _count_records_by_type(
            data_store,
            "node_output:l_loop_budget_plan_frame",
        ),
        "search_top_k": search_top_k,
        "max_query_attempts": max_query_candidates
        if max_query_candidates is not None
        else max_query_attempts,
        "max_document_context_chars": max_document_context_chars,
        "l_loop_run_count": len(l_results),
        "same_turn_l_reroute_enabled": same_turn_l_reroute_enabled,
        "max_l_runs_per_turn": max_l_runs_per_turn,
        "effective_max_l_runs_per_turn": policy.effective_max_l_runs_per_turn,
        "same_turn_rerun_allowed": (
            final_reroute_controller.same_turn_rerun_allowed
            if final_reroute_controller is not None
            else False
        ),
        "rerun_block_reason": (
            final_reroute_controller.decision_reason
            if final_reroute_controller is not None
            else None
        ),
        "planned_next_step": (
            final_reroute_controller.planned_next_step
            if final_reroute_controller is not None
            else None
        ),
        "reroute_controller_data_ids": reroute_controller_data_ids,
        "reroute_controller_decision": (
            final_reroute_controller.controller_decision
            if final_reroute_controller is not None
            else None
        ),
        "reroute_controller_reason": (
            final_reroute_controller.decision_reason
            if final_reroute_controller is not None
            else None
        ),
        "l_loop_final_decision": last_l_result.final_control_decision if last_l_result is not None else None,
        "l_loop_final_continuation_status": last_l_result.final_continuation_status if last_l_result is not None else None,
        "l_loop_continuation_count": len(last_l_result.continuation_data_ids) if last_l_result is not None else 0,
        "l_loop_revision_query_count": len(last_l_result.revision_query_data_ids) if last_l_result is not None else 0,
        "l2_query_source": _read_l2_query_source(data_store),
        "node1_llm_routing_count": _count_node1_llm_routes(data_store),
        "node1_llm_routing_failed_count": _count_node1_llm_failed_routes(data_store),
        "node1_router_fallback_count": _count_node1_router_fallbacks(data_store),
        "node1_router_fallback_policy": node_1_router_fallback_policy,
        "l1_goal_generation_source": _read_payload_text(data_store, "L1:goal_frame", "goal_generation_source"),
        "l3_achievement_generation_source": _read_payload_text(
            data_store,
            "L3:achievement_frame",
            "achievement_generation_source",
        ),
        "route2_handoff_status": _read_payload_text(
            data_store,
            "node_2:handoff_frame",
            "handoff_status",
            data_type="node_output:node2_handoff_frame",
        ),
        "node3_brief_status": _read_payload_text(
            data_store,
            "node_3:input_brief_frame",
            "brief_status",
            data_type="node_output:node3_input_brief_frame",
        ),
        "node2_answer_basis_mode": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_mode",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_generated_by": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "generated_by",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_reason_codes": _read_payload_string_list(
            data_store,
            "node_2:answer_basis_frame",
            "basis_reason_codes",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_semantic_judgement_status": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "semantic_judgement_status",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_failure_type": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_failure_type",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_llm_call_data_id": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_llm_call_data_id",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_trace_event_id": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_trace_event_id",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_validation_error": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_validation_error",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_raw_text_present": _read_payload_bool(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_raw_text_present",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_prompt_ref": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_prompt_ref",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node2_answer_basis_payload_parse_status": _read_payload_text(
            data_store,
            "node_2:answer_basis_frame",
            "answer_basis_payload_parse_status",
            data_type="node_output:node2_answer_basis_frame",
        ),
        "node3_reporter_status": _read_payload_text(
            data_store,
            "report_dry_001",
            "llm_reporter_status",
            data_type="node_output:report",
        ),
        "node4_gate_status": _read_payload_text(
            data_store,
            "node_4:gatekeeper_frame",
            "gate_status",
            data_type="node_output:node4_gatekeeper_frame",
        ),
        "node4_recent_memory_guard_status": _read_payload_text(
            data_store,
            "node_4:gatekeeper_frame",
            "recent_memory_guard_status",
            data_type="node_output:node4_gatekeeper_frame",
        ),
        "node4_unsupported_recent_memory_claim_count": _read_payload_int(
            data_store,
            "node_4:gatekeeper_frame",
            "unsupported_recent_memory_claim_count",
            data_type="node_output:node4_gatekeeper_frame",
        ),
        "force_l_route": force_l_route,
        "report": report,
    }
    if export_dir is not None:
        exported = export_runtime_artifacts(
            output_dir=export_dir,
            trace_store=trace_store,
            data_store=data_store,
            report=report,
            summary={
                key: value
                for key, value in result.items()
                if key not in {"data_records", "report"}
            },
        )
        result["export_dir"] = str(exported)
    return result


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

def _count_records_by_type(data_store: DataStore, data_type: str) -> int:
    return sum(1 for record in data_store.list_records() if record.data_type == data_type)


def _count_records_with_type_prefix(data_store: DataStore, prefix: str) -> int:
    return sum(1 for record in data_store.list_records() if record.data_type.startswith(prefix))


def _read_l2_query_source(data_store: DataStore) -> str | None:
    record = data_store.get_record("L2:query_frame")
    if record is None:
        record = _latest_record_by_type(data_store, "node_output:L2_query_frame")
    if record is None or not isinstance(record.payload, dict):
        return None
    query_source = record.payload.get("query_source")
    return query_source if isinstance(query_source, str) else None


def _count_node1_llm_routes(data_store: DataStore) -> int:
    return _count_node1_routes_with_field(
        data_store,
        field_name="llm_routing_status",
        expected_value="ran",
    )


def _count_node1_llm_failed_routes(data_store: DataStore) -> int:
    return _count_node1_routes_with_field(
        data_store,
        field_name="llm_routing_status",
        expected_value="failed",
    )


def _count_node1_router_fallbacks(data_store: DataStore) -> int:
    return _count_node1_routes_with_field(
        data_store,
        field_name="fallback_after_llm_failure",
        expected_value=True,
    )


def _count_node1_routes_with_field(
    data_store: DataStore,
    *,
    field_name: str,
    expected_value: object,
) -> int:
    count = 0
    for record in data_store.list_records():
        if record.data_type != "node_output:routing_decision":
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get(field_name) == expected_value:
            count += 1
    return count


def _read_payload_text(
    data_store: DataStore,
    data_id: str,
    field_name: str,
    *,
    data_type: str | None = None,
) -> str | None:
    record = data_store.get_record(data_id)
    if record is None and data_type is not None:
        record = _latest_record_by_type(data_store, data_type)
    if record is None or not isinstance(record.payload, dict):
        return None
    value = record.payload.get(field_name)
    return value if isinstance(value, str) else None


def _read_payload_int(
    data_store: DataStore,
    data_id: str,
    field_name: str,
    *,
    data_type: str | None = None,
) -> int | None:
    record = data_store.get_record(data_id)
    if record is None and data_type is not None:
        record = _latest_record_by_type(data_store, data_type)
    if record is None or not isinstance(record.payload, dict):
        return None
    value = record.payload.get(field_name)
    return value if isinstance(value, int) else None


def _read_payload_bool(
    data_store: DataStore,
    data_id: str,
    field_name: str,
    *,
    data_type: str | None = None,
) -> bool | None:
    record = data_store.get_record(data_id)
    if record is None and data_type is not None:
        record = _latest_record_by_type(data_store, data_type)
    if record is None or not isinstance(record.payload, dict):
        return None
    value = record.payload.get(field_name)
    return value if isinstance(value, bool) else None


def _read_payload_string_list(
    data_store: DataStore,
    data_id: str,
    field_name: str,
    *,
    data_type: str | None = None,
) -> list[str] | None:
    record = data_store.get_record(data_id)
    if record is None and data_type is not None:
        record = _latest_record_by_type(data_store, data_type)
    if record is None or not isinstance(record.payload, dict):
        return None
    value = record.payload.get(field_name)
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, str)]


def _latest_record_by_type(data_store: DataStore, data_type: str):
    for record in reversed(data_store.list_records()):
        if record.data_type == data_type:
            return record
    return None


def _adapter_label(adapter: LLMAdapter | None, *, fallback: str) -> str:
    if adapter is None:
        return fallback
    model_id = getattr(adapter, "model_id", None)
    return f"LLM:{model_id}" if isinstance(model_id, str) and model_id else "LLM:unknown"


def _loop_adapter_label(
    *,
    l1_goal_adapter: LLMAdapter | None,
    l_tool_scope_adapter: LLMAdapter | None,
    l2_query_planner_adapter: LLMAdapter | None,
    l3_result_adapter: LLMAdapter | None,
) -> str:
    labels = [
        _adapter_label(l1_goal_adapter, fallback="L1:CODE/RULE_STUB"),
        _adapter_label(l_tool_scope_adapter, fallback="L_scope:CODE/FALLBACK"),
        _adapter_label(l2_query_planner_adapter, fallback="L2:CODE/FALLBACK"),
        _adapter_label(l3_result_adapter, fallback="L3:CODE/OPERATION_CHECK"),
    ]
    unique_labels = _unique_strings(labels)
    return unique_labels[0] if len(unique_labels) == 1 else "mixed:" + ",".join(unique_labels)


def _assigned_model_by_node(
    *,
    node_1_router_adapter: LLMAdapter | None,
    memory_relevance_selector_label: str,
    l1_goal_adapter: LLMAdapter | None,
    l_tool_scope_adapter: LLMAdapter | None,
    l2_query_planner_adapter: LLMAdapter | None,
    l3_result_adapter: LLMAdapter | None,
    node_2_boundary_adapter: LLMAdapter | None,
    node_3_reporter_adapter: LLMAdapter | None,
    node_4_gatekeeper_adapter: LLMAdapter | None,
) -> dict[str, str]:
    return {
        "node_0": "CODE:RULE_STUB",
        "node_1": _adapter_label(node_1_router_adapter, fallback="CODE:RULE_STUB"),
        "memory_relevance_selector": memory_relevance_selector_label,
        "L": _loop_adapter_label(
            l1_goal_adapter=l1_goal_adapter,
            l_tool_scope_adapter=l_tool_scope_adapter,
            l2_query_planner_adapter=l2_query_planner_adapter,
            l3_result_adapter=l3_result_adapter,
        ),
        "node_2": _adapter_label(node_2_boundary_adapter, fallback="CODE+OPTIONAL_LLM"),
        "node_3": _adapter_label(node_3_reporter_adapter, fallback="CODE/RENDERER"),
        "node_4": _adapter_label(node_4_gatekeeper_adapter, fallback="not_scheduled"),
    }


if __name__ == "__main__":
    result = run_dry_turn()
    print("DRY_RUN_OK")
    print(f"turn_id={result['turn_id']}")
    print(f"trace_count={result['trace_count']}")
    print(f"data_record_count={result['data_record_count']}")
    print(f"movement_count={result['movement_count']}")
    print(f"task_frame_count={result['task_frame_count']}")
    print(f"current_route={result['current_route']}")
    print(f"capsule_trace_count={result['capsule_trace_count']}")
    print(result["report"])
