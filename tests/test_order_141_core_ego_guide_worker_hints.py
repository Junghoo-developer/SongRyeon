from __future__ import annotations

import json

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import (
    TIME_AXIS_NODE_ID,
    build_graph_memory_snapshot_from_capsules,
)
from songryeon_core.core.schemas import (
    CoreEgoGuideWorkerHintFrame,
    NodeMovement,
    TurnStateCapsule,
    validate_core_ego_guide_worker_hint_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.fake import BrokenJSONFakeLLMAdapter
from songryeon_core.nodes.core_ego_guide_worker import (
    CORE_EGO_GUIDE_WORKER_PROMPT_REF,
    run_core_ego_guide_worker_hint,
)


class CoreEgoGuideWorkerPayloadFakeAdapter:
    model_id = "core-ego-guide-worker-payload-fake-adapter"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_input_payload = request.input_payload
        return LLMResponse(
            text=json.dumps(self.payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=self.payload,
        )


def test_core_ego_guide_worker_accepts_available_entry_id() -> None:
    trace_store, data_store, guide = _stores_and_guide()
    adapter = CoreEgoGuideWorkerPayloadFakeAdapter(
        {
            "recommended_entry_node_ids": [TIME_AXIS_NODE_ID],
            "avoid_entry_node_ids": [],
            "traversal_strategy_hint": "Start from the time axis and inspect recent time bundles first.",
            "reason_summary": "The code guide exposes the time axis as the only current entry.",
            "risk_notes": ["semantic axis is not created"],
            "expected_depth_policy": "Use shallow traversal, then descend only if raw capsules are needed.",
            "source_graph_node_ids": [TIME_AXIS_NODE_ID],
            "source_data_ids": [guide.packet_id, guide.graph_snapshot_id],
            "info_class": "mixed",
            "semantic_judgement_status": "ran",
        }
    )

    _, frame_id, frame = run_core_ego_guide_worker_hint(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_141",
        guide_packet=guide,
        adapter=adapter,
    )

    assert frame_id == f"{guide.packet_id}:core_ego_guide_worker_hint"
    assert frame.recommended_entry_node_ids == [TIME_AXIS_NODE_ID]
    assert frame.hint_status == "ran"
    assert frame.failure_type == "none"
    assert frame.generated_by == f"LLM:{adapter.model_id}:core_ego_guide_worker"
    assert frame.info_class == "mixed"
    assert frame.source_mode == "source_bundle"
    assert frame.claim_alignment == "multi_source_bundle"
    assert frame.semantic_judgement_status == "ran"
    assert guide.packet_id in frame.source_data_ids
    assert guide.graph_snapshot_id in frame.source_data_ids
    assert frame.llm_call_data_id in frame.source_data_ids
    assert data_store.require_record(frame.frame_id).data_type == (
        "node_output:core_ego_guide_worker_hint_frame"
    )
    assert adapter.last_input_payload is not None
    assert adapter.last_input_payload["available_entry_node_ids"] == [TIME_AXIS_NODE_ID]


def test_core_ego_guide_worker_rejects_recommendation_outside_available_entries() -> None:
    trace_store, data_store, guide = _stores_and_guide()
    adapter = CoreEgoGuideWorkerPayloadFakeAdapter(
        {
            "recommended_entry_node_ids": ["graph:axis:semantic"],
            "avoid_entry_node_ids": [],
            "traversal_strategy_hint": "Use the semantic axis.",
            "reason_summary": "This payload intentionally invents an unavailable entry.",
            "risk_notes": [],
            "expected_depth_policy": "shallow",
            "source_graph_node_ids": [TIME_AXIS_NODE_ID],
            "source_data_ids": [guide.packet_id],
        }
    )

    _, _, frame = run_core_ego_guide_worker_hint(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_141",
        guide_packet=guide,
        adapter=adapter,
    )

    assert frame.hint_status == "failed"
    assert frame.failure_type == "schema_failed"
    assert frame.payload_parse_status == "passed"
    assert frame.recommended_entry_node_ids == []
    assert frame.semantic_judgement_status == "failed"
    assert frame.llm_call_data_id is not None
    llm_call = data_store.require_record(frame.llm_call_data_id)
    assert llm_call.payload["failure_type"] == "schema_failed"


def test_core_ego_guide_worker_parse_failure_records_empty_failed_hint() -> None:
    trace_store, data_store, guide = _stores_and_guide()

    _, _, frame = run_core_ego_guide_worker_hint(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_141",
        guide_packet=guide,
        adapter=BrokenJSONFakeLLMAdapter(),
    )

    assert frame.hint_status == "failed"
    assert frame.failure_type == "parse_failed"
    assert frame.payload_parse_status == "failed"
    assert frame.recommended_entry_node_ids == []
    assert frame.avoid_entry_node_ids == []
    assert frame.traversal_strategy_hint == ""
    assert frame.llm_call_data_id in frame.source_data_ids


def test_core_ego_guide_worker_hint_schema_rejects_direct_invalid_frame() -> None:
    _, _, guide = _stores_and_guide()
    frame = CoreEgoGuideWorkerHintFrame(
        frame_id=f"{guide.packet_id}:core_ego_guide_worker_hint",
        source_rloop_graph_guide_packet_id=guide.packet_id,
        graph_snapshot_id=guide.graph_snapshot_id,
        available_entry_node_ids=[TIME_AXIS_NODE_ID],
        available_source_graph_node_ids=list(guide.source_graph_node_ids),
        recommended_entry_node_ids=["graph:axis:semantic"],
        traversal_strategy_hint="invalid semantic entry",
        reason_summary="test fixture",
        expected_depth_policy="shallow",
        hint_status="ran",
        failure_type="none",
        payload_parse_status="passed",
        prompt_ref=CORE_EGO_GUIDE_WORKER_PROMPT_REF,
        source_graph_node_ids=[TIME_AXIS_NODE_ID],
        source_data_ids=[guide.packet_id, guide.graph_snapshot_id],
        generated_by="LLM:test:core_ego_guide_worker",
        info_class="mixed",
        source_mode="source_bundle",
        claim_alignment="multi_source_bundle",
        semantic_judgement_status="ran",
    )

    with pytest.raises(ValueError, match="entry node id must be available"):
        validate_core_ego_guide_worker_hint_frame(frame)


def test_code_guide_packet_and_llm_hint_stay_separate() -> None:
    trace_store, data_store, guide = _stores_and_guide()
    adapter = CoreEgoGuideWorkerPayloadFakeAdapter(
        {
            "recommended_entry_node_ids": [TIME_AXIS_NODE_ID],
            "avoid_entry_node_ids": [],
            "traversal_strategy_hint": "The first future R loop should start at the time axis.",
            "reason_summary": "Only time-axis entry data is code-confirmed in this snapshot.",
            "risk_notes": [],
            "expected_depth_policy": "Inspect one level before descending.",
            "source_graph_node_ids": [TIME_AXIS_NODE_ID],
            "source_data_ids": [guide.packet_id, guide.graph_snapshot_id],
        }
    )

    _, _, frame = run_core_ego_guide_worker_hint(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_141",
        guide_packet=guide,
        adapter=adapter,
    )

    assert guide.generated_by == "CODE:GRAPH_MEMORY_GUIDE_BUILDER"
    assert guide.info_class == "absolute"
    assert guide.semantic_judgement_status == "not_run"
    assert guide.recommended_traversal_hints == []
    assert guide.recommended_traversal_hints_status == "not_run"
    assert frame.generated_by.startswith("LLM:")
    assert frame.info_class == "mixed"
    assert frame.source_rloop_graph_guide_packet_id == guide.packet_id


def _stores_and_guide():
    build = build_graph_memory_snapshot_from_capsules(
        capsules=[_sample_capsule()],
        batch_id="batch_order_141",
    )
    return TraceStore(), DataStore(), build.guide_packet


def _sample_capsule(turn_id: str = "turn_order_141_previous") -> TurnStateCapsule:
    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=[
            NodeMovement(
                movement_id=f"move:{turn_id}:001",
                turn_id=turn_id,
                step_index=1,
                node_id="node_0",
                mode="pre_route_report",
                input_trace_ids=[f"trace:{turn_id}:user"],
                output_trace_ids=[f"trace:{turn_id}:node0"],
                status="completed",
            )
        ],
        trace_event_ids=[
            f"trace:{turn_id}:user",
            f"trace:{turn_id}:node0",
            f"trace:{turn_id}:final",
        ],
        user_input_trace_id=f"trace:{turn_id}:user",
        final_response_trace_id=f"trace:{turn_id}:final",
    )
