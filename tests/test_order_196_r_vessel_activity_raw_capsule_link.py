from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.r_loop_vessel_read_packet import record_r_loop_vessel_read_packet
from songryeon_core.core.r_loop_vessel_start_handoff import (
    record_r_loop_vessel_start_handoff_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.core.turn_activity_graph_links import (
    TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE,
    activity_ledger_graph_edge_id,
    activity_ledger_graph_node_id,
    record_turn_activity_graph_links,
)
from songryeon_core.loops.r_loop_vessel_activity_ledger import (
    record_r_loop_vessel_activity_ledger,
)
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)
from songryeon_core.runtime.r_loop_vessel_one_step import (
    render_r_loop_vessel_traverse_text,
    run_local_r_loop_vessel_traverse,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    READ_AT,
    FakeRLoopVesselDriverFactory,
    _config,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)


def test_raw_capsule_links_to_r_vessel_activity_ledger() -> None:
    trace_store, data_store, activity_ledger_id = _record_r_vessel_activity_ledger()

    _, frame_id, frame = record_turn_activity_graph_links(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_196",
        l_loop_activity_ledger_data_ids=[],
        r_graph_access_ledger_data_ids=[],
        r_vessel_activity_ledger_data_ids=[activity_ledger_id],
    )

    raw_node_id = "graph:raw_capsule:turn_order_196"
    activity_node_id = activity_ledger_graph_node_id(activity_ledger_id)
    edge_id = activity_ledger_graph_edge_id(
        raw_capsule_node_id=raw_node_id,
        activity_node_id=activity_node_id,
    )
    link_record = data_store.require_record(frame_id)

    assert link_record.data_type == TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE
    assert frame.r_vessel_activity_ledger_data_ids == [activity_ledger_id]
    assert frame.l_loop_activity_ledger_data_ids == []
    assert frame.r_graph_access_ledger_data_ids == []
    assert activity_node_id in frame.activity_ledger_graph_node_ids
    assert edge_id in frame.activity_ledger_graph_edge_ids
    assert frame.link_records == [
        {
            "activity_kind": "r_vessel_activity_ledger",
            "ledger_data_id": activity_ledger_id,
            "graph_node_id": activity_node_id,
            "edge_id": edge_id,
            "source_field": "r_vessel_activity_ledger_data_ids",
        }
    ]

    node = data_store.require_record(activity_node_id).payload
    assert node["node_kind"] == "activity_ledger"
    assert node["data_kind"] == "r_vessel_activity_ledger"
    assert node["source_graph_node_ids"] == [raw_node_id]
    assert node["source_data_ids"] == [activity_ledger_id]

    edge = data_store.require_record(edge_id).payload
    assert edge["edge_kind"] == "HAS_ACTIVITY_LEDGER"
    assert edge["from_node_id"] == raw_node_id
    assert edge["to_node_id"] == activity_node_id
    assert activity_ledger_id in edge["source_data_ids"]


def test_no_r_vessel_ledger_list_creates_no_fake_activity_nodes() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    _, _, frame = record_turn_activity_graph_links(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_196_empty",
        l_loop_activity_ledger_data_ids=[],
        r_graph_access_ledger_data_ids=[],
        r_vessel_activity_ledger_data_ids=[],
    )

    assert frame.r_vessel_activity_ledger_data_ids == []
    assert frame.activity_ledger_graph_node_ids == []
    assert frame.activity_ledger_graph_edge_ids == []
    assert frame.link_records == []


def test_local_vessel_r_traverse_records_r_vessel_raw_capsule_link() -> None:
    result = run_local_r_loop_vessel_traverse(
        user_question="R Vessel ledger raw capsule link를 확인해",
        batch_id="order_196_local",
        turn_id="turn_order_196_local",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[]),
            ],
            summary_rows=[_summary_row()],
        ),
    )

    assert result["turn_activity_graph_link_r_vessel_ledger_count"] == 1
    assert result["turn_activity_graph_link_node_count"] == 1
    assert result["turn_activity_graph_link_edge_count"] == 1
    assert result["activity_ledger_frame_id"] in (
        result["turn_activity_graph_link_frame"]["r_vessel_activity_ledger_data_ids"]
    )
    rendered = render_r_loop_vessel_traverse_text(result)
    assert "R Vessel raw capsule link: r_vessel_ledgers=1" in rendered


def _record_r_vessel_activity_ledger() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    recorded_packet = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_196",
        batch_id="order_196_packet",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[]),
            ],
            summary_rows=[_summary_row()],
        ),
    )
    handoff = record_r_loop_vessel_start_handoff_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_196",
        batch_id="order_196_start",
        read_packet=recorded_packet.packet,
        source_read_packet_trace_event_id=recorded_packet.trace_event_id,
    )
    run = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_196",
        user_question="R Vessel raw capsule link source를 만들어",
        read_packet=recorded_packet.packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_196_traverse",
        input_ref=[recorded_packet.trace_event_id, handoff.trace_event_id],
        start_handoff_packet_id=handoff.packet.packet_id,
    )
    _, activity_ledger_id, _ = record_r_loop_vessel_activity_ledger(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_196",
        traverse_run=run,
        frame_label="order_196_traverse",
        source_start_handoff_packet_id=handoff.packet.packet_id,
    )
    return trace_store, data_store, activity_ledger_id
