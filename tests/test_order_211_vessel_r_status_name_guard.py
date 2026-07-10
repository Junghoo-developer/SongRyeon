from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


def test_node4_blocks_vessel_r_failed_status_renamed_as_insufficient() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    _record_failed_vessel_r_traverse(data_store)
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_211_guard",
        user_question="R 실패 상태명을 정확히 지켜줘",
        handoff_frame_id="node_2:handoff:order_211_guard",
        boundary=MetainfoBoundary(),
        input_trace_ids=["trace:user"],
        source_data_ids=["node_2:handoff:order_211_guard"],
    )
    rendered_markdown = "\n\n".join(
        [
            build_node3_grounding_block(brief),
            "`vessel_r_material.task_status`는 `insufficient`로 표시되어 있습니다.",
        ]
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_211_guard",
        report_id="node_3:report:order_211_guard",
        boundary_id="node_2:boundary:order_211_guard",
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
        contradiction.startswith("vessel_r_status_name_mismatch")
        for contradiction in gate_payload["contradictions"]
    )


def test_node4_does_not_block_generic_limited_material_wording() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    _record_failed_vessel_r_traverse(data_store)
    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_211_limited",
        user_question="R 실패 상태명을 정확히 지켜줘",
        handoff_frame_id="node_2:handoff:order_211_limited",
        boundary=MetainfoBoundary(),
        input_trace_ids=["trace:user"],
        source_data_ids=["node_2:handoff:order_211_limited"],
    )
    rendered_markdown = "\n\n".join(
        [
            build_node3_grounding_block(brief),
            "Vessel R 자료가 없어 구체 브리핑은 제한됩니다.",
        ]
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_211_limited",
        report_id="node_3:report:order_211_limited",
        boundary_id="node_2:boundary:order_211_limited",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=PassGatekeeperAdapter(),
        input_ref=["trace:user"],
        source_data_ids=[brief.frame_id],
    )

    gate_payload = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate_payload["gate_status"] == "pass"
    assert not any(
        contradiction.startswith("vessel_r_status_name_mismatch")
        for contradiction in gate_payload["contradictions"]
    )


def _record_failed_vessel_r_traverse(data_store: DataStore) -> None:
    data_store.create_record(
        data_id="r_loop:vessel_traverse_result:order_211_failed",
        data_type="r_loop:vessel_traverse_result",
        payload={
            "frame_id": "r_loop:vessel_traverse_result:order_211_failed",
            "source_packet_id": "r_loop:vessel_read_packet:missing",
            "traverse_status": "failed",
            "r_loop_task_status": "failed",
            "failure_stage": "R2:step_0001",
            "failure_type": "schema_failed",
            "failure_reason": "R2 expected_information_granularity is invalid",
            "selected_graph_node_ids": [],
            "inspected_graph_node_ids": [],
            "source_data_ids": ["r_loop:vessel_read_packet:missing"],
            "source_trace_ids": ["trace:r:failed"],
        },
        source_trace_id="trace:r:failed",
    )


class PassGatekeeperAdapter:
    model_id = "fake-pass-gatekeeper"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(
                {
                    "gate_status": "pass",
                    "reason": "fake pass before code guards",
                    "checked_claims": [],
                    "unsupported_claims": [],
                    "contradictions": [],
                    "revision_targets": [],
                },
                ensure_ascii=False,
            ),
            model_id=self.model_id,
            raw={},
        )
