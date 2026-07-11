from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import Node3InputBriefFrame, Node3VesselRMaterial
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


def test_node4_does_not_treat_negated_vessel_r_success_phrase_as_claim() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    brief = _partial_vessel_r_brief()
    rendered_markdown = "\n\n".join(
        [
            build_node3_grounding_block(brief),
            "Vessel R 자료는 부분 장부라서 graph memory 탐색 성공으로 단정하지 않는다.",
        ]
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_230_negative_success",
        report_id="node_3:report:order_230_negative_success",
        boundary_id="node_2:boundary:order_230_negative_success",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=PassGatekeeperAdapter(),
        input_ref=["trace:user"],
        source_data_ids=[brief.frame_id],
    )

    gate_payload = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate_payload["gate_status"] == "pass"
    assert "CODE_STATUS:vessel_r_material_claim_mismatch" not in gate_payload["reason"]


def test_node3_grounding_block_uses_non_success_wording_for_partial_r() -> None:
    grounding_block = build_node3_grounding_block(_partial_vessel_r_brief())

    assert "Vessel R graph material: 0개 / status=present / task=partial" in grounding_block
    assert "R 탐색이 요구 수준에 도달했다고 보지 않는다" in grounding_block
    assert "R 탐색 상태가 요구 수준에 도달했다고 단정하지 않는다" not in grounding_block


def _partial_vessel_r_brief() -> Node3InputBriefFrame:
    vessel_material = Node3VesselRMaterial(
        source_data_id="r_loop:vessel_return_packet:order_230_partial",
        material_status="present",
        traverse_status="completed",
        r_loop_task_status="partial",
        failure_type=None,
        failure_reason=None,
        traversal_path_count=0,
        selected_graph_node_ids=[],
        inspected_graph_node_ids=[],
        summary_material_count=0,
        raw_original_material_count=0,
        source_data_ids=["r_loop:vessel_return_packet:order_230_partial"],
    )
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame:order_230_partial",
        turn_id="turn_order_230_partial",
        user_question="partial R 결과를 성공처럼 말하지 마",
        brief_status="ready",
        handoff_frame_id="node_2:handoff:order_230_partial",
        vessel_r_material_status="present",
        vessel_r_material_count=0,
        vessel_r_material_source_data_ids=["r_loop:vessel_return_packet:order_230_partial"],
        vessel_r_material=vessel_material,
        source_trace_ids=["trace:user"],
        source_data_ids=[
            "node_2:handoff:order_230_partial",
            "r_loop:vessel_return_packet:order_230_partial",
        ],
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
            raw={},
        )
