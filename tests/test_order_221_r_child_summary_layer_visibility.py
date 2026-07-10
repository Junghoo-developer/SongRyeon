from __future__ import annotations

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
    TokenSummaryNeedsDeeperAdapter,
    _entry_rows,
    _summary_rows,
)


def test_r2_receives_clean_child_summary_layer_without_candidate_trimming() -> None:
    adapter = CapturingChildSummaryLayerAdapter()

    run_r_loop_vessel_traverse(
        trace_store=TraceStore(),
        data_store=DataStore(),
        turn_id="turn_order_221_r2_visibility",
        user_question="source kind 아래 child summary layer를 확인해",
        read_packet=_packet(),
        adapter=adapter,
        frame_label="order_221_r2_visibility",
        input_ref=["trace:order_221"],
    )

    source_kind_cards = [
        record
        for payload in adapter.r2_payloads
        for records in _records_by_surface(payload).values()
        for record in records
        if record.get("candidate_kind") == "source_kind_bundle"
    ]

    assert source_kind_cards
    source_kind_card = source_kind_cards[0]
    assert source_kind_card["child_summary_layer_status"] == "clean_summary_layer"
    assert source_kind_card["child_summary_layer_data_kind"] == (
        "token_budget_bundle_summary"
    )
    assert source_kind_card["child_summary_layer_record_count"] == 2
    layer_records = source_kind_card["child_summary_layer_records"]
    assert isinstance(layer_records, list)
    assert len(layer_records) == 2
    assert all("summary_text_preview" in record for record in layer_records)
    assert all("summary_text" not in record for record in layer_records)


def test_r3_receives_same_clean_child_summary_layer_for_selected_source_kind() -> None:
    adapter = CapturingChildSummaryLayerAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=TraceStore(),
        data_store=DataStore(),
        turn_id="turn_order_221_r3_visibility",
        user_question="source kind 아래 child summary layer를 R3도 확인해",
        read_packet=_packet(),
        adapter=adapter,
        frame_label="order_221_r3_visibility",
        input_ref=["trace:order_221"],
    )

    assert result.result_frame.traverse_status == "completed"
    source_kind_payloads = [
        payload
        for payload in adapter.r3_payloads
        if isinstance(payload.get("selected_candidate_record"), dict)
        and payload["selected_candidate_record"].get("candidate_kind")
        == "source_kind_bundle"
    ]
    assert source_kind_payloads
    child_layer = source_kind_payloads[0]["hierarchy_child_summary_layer"]
    assert child_layer["status"] == "clean_summary_layer"
    assert child_layer["data_kind"] == "token_budget_bundle_summary"
    assert child_layer["record_count"] == 2
    assert len(child_layer["records"]) == 2


class CapturingChildSummaryLayerAdapter(TokenSummaryNeedsDeeperAdapter):
    def __init__(self) -> None:
        self.r2_payloads: list[dict[str, object]] = []
        self.r3_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" in request.prompt:
            self.r2_payloads.append(dict(request.input_payload))
        if "R3 Vessel Inspector" in request.prompt:
            self.r3_payloads.append(dict(request.input_payload))
        return super().complete(request)


def _packet():
    recorded = record_r_loop_vessel_read_packet(
        trace_store=TraceStore(),
        data_store=DataStore(),
        turn_id="turn_order_221_packet",
        batch_id="order_221_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    return recorded.packet


def _records_by_surface(
    payload: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(records_by_surface, dict):
        return {}
    result: dict[str, list[dict[str, object]]] = {}
    for surface_ref, records in records_by_surface.items():
        if not isinstance(surface_ref, str) or not isinstance(records, list):
            continue
        result[surface_ref] = [
            record for record in records if isinstance(record, dict)
        ]
    return result
