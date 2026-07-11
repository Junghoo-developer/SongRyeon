from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
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
from tests.test_order_190_r_vessel_token_summary_deeper_child_expansion import (
    _entry_rows,
    _summary_rows,
)


def test_r2_payload_puts_official_selection_table_first() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_226_packet",
        batch_id="order_226_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = OfficialTableOnlyAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_226_traverse",
        user_question="R2 공식 선택표만 보고 한 후보를 골라",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_226_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert adapter.r2_payloads
    payload = adapter.r2_payloads[0]
    assert list(payload)[0] == "official_selection_table"

    table = payload["official_selection_table"]
    assert isinstance(table, dict)
    assert table["table_status"] == "available"
    assert table["allowed_surface_refs"] == payload["available_surface_refs"]
    assert table["allowed_node_refs_by_surface_ref"]
    assert table["candidate_rows"]
    assert "graph_node_id" not in json.dumps(table, ensure_ascii=False)
    assert "summary_text" not in json.dumps(table, ensure_ascii=False)


def test_r2_repair_payload_carries_official_selection_table() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_226_repair_packet",
        batch_id="order_226_repair_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = OfficialTableRepairAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_226_repair",
        user_question="R2 공식 선택표가 repair에도 남는지 확인해",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_226_repair",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert adapter.repair_table_status == "available"
    assert adapter.preserve_status == "valid_selected_refs"
    assert adapter.repaired_surface_ref == adapter.failed_surface_ref
    assert adapter.repaired_node_ref == adapter.failed_node_ref


class OfficialTableOnlyAdapter:
    model_id = "order-226-official-table-only-fake"

    def __init__(self) -> None:
        self.r2_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            payload = {
                "graph_search_goal": "Select from the official R2 selection table.",
                "user_question_anchor_id": request.input_payload["user_question_anchor"]["anchor_id"],
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 3,
                "stop_condition": "Stop after one official table selection.",
            }
        elif "R2 Vessel Node Selector" in request.prompt:
            self.r2_payloads.append(dict(request.input_payload))
            surface_ref, node_ref = _first_official_table_row(request.input_payload)
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Copied refs from official_selection_table only.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "official_table_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "One official-table-selected candidate is enough for this test.",
            }
        else:
            payload = {}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


class OfficialTableRepairAdapter(OfficialTableOnlyAdapter):
    model_id = "order-226-official-table-repair-fake"

    def __init__(self) -> None:
        super().__init__()
        self.failed_once = False
        self.failed_surface_ref: str | None = None
        self.failed_node_ref: str | None = None
        self.repaired_surface_ref: str | None = None
        self.repaired_node_ref: str | None = None
        self.repair_table_status: str | None = None
        self.preserve_status: str | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" not in request.prompt:
            return super().complete(request)
        self.r2_payloads.append(dict(request.input_payload))
        if "schema_repair_request" not in request.input_payload and not self.failed_once:
            self.failed_once = True
            surface_ref, node_ref = _first_official_table_row(request.input_payload)
            self.failed_surface_ref = surface_ref
            self.failed_node_ref = node_ref
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": surface_ref,
                "selected_node_ref": node_ref,
                "selection_reason": "Valid table refs, invalid enum for repair.",
                "expected_information_granularity": "낮은 요약",
                "expected_source_kind": "official_table_candidate",
            }
        elif "schema_repair_request" in request.input_payload:
            repair_table = request.input_payload["r2_copy_repair_table"]
            official_table = repair_table["official_selection_table"]
            preserve = repair_table["preserve_failed_selection_refs"]
            self.repair_table_status = official_table["table_status"]
            self.preserve_status = preserve["status"]
            self.repaired_surface_ref = preserve["selected_surface_ref"]
            self.repaired_node_ref = preserve["selected_node_ref"]
            payload = {
                "selection_status": "selected",
                "selected_surface_ref": self.repaired_surface_ref,
                "selected_node_ref": self.repaired_node_ref,
                "selection_reason": "Repair preserved official-table refs and fixed enum.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "official_table_candidate",
            }
        else:
            surface_ref, node_ref = _first_official_table_row(request.input_payload)
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Copied refs from official_selection_table after repair test.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "official_table_candidate",
            }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_official_table_row(
    payload: dict[str, object],
) -> tuple[str | None, str | None]:
    table = payload.get("official_selection_table")
    if not isinstance(table, dict):
        return None, None
    rows = table.get("candidate_rows")
    if not isinstance(rows, list):
        return None, None
    for row in rows:
        if not isinstance(row, dict):
            continue
        surface_ref = row.get("surface_ref")
        node_ref = row.get("node_ref")
        if isinstance(surface_ref, str) and isinstance(node_ref, str):
            return surface_ref, node_ref
    return None, None
