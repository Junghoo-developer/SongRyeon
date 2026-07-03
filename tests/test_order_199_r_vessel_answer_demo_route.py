from __future__ import annotations

from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper
from songryeon_core.runtime.r_loop_vessel_answer_demo import (
    render_r_loop_vessel_answer_demo_text,
    run_local_r_loop_vessel_answer_demo,
)

from tests.test_order_175_vessel_backed_r_read_packet import (
    FailingDriverFactory,
    FakeRLoopVesselDriverFactory,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _source_ingest_row,
    _source_kind_row,
    _summary_row,
    _time_axis_row,
)
from tests.test_order_193_r_result_to_node3_vessel_material import (
    PassGatekeeperAdapter,
)


def test_fake_answer_demo_runs_from_r_start_to_node4_pass() -> None:
    result = run_local_r_loop_vessel_answer_demo(
        user_question="Vessel R answer demo로 그래프 기억 재료를 설명해줘",
        batch_id="order_199_success",
        turn_id="turn_order_199_success",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
            ],
            summary_rows=[_summary_row()],
        ),
    )

    assert result["status"] == "R_LOOP_VESSEL_ANSWER_DEMO_OK"
    assert result["demo_status"] == "completed"
    assert result["return_packet_status"] == "available"
    assert result["return_packet_node3_material_ready"] is True
    assert result["node2_handoff_status"] == "ready"
    assert result["node3_vessel_r_material_status"] == "present"
    assert result["node3_reporter_status"] == "ran"
    assert result["node4_gate_status"] == "pass"
    assert "graph-memory 재료" in str(result["final_answer"])
    assert "문서 근거" not in str(result["final_answer"])

    key_frame_ids = result["key_frame_ids"]
    assert isinstance(key_frame_ids, dict)
    for key in [
        "read_packet",
        "start_handoff",
        "traverse_result",
        "activity_ledger",
        "return_packet",
        "node2_handoff",
        "node3_brief",
        "node3_report",
        "node4_gatekeeper",
    ]:
        assert key_frame_ids[key]

    rendered = render_r_loop_vessel_answer_demo_text(result)
    assert "node_0 Vessel R return packet: status=available" in rendered
    assert "node_4 gatekeeper: status=pass" in rendered


def test_failed_r_traversal_demo_keeps_safe_partial_answer() -> None:
    result = run_local_r_loop_vessel_answer_demo(
        user_question="R read failure도 성공처럼 말하지 마",
        batch_id="order_199_failed",
        turn_id="turn_order_199_failed",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FailingDriverFactory(),
    )

    assert result["status"] == "R_LOOP_VESSEL_ANSWER_DEMO_OK"
    assert result["read_packet_status"] == "read_failed"
    assert result["traverse_status"] == "failed"
    assert result["return_packet_status"] == "failed"
    assert result["return_packet_node3_material_ready"] is False
    assert result["node3_vessel_r_material_status"] == "failed"
    assert result["node4_gate_status"] == "pass"
    assert "완료 상태로 단정하지 않고" in str(result["final_answer"])


def test_node3_brief_uses_return_packet_as_vessel_material_source() -> None:
    result = run_local_r_loop_vessel_answer_demo(
        user_question="return packet source 확인",
        batch_id="order_199_return_source",
        turn_id="turn_order_199_return_source",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FakeRLoopVesselDriverFactory(
            entry_rows=[
                _time_axis_row(),
                _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
                _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
            ],
            summary_rows=[_summary_row()],
        ),
    )

    brief = result["node3_brief_frame"]
    assert isinstance(brief, dict)
    vessel_material = brief["vessel_r_material"]
    assert isinstance(vessel_material, dict)
    assert vessel_material["source_data_id"] == result["return_packet_id"]
    assert result["return_packet_id"] in brief["vessel_r_material_source_data_ids"]


def test_node4_still_blocks_overclaimed_failed_r_material() -> None:
    result = run_local_r_loop_vessel_answer_demo(
        user_question="실패한 R material을 만들어줘",
        batch_id="order_199_guard_failed",
        turn_id="turn_order_199_guard_failed",
        database="neo4j",
        allow_no_auth=True,
        llm_mode="fake",
        driver_factory_for_test=FailingDriverFactory(),
    )
    from songryeon_core.core.data_store import DataStore
    from songryeon_core.core.trace_store import TraceStore

    trace_store = TraceStore()
    data_store = DataStore()
    data_store.create_record(
        data_id=result["return_packet_id"],
        data_type="r_loop:vessel_return_packet",
        payload=result["return_packet_frame"],
        source_trace_id="trace:r:return",
    )
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_199_guard_recheck",
        user_question="실패한 R 탐색을 성공으로 과장하지 마",
        handoff_frame_id="node_2:handoff:order_199_guard",
        boundary=MetainfoBoundary(),
        input_trace_ids=["trace:user"],
        source_data_ids=["node_2:handoff:order_199_guard", result["return_packet_id"]],
    )
    overclaimed = "\n\n".join(
        [
            build_node3_grounding_block(brief),
            "Vessel R 탐색은 성공했고 graph memory traversal도 충분했다.",
        ]
    )
    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_199_guard_recheck",
        report_id="node_3:report:order_199_guard",
        boundary_id="node_2:boundary:order_199_guard",
        brief_frame=brief,
        rendered_markdown=overclaimed,
        adapter=PassGatekeeperAdapter(),
        input_ref=["trace:user"],
        source_data_ids=[brief.frame_id],
    )

    gate = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate["gate_status"] == "needs_revision"
    assert "CODE_STATUS:vessel_r_material_claim_mismatch" in gate["reason"]
