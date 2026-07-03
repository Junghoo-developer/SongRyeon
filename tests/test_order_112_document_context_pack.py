from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary, validate_document_context_pack_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools.document_context_pack import (
    DOCUMENT_CONTEXT_PACK_DATA_TYPE,
    EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE,
    build_document_context_pack_frame,
    build_explicit_artifact_reference_frame,
    extract_explicit_artifact_references,
)


def test_explicit_order_references_are_extracted_from_user_input() -> None:
    text = (
        "ORDER_100, ORDER_105_MEMORY_SELECTION_TO_NODE2_HANDOFF_V0, "
        "04_Orders/ORDER_105_MEMORY_SELECTION_TO_NODE2_HANDOFF_V0.md"
    )

    assert extract_explicit_artifact_references(text) == [
        "ORDER_100",
        "ORDER_105_MEMORY_SELECTION_TO_NODE2_HANDOFF_V0",
        "04_Orders/ORDER_105_MEMORY_SELECTION_TO_NODE2_HANDOFF_V0.md",
    ]


def test_unique_explicit_order_is_ranked_before_embedding_candidate() -> None:
    frame = build_explicit_artifact_reference_frame(
        turn_id="turn_test",
        user_text="ORDER_100을 직접 읽어줘",
        document_root="Administrative_Reform_1",
        frame_id="explicit:test",
        source_trace_ids=["trace_user"],
        source_data_ids=["data_user"],
    )
    assert frame.resolved_references[0].resolve_status == "unique"
    assert frame.resolved_references[0].selected_doc_id == (
        "04_Orders/ORDER_100_RECENT_TURN_CAPSULE_READ_WINDOW_PACKET_V0.md"
    )

    data_store = DataStore()
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE,
        payload=asdict(frame),
    )
    data_store.create_record(
        data_id="L3:preserved_info_frame",
        data_type="node_output:L3_preserved_info_frame",
        payload={
            "frame_id": "L3:preserved_info_frame",
            "candidates": [
                {
                    "doc_id": "README.md",
                    "source_data_id": "tool_result:search_docs:test",
                }
            ],
        },
    )

    pack = build_document_context_pack_frame(
        data_store=data_store,
        turn_id="turn_test",
        document_root="Administrative_Reform_1",
        max_document_context_chars=100000,
        frame_id="pack:test",
        explicit_reference_data_id=frame.frame_id,
        source_trace_ids=["trace_pack"],
        source_data_ids=[frame.frame_id],
        id_namespace=None,
    )

    assert pack.included_documents[0].doc_id == (
        "04_Orders/ORDER_100_RECENT_TURN_CAPSULE_READ_WINDOW_PACKET_V0.md"
    )
    assert pack.included_documents[0].selection_basis.startswith(
        "explicit_artifact_reference_unique"
    )
    assert pack.included_documents[1].doc_id == "README.md"


def test_ambiguous_explicit_order_reference_is_not_selected(tmp_path) -> None:
    root = tmp_path / "docs"
    orders = root / "04_Orders"
    orders.mkdir(parents=True)
    (orders / "ORDER_100_ALPHA.md").write_text("alpha", encoding="utf-8")
    (orders / "ORDER_100_BETA.md").write_text("beta", encoding="utf-8")

    frame = build_explicit_artifact_reference_frame(
        turn_id="turn_test",
        user_text="ORDER_100을 찾아줘",
        document_root=root,
        frame_id="explicit:test",
        source_trace_ids=["trace_user"],
        source_data_ids=["data_user"],
    )

    assert frame.resolved_references[0].resolve_status == "ambiguous"
    assert frame.resolved_references[0].selected_doc_id is None
    assert frame.resolved_references[0].candidate_count == 2


def test_whole_document_pack_excludes_without_mid_document_cut(tmp_path) -> None:
    root = tmp_path / "docs"
    orders = root / "04_Orders"
    orders.mkdir(parents=True)
    (orders / "ORDER_100_ALPHA.md").write_text("11111", encoding="utf-8")
    (orders / "ORDER_101_BETA.md").write_text("2222222", encoding="utf-8")
    (orders / "ORDER_104_GAMMA.md").write_text("3333", encoding="utf-8")

    data_store = DataStore()
    data_store.create_record(
        data_id="explicit:test",
        data_type=EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE,
        payload={
            "resolved_references": [],
        },
    )
    data_store.create_record(
        data_id="L3:preserved_info_frame",
        data_type="node_output:L3_preserved_info_frame",
        payload={
            "candidates": [
                {"doc_id": "04_Orders/ORDER_100_ALPHA.md", "source_data_id": "search:1"},
                {"doc_id": "04_Orders/ORDER_101_BETA.md", "source_data_id": "search:1"},
                {"doc_id": "04_Orders/ORDER_104_GAMMA.md", "source_data_id": "search:1"},
            ],
        },
    )

    pack = build_document_context_pack_frame(
        data_store=data_store,
        turn_id="turn_test",
        document_root=root,
        max_document_context_chars=10,
        frame_id="pack:test",
        explicit_reference_data_id="explicit:test",
        source_trace_ids=["trace_pack"],
        source_data_ids=["explicit:test"],
        id_namespace=None,
    )
    validate_document_context_pack_frame(pack)

    assert [item.doc_id for item in pack.included_documents] == [
        "04_Orders/ORDER_100_ALPHA.md"
    ]
    assert pack.included_documents[0].text == "11111"
    assert pack.excluded_documents[0].doc_id == "04_Orders/ORDER_101_BETA.md"
    assert pack.excluded_documents[0].exclusion_reason == "excluded_due_to_context_budget"
    assert pack.excluded_documents[1].doc_id == "04_Orders/ORDER_104_GAMMA.md"
    assert pack.excluded_documents[1].exclusion_reason == "excluded_after_strict_rank_cutoff"


def test_node3_brief_reads_only_context_pack_included_documents(tmp_path) -> None:
    root = tmp_path / "docs"
    orders = root / "04_Orders"
    orders.mkdir(parents=True)
    (orders / "ORDER_100_ALPHA.md").write_text("11111", encoding="utf-8")
    (orders / "ORDER_101_BETA.md").write_text("2222222", encoding="utf-8")

    data_store = DataStore()
    data_store.create_record(
        data_id="explicit:test",
        data_type=EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE,
        payload={"resolved_references": []},
    )
    data_store.create_record(
        data_id="L3:preserved_info_frame",
        data_type="node_output:L3_preserved_info_frame",
        payload={
            "candidates": [
                {"doc_id": "04_Orders/ORDER_100_ALPHA.md", "source_data_id": "search:1"},
                {"doc_id": "04_Orders/ORDER_101_BETA.md", "source_data_id": "search:1"},
            ],
        },
    )
    pack = build_document_context_pack_frame(
        data_store=data_store,
        turn_id="turn_test",
        document_root=root,
        max_document_context_chars=5,
        frame_id="pack:test",
        explicit_reference_data_id="explicit:test",
        source_trace_ids=["trace_pack"],
        source_data_ids=["explicit:test"],
        id_namespace=None,
    )
    data_store.create_record(
        data_id=pack.frame_id,
        data_type=DOCUMENT_CONTEXT_PACK_DATA_TYPE,
        payload=asdict(pack),
    )
    trace_store = TraceStore()
    seed = trace_store.create_event(
        turn_id="turn_test",
        actor="test",
        event_type="node_output",
        output_ref=["pack:test"],
        schema_status="passed",
    )

    _, _, brief = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_test",
        user_question="ORDER_100과 ORDER_101을 읽어줘",
        handoff_frame_id="node_2:handoff_frame",
        boundary=MetainfoBoundary(),
        input_trace_ids=[seed.event_id],
        source_data_ids=["node_2:handoff_frame", "pack:test"],
    )

    assert len(brief.read_documents) == pack.included_document_count == 1
    assert brief.read_documents[0].document_name == "ORDER_100_ALPHA.md"
    assert len(brief.excluded_document_contexts) == pack.excluded_document_count == 1
    assert brief.excluded_document_contexts[0].document_name == "ORDER_101_BETA.md"


def test_terminal_view_displays_explicit_resolve_and_context_pack() -> None:
    result = {
        "status": "ok",
        "runtime": {"model_id": "test", "transport": "fake"},
        "trace_count": 0,
        "data_record_count": 2,
        "data_records": [
            {
                "data_id": "explicit:test",
                "data_type": EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE,
                "payload": {
                    "frame_id": "explicit:test",
                    "extracted_reference_count": 1,
                    "resolved_references": [
                        {
                            "raw_ref": "ORDER_100",
                            "resolve_status": "unique",
                            "selected_doc_id": "04_Orders/ORDER_100_ALPHA.md",
                        }
                    ],
                    "generated_by": "CODE:EXPLICIT_ARTIFACT_RESOLVER",
                    "info_class": "absolute_resolve_result",
                    "semantic_judgement_status": "not_run",
                    "source_data_ids": ["data_user"],
                },
            },
            {
                "data_id": "pack:test",
                "data_type": DOCUMENT_CONTEXT_PACK_DATA_TYPE,
                "payload": {
                    "frame_id": "pack:test",
                    "included_document_count": 1,
                    "excluded_document_count": 1,
                    "included_total_chars": 5,
                    "max_document_context_chars": 10,
                    "budget_unit": "chars",
                    "whole_document_only": True,
                    "strict_rank_order": True,
                    "cutoff_reason": "excluded_due_to_context_budget at ORDER_101",
                    "included_documents": [
                        {
                            "rank_index": 1,
                            "doc_id": "04_Orders/ORDER_100_ALPHA.md",
                            "char_count": 5,
                            "selection_basis": "explicit_artifact_reference_unique:ORDER_100",
                        }
                    ],
                    "excluded_documents": [
                        {
                            "rank_index": 2,
                            "doc_id": "04_Orders/ORDER_101_BETA.md",
                            "char_count": 7,
                            "exclusion_reason": "excluded_due_to_context_budget",
                        }
                    ],
                    "generated_by": "CODE:DOCUMENT_CONTEXT_PACKER",
                    "info_class": "absolute_context_packing_result",
                    "semantic_judgement_status": "not_run",
                    "source_data_ids": ["explicit:test"],
                },
            },
        ],
    }

    rendered = render_runtime_view(result, user_input="ORDER_100")

    assert "explicit_artifact_refs" in rendered
    assert "ORDER_100 -> unique" in rendered
    assert "document_context_pack" in rendered
    assert "included=1 / excluded=1 / budget=5/10 chars" in rendered
    assert "whole_document_only=true / strict_rank_order=true" in rendered
