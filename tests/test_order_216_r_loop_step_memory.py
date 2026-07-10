from __future__ import annotations

from songryeon_core.loops.r_loop_vessel_one_step import (
    R_LOOP_VESSEL_STEP_MEMORY_DATA_TYPE,
    run_r_loop_vessel_traverse,
)

from tests.test_order_190_r_vessel_token_summary_deeper_child_expansion import (
    CHILD_TOKEN_SUMMARY_ID,
    PARENT_TOKEN_SUMMARY_ID,
    TokenSummaryNeedsDeeperAdapter,
    _entry_rows,
    _summary_rows,
)
from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import (
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    build_r_loop_vessel_activity_ledger_frame,
)


def test_r_loop_records_step_memory_and_feeds_it_forward() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_216_packet",
        batch_id="order_216_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = RecordingStepMemoryAdapter()

    result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_216_traverse",
        user_question="R step memory를 보존하며 token summary 아래로 내려가",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_216_traverse",
        input_ref=[recorded.trace_event_id],
    )

    assert result.result_frame.traverse_status == "completed"
    assert result.result_frame.step_memory_packet_ids == [
        packet.packet_id for packet in result.step_memory_packets
    ]
    assert len(result.step_memory_packets) == result.result_frame.step_count
    for packet in result.step_memory_packets:
        record = data_store.require_record(packet.packet_id)
        assert record.data_type == R_LOOP_VESSEL_STEP_MEMORY_DATA_TYPE
        assert packet.generated_by == "CODE:NODE_0_R_VESSEL_STEP_MEMORY"
        assert packet.info_class == "absolute"
        assert packet.semantic_judgement_status == "not_run"

    parent_packet = next(
        packet
        for packet in result.step_memory_packets
        if packet.inspected_graph_node_id == PARENT_TOKEN_SUMMARY_ID
    )
    assert parent_packet.visible_child_candidate_node_ids == [CHILD_TOKEN_SUMMARY_ID]
    assert parent_packet.promoted_next_candidate_graph_node_ids == [
        CHILD_TOKEN_SUMMARY_ID
    ]
    assert parent_packet.r3_recommended_next_action == "deeper"
    assert parent_packet.continuation_status == "continue_deeper"

    assert "previous_r_step_memory_packet" not in adapter.r2_payloads[0]
    assert "previous_r_step_memory_packet" in adapter.r2_payloads[1]
    assert "previous_r_step_memory_packet" in adapter.r3_payloads[1]
    assert (
        adapter.r2_payloads[1]["previous_r_step_memory_packet"]["packet_id"]
        == result.step_memory_packets[0].packet_id
    )

    ledger = build_r_loop_vessel_activity_ledger_frame(
        data_store=data_store,
        turn_id="turn_order_216_ledger",
        traverse_run=result,
        frame_label="order_216_ledger",
    )
    assert ledger.step_memory_packet_ids == [
        packet.packet_id for packet in result.step_memory_packets
    ]
    assert {
        record["stage"]
        for record in ledger.activity_records
        if record["data_id"] in ledger.step_memory_packet_ids
    } == {"step_memory"}


def test_r3_sees_child_candidates_as_preview_not_bulk_summary_text() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_216_preview_packet",
        batch_id="order_216_preview_packet",
        config=_config(),
        created_at=READ_AT,
        limit=2,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )
    adapter = RecordingStepMemoryAdapter()

    run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_216_preview",
        user_question="R3 child preview만 확인해",
        read_packet=recorded.packet,
        adapter=adapter,
        frame_label="order_216_preview",
        input_ref=[recorded.trace_event_id],
    )

    parent_payload = next(
        payload
        for payload in adapter.r3_payloads
        if isinstance(payload.get("selected_candidate_record"), dict)
        and payload["selected_candidate_record"].get("summary_node_id")
        == PARENT_TOKEN_SUMMARY_ID
    )
    selected = parent_payload["selected_candidate_record"]
    assert selected["summary_text"]
    child_records = selected["hierarchy_child_candidate_records"]
    assert child_records == parent_payload["hierarchy_child_candidate_records"]
    assert child_records[0]["candidate_node_id"] == CHILD_TOKEN_SUMMARY_ID
    assert "summary_text_preview" in child_records[0]
    assert "summary_text" not in child_records[0]


class RecordingStepMemoryAdapter(TokenSummaryNeedsDeeperAdapter):
    def __init__(self) -> None:
        self.r2_payloads: list[dict[str, object]] = []
        self.r3_payloads: list[dict[str, object]] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R2 Vessel Node Selector" in request.prompt:
            self.r2_payloads.append(dict(request.input_payload))
        if "R3 Vessel Inspector" in request.prompt:
            self.r3_payloads.append(dict(request.input_payload))
        return super().complete(request)
