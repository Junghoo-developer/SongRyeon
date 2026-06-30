from __future__ import annotations


def render_runtime_view(result: dict[str, object], *, user_input: str) -> str:
    """터미널에서 사람이 봐야 할 내부 처리만 짧게 보여준다.

    이 함수는 최종 답변을 만들지 않는다. 역할은 trace/data에 남은
    생성자, 정보 등급, 출처, 의미판단 여부를 사람이 읽을 수 있게 펴는 것이다.
    """

    records = _records_by_id(result)
    llm_call_ids = _llm_call_ids_by_node(result)
    lines = [
        "[runtime]",
        f"- 입력: {user_input}",
        f"- 모델: {_runtime_model(result)}",
        f"- 상태: {result.get('status', 'unknown')}",
        f"- trace/data: {result.get('trace_count', 0)} / {result.get('data_record_count', 0)}",
    ]
    if result.get("status") == "structure_failed":
        lines.extend(_structure_failure_runtime_lines(result))
    session_memory = result.get("session_memory")
    if isinstance(session_memory, dict):
        lines.append(
            "- session_memory: "
            f"recent_raw_conversation={session_memory.get('recent_raw_conversation_count', 0)} / "
            f"previous_turn_capsules={session_memory.get('previous_turn_capsule_count', 0)} / "
            f"current_turn_id={session_memory.get('current_turn_id', result.get('turn_id', 'unknown'))}"
        )

    task_frames = _payloads_with_type(result, "task_ledger:task_frame")
    task_results = _payloads_with_type(result, "task_ledger:task_result_frame")
    if task_frames:
        first_policy = task_frames[0].get("scheduling_policy", "unknown")
        first_worker = task_frames[0].get("assigned_worker_id", "unknown")
        lines.append(
            "- task ledger: "
            f"tasks={len(task_frames)} / results={len(task_results)} / "
            f"policy={first_policy} / worker={first_worker}"
        )
        for task in task_frames[:5]:
            lines.append(
                "  - "
                f"{task.get('task_id', 'unknown')} "
                f"{task.get('node_id', 'unknown')}:{task.get('mode', 'unknown')} "
                f"status={task.get('status', 'unknown')} "
                f"model={task.get('assigned_model_id', 'unknown')}"
            )
        if len(task_frames) > 5:
            lines.append(f"  - ... +{len(task_frames) - 5} tasks")

    l_loop_run_frames = _payloads_with_type(result, "node_output:L_loop_run_frame")
    if l_loop_run_frames:
        lines.append(
            "- L 실행 구분: "
            f"actual_l_runs={len(l_loop_run_frames)} / "
            f"top_level_l_reroute_request_blocked={_blocked_same_turn_l_reroute_request_count(result)} / "
            f"l_internal_revision={_l_internal_revision_state(result)}"
        )
        lines.append("- L loop run namespace:")
        for frame in l_loop_run_frames:
            lines.append(
                "  - "
                f"run={frame.get('run_index', '?')} / "
                f"policy={frame.get('namespace_policy', 'unknown')} / "
                f"same_turn_rerun_allowed={frame.get('same_turn_rerun_allowed', False)}"
            )
            block_reason = frame.get("rerun_block_reason")
            if isinstance(block_reason, str) and block_reason:
                lines.append(f"    block_reason: {block_reason}")
            planned_next_step = frame.get("planned_next_step")
            if isinstance(planned_next_step, str) and planned_next_step:
                lines.append(f"    next: {planned_next_step}")
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by="CODE:L_LOOP_RUN_FRAME",
                    info_class="absolute_policy_state",
                    source_data_ids=_source_data_ids(frame, fallback=[str(frame.get("frame_id") or "L:run_frame")]),
                    semantic_judgement_status="not_run",
                )
            )

    reroute_controller_frames = _payloads_with_type(
        result,
        "node_output:same_turn_l_reroute_controller_frame",
    )
    if reroute_controller_frames:
        lines.append("- L same-turn reroute controller:")
        for frame in reroute_controller_frames:
            lines.append(
                "  - "
                f"controller={frame.get('controller_id', 'unknown')} / "
                f"run={frame.get('current_run_index', '?')} -> "
                f"{frame.get('next_run_index', 'route_2')} / "
                f"node1_route={frame.get('node1_route', 'unknown')} / "
                f"decision={frame.get('controller_decision', 'unknown')}"
            )
            lines.append(
                "    policy: "
                f"enabled={frame.get('same_turn_l_reroute_enabled', False)} / "
                f"max={frame.get('effective_max_l_runs_per_turn', frame.get('max_l_runs_per_turn', '?'))} / "
                f"allowed={frame.get('same_turn_rerun_allowed', False)}"
            )
            lines.append(f"    reason: {frame.get('decision_reason', '')}")
            lines.append(f"    next: {frame.get('planned_next_step', '')}")
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(frame.get("generated_by") or "CODE:SAME_TURN_L_REROUTE_CONTROLLER"),
                    info_class=str(frame.get("info_class") or "absolute_policy_decision"),
                    source_data_ids=_source_data_ids(
                        frame,
                        fallback=[str(frame.get("controller_id") or "L:reroute_controller")],
                    ),
                    semantic_judgement_status=str(
                        frame.get("semantic_judgement_status") or "not_run"
                    ),
                )
            )

    memory_packets = _payloads_with_type(result, "node_output:memory_packet")
    if memory_packets:
        lines.append("- 0 기억 공급 [CODE:RULE_STUB | LLM_SUMMARY=not_run]:")
        for packet in memory_packets:
            target = packet.get("target", "unknown")
            mode = packet.get("mode", "unknown")
            evidence_count = _list_count(packet.get("evidence_trace_ids"))
            memory_items = packet.get("memory_items")
            previous_capsule_count = _memory_item_type_count(
                memory_items,
                "previous_turn_capsule_index",
            )
            raw_alignment_count = _memory_item_type_count(
                memory_items,
                "recent_raw_conversation_capsule_alignment",
            )
            relevance_candidate_count = _list_count(packet.get("relevance_candidate_frames"))
            compression_candidate_frames = packet.get("compression_candidate_frames")
            compression_candidate_count = _list_count(compression_candidate_frames)
            operation_label = packet.get("operation_label") or packet.get("compression_summary")
            source = packet.get("packet_id", "unknown")
            relevance_suffix = (
                f" / relevance_candidates {relevance_candidate_count}개"
                if relevance_candidate_count
                else ""
            )
            compression_suffix = (
                f" / compression_frames {compression_candidate_count}개"
                if compression_candidate_count
                else ""
            )
            lines.append(
                f"  - source={source} / {mode} -> {target}: "
                f"trace {evidence_count}개{relevance_suffix}{compression_suffix} "
                f"/ operation_label={operation_label}"
            )
            if previous_capsule_count or raw_alignment_count or relevance_candidate_count:
                lines.append(
                    "    "
                    "memory_items: "
                    f"previous_turn_capsule_index={previous_capsule_count} / "
                    f"recent_raw_conversation_capsule_alignment={raw_alignment_count} / "
                    f"recent_memory_relevance_candidate={relevance_candidate_count}"
                )
            if isinstance(compression_candidate_frames, list):
                for frame in compression_candidate_frames:
                    if not isinstance(frame, dict):
                        continue
                    lines.append(
                        "    "
                        "raw_memory_window: "
                        f"status={frame.get('candidate_status', 'unknown')} / "
                        f"raw={frame.get('raw_conversation_count', 0)} / "
                        f"candidate={_list_count(frame.get('candidate_turn_ids'))} / "
                        f"retained={_list_count(frame.get('retained_raw_turn_ids'))} / "
                        f"older={frame.get('older_unmanaged_raw_turn_count', 0)}"
                    )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(packet.get("generated_by") or "CODE:RULE_STUB"),
                    info_class="absolute",
                    source_data_ids=_source_data_ids(packet, fallback=[source]),
                    semantic_judgement_status=str(
                        packet.get("llm_semantic_summary_status") or "not_run"
                    ),
                )
            )

    graph_guides = _payloads_with_type(result, "graph_memory:rloop_guide_packet")
    if graph_guides:
        lines.append("- graph memory guide:")
        for guide in graph_guides:
            guide_id = str(guide.get("packet_id") or "unknown")
            lines.append(
                "  - "
                f"source={guide_id} / "
                f"snapshot={guide.get('graph_snapshot_id', 'unknown')} / "
                f"target={guide.get('target_consumer', 'unknown')} / "
                f"entries={_list_count(guide.get('available_entry_nodes'))} / "
                f"hints={guide.get('recommended_traversal_hints_status', 'unknown')}"
            )
            lines.append(
                "    "
                f"node_kinds={guide.get('node_kind_counts', {})} / "
                f"summary_depth_range={guide.get('summary_depth_range', [])} / "
                f"source_leaf_count_range={guide.get('source_leaf_count_range', [])}"
            )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(
                        guide.get("generated_by") or "CODE:GRAPH_MEMORY_GUIDE_BUILDER"
                    ),
                    info_class=str(guide.get("info_class") or "absolute"),
                    source_data_ids=_source_data_ids(guide, fallback=[guide_id]),
                    semantic_judgement_status=str(
                        guide.get("semantic_judgement_status") or "not_run"
                    ),
                )
            )

    r_loop_handoffs = _payloads_with_type(
        result,
        "node_output:r_loop_memory_handoff_packet_frame",
    )
    if r_loop_handoffs:
        lines.append("- R loop memory handoff:")
        for packet in r_loop_handoffs:
            packet_id = str(packet.get("packet_id") or "unknown")
            depth_range = packet.get("summary_depth_range")
            if isinstance(depth_range, list) and len(depth_range) == 2:
                depth_display = f"{depth_range[0]}..{depth_range[1]}"
            else:
                depth_display = "unknown"
            lines.append(
                "  - "
                f"status={packet.get('packet_status', 'unknown')} / "
                f"target={packet.get('target', 'unknown')} / "
                f"mode={packet.get('mode', 'unknown')} / "
                f"entry_nodes={_list_count(packet.get('available_entry_node_ids'))} / "
                f"summary_depth_range={depth_display} / "
                f"semantic_hint_status={packet.get('semantic_hint_status', 'unknown')}"
            )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(
                        packet.get("generated_by") or "CODE:node_0_memory_supplier"
                    ),
                    info_class=str(packet.get("info_class") or "absolute"),
                    source_data_ids=_source_data_ids(packet, fallback=[packet_id]),
                    semantic_judgement_status=str(
                        packet.get("semantic_judgement_status") or "not_run"
                    ),
                )
            )

    r_return_summaries = _payloads_with_type(result, "node_output:R_loop_return_summary_frame")
    if r_return_summaries:
        r_continuations = _payloads_with_type(result, "node_output:R_loop_continuation_frame")
        lines.append("- R dry-run skeleton [CODE:R_LOOP_DRY_RUN_ONLY]:")
        for summary in r_return_summaries:
            continuation_status = summary.get("continuation_status", "unknown")
            next_target = "unknown"
            if r_continuations:
                next_target = str(r_continuations[-1].get("next_target_node") or "unknown")
            lines.append(
                "  - "
                f"task_status={summary.get('r_loop_task_status', 'unknown')} / "
                f"selected_entries={_list_count(summary.get('selected_entry_node_ids'))} / "
                f"inspected_nodes={_list_count(summary.get('inspected_graph_node_ids'))} / "
                f"continuation={continuation_status} / "
                f"next={next_target} / "
                f"budget={summary.get('budget_status', 'unknown')}"
            )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(summary.get("generated_by") or "CODE:R_LOOP_DRY_RUN_ONLY"),
                    info_class=str(summary.get("info_class") or "absolute"),
                    source_data_ids=_source_data_ids(
                        summary,
                        fallback=[str(summary.get("frame_id") or "R:return_summary")],
                    ),
                    semantic_judgement_status=str(
                        summary.get("semantic_judgement_status") or "not_run"
                    ),
                )
            )

    relevance_selection_frames = _payloads_with_type(
        result,
        "node_output:memory_relevance_selection_frame",
    )
    if relevance_selection_frames:
        lines.append("- 최근 기억 selector:")
        for frame in relevance_selection_frames:
            lines.append(
                "  - "
                "memory_relevance_selection: "
                f"status={frame.get('selection_status', 'unknown')} / "
                f"candidates={_list_count(frame.get('candidate_frame_ids'))} / "
                f"selected={_list_count(frame.get('selected_candidate_frame_ids'))} / "
                f"generated_by={frame.get('generated_by', 'unknown')}"
            )
            lines.append(
                "    "
                f"source={frame.get('frame_id', 'unknown')} / "
                f"judged_by={frame.get('judged_by')} / "
                f"llm_call={frame.get('llm_call_data_id')} / "
                f"reason={frame.get('selection_reason', '')}"
            )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(frame.get("generated_by") or "unknown"),
                    info_class=str(frame.get("info_class") or "unknown"),
                    source_data_ids=_source_data_ids(
                        frame,
                        fallback=[
                            str(
                                frame.get("source_memory_packet_id")
                                or "memory_packet:node_1:pre_route_report"
                            )
                        ],
                    ),
                    semantic_judgement_status=(
                        "ran"
                        if frame.get("judged_by")
                        else str(frame.get("selection_status") or "not_run")
                    ),
                )
            )

    selected_context_frames = _payloads_with_type(
        result,
        "node_output:selected_recent_memory_context_frame",
    )
    if selected_context_frames:
        lines.append("- selected recent memory context:")
        for frame in selected_context_frames:
            items = frame.get("items")
            copied_count = _list_count(items)
            missing_count = frame.get("missing_selected_memory_context_count", 0)
            lines.append(
                "  - "
                f"status={frame.get('selection_status', 'unknown')} / "
                f"copied={copied_count} / "
                f"missing={missing_count} / "
                f"generated_by={frame.get('generated_by', 'unknown')}"
            )
            if isinstance(items, list):
                for item in items[:3]:
                    if not isinstance(item, dict):
                        continue
                    lines.append(
                        "    "
                        f"turn={item.get('source_turn_id', 'unknown')} / "
                        f"user_chars={item.get('raw_user_text_chars', 0)}"
                        f"{' truncated' if item.get('raw_user_text_truncated') else ''} / "
                        f"assistant_chars={item.get('raw_assistant_text_chars', 0)}"
                        f"{' truncated' if item.get('raw_assistant_text_truncated') else ''}"
                    )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(
                        frame.get("generated_by")
                        or "CODE:SELECTED_RECENT_MEMORY_CONTEXT_BUILDER"
                    ),
                    info_class=str(frame.get("info_class") or "absolute_copied_context"),
                    source_data_ids=_source_data_ids(
                        frame,
                        fallback=[str(frame.get("selection_frame_id") or "")],
                    ),
                    semantic_judgement_status=str(
                        frame.get("semantic_judgement_status") or "not_run"
                    ),
                )
            )

    route_frames = _payloads_with_type(result, "node_output:routing_decision")
    if route_frames:
        lines.append("- 1 라우팅:")
        for route in route_frames:
            route_source_id = str(route.get("frame_id") or "unknown")
            lines.append(
                f"  - source={route_source_id} / route={route.get('route', 'unknown')} "
                f"/ route_source={route.get('route_source', 'unknown')} "
                f"/ next_0={route.get('expected_next_0_mode', 'unknown')}"
            )
            lines.append(
                f"    route_rule_id={route.get('route_rule_id', '')} "
                f"/ matched_keywords={route.get('matched_keywords', [])} "
                f"/ policy_flag={route.get('policy_flag')}"
            )
            lines.append(f"    node_1 router: {_node1_router_status(route)}")
            if route.get("fallback_after_llm_failure") is True:
                lines.append(
                    "    fallback: "
                    f"policy={route.get('fallback_policy', 'unknown')} / "
                    f"allowed={route.get('fallback_allowed_by_runtime_policy', False)} / "
                    f"failure_type={route.get('router_llm_failure_type', 'unknown')} / "
                    f"fallback_rule={route.get('fallback_source_route_rule_id', 'unknown')}"
                )
                lines.append(
                    "    failure_source: "
                    f"data={route.get('router_llm_failure_data_id')} / "
                    f"trace={route.get('router_llm_failure_trace_event_id')}"
                )
            lines.extend(
                _metainfo_lines(
                    indent=4,
                    generated_by=str(route.get("route_source") or "CODE:RULE_STUB"),
                    info_class="mixed" if route.get("llm_routing_status") == "ran" else "absolute",
                    source_data_ids=_source_data_ids(route, fallback=[route_source_id]),
                    semantic_judgement_status=str(route.get("llm_routing_status") or "not_run"),
                )
            )

    l1_goal_record = _latest_run_scoped_record(
        result,
        records,
        "L1:goal_frame",
        data_type="node_output:L1_goal_frame",
    )
    l1_goal = _payload_from_record(l1_goal_record)
    if l1_goal:
        l1_goal_source_id = str(l1_goal_record.get("data_id") or "L1:goal_frame")
        lines.append(
            "- L1 목표: "
            f"[{l1_goal.get('goal_generation_source', 'RULE_STUB')} | "
            f"LLM_GOAL={l1_goal.get('llm_goal_judgement_status', 'not_run')} | source={l1_goal_source_id}]"
        )
        lines.append(f"  - 거시: {l1_goal.get('macro_goal', '')}")
        macro_reason = l1_goal.get("macro_goal_reason")
        if isinstance(macro_reason, str) and macro_reason:
            reason_label = "LLM_reason" if l1_goal.get("llm_goal_judgement_status") == "ran" else "stub_label"
            lines.append(f"    {reason_label}: {macro_reason}")
        lines.append(f"  - 미시: {l1_goal.get('micro_goal', '')}")
        micro_reason = l1_goal.get("micro_goal_reason")
        if isinstance(micro_reason, str) and micro_reason:
            reason_label = "LLM_reason" if l1_goal.get("llm_goal_judgement_status") == "ran" else "stub_label"
            lines.append(f"    {reason_label}: {micro_reason}")
        evidence_kind = l1_goal.get("evidence_requirement_kind")
        if isinstance(evidence_kind, str) and evidence_kind:
            lines.append(
                "  - 근거 요구: "
                f"kind={evidence_kind} / "
                f"min_read={l1_goal.get('minimum_read_documents', 0)} / "
                f"cross_doc={l1_goal.get('requires_cross_document_analysis', False)} / "
                f"randomness={l1_goal.get('randomness_mode', 'not_random')}"
            )
        success_condition = l1_goal.get("l_loop_success_condition")
        if isinstance(success_condition, str) and success_condition:
            lines.append(f"    성공 조건: {success_condition}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(l1_goal.get("goal_generation_source") or "RULE_STUB"),
                    info_class="mixed" if l1_goal.get("llm_goal_judgement_status") == "ran" else "absolute_stub",
                source_data_ids=_source_data_ids(l1_goal, fallback=[l1_goal_source_id]),
                semantic_judgement_status=str(
                    l1_goal.get("llm_goal_judgement_status") or "not_run"
                ),
            )
        )

    query_plan_record = _latest_run_scoped_record(
        result,
        records,
        "L2:query_plan_frame",
        data_type="node_output:L2_query_plan_frame",
    )
    query_plan = _payload_from_record(query_plan_record)
    query_plan_source_id = str(query_plan_record.get("data_id") or "L2:query_plan_frame")
    selected_candidate = _selected_query_candidate(query_plan)
    if selected_candidate:
        l2_sources = _source_data_ids(
            query_plan,
            fallback=[query_plan_source_id, *llm_call_ids.get("L2", [])],
        )
        lines.append(
            f"- L2 계획 [LLM:{_runtime_model_id(result)} | SCHEMA_PASSED | source={query_plan_source_id}]: "
            f"{selected_candidate.get('query_text', '')} "
            f"(출처: {result.get('l2_query_source', 'unknown')})"
        )
        purpose = selected_candidate.get("purpose")
        if isinstance(purpose, str) and purpose:
            lines.append(f"  - LLM 목적: {purpose}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=f"LLM:{_runtime_model_id(result)}",
                info_class="mixed",
                source_data_ids=l2_sources,
                semantic_judgement_status="llm_query_plan_ran",
            )
        )
    else:
        query_frame_record = _latest_run_scoped_record(
            result,
            records,
            "L2:query_frame",
            data_type="node_output:L2_query_frame",
        )
        query_frame = _payload_from_record(query_frame_record)
        query_frame_source_id = str(query_frame_record.get("data_id") or "L2:query_frame")
        query_text = query_frame.get("query_text")
        if isinstance(query_text, str) and query_text:
            lines.append(
                "- L2 검색어 [CODE/FALLBACK | LLM_PLAN=not_available]: "
                f"{query_text} "
                f"(출처: {query_frame.get('query_source', 'unknown')})"
            )
            lines.extend(
                _metainfo_lines(
                    indent=2,
                    generated_by="CODE/FALLBACK",
                    info_class="code_policy_fallback",
                    source_data_ids=_source_data_ids(query_frame, fallback=[query_frame_source_id]),
                    semantic_judgement_status="LLM_PLAN=not_available",
                )
            )

    search_record = _latest_record_with_type_prefix(result, "tool_result:search_docs")
    search_payload = _payload_from_record(search_record)
    if search_payload:
        search_data_id = str(search_record.get("data_id") or "tool_result:search_docs")
        lines.append(
            f"- search_docs [TOOL_RESULT | source={search_data_id}]: "
            f"{search_payload.get('result_count', 0)}개 후보"
            f"(top_k={search_payload.get('top_k', '?')}), "
            f"문서 {search_payload.get('document_count', '?')}개 / "
            f"chunk {search_payload.get('chunk_count', '?')}개 색인"
        )
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by="TOOL:search_docs",
                info_class="absolute_tool_result",
                source_data_ids=[search_data_id],
                semantic_judgement_status="not_run",
            )
        )
        top_docs = _top_search_docs(search_payload, limit=3)
        if top_docs:
            lines.append("- 상위 후보:")
            for index, item in enumerate(top_docs, start=1):
                score = item.get("score")
                score_text = f", score={score}" if isinstance(score, (int, float)) else ""
                lines.append(
                    f"  {index}. {item.get('doc_id', '')}"
                    f" [{item.get('document_kind', 'unknown')}/{item.get('source_role', 'unknown')}{score_text}]"
                )

    explicit_frames = _payloads_with_type(result, "node_output:explicit_artifact_reference_frame")
    if explicit_frames:
        frame = explicit_frames[-1]
        extracted_count = frame.get("extracted_reference_count", 0)
        if isinstance(extracted_count, int) and extracted_count > 0:
            lines.append("- explicit_artifact_refs:")
            resolved = frame.get("resolved_references")
            if isinstance(resolved, list):
                for item in resolved[:10]:
                    if not isinstance(item, dict):
                        continue
                    status = item.get("resolve_status", "unknown")
                    raw_ref = item.get("raw_ref", "")
                    selected_doc_id = item.get("selected_doc_id")
                    if status == "unique" and isinstance(selected_doc_id, str):
                        lines.append(f"  - {raw_ref} -> unique: {selected_doc_id}")
                    elif status == "ambiguous":
                        lines.append(
                            f"  - {raw_ref} -> ambiguous: "
                            f"{item.get('candidate_count', 0)} candidates"
                        )
                    else:
                        lines.append(f"  - {raw_ref} -> {status}")
                if len(resolved) > 10:
                    lines.append(f"  - ... +{len(resolved) - 10} refs")
            lines.extend(
                _metainfo_lines(
                    indent=2,
                    generated_by=str(frame.get("generated_by") or "CODE:EXPLICIT_ARTIFACT_RESOLVER"),
                    info_class=str(frame.get("info_class") or "absolute_resolve_result"),
                    source_data_ids=_source_data_ids(
                        frame,
                        fallback=[str(frame.get("frame_id") or "L:explicit_artifact_reference_frame")],
                    ),
                    semantic_judgement_status=str(
                        frame.get("semantic_judgement_status") or "not_run"
                    ),
                )
            )

    for read_record in _document_extract_records_for_display(result):
        read_payload = _payload_from_record(read_record)
        if not read_payload:
            continue
        read_data_id = str(read_record.get("data_id") or "tool_result:document_extract")
        read_tool_name = _document_extract_tool_name(read_record)
        lines.append(
            f"- {read_tool_name} [TOOL_RESULT:DOCUMENT_EXTRACT | source={read_data_id}]: "
            f"{read_payload.get('doc_id', '')} "
            f"({read_payload.get('char_count', '?')}자)"
        )
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=f"TOOL:{read_tool_name}",
                info_class="absolute_document_extract",
                source_data_ids=[read_data_id],
                semantic_judgement_status="not_run",
                copied_from=f"{read_data_id}.payload.text",
                selection_method=f"{read_tool_name}_payload",
                truncated=False,
            )
        )

    document_context_pack_frames = _payloads_with_type(
        result,
        "node_output:document_context_pack_frame",
    )
    if document_context_pack_frames:
        frame = document_context_pack_frames[-1]
        included_count = frame.get("included_document_count", 0)
        excluded_count = frame.get("excluded_document_count", 0)
        included_chars = frame.get("included_total_chars", 0)
        max_chars = frame.get("max_document_context_chars", "?")
        lines.append("- document_context_pack:")
        lines.append(
            "  - "
            f"included={included_count} / excluded={excluded_count} / "
            f"budget={included_chars}/{max_chars} {frame.get('budget_unit', 'chars')}"
        )
        lines.append(
            "  - "
            f"whole_document_only={str(frame.get('whole_document_only', False)).lower()} / "
            f"strict_rank_order={str(frame.get('strict_rank_order', False)).lower()} / "
            f"cutoff={frame.get('cutoff_reason', 'none')}"
        )
        included_documents = frame.get("included_documents")
        if isinstance(included_documents, list) and included_documents:
            lines.append("  - included:")
            for item in included_documents[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    "    - "
                    f"{item.get('rank_index', '?')}. {item.get('doc_id', '')} "
                    f"({item.get('char_count', 0)} chars, {item.get('selection_basis', '')})"
                )
            if len(included_documents) > 5:
                lines.append(f"    - ... +{len(included_documents) - 5} included")
        excluded_documents = frame.get("excluded_documents")
        if isinstance(excluded_documents, list) and excluded_documents:
            lines.append("  - excluded:")
            for item in excluded_documents[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    "    - "
                    f"{item.get('rank_index', '?')}. {item.get('doc_id', '')} "
                    f"({item.get('char_count', 0)} chars, {item.get('exclusion_reason', '')})"
                )
            if len(excluded_documents) > 5:
                lines.append(f"    - ... +{len(excluded_documents) - 5} excluded")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(frame.get("generated_by") or "CODE:DOCUMENT_CONTEXT_PACKER"),
                info_class=str(frame.get("info_class") or "absolute_context_packing_result"),
                source_data_ids=_source_data_ids(
                    frame,
                    fallback=[str(frame.get("frame_id") or "L:document_context_pack_frame")],
                ),
                semantic_judgement_status=str(
                    frame.get("semantic_judgement_status") or "not_run"
                ),
            )
        )

    document_material_frames = _payloads_with_type(
        result,
        "node_output:node0_document_material_packet_frame",
    )
    if document_material_frames:
        frame = document_material_frames[-1]
        lines.append("- node_0 document material packet:")
        lines.append(
            "  - "
            f"items={frame.get('item_count', 0)} / "
            f"search_candidates={frame.get('search_candidate_count', 0)} / "
            f"actual_read={frame.get('actual_tool_read_doc_count', 0)} / "
            f"supplied_contexts={frame.get('supplied_document_context_count', 0)} / "
            f"unread_candidates={frame.get('unread_candidate_count', 0)}"
        )
        items = frame.get("items")
        if isinstance(items, list) and items:
            lines.append("  - items:")
            for item in items[:5]:
                if not isinstance(item, dict):
                    continue
                roles = item.get("source_roles")
                role_text = ",".join(roles) if isinstance(roles, list) else ""
                lines.append(
                    "    - "
                    f"{item.get('document_name', item.get('doc_id', ''))} "
                    f"[{role_text}]"
                )
            if len(items) > 5:
                lines.append(f"    - ... +{len(items) - 5} items")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(
                    frame.get("generated_by") or "CODE:NODE0_DOCUMENT_MATERIAL_PACKET"
                ),
                info_class=str(frame.get("info_class") or "absolute_material_index"),
                source_data_ids=_source_data_ids(
                    frame,
                    fallback=[str(frame.get("frame_id") or "node_0:document_material_packet_frame")],
                ),
                semantic_judgement_status=str(
                    frame.get("semantic_judgement_status") or "not_run"
                ),
            )
        )

    budget_plan_payloads = _payloads_with_type(result, "node_output:l_loop_budget_plan_frame")
    if budget_plan_payloads:
        budget_plan = budget_plan_payloads[-1]
        lines.append("- L budget plan [CODE:BUDGET_POLICY | ABSOLUTE_POLICY]:")
        lines.append(
            "  - requested:"
            f" tool_calls={budget_plan.get('requested_max_tool_calls', 0)}"
            f" / query_attempts={budget_plan.get('requested_max_query_attempts', 0)}"
            f" / search_top_k={budget_plan.get('requested_search_top_k', 0)}"
            f" / read_doc={budget_plan.get('requested_max_read_doc_calls', 0)}"
        )
        lines.append(
            "  - approved:"
            f" tool_calls={budget_plan.get('approved_max_tool_calls', '?')}"
            f" / query_attempts={budget_plan.get('approved_max_query_attempts', '?')}"
            f" / search_top_k={budget_plan.get('approved_search_top_k', '?')}"
            f" / read_doc={budget_plan.get('approved_max_read_doc_calls', '?')}"
        )
        lines.append(
            "  - ceilings:"
            f" tool_calls={budget_plan.get('max_tool_calls_ceiling', '?')}"
            f" / query_attempts={budget_plan.get('max_query_attempts_ceiling', '?')}"
            f" / search_top_k={budget_plan.get('search_top_k_ceiling', '?')}"
            f" / read_doc={budget_plan.get('max_read_doc_calls_ceiling', '?')}"
        )
        reason = budget_plan.get("approval_reason") or "unknown"
        lines.append(f"  - approval_reason: {reason}")
        request_reason = budget_plan.get("budget_request_reason")
        if request_reason:
            lines.append(f"  - L1 request reason: {request_reason}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by="CODE:BUDGET_POLICY",
                info_class="absolute_policy_decision",
                source_data_ids=[str(budget_plan.get("goal_data_id") or "L1:goal_frame")],
                semantic_judgement_status="not_run",
            )
        )

    tool_scope_payloads = _payloads_with_type(result, "node_output:L_tool_scope_frame")
    if tool_scope_payloads:
        scope = tool_scope_payloads[-1]
        lines.append("- L tool scope:")
        lines.append(
            "  -"
            f" mode={scope.get('tool_scope_mode', 'unknown')}"
            f" / groups={scope.get('allowed_tool_groups', [])}"
            f" / materials={scope.get('required_materials', [])}"
        )
        reason = scope.get("scope_reason")
        if reason:
            lines.append(f"  - reason: {reason}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(scope.get("generated_by") or "unknown"),
                info_class=str(scope.get("info_class") or "unknown"),
                source_data_ids=_source_data_ids(
                    scope,
                    fallback=[str(scope.get("frame_id") or "L:tool_scope_frame")],
                ),
                semantic_judgement_status=str(scope.get("semantic_judgement_status") or "unknown"),
            )
        )

    partition_payloads = _payloads_with_type(result, "node_output:L_tool_budget_partition_frame")
    if partition_payloads:
        partition = partition_payloads[-1]
        lines.append("- L tool budget partition [CODE]:")
        lines.append(
            "  - document:"
            f" tool={partition.get('document_tool_call_budget', 0)}"
            f" / query={partition.get('document_query_budget', 0)}"
            f" / read={partition.get('document_read_budget', 0)}"
        )
        lines.append(
            "  - code:"
            f" tool={partition.get('code_tool_call_budget', 0)}"
            f" / query={partition.get('code_query_budget', 0)}"
            f" / read={partition.get('code_read_budget', 0)}"
        )
        runtime_budget = partition.get("runtime_record_budget", 0)
        if runtime_budget:
            lines.append(f"  - runtime_record_budget={runtime_budget}")
        lines.append(f"  - reason: {partition.get('partition_reason', 'unknown')}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(partition.get("generated_by") or "CODE:L_TOOL_BUDGET_PARTITION_POLICY"),
                info_class=str(partition.get("info_class") or "absolute_policy_decision"),
                source_data_ids=_source_data_ids(
                    partition,
                    fallback=[str(partition.get("frame_id") or "L:tool_budget_partition_frame")],
                ),
                semantic_judgement_status=str(partition.get("semantic_judgement_status") or "not_run"),
            )
        )

    budget_payloads = _payloads_with_type(result, "tool_use_budget")
    if budget_payloads:
        latest_budget = budget_payloads[-1]
        lines.append(
            "- L 도구 예산:"
            f" tool_calls={latest_budget.get('tool_call_count', 0)}/{latest_budget.get('max_tool_calls', '?')}"
            f" / query_attempts={latest_budget.get('query_count', 0)}/{latest_budget.get('max_query_attempts', '?')}"
            f" / search_top_k={latest_budget.get('search_top_k', '?')}"
            f" / read_doc={latest_budget.get('read_doc_count', 0)}/{latest_budget.get('max_read_doc_calls', '?')}"
            f" / stop_reason={latest_budget.get('stop_reason', 'unknown')}"
        )
        old_name = latest_budget.get("max_query_candidates")
        new_name = latest_budget.get("max_query_attempts")
        if old_name == new_name:
            lines.append("  - note: max_query_candidates는 호환용 옛 이름이고 현재 의미는 max_query_attempts야.")

    continuation_frames = _payloads_with_type(result, "node_output:L_loop_continuation_frame")
    if continuation_frames:
        lines.append("- L continuation:")
        for frame in continuation_frames:
            lines.append(
                "  - "
                f"attempt={frame.get('attempt_index', '?')}/{frame.get('max_attempts', '?')} "
                f"status={frame.get('continuation_status', 'unknown')} "
                f"next={frame.get('next_target_node', 'unknown')}"
            )
            lines.append(f"    reason: {frame.get('continuation_reason_code', '')}")
            lines.append(
                "    source: "
                f"L3={frame.get('source_l3_achievement_id', '')} / "
                f"L2={frame.get('source_l2_query_frame_id', '')}"
            )

    return_summaries = _payloads_with_type(result, "node_output:l_loop_return_summary_frame")
    if return_summaries:
        frame = return_summaries[-1]
        lines.append("- 0 -> 1 L루프 반환 요약:")
        lines.append(
            "  - "
            f"task={frame.get('l_loop_task_status', 'unknown')} "
            f"/ failure_level={frame.get('failure_level', 'unknown')} "
            f"/ route_hint={frame.get('recommended_next_route_for_node1', 'none')}"
        )
        lines.append(
            "  - evidence: "
            f"kind={frame.get('evidence_requirement_kind', 'unspecified')} "
            f"/ required_read={frame.get('required_min_read_documents', 0)} "
            f"/ actual_read_doc={frame.get('actual_read_doc_count', 0)} "
            f"/ actual_read_code_file={frame.get('actual_read_code_file_count', 0)} "
            f"/ candidates={frame.get('search_candidate_count', 0)}"
        )
        lines.append(
            "  - budget: "
            f"stop={frame.get('budget_stop_reason', 'unknown')} "
            f"/ remaining_tool={frame.get('remaining_tool_calls', 0)} "
            f"/ remaining_read={frame.get('remaining_read_doc_calls', 0)} "
            f"/ remaining_query={frame.get('remaining_query_attempts', 0)}"
        )
        lines.append(f"  - route_hint_reason: {frame.get('route_hint_reason', '')}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by="CODE:ZERO_RETURN_SUMMARY",
                info_class="absolute_summary_from_structured_records",
                source_data_ids=_source_data_ids(frame, fallback=["L:return_summary_frame"]),
                semantic_judgement_status="not_run",
            )
        )

    revision_queries = _payloads_with_type(result, "node_output:L2_revision_query_frame")
    if revision_queries:
        lines.append("- L2 revision query:")
        for frame in revision_queries:
            lines.append(
                "  - "
                f"{frame.get('frame_id', 'unknown')} "
                f"tool={frame.get('target_tool_name', 'unknown')} "
                f"source={frame.get('query_source', 'unknown')}"
            )
            lines.append(f"    query: {frame.get('query_text', '')}")

    revision_achievements = _payloads_with_type(result, "node_output:L3_revision_achievement_frame")
    if revision_achievements:
        lines.append("- L3 revision recheck:")
        for frame in revision_achievements:
            lines.append(
                "  - "
                f"{frame.get('frame_id', 'unknown')} "
                f"status={frame.get('achievement_status', 'unknown')} "
                f"candidates={frame.get('candidate_count', 0)} "
                f"LLM_SEMANTIC={frame.get('llm_semantic_judgement_status', 'not_run')}"
            )
            lines.append(f"    reason: {frame.get('reason', '')}")

    achievement_record = _latest_run_scoped_record(
        result,
        records,
        "L3:achievement_frame",
        data_type="node_output:L3_achievement_frame",
    )
    achievement = _payload_from_record(achievement_record)
    if achievement:
        achievement_source_id = str(achievement_record.get("data_id") or "L3:achievement_frame")
        lines.append(
            "- L3 달성 판단 "
            f"[{achievement.get('achievement_generation_source', 'CODE:OPERATION_CHECK')} | "
            f"LLM_SEMANTIC={achievement.get('llm_semantic_judgement_status', 'not_run')}]: "
            f"{achievement.get('achievement_status', 'unknown')} / "
            f"{achievement.get('controller_decision', 'unknown')}"
        )
        macro_status = achievement.get("macro_achievement_status")
        macro_reason = achievement.get("macro_achievement_reason")
        micro_status = achievement.get("micro_achievement_status")
        micro_reason = achievement.get("micro_achievement_reason")
        if macro_status or macro_reason or micro_status or micro_reason:
            lines.append("- L3 목표 운영 체크:")
            lines.append(
                f"  - 거시: {achievement.get('target_macro_goal', '')} "
                f"=> operation_{macro_status or achievement.get('achievement_status', 'unknown')}"
            )
            if isinstance(macro_reason, str) and macro_reason:
                reason_label = "LLM_reason" if achievement.get("llm_semantic_judgement_status") == "ran" else "operation_label"
                lines.append(f"    {reason_label}: {macro_reason}")
            lines.append(
                f"  - 미시: {achievement.get('target_micro_goal', '')} "
                f"=> operation_{micro_status or achievement.get('achievement_status', 'unknown')}"
            )
            if isinstance(micro_reason, str) and micro_reason:
                reason_label = "LLM_reason" if achievement.get("llm_semantic_judgement_status") == "ran" else "operation_label"
                lines.append(f"    {reason_label}: {micro_reason}")
            lines.append(f"  - LLM 의미판단: {achievement.get('llm_semantic_judgement_status', 'not_run')}")
        goal_match_status = achievement.get("goal_match_status")
        if isinstance(goal_match_status, str) and goal_match_status:
            requested_doc_hint = achievement.get("requested_doc_hint") or "none"
            lines.append(
                f"- L3 문서 목표 매칭: {goal_match_status} / hint={requested_doc_hint}"
            )
            goal_match_reason = achievement.get("goal_match_reason")
            if isinstance(goal_match_reason, str) and goal_match_reason:
                lines.append(f"  - reason: {goal_match_reason}")
            read_doc_ids = achievement.get("read_doc_ids")
            if isinstance(read_doc_ids, list) and read_doc_ids:
                lines.append(f"  - read_doc_ids: {_format_source_ids(read_doc_ids)}")
            read_code_file_paths = achievement.get("read_code_file_paths")
            if isinstance(read_code_file_paths, list) and read_code_file_paths:
                lines.append(
                    f"  - read_code_file_paths: {_format_source_ids(read_code_file_paths)}"
                )
            search_result_doc_ids = achievement.get("search_result_doc_ids")
            if isinstance(search_result_doc_ids, list) and search_result_doc_ids:
                lines.append(
                    f"  - search_result_doc_ids: {_format_source_ids(search_result_doc_ids)}"
                )
        semantic_goal_status = achievement.get("semantic_goal_match_status")
        if isinstance(semantic_goal_status, str) and semantic_goal_status:
            lines.append(f"- L3 semantic goal match: {semantic_goal_status}")
            semantic_goal_reason = achievement.get("semantic_goal_match_reason")
            if isinstance(semantic_goal_reason, str) and semantic_goal_reason:
                lines.append(f"  - reason: {semantic_goal_reason}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(achievement.get("achievement_generation_source") or "CODE:OPERATION_CHECK"),
                info_class="mixed" if achievement.get("llm_semantic_judgement_status") == "ran" else "absolute_operation_label",
                source_data_ids=_source_data_ids(achievement, fallback=[achievement_source_id]),
                semantic_judgement_status=str(
                    achievement.get("llm_semantic_judgement_status") or "not_run"
                ),
            )
        )

    route2_handoff_record = _latest_run_scoped_record(
        result,
        records,
        "node_2:handoff_frame",
        data_type="node_output:node2_handoff_frame",
    )
    route2_handoff = _payload_from_record(route2_handoff_record)
    if route2_handoff:
        lines.append(
            "- route=2 handoff: "
            f"{route2_handoff.get('handoff_status', 'unknown')} / "
            f"path={route2_handoff.get('route_path', [])}"
        )
        lines.append(
            "  - condition check: "
            f"L_run={route2_handoff.get('l_loop_was_run', False)} / "
            f"L1={route2_handoff.get('l1_goal_present', False)} / "
            f"L2={route2_handoff.get('l2_query_present', False)} / "
            f"L3={route2_handoff.get('l3_preserved_present', False)} / "
            f"search={route2_handoff.get('search_result_count', 0)} / "
            f"reportable_documents={route2_handoff.get('reportable_document_count', route2_handoff.get('read_doc_count', 0))} / "
            f"reportable_code_files={route2_handoff.get('reportable_code_file_count', 0)}"
        )
        raw_extract_count = route2_handoff.get("raw_document_extract_record_count")
        reportable_count = route2_handoff.get("reportable_document_count")
        empty_extract_count = route2_handoff.get("empty_document_extract_record_count")
        if isinstance(raw_extract_count, int) or isinstance(reportable_count, int):
            lines.append(
                "  - document counts: "
                f"reportable={reportable_count if isinstance(reportable_count, int) else route2_handoff.get('read_doc_count', 0)} / "
                f"raw_extract_records={raw_extract_count if isinstance(raw_extract_count, int) else route2_handoff.get('read_doc_count', 0)} / "
                f"empty_extract_records={empty_extract_count if isinstance(empty_extract_count, int) else 0}"
            )
        raw_code_count = route2_handoff.get("raw_code_extract_record_count")
        reportable_code_count = route2_handoff.get("reportable_code_file_count")
        empty_code_count = route2_handoff.get("empty_code_extract_record_count")
        if isinstance(raw_code_count, int) or isinstance(reportable_code_count, int):
            lines.append(
                "  - code counts: "
                f"reportable={reportable_code_count if isinstance(reportable_code_count, int) else 0} / "
                f"raw_extract_records={raw_code_count if isinstance(raw_code_count, int) else 0} / "
                f"empty_extract_records={empty_code_count if isinstance(empty_code_count, int) else 0}"
            )
        pack_frame_id = route2_handoff.get("document_context_pack_frame_id")
        if isinstance(pack_frame_id, str) and pack_frame_id:
            lines.append(
                "  - document_context_pack: "
                f"included={route2_handoff.get('document_context_included_count', 0)} / "
                f"excluded={route2_handoff.get('document_context_excluded_count', 0)} / "
                f"cutoff={route2_handoff.get('document_context_cutoff_reason', 'none')}"
            )
        memory_selection_status = route2_handoff.get("memory_relevance_selection_status")
        if isinstance(memory_selection_status, str) and memory_selection_status:
            lines.append(
                "  - memory_relevance_selection: "
                f"status={memory_selection_status} / "
                f"candidates={route2_handoff.get('memory_relevance_candidate_count', 0)} / "
                f"selected={route2_handoff.get('memory_relevance_selected_count', 0)} / "
                f"generated_by={route2_handoff.get('memory_relevance_generated_by', '')}"
            )
        actual_l_runs = route2_handoff.get("actual_l_run_count")
        blocked_l_requests = route2_handoff.get("blocked_same_turn_l_reroute_request_count")
        if isinstance(actual_l_runs, int) or isinstance(blocked_l_requests, int):
            lines.append(
                "  - L route display: "
                f"actual_l_runs={actual_l_runs if isinstance(actual_l_runs, int) else 'unknown'} / "
                f"blocked_top_level_l_requests={blocked_l_requests if isinstance(blocked_l_requests, int) else 0} / "
                f"l_internal_revision_records={route2_handoff.get('l_internal_revision_count', 0)}"
            )
        controller_decisions = route2_handoff.get("same_turn_l_reroute_controller_decisions")
        if isinstance(controller_decisions, list) and controller_decisions:
            lines.append("  - same-turn reroute controller decisions:")
            for decision in controller_decisions[:3]:
                lines.append(f"    - {decision}")
            if len(controller_decisions) > 3:
                lines.append(f"    - ... +{len(controller_decisions) - 3}")
        reasons = route2_handoff.get("insufficiency_reasons")
        if isinstance(reasons, list) and reasons:
            lines.append(f"  - insufficiency: {reasons}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by="CODE:ROUTE2_HANDOFF_CHECK",
                info_class="absolute_condition_check",
                source_data_ids=_source_data_ids(
                    route2_handoff,
                    fallback=[str(route2_handoff_record.get("data_id") or "node_2:handoff_frame")],
                ),
                semantic_judgement_status="not_run",
            )
        )

    node2_review = _payload(records, "node_2:boundary_review")
    if node2_review:
        lines.append(
            "- node_2 boundary review: "
            f"{node2_review.get('review_status', 'unknown')} / "
            f"ready={node2_review.get('ready_for_report', False)}"
        )
        summary = node2_review.get("boundary_summary")
        if isinstance(summary, str) and summary:
            lines.append(f"  - summary: {summary}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(node2_review.get("review_generation_source") or "unknown"),
                info_class="mixed",
                source_data_ids=_source_data_ids(node2_review, fallback=["node_2:boundary_review"]),
                semantic_judgement_status=str(node2_review.get("review_status") or "unknown"),
            )
        )

    answer_basis_record = _latest_run_scoped_record(
        result,
        records,
        "node_2:answer_basis_frame",
        data_type="node_output:node2_answer_basis_frame",
    )
    answer_basis = _payload_from_record(answer_basis_record)
    if answer_basis:
        lines.append(
            "- node_2 answer basis: "
            f"mode={answer_basis.get('answer_basis_mode', 'unknown')} / "
            f"generated_by={answer_basis.get('generated_by', 'unknown')} / "
            f"semantic={answer_basis.get('semantic_judgement_status', 'unknown')}"
        )
        reason_codes = answer_basis.get("basis_reason_codes")
        if isinstance(reason_codes, list) and reason_codes:
            lines.append(f"  - reason_codes: {reason_codes}")
        reason = answer_basis.get("mode_selection_reason")
        if isinstance(reason, str) and reason:
            lines.append(f"  - mode_selection_reason: {reason}")
        failure_type = answer_basis.get("answer_basis_failure_type")
        if isinstance(failure_type, str) and failure_type and failure_type != "none":
            lines.append(f"  - failure_type: {failure_type}")
            parse_status = answer_basis.get("answer_basis_payload_parse_status")
            if isinstance(parse_status, str) and parse_status:
                lines.append(f"  - payload_parse_status: {parse_status}")
            raw_text_present = answer_basis.get("answer_basis_raw_text_present")
            if isinstance(raw_text_present, bool):
                lines.append(f"  - raw_text_present: {str(raw_text_present).lower()}")
            validation_error = answer_basis.get("answer_basis_validation_error")
            if isinstance(validation_error, str) and validation_error:
                lines.append(f"  - validation_error: {_short_display_text(validation_error)}")
            llm_call_id = answer_basis.get("answer_basis_llm_call_data_id")
            if isinstance(llm_call_id, str) and llm_call_id:
                lines.append(f"  - llm_call: {llm_call_id}")
            trace_event_id = answer_basis.get("answer_basis_trace_event_id")
            if isinstance(trace_event_id, str) and trace_event_id:
                lines.append(f"  - trace_event: {trace_event_id}")
            prompt_ref = answer_basis.get("answer_basis_prompt_ref")
            if isinstance(prompt_ref, str) and prompt_ref:
                lines.append(f"  - prompt: {_display_document_name(prompt_ref)}")
        evidence_roles = answer_basis.get("evidence_roles")
        if isinstance(evidence_roles, list) and evidence_roles:
            role_summary: list[str] = []
            for role in evidence_roles[:3]:
                if not isinstance(role, dict):
                    continue
                role_summary.append(
                    f"{role.get('evidence_role', 'unknown')}:{role.get('source_data_id', '')}"
                )
            if role_summary:
                lines.append(f"  - evidence_roles: {role_summary}")
            if len(evidence_roles) > 3:
                lines.append(f"  - evidence_roles_more: {len(evidence_roles) - 3}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(answer_basis.get("generated_by") or "unknown"),
                info_class=str(answer_basis.get("info_class") or "mixed"),
                source_data_ids=_source_data_ids(
                    answer_basis,
                    fallback=[
                        str(answer_basis_record.get("data_id") or "node_2:answer_basis_frame")
                    ],
                ),
                semantic_judgement_status=str(
                    answer_basis.get("semantic_judgement_status") or "unknown"
                ),
            )
        )

    node3_brief_record = _latest_run_scoped_record(
        result,
        records,
        "node_3:input_brief_frame",
        data_type="node_output:node3_input_brief_frame",
    )
    node3_brief = _payload_from_record(node3_brief_record)
    if node3_brief:
        read_documents = node3_brief.get("read_documents")
        search_candidate_documents = node3_brief.get("search_candidate_documents")
        allowed_claims = node3_brief.get("allowed_claims")
        memory_selection_material = node3_brief.get("memory_selection_material")
        selected_recent_memory_contexts = node3_brief.get("selected_recent_memory_contexts")
        l3_document_summaries = node3_brief.get("l3_document_summaries")
        source_code_outlines = node3_brief.get("source_code_outlines")
        excluded_document_contexts = node3_brief.get("excluded_document_contexts")
        document_material_items = node3_brief.get("document_material_items")
        runtime_tasks = node3_brief.get("runtime_tasks")
        doc_count = len(read_documents) if isinstance(read_documents, list) else 0
        supplied_context_count = _payload_int(
            node3_brief.get("supplied_document_context_count"),
            fallback=doc_count,
        )
        actual_tool_read_doc_count = _payload_int(
            node3_brief.get("actual_tool_read_doc_count"),
            fallback=0,
        )
        actual_tool_read_code_file_count = _payload_int(
            node3_brief.get("actual_tool_read_code_file_count"),
            fallback=0,
        )
        supplied_source_code_context_count = _payload_int(
            node3_brief.get("supplied_source_code_context_count"),
            fallback=0,
        )
        final_search_candidate_count = _payload_int(
            node3_brief.get("final_search_candidate_count"),
            fallback=_payload_int(
                node3_brief.get("search_candidate_count"),
                fallback=len(search_candidate_documents)
                if isinstance(search_candidate_documents, list)
                else 0,
            ),
        )
        accumulated_search_candidate_count = _payload_int(
            node3_brief.get("accumulated_search_candidate_count"),
            fallback=final_search_candidate_count,
        )
        claim_count = len(allowed_claims) if isinstance(allowed_claims, list) else 0
        selected_context_count = (
            len(selected_recent_memory_contexts)
            if isinstance(selected_recent_memory_contexts, list)
            else 0
        )
        excluded_context_count = (
            len(excluded_document_contexts)
            if isinstance(excluded_document_contexts, list)
            else 0
        )
        material_item_count = (
            len(document_material_items)
            if isinstance(document_material_items, list)
            else 0
        )
        l3_document_summary_count = (
            len(l3_document_summaries)
            if isinstance(l3_document_summaries, list)
            else 0
        )
        source_code_outline_count = (
            len(source_code_outlines)
            if isinstance(source_code_outlines, list)
            else 0
        )
        llm_raw_document_text_count = _payload_int(
            node3_brief.get("llm_raw_document_text_count"),
            fallback=supplied_context_count,
        )
        llm_l3_summary_context_count = _payload_int(
            node3_brief.get("llm_l3_summary_context_count"),
            fallback=l3_document_summary_count,
        )
        runtime_task_count = len(runtime_tasks) if isinstance(runtime_tasks, list) else 0
        lines.append(
            "- node_3 input brief: "
            f"{node3_brief.get('brief_status', 'unknown')} / "
            f"actual_read_doc={actual_tool_read_doc_count} / "
            f"actual_read_code_file={actual_tool_read_code_file_count} / "
            f"supplied_contexts={supplied_context_count} / "
            f"source_code_contexts={supplied_source_code_context_count} / "
            f"source_code_outlines={source_code_outline_count} / "
            f"llm_raw_text={llm_raw_document_text_count} / "
            f"llm_l3_summaries={llm_l3_summary_context_count} / "
            f"search_candidates_final={final_search_candidate_count} / "
            f"search_candidates_accumulated={accumulated_search_candidate_count} / "
            f"excluded_contexts={excluded_context_count} / "
            f"document_materials={material_item_count} / "
            f"l3_document_summaries={l3_document_summary_count} / "
            f"claims={claim_count} / "
            f"selected_memory_contexts={selected_context_count} / "
            f"runtime_tasks={runtime_task_count}"
        )
        pack_status = node3_brief.get("document_context_pack_status")
        if isinstance(pack_status, str) and pack_status != "not_recorded":
            lines.append(
                "  - document context pack: "
                f"status={pack_status} / "
                f"frame={node3_brief.get('document_context_pack_frame_id', '')}"
            )
        material_frame_id = node3_brief.get("document_material_packet_frame_id")
        if isinstance(material_frame_id, str) and material_frame_id:
            unread_count = 0
            if isinstance(document_material_items, list):
                unread_count = sum(
                    1
                    for item in document_material_items
                    if isinstance(item, dict) and item.get("was_unread_candidate") is True
                )
            lines.append(
                "  - document material packet: "
                f"items={material_item_count} / unread_candidates={unread_count} / "
                f"frame={material_frame_id}"
            )
        reasons = node3_brief.get("insufficiency_reasons")
        if isinstance(reasons, list) and reasons:
            lines.append(f"  - insufficiency: {reasons}")
        if isinstance(memory_selection_material, dict):
            lines.append(
                "  - memory selection material: "
                f"status={memory_selection_material.get('memory_selection_status', 'unknown')} / "
                f"selected={memory_selection_material.get('selected_memory_count', 0)} / "
                f"info_class={memory_selection_material.get('memory_selection_info_class', '')} / "
                f"generated_by={memory_selection_material.get('generated_by', '')}"
            )
        if selected_context_count:
            lines.append(f"  - selected recent memory contexts: {selected_context_count}")
        material_delivery_mode = node3_brief.get("material_delivery_mode")
        if isinstance(material_delivery_mode, str) and material_delivery_mode:
            lines.append(
                "  - material delivery policy: "
                f"mode={material_delivery_mode} / "
                f"raw_policy={node3_brief.get('raw_document_policy', '')} / "
                f"summary_policy={node3_brief.get('l3_summary_policy', '')} / "
                f"reason={node3_brief.get('material_policy_reason_code', '')}"
            )
        l_loop_attitude_hint = node3_brief.get("l_loop_result_attitude_hint")
        if isinstance(l_loop_attitude_hint, str) and l_loop_attitude_hint != "not_recorded":
            lines.append(
                "  - L loop result in brief: "
                f"task={node3_brief.get('l_loop_task_status', 'unknown')} / "
                f"failure={node3_brief.get('l_loop_failure_level', 'unknown')} / "
                f"semantic={node3_brief.get('l3_semantic_goal_match_status', 'unknown')} / "
                f"remaining_query={node3_brief.get('remaining_query_attempts', 0)} / "
                f"hint={l_loop_attitude_hint}"
            )
        answer_basis_mode = node3_brief.get("answer_basis_mode")
        if isinstance(answer_basis_mode, str) and answer_basis_mode:
            lines.append(
                "  - answer basis in brief: "
                f"mode={answer_basis_mode} / "
                f"reason_codes={node3_brief.get('basis_reason_codes', [])} / "
                f"generated_by={node3_brief.get('answer_basis_generated_by', '')}"
            )
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by="CODE:NODE3_BRIEF_BUILDER",
                info_class="code_assembled_brief_from_absolute_sources",
                source_data_ids=_source_data_ids(
                    node3_brief,
                    fallback=[str(node3_brief_record.get("data_id") or "node_3:input_brief_frame")],
                ),
                semantic_judgement_status="not_run",
            )
        )

    report_record = _latest_run_scoped_record(
        result,
        records,
        "report_dry_001",
        data_type="node_output:report",
    )
    report_payload = _payload_from_record(report_record)
    if report_payload:
        lines.append(
            "- node_3 report: "
            f"{report_payload.get('llm_reporter_status', 'not_run')} / "
            f"{report_payload.get('report_generation_source', 'CODE/RENDERER')}"
        )
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(report_payload.get("report_generation_source") or "CODE/RENDERER"),
                info_class="mixed" if report_payload.get("llm_reporter_status") == "ran" else "rendered_view",
                source_data_ids=_source_data_ids(
                    report_payload,
                    fallback=[str(report_record.get("data_id") or "report_dry_001")],
                ),
                semantic_judgement_status=str(report_payload.get("llm_reporter_status") or "not_run"),
            )
        )

    node4_gate_record = _latest_run_scoped_record(
        result,
        records,
        "node_4:gatekeeper_frame",
        data_type="node_output:node4_gatekeeper_frame",
    )
    node4_gate = _payload_from_record(node4_gate_record)
    if node4_gate:
        lines.append(
            "- node_4 gatekeeper: "
            f"{node4_gate.get('gate_status', 'unknown')} / "
            f"{node4_gate.get('llm_gate_status', 'unknown')}"
        )
        reason = node4_gate.get("reason")
        if isinstance(reason, str) and reason:
            lines.append(f"  - reason: {reason}")
        checked_count = _list_count(node4_gate.get("checked_claims"))
        unsupported_count = _list_count(node4_gate.get("unsupported_claims"))
        contradiction_count = _list_count(node4_gate.get("contradictions"))
        lines.append(
            "  - checks: "
            f"checked={checked_count} / unsupported={unsupported_count} / "
            f"contradictions={contradiction_count}"
        )
        recent_memory_guard_status = node4_gate.get("recent_memory_guard_status")
        if isinstance(recent_memory_guard_status, str) and recent_memory_guard_status:
            lines.append(
                "  - recent memory guard: "
                f"{recent_memory_guard_status} / "
                f"claims={node4_gate.get('recent_memory_claim_count', 0)} / "
                f"unsupported={node4_gate.get('unsupported_recent_memory_claim_count', 0)} / "
                f"internal_id_leak={node4_gate.get('recent_memory_internal_id_leak_count', 0)}"
            )
            reason_codes = node4_gate.get("recent_memory_guard_reason_codes")
            if isinstance(reason_codes, list) and reason_codes:
                lines.append(f"    reason_codes: {reason_codes}")
        contradictions = node4_gate.get("contradictions")
        if isinstance(contradictions, list) and contradictions:
            lines.append("  - contradiction details:")
            for item in contradictions[:3]:
                lines.append(f"    - {item}")
            if len(contradictions) > 3:
                lines.append(f"    - ... +{len(contradictions) - 3}")
        revision_targets = node4_gate.get("revision_targets")
        if isinstance(revision_targets, list) and revision_targets:
            lines.append("  - revision targets:")
            for item in revision_targets[:3]:
                lines.append(f"    - {item}")
            if len(revision_targets) > 3:
                lines.append(f"    - ... +{len(revision_targets) - 3}")
        lines.extend(
            _metainfo_lines(
                indent=2,
                generated_by=str(node4_gate.get("gate_generation_source") or "unknown"),
                info_class="mixed",
                source_data_ids=_source_data_ids(
                    node4_gate,
                    fallback=[str(node4_gate_record.get("data_id") or "node_4:gatekeeper_frame")],
                ),
                semantic_judgement_status=str(node4_gate.get("llm_gate_status") or "unknown"),
            )
        )

    export_dir = result.get("export_dir")
    if isinstance(export_dir, str) and export_dir:
        lines.append(f"- 기록 저장: {export_dir}")

    return "\n".join(lines)


def render_chat_answer(result: dict[str, object], *, user_input: str) -> str:
    """현재 구조가 확보한 근거만 이용해 대화용 최종 답변을 만든다.

    node_3 LLM reporter가 성공했다면 그 보고문을 우선 보여준다.
    reporter가 없거나 실패한 경우에만 코드 렌더러가 DataStore를 재렌더링한다.
    """

    records = _records_by_id(result)
    node4_gate_record = _latest_run_scoped_record(
        result,
        records,
        "node_4:gatekeeper_frame",
        data_type="node_output:node4_gatekeeper_frame",
    )
    node4_gate = _payload_from_record(node4_gate_record)
    if _node4_blocks_final_answer(node4_gate):
        return _render_safe_blocking_answer(node4_gate)

    search_record = _latest_record_with_type_prefix(result, "tool_result:search_docs")
    search_payload = _payload_from_record(search_record)
    read_record = _latest_document_extract_record(result)
    read_payload = _payload_from_record(read_record)
    achievement = _payload_from_record(
        _latest_run_scoped_record(
            result,
            records,
            "L3:achievement_frame",
            data_type="node_output:L3_achievement_frame",
        )
    )
    query_frame = _payload_from_record(
        _latest_run_scoped_record(
            result,
            records,
            "L2:query_frame",
            data_type="node_output:L2_query_frame",
        )
    )
    report_record = _latest_run_scoped_record(
        result,
        records,
        "report_dry_001",
        data_type="node_output:report",
    )
    report_payload = _payload_from_record(report_record)
    if report_payload.get("llm_reporter_status") == "ran":
        rendered = report_payload.get("rendered_markdown")
        lines = [
            "[answer]",
            f"[{report_payload.get('report_generation_source', 'LLM:unknown')} | LLM_REPORTER=ran]",
            "generated_by: "
            f"{report_payload.get('report_generation_source', 'LLM:unknown')} | "
            "info_class: mixed | semantic_judgement_status: ran",
            "",
            rendered if isinstance(rendered, str) and rendered else "LLM reporter returned an empty report.",
        ]
        node4_gate = _payload_from_record(
            _latest_run_scoped_record(
                result,
                records,
                "node_4:gatekeeper_frame",
                data_type="node_output:node4_gatekeeper_frame",
            )
        )
        if node4_gate:
            lines.extend(
                [
                    "",
                    f"[최종 검사] {node4_gate.get('gate_status', 'unknown')}: {node4_gate.get('reason', '')}",
                ]
            )
        return "\n".join(lines)

    if result.get("status") == "structure_failed":
        return _render_structure_failed_answer(
            result,
            search_payload=search_payload,
            read_payload=read_payload,
        )

    lines = [
        "[answer]",
        "[CODE/RENDERER | LLM_REPORTER=not_run]",
        "generated_by: CODE/RENDERER | info_class: rendered_view | semantic_judgement_status: LLM_REPORTER=not_run",
        "아래 답변은 DataStore 기록을 코드가 재렌더링한 것이고, Qwen 최종 보고문이 아니야.",
    ]
    if result.get("status") == "model_fallback":
        lines.append("Qwen 계획이 스키마를 통과하지 못해서 사용자 입력 fallback 검색으로 처리했어.")
    elif result.get("status") != "ok":
        lines.append(f"이번 턴 상태가 `{result.get('status', 'unknown')}`라서 답변 신뢰도를 낮게 봐야 해.")

    query_text = query_frame.get("query_text")
    if isinstance(query_text, str) and query_text:
        query_source = query_frame.get("query_source")
        if query_source == "llm_query_plan":
            lines.append(f"[LLM:{_runtime_model_id(result)} -> CODE/RENDER] `{query_text}`라는 검색 계획으로 내부 문서를 찾았어.")
        else:
            lines.append(f"[CODE/FALLBACK -> CODE/RENDER] `{query_text}`로 내부 문서를 찾았어.")
    else:
        lines.append(f"[CODE/FALLBACK -> CODE/RENDER] `{user_input}`에 맞춰 내부 문서를 찾았어.")

    if read_payload:
        doc_name = _display_document_name(read_payload.get("doc_id"))
        lines.append(f"[문서 읽기 -> CODE/RENDER] 가장 직접적으로 읽은 문서는 `{doc_name}`야.")
        extracted = _extract_doc_summary(read_payload)
        if extracted:
            lines.append("")
            lines.extend(extracted)
    elif search_payload:
        top_docs = _top_search_docs(search_payload, limit=3)
        if top_docs:
            lines.append("원문 읽기까지는 가지 못했고, 검색 후보는 이 순서로 잡혔어:")
            for index, item in enumerate(top_docs, start=1):
                lines.append(f"{index}. `{_display_document_name(item.get('doc_id'))}`")
    else:
        lines.append("검색 결과 payload를 찾지 못해서 근거 문서 요약은 만들지 못했어.")

    if search_payload:
        document_count = search_payload.get("document_count")
        chunk_count = search_payload.get("chunk_count")
        if document_count and chunk_count:
            lines.append("")
            lines.append(
                f"이번 검색은 문서 {document_count}개, chunk {chunk_count}개 색인에서 돌았어."
            )

    reason = achievement.get("reason") if achievement else None
    if isinstance(reason, str) and reason:
        lines.append("")
        lines.append(f"[CODE/OPERATION_CHECK] operation_label: {reason}")
        lines.append("LLM 의미판단: not_run")

    lines.append("")
    lines.append("주의: 여기서 확인한 것은 문서 ID, 검색 결과, 읽은 원문 같은 근거야. 문서 내용 자체의 최종 진실성까지 단정한 것은 아니야.")
    return "\n".join(lines)


def _render_structure_failed_answer(
    result: dict[str, object],
    *,
    search_payload: dict[str, object],
    read_payload: dict[str, object],
) -> str:
    lines = [
        "[answer]",
        "[CODE/RENDERER | LLM_REPORTER=not_run]",
        "generated_by: CODE/RENDERER | info_class: rendered_view | semantic_judgement_status: LLM_REPORTER=not_run",
        "이번 턴은 structure_failed 상태라서 송련의 정상 노드 흐름이 끝까지 기록되지 않았어.",
        "node_3 최종 보고도 실행되지 않았고, 확인 가능한 trace/data 기록이 없거나 불완전해.",
    ]
    trace_count = result.get("trace_count")
    data_record_count = result.get("data_record_count")
    lines.append(f"확인된 trace/data 수: {trace_count or 0} / {data_record_count or 0}")

    stage = result.get("structure_failure_stage")
    exception_type = result.get("structure_failure_exception_type")
    reason = result.get("structure_failure_reason") or result.get("reason")
    diagnostics: list[str] = []
    if isinstance(stage, str) and stage:
        diagnostics.append(f"stage={stage}")
    if isinstance(exception_type, str) and exception_type:
        diagnostics.append(f"exception={exception_type}")
    if isinstance(reason, str) and reason:
        diagnostics.append(f"reason={_short_display_text(reason)}")
    if diagnostics:
        lines.append(f"짧은 진단: {', '.join(diagnostics)}")
    budget_type = result.get("budget_failure_type")
    if isinstance(budget_type, str) and budget_type:
        lines.append(
            "예산 진단: "
            f"type={budget_type}, "
            f"query={result.get('budget_failure_query_count', '?')}/"
            f"{result.get('budget_failure_max_query_attempts', '?')}, "
            f"tool={result.get('budget_failure_tool_calls', '?')}/"
            f"{result.get('budget_failure_max_tool_calls', '?')}, "
            f"read_doc={result.get('budget_failure_read_doc_count', '?')}/"
            f"{result.get('budget_failure_max_read_doc', '?')}"
        )
        budget_stage = result.get("budget_failure_stage")
        if isinstance(budget_stage, str) and budget_stage:
            lines.append(f"예산 실패 단계: {budget_stage}")

    if search_payload or read_payload:
        lines.extend(["", "다만 DataStore에 검색/문서 payload가 남아 있어 그 범위만 재렌더링할 수 있어."])
        if search_payload:
            result_count = search_payload.get("result_count", 0)
            lines.append(f"- search_docs payload: 후보 {result_count}개")
            top_docs = _top_search_docs(search_payload, limit=3)
            if top_docs:
                for index, item in enumerate(top_docs, start=1):
                    lines.append(f"  {index}. `{_display_document_name(item.get('doc_id'))}`")
        else:
            lines.append("- search_docs payload: 없음")
        if read_payload:
            doc_name = _display_document_name(read_payload.get("doc_id"))
            char_count = read_payload.get("char_count", "?")
            lines.append(f"- read_doc payload: `{doc_name}` ({char_count}자)")
        else:
            lines.append("- read_doc payload: 없음")
    else:
        lines.append("확인 가능한 search_docs/read_doc payload도 없어.")

    lines.extend(
        [
            "",
            "따라서 사용자 질문에 대한 의미 답변은 만들지 않고, 실패 상태만 보고할게.",
        ]
    )
    return "\n".join(lines)


def _node4_blocks_final_answer(node4_gate: dict[str, object]) -> bool:
    """node_4가 pass하지 않은 보고문은 사용자-facing 최종 답변으로 확정하지 않는다."""

    gate_status = node4_gate.get("gate_status")
    return gate_status in {"needs_revision", "failed"}


def _render_safe_blocking_answer(node4_gate: dict[str, object]) -> str:
    """반려된 node_3 원문 대신 보여줄 안전 차단 답변."""

    gate_status = str(node4_gate.get("gate_status") or "unknown")
    reason = str(node4_gate.get("reason") or "").strip()
    if gate_status == "failed":
        return "\n".join(
            [
                "[answer]",
                f"[FINAL_BLOCKED_BY_GATEKEEPER | gate_status={gate_status}]",
                "최종 검사 자체가 실패해서 방금 답변을 확정하지 않았어.",
                "",
                "이건 근거 밖 주장이나 모순이 감지됐다는 뜻이 아니야.",
                "최종 검사 LLM 호출, JSON 파싱, 또는 스키마 검증이 실패했다는 뜻이야.",
                f"실패 이유: {reason or 'unknown'}",
                "",
                "원문 답변은 안전을 위해 최종 출력하지 않았고, 자세한 실패 기록은 위 runtime에 남아 있어.",
            ]
        )

    revision_targets = node4_gate.get("revision_targets")
    contradictions = node4_gate.get("contradictions")
    target_count = len(revision_targets) if isinstance(revision_targets, list) else 0
    contradiction_count = len(contradictions) if isinstance(contradictions, list) else 0
    lines = [
        "[answer]",
        f"[FINAL_BLOCKED_BY_GATEKEEPER | gate_status={gate_status}]",
        "방금 생성된 답변이 최종 검사에서 반려됐어.",
        "",
        "반려된 원문은 최종 답변으로 확정하지 않을게.",
        "이유: 근거 밖 주장, 모순, 또는 수정 필요 신호가 감지됐어.",
    ]
    if target_count:
        lines.append(f"수정 대상 신호: {target_count}개")
    if contradiction_count:
        lines.append(f"모순/불일치 신호: {contradiction_count}개")
    if isinstance(revision_targets, list) and revision_targets:
        lines.append(f"첫 수정 대상: {revision_targets[0]}")
    elif isinstance(contradictions, list) and contradictions:
        lines.append(f"첫 불일치 신호: {contradictions[0]}")
    lines.extend(
        [
            "",
            "다음 조치는 내부 문서를 더 정확히 검색하거나 질문 범위를 좁힌 뒤 다시 답변을 만드는 거야.",
            "상세한 반려 이유와 원래 보고문은 위 runtime 기록에 보존돼 있어.",
        ]
    )
    return "\n".join(lines)


def render_pretty_turn(result: dict[str, object], *, user_input: str) -> str:
    """한 턴 결과를 런타임 요약과 최종 답변으로 합쳐 출력한다."""

    return f"{render_runtime_view(result, user_input=user_input)}\n\n{render_chat_answer(result, user_input=user_input)}"


def _records_by_id(result: dict[str, object]) -> dict[str, dict[str, object]]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}
    mapped: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        data_id = record.get("data_id")
        if isinstance(data_id, str):
            mapped[data_id] = record
    return mapped


def _payload(
    records: dict[str, dict[str, object]],
    data_id: str,
    *,
    data_type: str | None = None,
) -> dict[str, object]:
    record = records.get(data_id)
    if not isinstance(record, dict) and data_type is not None:
        record = _latest_record_with_type(records, data_type)
    if not isinstance(record, dict):
        return {}
    payload = record.get("payload")
    return payload if isinstance(payload, dict) else {}


def _latest_run_scoped_record(
    result: dict[str, object],
    records: dict[str, dict[str, object]],
    legacy_data_id: str,
    *,
    data_type: str | None = None,
) -> dict[str, object]:
    latest_run_index = _latest_l_run_index(result)
    if latest_run_index > 1:
        scoped_data_id = f"L:run:{latest_run_index:04d}:{legacy_data_id}"
        scoped_record = records.get(scoped_data_id)
        if isinstance(scoped_record, dict):
            return scoped_record

    legacy_record = records.get(legacy_data_id)
    if isinstance(legacy_record, dict):
        return legacy_record

    if data_type is not None:
        return _latest_record_with_type(records, data_type)
    return {}


def _latest_l_run_index(result: dict[str, object]) -> int:
    indexes: list[int] = []
    for frame in _payloads_with_type(result, "node_output:L_loop_run_frame"):
        run_index = frame.get("run_index")
        if isinstance(run_index, int):
            indexes.append(run_index)
    return max(indexes, default=1)


def _blocked_same_turn_l_reroute_request_count(result: dict[str, object]) -> int:
    count = 0
    for frame in _payloads_with_type(result, "node_output:same_turn_l_reroute_controller_frame"):
        if frame.get("node1_route") != "L":
            continue
        if frame.get("controller_decision") != "close_route_2":
            continue
        count += 1
    return count


def _l_internal_revision_state(result: dict[str, object]) -> str:
    revision_types = {
        "node_output:L2_revision_query_frame",
        "node_output:L3_revision_achievement_frame",
    }
    records = result.get("data_records")
    if not isinstance(records, list):
        return "none"
    for record in records:
        if isinstance(record, dict) and record.get("data_type") in revision_types:
            return "present"
    return "none"


def _latest_record_with_type(
    records: dict[str, dict[str, object]],
    data_type: str,
) -> dict[str, object]:
    for record in reversed(list(records.values())):
        if isinstance(record, dict) and record.get("data_type") == data_type:
            return record
    return {}


def _latest_record_with_type_prefix(result: dict[str, object], prefix: str) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}
    for record in reversed(records):
        if not isinstance(record, dict):
            continue
        data_type = record.get("data_type")
        if not isinstance(data_type, str) or not data_type.startswith(prefix):
            continue
        return record
    return {}


def _first_record_with_type_prefix(result: dict[str, object], prefix: str) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}
    for record in records:
        if not isinstance(record, dict):
            continue
        data_type = record.get("data_type")
        if not isinstance(data_type, str) or not data_type.startswith(prefix):
            continue
        return record
    return {}


def _document_extract_records_for_display(result: dict[str, object]) -> list[dict[str, object]]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return []

    extract_records: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        data_type = record.get("data_type")
        if not isinstance(data_type, str) or not _is_document_extract_data_type(data_type):
            continue
        extract_records.append(record)

    latest_run_index = _latest_l_run_index(result)
    if latest_run_index > 1:
        latest_run_prefix = f"L:run:{latest_run_index:04d}:"
        latest_run_records = [
            record
            for record in extract_records
            if str(record.get("data_id") or "").startswith(latest_run_prefix)
        ]
        if latest_run_records:
            return latest_run_records

    return extract_records


def _latest_document_extract_record(result: dict[str, object]) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}

    latest_extract_record: dict[str, object] = {}
    for record in reversed(records):
        if not isinstance(record, dict):
            continue
        data_type = record.get("data_type")
        if not isinstance(data_type, str) or not _is_document_extract_data_type(data_type):
            continue
        if not latest_extract_record:
            latest_extract_record = record
        payload = _payload_from_record(record)
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return record
    return latest_extract_record


def _first_document_extract_record(result: dict[str, object]) -> dict[str, object]:
    read_doc = _first_record_with_type_prefix(result, "tool_result:read_doc")
    if read_doc:
        return read_doc
    return _first_record_with_type_prefix(result, "tool_result:read_artifact")


def _is_document_extract_data_type(data_type: str) -> bool:
    return data_type.startswith("tool_result:read_doc") or data_type.startswith("tool_result:read_artifact")


def _document_extract_tool_name(record: dict[str, object]) -> str:
    data_type = str(record.get("data_type") or "")
    data_id = str(record.get("data_id") or "")
    if data_type.startswith("tool_result:read_artifact") or "tool_result:read_artifact" in data_id:
        return "read_artifact"
    return "read_doc"


def _payload_from_record(record: dict[str, object]) -> dict[str, object]:
    payload = record.get("payload") if isinstance(record, dict) else None
    return payload if isinstance(payload, dict) else {}


def _payloads_with_type(result: dict[str, object], data_type: str) -> list[dict[str, object]]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return []
    payloads: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("data_type") != data_type:
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _metainfo_lines(
    *,
    indent: int,
    generated_by: str,
    info_class: str,
    source_data_ids: list[str],
    semantic_judgement_status: str,
    copied_from: str | None = None,
    selection_method: str | None = None,
    truncated: bool | None = None,
) -> list[str]:
    prefix = " " * indent
    lines = [
        f"{prefix}generated_by: {generated_by}",
        f"{prefix}info_class: {info_class}",
        f"{prefix}source_data_ids: {_format_source_ids(source_data_ids)}",
        f"{prefix}semantic_judgement_status: {semantic_judgement_status}",
    ]
    if copied_from is not None:
        lines.append(f"{prefix}copied_from: {copied_from}")
    if selection_method is not None:
        lines.append(f"{prefix}selection_method: {selection_method}")
    if truncated is not None:
        lines.append(f"{prefix}truncated: {str(truncated).lower()}")
    return lines


def _structure_failure_runtime_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    field_labels = [
        ("structure_failure_stage", "stage"),
        ("structure_failure_node", "node"),
        ("structure_failure_prompt_ref", "prompt"),
        ("structure_failure_exception_type", "exception"),
        ("structure_failure_reason", "reason"),
        ("structure_failure_llm_call_data_id", "llm_call"),
        ("structure_failure_trace_event_id", "trace_event"),
    ]
    for field_name, label in field_labels:
        value = result.get(field_name)
        if not isinstance(value, str) or not value:
            continue
        display_value = _display_document_name(value) if label == "prompt" else _short_display_text(value)
        lines.append(f"- structure_failure_{label}: {display_value}")
    budget_lines = _budget_failure_runtime_lines(result)
    if budget_lines:
        lines.extend(budget_lines)
    return lines


def _budget_failure_runtime_lines(result: dict[str, object]) -> list[str]:
    budget_type = result.get("budget_failure_type")
    if not isinstance(budget_type, str) or not budget_type:
        return []
    lines = [f"- budget_failure_type: {budget_type}"]
    text_fields = [
        ("budget_failure_stage", "stage"),
        ("budget_failure_reason", "reason"),
        ("budget_failure_frame_id", "frame"),
        ("budget_failure_route", "route"),
        ("budget_failure_l_run_id", "l_run"),
    ]
    for field_name, label in text_fields:
        value = result.get(field_name)
        if isinstance(value, str) and value:
            lines.append(f"- budget_failure_{label}: {_short_display_text(value)}")
    source_ids = result.get("budget_failure_source_data_ids")
    if isinstance(source_ids, list):
        lines.append(
            "- budget_failure_source_data_ids: "
            f"{_format_source_ids([item for item in source_ids if isinstance(item, str)])}"
        )
    count_fields = [
        ("budget_failure_query_count", "query_count"),
        ("budget_failure_max_query_attempts", "max_query_attempts"),
        ("budget_failure_tool_calls", "tool_calls"),
        ("budget_failure_max_tool_calls", "max_tool_calls"),
        ("budget_failure_read_doc_count", "read_doc_count"),
        ("budget_failure_max_read_doc", "max_read_doc"),
    ]
    for field_name, label in count_fields:
        value = result.get(field_name)
        if isinstance(value, int):
            lines.append(f"- budget_failure_{label}: {value}")
    return lines


def _short_display_text(text: str, *, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _source_data_ids(payload: dict[str, object], *, fallback: list[str]) -> list[str]:
    values = payload.get("source_data_ids")
    if isinstance(values, list):
        source_ids = [item for item in values if isinstance(item, str) and item]
    else:
        source_ids = []
    for item in fallback:
        if item and item not in source_ids:
            source_ids.append(item)
    return source_ids


def _node1_router_status(route: dict[str, object]) -> str:
    route_source = str(route.get("route_source") or "CODE:RULE_STUB")
    if route.get("fallback_after_llm_failure") is True:
        return f"LLM failed -> {route_source} fallback"
    if route.get("llm_routing_status") == "ran":
        return "LLM ran"
    return route_source


def _format_source_ids(source_data_ids: list[str]) -> str:
    if not source_data_ids:
        return "[]"
    if len(source_data_ids) <= 4:
        return "[" + ", ".join(source_data_ids) + "]"
    head = ", ".join(source_data_ids[:4])
    return f"[{head}, ... +{len(source_data_ids) - 4}]"


def _llm_call_ids_by_node(result: dict[str, object]) -> dict[str, list[str]]:
    records = result.get("data_records")
    if not isinstance(records, list):
        return {}
    mapped: dict[str, list[str]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("data_type") != "llm_call":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        node_id = payload.get("node_id")
        data_id = record.get("data_id")
        if not isinstance(node_id, str) or not isinstance(data_id, str):
            continue
        mapped.setdefault(node_id, []).append(data_id)
    return mapped


def _selected_query_candidate(plan_payload: dict[str, object]) -> dict[str, object]:
    selected_id = plan_payload.get("selected_candidate_id")
    candidates = plan_payload.get("candidates")
    if not isinstance(selected_id, str) or not isinstance(candidates, list):
        return {}
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == selected_id:
            return candidate
    return {}


def _top_search_docs(search_payload: dict[str, object], *, limit: int) -> list[dict[str, object]]:
    results = search_payload.get("results")
    if not isinstance(results, list):
        return []
    return [item for item in results[:limit] if isinstance(item, dict)]


def _list_count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _payload_int(value: object, *, fallback: int = 0) -> int:
    return value if isinstance(value, int) and value >= 0 else fallback


def _memory_item_type_count(value: object, item_type: str) -> int:
    if not isinstance(value, list):
        return 0
    return sum(
        1
        for item in value
        if isinstance(item, dict) and item.get("item_type") == item_type
    )


def _extract_doc_summary(read_payload: dict[str, object]) -> list[str]:
    text = read_payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return []

    compact_lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = compact_lines[0] if compact_lines else ""
    goal = _line_after_prefix(compact_lines, "**목표**:")
    scope = _section_numbered_items(compact_lines, "## 범위", limit=5)
    principles = _section_numbered_items(compact_lines, "## 원칙", limit=3)

    lines: list[str] = []
    if title:
        lines.append(f"문서 제목: {title}")
    if goal:
        lines.append(f"핵심 목표: {goal}")
    if scope:
        lines.append("문서가 말하는 범위:")
        for item in scope:
            lines.append(f"- {item}")
    if principles:
        lines.append("주의 원칙:")
        for item in principles:
            lines.append(f"- {item}")
    if not lines:
        preview = " ".join(text.split())[:500]
        lines.append(f"읽은 원문 미리보기: {preview}")
    return lines


def _display_document_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "읽은 문서"
    normalized = value.replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] or "읽은 문서"


def _line_after_prefix(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def _section_numbered_items(lines: list[str], heading: str, *, limit: int) -> list[str]:
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []

    items: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if not line[:1].isdigit() or ". " not in line:
            continue
        items.append(line.split(". ", 1)[1].strip())
        if len(items) >= limit:
            break
    return items


def _runtime_model(result: dict[str, object]) -> str:
    runtime = result.get("runtime")
    if not isinstance(runtime, dict):
        return "unknown"
    model_id = runtime.get("model_id") or "unknown"
    transport = runtime.get("transport") or runtime.get("adapter_kind") or "unknown"
    return f"{model_id} via {transport}"


def _runtime_model_id(result: dict[str, object]) -> str:
    runtime = result.get("runtime")
    if not isinstance(runtime, dict):
        return "unknown"
    model_id = runtime.get("model_id")
    return model_id if isinstance(model_id, str) and model_id else "unknown"
