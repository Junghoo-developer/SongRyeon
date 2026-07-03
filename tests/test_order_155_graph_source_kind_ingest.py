from __future__ import annotations

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_integrity import audit_graph_memory_integrity
from songryeon_core.core.graph_source_ingest import (
    GRAPH_SOURCE_FILE_DATA_TYPE,
    GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE,
    GRAPH_SOURCE_KIND_INGEST_GENERATOR,
    record_graph_source_kind_ingest,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore


FIXED_OBSERVED_AT = "2026-07-01T12:00:00"
FIXED_INGESTED_AT = "2026-07-01T12:00:01"


def test_source_kind_ingest_creates_separate_bundles(tmp_path) -> None:
    internal_doc = tmp_path / "ORDER_155_NOTE.md"
    source_code = tmp_path / "module.py"
    external_file = tmp_path / "external.md"
    internal_doc.write_text("# internal\n문서 좌표\n", encoding="utf-8")
    source_code.write_text("def run():\n    return 1\n", encoding="utf-8")
    external_file.write_text("external project note\n", encoding="utf-8")

    trace_store = TraceStore()
    data_store = _data_store_with_core_time_axis(trace_store)

    result = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_155",
        batch_id="batch_order_155",
        source_paths_by_kind={
            "internal_document": [internal_doc],
            "source_code_file": [source_code],
            "external_project_file": [external_file],
        },
        observed_at=FIXED_OBSERVED_AT,
        ingested_at=FIXED_INGESTED_AT,
    )

    assert result.source_kind_counts == {
        "external_project_file": 1,
        "internal_document": 1,
        "source_code_file": 1,
    }
    assert len(result.source_kind_bundle_node_ids) == 3
    assert len(result.raw_source_node_ids) == 3
    assert len(result.graph_edge_ids) == 7

    bundle_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:source_kind_bundle"
    ]
    assert len(bundle_records) == 3
    for record in bundle_records:
        payload = record.payload
        assert isinstance(payload, dict)
        source_kind = payload["source_bundle_kind"]
        assert payload["node_kind"] == "source_kind_bundle"
        assert payload["data_kind"] == f"{source_kind}_bundle"
        assert payload["source_leaf_count"] == 1
        assert payload["generated_by"] == "CODE:GRAPH_MEMORY_BUILDER"
        assert payload["info_class"] == "absolute"
        assert payload["semantic_judgement_status"] == "not_run"

        child_id = payload["source_graph_node_ids"][0]
        child_record = data_store.require_record(child_id)
        child_payload = child_record.payload
        assert isinstance(child_payload, dict)
        assert child_payload["node_kind"] == "raw_source"
        assert child_payload["data_kind"] == source_kind

    frame = data_store.require_record(result.frame_id)
    assert frame.data_type == GRAPH_SOURCE_INGEST_FRAME_DATA_TYPE
    assert frame.payload["generated_by"] == GRAPH_SOURCE_KIND_INGEST_GENERATOR
    assert frame.payload["info_class"] == "absolute"
    assert frame.payload["semantic_judgement_status"] == "not_run"

    report = audit_graph_memory_integrity(data_store)
    assert report.passed, report.to_summary()


def test_raw_source_records_absolute_file_coordinates_only(tmp_path) -> None:
    source = tmp_path / "policy.md"
    source.write_text("절대 좌표만 저장한다.\n", encoding="utf-8")

    data_store = _data_store_with_core_time_axis()
    result = record_graph_source_kind_ingest(
        trace_store=TraceStore(),
        data_store=data_store,
        turn_id="turn_order_155",
        batch_id="batch_order_155_single",
        source_paths_by_kind={"internal_document": [source]},
        observed_at=FIXED_OBSERVED_AT,
        ingested_at=FIXED_INGESTED_AT,
    )

    raw_record = data_store.require_record(result.raw_source_node_ids[0])
    raw_payload = raw_record.payload
    assert isinstance(raw_payload, dict)
    assert raw_payload["node_kind"] == "raw_source"
    assert raw_payload["data_kind"] == "internal_document"
    assert raw_payload["source_leaf_count"] == 1
    assert raw_payload["source_summary_count"] == 0
    assert raw_payload["semantic_judgement_status"] == "not_run"

    file_record = data_store.require_record(result.source_file_data_ids[0])
    file_payload = file_record.payload
    assert file_record.data_type == GRAPH_SOURCE_FILE_DATA_TYPE
    assert isinstance(file_payload, dict)
    assert file_payload["source_kind"] == "internal_document"
    assert file_payload["path"].endswith("policy.md")
    assert file_payload["path_name"] == "policy.md"
    assert file_payload["suffix"] == ".md"
    assert file_payload["exists"] is True
    assert file_payload["exists_at_ingest"] is True
    assert file_payload["char_count"] == len("절대 좌표만 저장한다.\n")
    assert file_payload["observed_at"] == FIXED_OBSERVED_AT
    assert file_payload["ingested_at"] == FIXED_INGESTED_AT
    assert file_payload["source_last_modified_at"]
    assert file_payload["content_sha1"]
    assert file_payload["generated_by"] == GRAPH_SOURCE_KIND_INGEST_GENERATOR

    for forbidden_field in (
        "summary",
        "semantic_topic",
        "importance_score",
        "importance_reason",
        "relevance_reason",
        "meaning_cluster",
    ):
        assert forbidden_field not in raw_payload
        assert forbidden_field not in file_payload


def test_same_file_in_two_source_kinds_is_not_merged(tmp_path) -> None:
    source = tmp_path / "shared.txt"
    source.write_text("same bytes, different source kind\n", encoding="utf-8")

    data_store = _data_store_with_core_time_axis()
    result = record_graph_source_kind_ingest(
        trace_store=TraceStore(),
        data_store=data_store,
        turn_id="turn_order_155",
        batch_id="batch_order_155_shared",
        source_paths_by_kind={
            "internal_document": [source],
            "external_project_file": [source],
        },
        observed_at=FIXED_OBSERVED_AT,
        ingested_at=FIXED_INGESTED_AT,
    )

    assert len(result.source_file_data_ids) == 2
    assert len(set(result.source_file_data_ids)) == 2
    assert len(result.raw_source_node_ids) == 2
    assert len(set(result.raw_source_node_ids)) == 2

    raw_kinds = {
        data_store.require_record(node_id).payload["data_kind"]
        for node_id in result.raw_source_node_ids
    }
    assert raw_kinds == {"internal_document", "external_project_file"}


def test_duplicate_paths_within_one_kind_are_deduped(tmp_path) -> None:
    source = tmp_path / "duplicate.md"
    source.write_text("dedupe me\n", encoding="utf-8")

    result = record_graph_source_kind_ingest(
        trace_store=TraceStore(),
        data_store=_data_store_with_core_time_axis(),
        turn_id="turn_order_155",
        batch_id="batch_order_155_dedupe",
        source_paths_by_kind={"internal_document": [source, source]},
        observed_at=FIXED_OBSERVED_AT,
        ingested_at=FIXED_INGESTED_AT,
    )

    assert result.source_kind_counts == {"internal_document": 1}
    assert len(result.source_file_data_ids) == 1
    assert len(result.raw_source_node_ids) == 1
    assert len(result.source_kind_bundle_node_ids) == 1
    assert len(result.graph_edge_ids) == 3


def test_unknown_source_kind_is_rejected(tmp_path) -> None:
    source = tmp_path / "bad.txt"
    source.write_text("bad kind\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown graph source kind"):
        record_graph_source_kind_ingest(
            trace_store=TraceStore(),
            data_store=DataStore(),
            turn_id="turn_order_155",
            batch_id="batch_order_155_bad_kind",
            source_paths_by_kind={"semantic_topic": [source]},
        )


def test_recording_same_batch_twice_is_idempotent(tmp_path) -> None:
    source = tmp_path / "stable.md"
    source.write_text("stable content\n", encoding="utf-8")
    trace_store = TraceStore()
    data_store = _data_store_with_core_time_axis(trace_store)

    first = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_155",
        batch_id="batch_order_155_idempotent",
        source_paths_by_kind={"internal_document": [source]},
        observed_at=FIXED_OBSERVED_AT,
        ingested_at=FIXED_INGESTED_AT,
    )
    second = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_155",
        batch_id="batch_order_155_idempotent",
        source_paths_by_kind={"internal_document": [source]},
        observed_at=FIXED_OBSERVED_AT,
        ingested_at=FIXED_INGESTED_AT,
    )

    assert first.created_data_ids
    assert not second.created_data_ids
    assert set(second.existing_data_ids) == set(first.created_data_ids)


def _data_store_with_core_time_axis(trace_store: TraceStore | None = None) -> DataStore:
    trace_store = trace_store or TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_155_core",
        batch_id="batch_order_155_core",
        capsules=[_sample_capsule()],
    )
    return data_store


def _sample_capsule(turn_id: str = "turn_order_155_previous") -> TurnStateCapsule:
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
