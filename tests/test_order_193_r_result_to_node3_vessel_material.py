import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import (
    RLoopVesselTraverseFakeLLMAdapter,
    run_r_loop_vessel_traverse,
)
from songryeon_core.nodes.node_2_handoff import (
    node3_brief_llm_payload,
    record_node3_input_brief,
)
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper

from tests.test_order_183_r_vessel_hierarchical_child_surface import (
    _source_ingest_row,
    _time_axis_row,
)
from tests.test_order_184_r_vessel_multi_step_traversal import (
    SOURCE_KIND_ID,
    SUMMARY_ID,
    _record_packet,
    _source_kind_row,
    _summary_row,
)


def test_node3_brief_receives_vessel_r_summary_material_without_raw_id_payload() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet(
        entry_rows=[
            _time_axis_row(),
            _source_ingest_row(source_graph_node_ids=[SOURCE_KIND_ID]),
            _source_kind_row(source_graph_node_ids=[SUMMARY_ID]),
        ],
        summary_rows=[_summary_row()],
    )
    traverse_result = run_r_loop_vessel_traverse(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_193_traverse",
        user_question="CoreEgo에서 소스 요약까지 계층적으로 내려가",
        read_packet=packet,
        adapter=RLoopVesselTraverseFakeLLMAdapter(),
        frame_label="order_193_traverse",
        input_ref=[packet_event_id],
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_193_brief",
        user_question="R 탐색 결과를 최종 답변 재료로 써도 되는지 확인해줘",
        handoff_frame_id="node_2:handoff:order_193",
        boundary=MetainfoBoundary(),
        input_trace_ids=[packet_event_id],
        source_data_ids=["node_2:handoff:order_193"],
    )

    assert traverse_result.result_frame.r_loop_task_status == "sufficient"
    assert brief.vessel_r_material_status == "present"
    assert brief.vessel_r_material is not None
    assert brief.vessel_r_material.r_loop_task_status == "sufficient"
    assert brief.vessel_r_material.summary_material_count == 1
    assert brief.vessel_r_material_count == len(brief.vessel_r_material.material_items)

    summary_item = next(
        item
        for item in brief.vessel_r_material.material_items
        if item.material_kind == "summary"
    )
    assert summary_item.summary_text == "Code source kind bundle summary for R traversal."
    assert summary_item.info_class == "mixed"
    assert SUMMARY_ID in brief.vessel_r_material.source_data_ids

    payload = node3_brief_llm_payload(brief)
    vessel_payload = payload["vessel_r_material"]
    assert vessel_payload["status"] == "present"
    assert vessel_payload["task_status"] == "sufficient"
    assert vessel_payload["summary_material_count"] == 1
    assert "graph_node_id" not in vessel_payload["items"][0]
    summary_payload_item = next(
        item
        for item in vessel_payload["items"]
        if item["material_kind"] == "summary"
    )
    assert summary_payload_item["summary_text"] == (
        "Code source kind bundle summary for R traversal."
    )

    grounding_block = build_node3_grounding_block(brief)
    assert "Vessel R graph material: 4개" in grounding_block


def test_node3_brief_preserves_failed_vessel_r_material_as_failed() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    data_store.create_record(
        data_id="r_loop:vessel_traverse_result:order_193_failed",
        data_type="r_loop:vessel_traverse_result",
        payload={
            "frame_id": "r_loop:vessel_traverse_result:order_193_failed",
            "source_packet_id": "r_loop:vessel_read_packet:missing",
            "traverse_status": "failed",
            "r_loop_task_status": "failed",
            "failure_type": "schema_failed",
            "failure_reason": "R2 selected_graph_node_id must be available",
            "selected_graph_node_ids": [],
            "inspected_graph_node_ids": [],
            "source_data_ids": ["r_loop:vessel_read_packet:missing"],
            "source_trace_ids": ["trace:r:failed"],
        },
        source_trace_id="trace:r:failed",
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_193_failed",
        user_question="R 실패 상태를 보존해줘",
        handoff_frame_id="node_2:handoff:order_193_failed",
        boundary=MetainfoBoundary(),
        input_trace_ids=["trace:user"],
        source_data_ids=["node_2:handoff:order_193_failed"],
    )

    assert brief.vessel_r_material_status == "failed"
    assert brief.vessel_r_material_count == 0
    assert brief.vessel_r_material is not None
    assert brief.vessel_r_material.failure_type == "schema_failed"
    assert brief.vessel_r_material.material_items == []


def test_node4_blocks_vessel_r_success_claim_when_material_is_failed() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    data_store.create_record(
        data_id="r_loop:vessel_traverse_result:order_193_guard_failed",
        data_type="r_loop:vessel_traverse_result",
        payload={
            "frame_id": "r_loop:vessel_traverse_result:order_193_guard_failed",
            "source_packet_id": "r_loop:vessel_read_packet:missing",
            "traverse_status": "failed",
            "r_loop_task_status": "failed",
            "failure_type": "schema_failed",
            "failure_reason": "simulated failed traversal",
            "selected_graph_node_ids": [],
            "inspected_graph_node_ids": [],
            "source_data_ids": ["r_loop:vessel_read_packet:missing"],
            "source_trace_ids": ["trace:r:failed"],
        },
        source_trace_id="trace:r:failed",
    )
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_193_guard",
        user_question="R 실패 상태를 보존해줘",
        handoff_frame_id="node_2:handoff:order_193_guard",
        boundary=MetainfoBoundary(),
        input_trace_ids=["trace:user"],
        source_data_ids=["node_2:handoff:order_193_guard"],
    )
    rendered_markdown = "\n\n".join(
        [
            build_node3_grounding_block(brief),
            "Vessel R 탐색은 성공했고 그래프 기억 탐색도 충분했다.",
        ]
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_193_guard",
        report_id="node_3:report:order_193_guard",
        boundary_id="node_2:boundary:order_193_guard",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=PassGatekeeperAdapter(),
        input_ref=["trace:user"],
        source_data_ids=[brief.frame_id],
    )

    gate_payload = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate_payload["gate_status"] == "needs_revision"
    assert "CODE_STATUS:vessel_r_material_claim_mismatch" in gate_payload["reason"]
    assert any(
        contradiction.startswith("vessel_r_success_claim_without_sufficient_material")
        for contradiction in gate_payload["contradictions"]
    )


class PassGatekeeperAdapter:
    model_id = "fake-pass-gatekeeper"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(
                {
                    "gate_status": "pass",
                    "reason": "fake pass before code guards",
                    "checked_claims": ["fake_llm_pass"],
                    "unsupported_claims": [],
                    "contradictions": [],
                    "revision_targets": [],
                },
                ensure_ascii=False,
            ),
            model_id=self.model_id,
        )
