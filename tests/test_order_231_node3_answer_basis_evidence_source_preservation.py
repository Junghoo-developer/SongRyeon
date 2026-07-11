from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import DataRef, MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.nodes.node_2_metainfo_boundary import run_node2_answer_basis_selection


def test_node3_brief_preserves_answer_basis_evidence_role_sources() -> None:
    trace_store, data_store, trace_id = _stores()
    boundary = MetainfoBoundary(
        absolute_info=[
            DataRef(
                data_id="source:sample_boundary_record",
                data_type="test:boundary_sample",
                source_trace_id=trace_id,
            )
        ]
    )
    _, _, answer_basis = run_node2_answer_basis_selection(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_231",
        user_question="R 실패 상황에서도 node_3 brief가 evidence role 좌표를 보존해?",
        boundary_id="source:boundary",
        boundary=boundary,
        handoff_frame_id="source:handoff",
        adapter=AnswerBasisPayloadFakeAdapter(),
        input_ref=[trace_id],
        source_data_ids=["source:runtime"],
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_231",
        user_question="R 실패 상황에서도 node_3 brief가 evidence role 좌표를 보존해?",
        handoff_frame_id="source:handoff",
        boundary=boundary,
        answer_basis_frame=answer_basis,
        input_trace_ids=[trace_id],
        source_data_ids=["source:handoff"],
    )

    assert answer_basis.evidence_roles[0].source_data_id == "source:sample_boundary_record"
    assert brief.evidence_roles[0].source_data_id == "source:sample_boundary_record"
    assert "source:sample_boundary_record" in brief.source_data_ids
    assert answer_basis.frame_id in brief.source_data_ids


class AnswerBasisPayloadFakeAdapter:
    model_id = "order-231-answer-basis-source-preservation-fake"

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "answer_basis_mode": "mixed_or_uncertain",
            "basis_reason_codes": ["multi_source_bundle"],
            "mode_selection_reason": "boundary sample과 runtime source를 함께 보는 source bundle이다.",
            "mode_selection_reason_info_class": "mixed",
            "evidence_roles": [
                {
                    "evidence_ref": "E004",
                    "evidence_role": "supporting_context",
                    "role_reason": "available_evidence_sources 안에 있는 sample 근거다.",
                    "role_reason_info_class": "mixed",
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_231",
        actor="test",
        event_type="node_output",
        output_ref=["source:runtime", "source:boundary", "source:handoff"],
        schema_status="passed",
    )
    for data_id in ("source:runtime", "source:boundary", "source:handoff"):
        data_store.create_record(
            data_id=data_id,
            data_type="test:source",
            source_trace_id=event.event_id,
            payload={"data_id": data_id},
        )
    return trace_store, data_store, event.event_id
