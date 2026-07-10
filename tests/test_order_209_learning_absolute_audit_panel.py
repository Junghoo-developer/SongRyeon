from __future__ import annotations

from songryeon_core.runtime.terminal_view import render_runtime_view


def test_learning_absolute_audit_panel_surfaces_key_counts() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "trace_count": 27,
            "data_record_count": 59,
            "data_records": [
                {
                    "data_id": "route:L",
                    "data_type": "node_output:routing_decision",
                    "payload": {
                        "frame_id": "route:L",
                        "route": "L",
                        "route_source": "LLM:fake",
                        "expected_next_0_mode": "targeted_memory_supply",
                        "llm_routing_status": "ran",
                    },
                },
                {
                    "data_id": "node_2:handoff_frame",
                    "data_type": "node_output:node2_handoff_frame",
                    "payload": {
                        "route_path": [
                            "1:route=L",
                            "0:targeted_memory_supply",
                            "L:L1_L2_tools_L3(run=1)",
                            "1:route=2",
                        ],
                    },
                },
                {
                    "data_id": "L:run_frame:0001",
                    "data_type": "node_output:L_loop_run_frame",
                    "payload": {"run_index": 1},
                },
                {
                    "data_id": "r_loop:handoff",
                    "data_type": "node_output:r_loop_memory_handoff_packet_frame",
                    "payload": {
                        "packet_status": "available",
                        "available_entry_node_ids": ["graph:core_ego:root"],
                    },
                },
                {
                    "data_id": "memory_selection",
                    "data_type": "node_output:memory_relevance_selection_frame",
                    "payload": {
                        "selection_status": "selected",
                        "candidate_frame_ids": ["candidate:1"],
                        "selected_candidate_frame_ids": ["candidate:1"],
                    },
                },
                {
                    "data_id": "selected_memory_context",
                    "data_type": "node_output:selected_recent_memory_context_frame",
                    "payload": {
                        "selection_status": "selected",
                        "items": [{"source_turn_id": "turn_chat_0001"}],
                        "missing_selected_memory_context_count": 0,
                    },
                },
                {
                    "data_id": "tool_result:read_doc:1",
                    "data_type": "tool_result:read_doc",
                    "payload": {"doc_id": "ORDER_001.md", "text": "ORDER"},
                },
                {
                    "data_id": "L:activity_ledger_frame",
                    "data_type": "loop_activity:l_loop_activity_ledger_frame",
                    "payload": {"frame_id": "L:activity_ledger_frame"},
                },
                {
                    "data_id": "node_0:document_material_packet_frame",
                    "data_type": "node_output:node0_document_material_packet_frame",
                    "payload": {
                        "item_count": 3,
                        "actual_tool_read_doc_count": 1,
                    },
                },
                {
                    "data_id": "graph:turn_activity",
                    "data_type": "graph_memory:turn_activity_graph_link_frame",
                    "payload": {
                        "r_vessel_activity_ledger_data_ids": ["R:ledger"],
                    },
                },
                {
                    "data_id": "node_3:input_brief_frame",
                    "data_type": "node_output:node3_input_brief_frame",
                    "payload": {
                        "actual_tool_read_doc_count": 1,
                        "supplied_document_context_count": 0,
                        "selected_recent_memory_contexts": [
                            {"source_turn_id": "turn_chat_0001"}
                        ],
                        "vessel_r_material": {
                            "material_status": "present",
                            "r_loop_task_status": "sufficient",
                            "material_items": [{"graph_node_id": "graph:summary:1"}],
                        },
                    },
                },
                {
                    "data_id": "node_4:gatekeeper_frame",
                    "data_type": "node_output:node4_gatekeeper_frame",
                    "payload": {
                        "gate_status": "pass",
                        "llm_gate_status": "ran",
                        "checked_claims": ["claim"],
                        "unsupported_claims": [],
                        "contradictions": [],
                        "recent_memory_guard_status": "pass",
                    },
                },
            ],
        },
        user_input="학습용 감사판 테스트",
    )

    assert "- 학습용 절대정보 감사판:" in rendered
    assert "sequence=['L'] / final=L" in rendered
    assert "path_steps=4" in rendered
    assert "L_runs=1 / L_blocked_reroute=0" in rendered
    assert "R_handoff_status=available / R_entry_nodes=1 / R_vessel_ledgers=1" in rendered
    assert "selector=selected / candidates=1 / selected=1" in rendered
    assert "copied_contexts=1 / missing_contexts=0 / node3_selected_contexts=1" in rendered
    assert "L_activity_ledgers=1 / read_doc_records=1" in rendered
    assert "material_items=3 / material_actual_read=1" in rendered
    assert "node3_vessel_status=present / node3_vessel_items=1" in rendered
    assert "gate=pass / llm=ran / checked=1 / unsupported=0 / contradictions=0" in rendered


def test_learning_absolute_audit_panel_is_present_with_missing_records() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "data_records": [],
        },
        user_input="빈 감사판 테스트",
    )

    assert "- 학습용 절대정보 감사판:" in rendered
    assert "final=none" in rendered
    assert "R_handoff_status=not_recorded" in rendered
    assert "node3_vessel_status=not_recorded" in rendered
    assert "gate=not_recorded" in rendered
