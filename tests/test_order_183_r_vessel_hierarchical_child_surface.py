import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_one_step

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)


def test_time_axis_selection_records_child_candidate_surface() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[_time_axis_row(), _source_ingest_row(), _time_bundle_row()],
        summary_rows=[],
    )
    adapter = HierarchyAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_183_axis",
        user_question="CoreEgo에서 시간축 아래 후보를 봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_183_axis",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r2_selection is not None
    assert result.r2_selection.selected_graph_node_id == "graph:axis:time"
    assert result.r3_inspection is not None
    assert set(result.r3_inspection.child_node_ids) == {
        "graph:source_ingest_time_bundle:night_changed_sources",
        "graph:time_bundle:manual_vessel_first_write:core",
    }
    assert result.graph_traversal_candidate_surface is not None
    assert set(result.graph_traversal_candidate_surface.child_candidate_node_ids) == set(
        result.r3_inspection.child_node_ids
    )
    record = data_store.require_record(result.graph_traversal_candidate_surface.frame_id)
    assert record.data_type == "node_output:R_graph_traversal_candidate_surface_frame"
    r3_payload = adapter.payloads_by_node["R3"]
    assert r3_payload["hierarchy_child_candidate_count"] == 2


def test_source_ingest_selection_exposes_source_kind_children() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _source_ingest_row(
                source_graph_node_ids=[
                    "graph:source_kind_bundle:batch:code",
                    "graph:source_kind_bundle:batch:document",
                ],
            ),
            _source_kind_row("code"),
            _source_kind_row("document"),
        ],
        summary_rows=[],
    )
    adapter = HierarchyAdapter(preferred_kind="source_ingest_bundle")

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_183_source_ingest",
        user_question="source ingest 아래 자료 종류 후보를 봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_183_source_ingest",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r3_inspection is not None
    assert result.r3_inspection.child_node_ids == [
        "graph:source_kind_bundle:batch:code",
        "graph:source_kind_bundle:batch:document",
    ]
    assert result.graph_traversal_candidate_surface is not None
    assert result.graph_traversal_candidate_surface.candidate_count == 2


def test_token_budget_bundle_selection_exposes_source_summary_children() -> None:
    summary_id = "graph:summary:source_leaf:code_tools"
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _token_budget_bundle_row(source_graph_node_ids=[summary_id]),
        ],
        summary_rows=[_summary_row(summary_id=summary_id)],
    )
    adapter = HierarchyAdapter(preferred_kind="token_budget_summary_bundle")

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_183_token_bundle",
        user_question="토큰 묶음 아래 요약 후보를 봐",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_183_token_bundle",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r3_inspection is not None
    assert result.r3_inspection.child_node_ids == [summary_id]
    assert result.graph_traversal_candidate_surface is not None
    assert result.graph_traversal_candidate_surface.child_candidate_node_ids == [summary_id]


def _record_packet(
    *,
    entry_rows: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
):
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_183_packet",
        batch_id="order_183_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=entry_rows,
            summary_rows=summary_rows,
        ),
    )
    return trace_store, data_store, recorded.trace_event_id, recorded.packet


def _time_axis_row() -> dict[str, object]:
    return {
        "candidate_node_id": "graph:axis:time",
        "display_name": "Time Axis",
        "node_kind": "time_axis",
        "data_kind": "time_axis",
        "created_at": "2026-07-02T00:00:00",
        "written_at": "2026-07-02T00:00:00",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "time_axis",
                "data_kind": "time_axis",
                "summary_depth": 0,
            },
            ensure_ascii=False,
        ),
        "labels": ["GraphMemoryNode", "TimeAxis"],
    }


def _source_ingest_row(
    *,
    source_graph_node_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "candidate_node_id": "graph:source_ingest_time_bundle:night_changed_sources",
        "display_name": "Source Ingest Bundle",
        "node_kind": "source_ingest_time_bundle",
        "data_kind": "source_ingest_time_bundle",
        "created_at": "2026-07-02T14:02:36",
        "written_at": "2026-07-02T14:02:36",
        "source_trace_id": "trace:source:manifest",
        "payload_json": json.dumps(
            {
                "node_kind": "source_ingest_time_bundle",
                "data_kind": "source_ingest_time_bundle",
                "summary_depth": 0,
                "source_leaf_count": 2,
                "source_summary_count": 0,
                "source_graph_node_ids": source_graph_node_ids or [],
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode", "SourceIngestBundle"],
        "parent_graph_node_ids": ["graph:axis:time"],
    }


def _time_bundle_row() -> dict[str, object]:
    return {
        "candidate_node_id": "graph:time_bundle:manual_vessel_first_write:core",
        "display_name": "Time Bundle",
        "node_kind": "time_bundle",
        "data_kind": "time_bundle",
        "created_at": "2026-07-01T18:39:54",
        "written_at": "2026-07-01T18:39:54",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "time_bundle",
                "data_kind": "time_bundle",
                "summary_depth": 0,
                "source_leaf_count": 1,
                "source_summary_count": 0,
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode", "TimeBundle"],
        "parent_graph_node_ids": ["graph:axis:time"],
    }


def _source_kind_row(source_kind: str) -> dict[str, object]:
    return {
        "candidate_node_id": f"graph:source_kind_bundle:batch:{source_kind}",
        "display_name": f"Source Kind Bundle: {source_kind}",
        "node_kind": "source_kind_bundle",
        "data_kind": f"{source_kind}_bundle",
        "created_at": "2026-07-02T14:02:36",
        "written_at": "2026-07-02T14:02:36",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "source_kind_bundle",
                "data_kind": f"{source_kind}_bundle",
                "summary_depth": 0,
                "source_leaf_count": 1,
                "source_summary_count": 0,
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode", "SourceKindBundle"],
        "parent_graph_node_ids": ["graph:source_ingest_time_bundle:night_changed_sources"],
    }


def _token_budget_bundle_row(*, source_graph_node_ids: list[str]) -> dict[str, object]:
    return {
        "candidate_node_id": "graph:token_budget_summary_bundle:night:0001",
        "display_name": "Token Budget Summary Bundle",
        "node_kind": "token_budget_summary_bundle",
        "data_kind": "token_budget_summary_bundle",
        "created_at": "2026-07-02T18:00:00",
        "written_at": "2026-07-02T18:00:00",
        "source_trace_id": None,
        "payload_json": json.dumps(
            {
                "node_kind": "token_budget_summary_bundle",
                "data_kind": "token_budget_summary_bundle",
                "summary_depth": 1,
                "source_leaf_count": 1,
                "source_summary_count": 1,
                "source_graph_node_ids": source_graph_node_ids,
            },
            ensure_ascii=False,
        ),
        "labels": ["VesselRecord", "GraphMemoryNode"],
    }


def _summary_row(*, summary_id: str) -> dict[str, object]:
    return {
        "summary_node_id": summary_id,
        "summary_display_name": "Summary: code_tools",
        "data_kind": "source_leaf_summary",
        "info_class": "relative",
        "generated_by": "LLM:fake:night_summarize_source_leaf",
        "payload_json": json.dumps(
            {
                "data_kind": "source_leaf_summary",
                "summary_depth": 1,
                "summary_status": "ran",
                "validity_status": "active",
                "review_status": "not_reviewed",
                "target_graph_node_id": "graph:raw_source:code_tools",
                "target_node_kind": "raw_source",
                "source_leaf_count": 1,
                "source_summary_count": 0,
                "source_graph_node_ids": ["graph:raw_source:code_tools"],
                "source_data_ids": ["graph:raw_source:code_tools"],
                "source_trace_ids": ["trace:summary:active"],
                "info_class": "relative",
                "generated_by": "LLM:fake:night_summarize_source_leaf",
                "summary_text": "code_tools.py read-only inspection tool summary.",
            },
            ensure_ascii=False,
        ),
        "target_graph_node_id": "graph:raw_source:code_tools",
        "target_display_name": "Raw Source: code_tools",
        "target_node_kind": "raw_source",
    }


class HierarchyAdapter:
    model_id = "hierarchy-adapter"

    def __init__(self, *, preferred_kind: str | None = None) -> None:
        self.preferred_kind = preferred_kind
        self.payloads_by_node: dict[str, dict[str, object]] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.payloads_by_node["R1"] = request.input_payload
            user_question = str(request.input_payload.get("user_question") or "")
            payload = {
                "graph_search_goal": f"Inspect graph hierarchy for: {user_question}",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "raw",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after one hierarchy inspection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.payloads_by_node["R2"] = request.input_payload
            surface_ref, node_ref = _select_node_ref(
                request.input_payload,
                preferred_kind=self.preferred_kind,
            )
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the hierarchy entry candidate requested by the test.",
                "expected_information_granularity": "raw",
                "expected_source_kind": self.preferred_kind or "entry_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            self.payloads_by_node["R3"] = request.input_payload
            has_children = bool(request.input_payload.get("hierarchy_child_candidate_count"))
            payload = {
                "current_information_granularity": "raw",
                "sufficiency_status": "insufficient" if has_children else "unknown",
                "granularity_problem_status": "needs_lower_granularity"
                if has_children
                else "unknown",
                "branch_problem_status": "none",
                "recommended_next_action": "deeper" if has_children else "fail",
                "inspection_reason": "Child candidates are available for the next graph layer."
                if has_children
                else "No hierarchy child candidates are available.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _select_node_ref(
    payload: dict[str, object],
    *,
    preferred_kind: str | None,
) -> tuple[str | None, str | None]:
    surface_refs = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(surface_refs, list) or not isinstance(records_by_surface, dict):
        return None, None
    fallback: tuple[str | None, str | None] = (None, None)
    for surface_ref in surface_refs:
        if not isinstance(surface_ref, str):
            continue
        records = records_by_surface.get(surface_ref)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            node_ref = record.get("node_ref")
            if not isinstance(node_ref, str):
                continue
            if fallback == (None, None):
                fallback = (surface_ref, node_ref)
            if preferred_kind and record.get("candidate_kind") == preferred_kind:
                return surface_ref, node_ref
    return fallback
