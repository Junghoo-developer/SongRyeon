import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
    R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_POLICY_ID,
    build_r_loop_vessel_read_packet_from_neo4j,
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_traverse

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
    _time_bundle_row,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    _source_kind_row,
)
from tests.test_order_188_r_vessel_raw_original_cap import _raw_source_chain_row


RAW_SOURCE_ID = "graph:raw_source:internal_document:order_190"
PARENT_TOKEN_SUMMARY_ID = "graph:summary:token_budget_bundle:order_190_parent"
UNRELATED_TOKEN_SUMMARY_ID = "graph:summary:token_budget_bundle:order_190_unrelated"
CHILD_TOKEN_SUMMARY_ID = "graph:summary:token_budget_bundle:order_190_child"
PARENT_TOKEN_BUNDLE_ID = "graph:token_budget_summary_bundle:order_190:parent"
UNRELATED_TOKEN_BUNDLE_ID = "graph:token_budget_summary_bundle:order_190:unrelated"
CHILD_TOKEN_BUNDLE_ID = "graph:token_budget_summary_bundle:order_190:child"


def test_read_packet_expands_summary_children_for_token_summary_traversal() -> None:
    packet = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_190_packet",
        created_at=READ_AT,
        limit=1,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    summary_ids = [
        record["summary_node_id"] for record in packet.summary_candidate_records
    ]

    assert packet.summary_child_expansion_policy_id == (
        R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_POLICY_ID
    )
    assert packet.base_summary_candidate_count == 1
    assert packet.summary_child_expanded_count == 1
    assert packet.summary_child_expanded_node_ids == [CHILD_TOKEN_SUMMARY_ID]
    assert packet.summary_child_expansion_truncated is False
    assert PARENT_TOKEN_SUMMARY_ID in summary_ids
    assert CHILD_TOKEN_SUMMARY_ID in summary_ids
    assert summary_ids == [
        PARENT_TOKEN_SUMMARY_ID,
        CHILD_TOKEN_SUMMARY_ID,
    ]


def test_traverse_continues_from_token_summary_to_lower_summary_layer() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_190_packet",
        batch_id="order_190_traverse_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_190_traverse",
        user_question="token summary 아래 lower summary layer까지 내려가",
        read_packet=recorded.packet,
        adapter=TokenSummaryNeedsDeeperAdapter(),
        frame_label="order_190_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.final_graph_node_id == CHILD_TOKEN_SUMMARY_ID
    assert result.result_frame.final_continuation_status == "stop_sufficient"
    assert result.result_frame.r_loop_task_status == "sufficient"
    assert result.result_frame.selected_graph_node_ids == [
        "graph:axis:time",
        "graph:source_ingest_time_bundle:night_changed_sources",
        SOURCE_KIND_ID,
        PARENT_TOKEN_SUMMARY_ID,
        CHILD_TOKEN_SUMMARY_ID,
    ]
    assert result.result_frame.raw_original_material_seen_count == 0
    token_surface = result.candidate_layer_surfaces[4]
    assert token_surface.total_candidate_count == 1
    assert token_surface.surface_records[0]["candidate_graph_node_ids"] == [
        CHILD_TOKEN_SUMMARY_ID
    ]


class TokenSummaryNeedsDeeperAdapter:
    model_id = "order-190-token-summary-needs-deeper-fake"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Traverse from token summary to lower summary layer",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 3,
                "stop_condition": "Stop after the source leaf summary is inspected.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            surface_ref, node_ref = _first_ref(request.input_payload)
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first official child candidate.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "hierarchy_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            selected = request.input_payload.get("selected_candidate_record")
            data_kind = selected.get("data_kind") if isinstance(selected, dict) else None
            has_children = request.input_payload.get("hierarchy_child_candidate_count")
            should_continue = (
                data_kind == "token_budget_bundle_summary"
                and isinstance(has_children, int)
                and has_children > 0
            )
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "insufficient" if should_continue else "sufficient",
                "granularity_problem_status": (
                    "needs_lower_granularity" if should_continue else "none"
                ),
                "branch_problem_status": "none",
                "recommended_next_action": "deeper" if should_continue else "stop",
                "inspection_reason": (
                    "Token summary has lower summary children, so continue deeper."
                    if should_continue
                    else "Source leaf summary is enough for this test."
                ),
            }
        else:
            payload = {"error": "unknown prompt"}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_ref(payload: dict[str, object]) -> tuple[str | None, str | None]:
    surfaces = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(surfaces, list) or not isinstance(records_by_surface, dict):
        return None, None
    for surface in surfaces:
        if not isinstance(surface, str):
            continue
        records = records_by_surface.get(surface)
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("node_ref"), str):
                return surface, record["node_ref"]
    return None, None


def _entry_rows() -> list[dict[str, object]]:
    return [
        _time_axis_row(),
        _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
        _time_bundle_row(),
        _source_kind_row(source_graph_node_ids=[RAW_SOURCE_ID]),
        _raw_source_chain_row(
            raw_id=RAW_SOURCE_ID,
            next_raw_id=None,
            parent_id=SOURCE_KIND_ID,
        ),
    ]


def _summary_rows() -> list[dict[str, object]]:
    return [
        _parent_token_summary_row(),
        _unrelated_token_summary_row(),
        _child_token_summary_row(),
    ]


def _parent_token_summary_row() -> dict[str, object]:
    return _token_summary_row(
        summary_id=PARENT_TOKEN_SUMMARY_ID,
        target_id=PARENT_TOKEN_BUNDLE_ID,
        source_ids=[PARENT_TOKEN_BUNDLE_ID, CHILD_TOKEN_SUMMARY_ID],
        source_data_ids=[PARENT_TOKEN_BUNDLE_ID, CHILD_TOKEN_SUMMARY_ID, RAW_SOURCE_ID],
        depth=3,
        text="Parent token summary that points at a lower token summary.",
    )


def _child_token_summary_row() -> dict[str, object]:
    return _token_summary_row(
        summary_id=CHILD_TOKEN_SUMMARY_ID,
        target_id=CHILD_TOKEN_BUNDLE_ID,
        source_ids=[CHILD_TOKEN_BUNDLE_ID],
        source_data_ids=[CHILD_TOKEN_BUNDLE_ID, RAW_SOURCE_ID],
        depth=2,
        text="Child token summary that is enough for this test.",
    )


def _unrelated_token_summary_row() -> dict[str, object]:
    return _token_summary_row(
        summary_id=UNRELATED_TOKEN_SUMMARY_ID,
        target_id=UNRELATED_TOKEN_BUNDLE_ID,
        source_ids=[UNRELATED_TOKEN_BUNDLE_ID],
        source_data_ids=[UNRELATED_TOKEN_BUNDLE_ID],
        depth=3,
        text="Unrelated token summary used to occupy the base summary window.",
    )


def _token_summary_row(
    *,
    summary_id: str,
    target_id: str,
    source_ids: list[str],
    source_data_ids: list[str],
    depth: int,
    text: str,
) -> dict[str, object]:
    return {
        "summary_node_id": summary_id,
        "summary_display_name": f"Summary: {target_id}",
        "data_kind": "token_budget_bundle_summary",
        "info_class": "mixed",
        "generated_by": "LLM:fake:night_summarize_token_budget_bundle",
        "payload_json": json.dumps(
            {
                "data_kind": "token_budget_bundle_summary",
                "summary_depth": depth,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": target_id,
                "target_node_kind": "token_budget_summary_bundle",
                "source_leaf_count": 1,
                "source_summary_count": 1,
                "source_graph_node_ids": source_ids,
                "source_data_ids": source_data_ids,
                "source_trace_ids": [f"trace:summary:{summary_id}"],
                "info_class": "mixed",
                "generated_by": "LLM:fake:night_summarize_token_budget_bundle",
                "summary_text": text,
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": target_id,
        "target_display_name": "Token Budget Summary Bundle",
        "target_node_kind": "token_budget_summary_bundle",
    }
