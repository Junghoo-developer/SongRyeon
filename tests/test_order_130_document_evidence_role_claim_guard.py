from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import Node0DocumentMaterialItem, Node3InputBriefFrame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.nodes.node_2_handoff import node3_brief_llm_payload
from songryeon_core.nodes.node_3_reporter import build_node3_grounding_block
from songryeon_core.nodes.node_4_gatekeeper import run_node4_gatekeeper


def test_node3_payload_exposes_document_role_boundaries() -> None:
    brief = _brief(
        [
            Node0DocumentMaterialItem(
                doc_id="04_Orders/ORDER_122.md",
                document_name="ORDER_122.md",
                source_roles=["supplied_document_context"],
                was_supplied_document_context=True,
                supplied_context_rank=1,
            )
        ]
    )

    payload = node3_brief_llm_payload(brief)
    boundaries = payload["document_evidence_role_boundaries"]

    assert boundaries["supplied_context_document_names"] == ["ORDER_122.md"]
    assert boundaries["supplied_but_not_actual_read_doc_document_names"] == [
        "ORDER_122.md"
    ]
    assert boundaries["actual_tool_read_doc_document_names"] == []


def test_node4_blocks_read_doc_claim_for_supplied_only_document() -> None:
    trace_store, data_store, trace_id = _stores()
    brief = _brief(
        [
            Node0DocumentMaterialItem(
                doc_id="04_Orders/ORDER_122.md",
                document_name="ORDER_122.md",
                source_roles=["supplied_document_context"],
                was_supplied_document_context=True,
                supplied_context_rank=1,
            )
        ]
    )
    rendered_markdown = (
        build_node3_grounding_block(brief)
        + "\n\nORDER_122.md는 `read_doc`으로 읽혔고 node_3에게 전달됐다."
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_130",
        report_id="report:order_130",
        boundary_id="boundary:order_130",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=SongRyeonAllNodesFakeLLMAdapter(),
        input_ref=[trace_id],
        source_data_ids=["report:order_130", brief.frame_id, "boundary:order_130"],
    )

    gate = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate["gate_status"] == "needs_revision"
    assert "CODE_STATUS:document_evidence_role_claim_mismatch" in gate["reason"]
    assert any(
        item.startswith("read_doc_claim_without_actual_tool_read_doc:ORDER_122.md")
        for item in gate["contradictions"]
    )


def test_node4_allows_context_claim_for_supplied_only_document() -> None:
    trace_store, data_store, trace_id = _stores()
    brief = _brief(
        [
            Node0DocumentMaterialItem(
                doc_id="04_Orders/ORDER_122.md",
                document_name="ORDER_122.md",
                source_roles=["supplied_document_context"],
                was_supplied_document_context=True,
                supplied_context_rank=1,
            )
        ]
    )
    rendered_markdown = (
        build_node3_grounding_block(brief)
        + "\n\nORDER_122.md는 node_3 문서 context로 공급됐고, 실제 read_doc 문서라고는 단정하지 않는다."
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_130",
        report_id="report:order_130",
        boundary_id="boundary:order_130",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=SongRyeonAllNodesFakeLLMAdapter(),
        input_ref=[trace_id],
        source_data_ids=["report:order_130", brief.frame_id, "boundary:order_130"],
    )

    gate = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate["gate_status"] == "pass"
    assert "document_evidence_role_guard" in gate["checked_claims"]


def test_node4_allows_read_doc_claim_for_actual_read_document() -> None:
    trace_store, data_store, trace_id = _stores()
    brief = _brief(
        [
            Node0DocumentMaterialItem(
                doc_id="04_Orders/ORDER_122.md",
                document_name="ORDER_122.md",
                source_roles=["actual_tool_read_doc", "supplied_document_context"],
                was_actual_tool_read_doc=True,
                was_supplied_document_context=True,
                actual_read_rank=1,
                supplied_context_rank=1,
            )
        ],
        actual_tool_read_doc_count=1,
        actual_tool_read_doc_documents=["ORDER_122.md"],
    )
    rendered_markdown = (
        build_node3_grounding_block(brief)
        + "\n\nORDER_122.md는 `read_doc`으로 읽혔고 node_3 문서 context로도 공급됐다."
    )

    run_node4_gatekeeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_130",
        report_id="report:order_130",
        boundary_id="boundary:order_130",
        brief_frame=brief,
        rendered_markdown=rendered_markdown,
        adapter=SongRyeonAllNodesFakeLLMAdapter(),
        input_ref=[trace_id],
        source_data_ids=["report:order_130", brief.frame_id, "boundary:order_130"],
    )

    gate = data_store.require_record("node_4:gatekeeper_frame").payload
    assert gate["gate_status"] == "pass"


def _brief(
    document_material_items: list[Node0DocumentMaterialItem],
    *,
    actual_tool_read_doc_count: int = 0,
    actual_tool_read_doc_documents: list[str] | None = None,
) -> Node3InputBriefFrame:
    supplied_count = sum(
        1 for item in document_material_items if item.was_supplied_document_context
    )
    return Node3InputBriefFrame(
        frame_id="node_3:input_brief_frame",
        turn_id="turn_order_130",
        user_question="문서 역할을 구분해줘",
        brief_status="ready",
        handoff_frame_id="node_2:handoff_frame",
        actual_tool_read_doc_count=actual_tool_read_doc_count,
        actual_tool_read_doc_documents=actual_tool_read_doc_documents or [],
        supplied_document_context_count=supplied_count,
        document_material_packet_frame_id="node_0:document_material_packet_frame",
        document_material_items=document_material_items,
        source_trace_ids=["trace_order_130"],
        source_data_ids=[
            "node_2:handoff_frame",
            "node_0:document_material_packet_frame",
        ],
    )


def _stores() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    event = trace_store.create_event(
        turn_id="turn_order_130",
        actor="test",
        event_type="node_output",
        output_ref=["seed"],
        schema_status="passed",
    )
    return trace_store, data_store, event.event_id
