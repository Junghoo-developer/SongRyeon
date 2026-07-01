from __future__ import annotations

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_integrity import audit_graph_memory_integrity
from songryeon_core.core.graph_source_ingest import GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.songryeon_source_manifest import (
    SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE,
    SONGRYEON_CORE_SOURCE_MANIFEST_GENERATOR,
    record_songryeon_core_source_manifest_ingest,
    resolve_songryeon_core_source_manifest,
)
from songryeon_core.core.trace_store import TraceStore


OBSERVED_AT = "2026-07-01T16:00:00"
INGESTED_AT = "2026-07-01T16:00:01"


def test_manifest_resolves_internal_docs_source_code_and_tests(tmp_path) -> None:
    root = _sample_repo(tmp_path)

    manifest = resolve_songryeon_core_source_manifest(
        root_path=root,
        batch_id="batch_order_157",
    )

    assert manifest.generated_by == SONGRYEON_CORE_SOURCE_MANIFEST_GENERATOR
    assert manifest.info_class == "absolute"
    assert manifest.semantic_judgement_status == "not_run"
    assert manifest.source_kind_counts == {
        "internal_document": 4,
        "source_code_file": 3,
    }
    internal_names = {path.split("/")[-1] for path in manifest.source_paths_by_kind["internal_document"]}
    code_names = {path.split("/")[-1] for path in manifest.source_paths_by_kind["source_code_file"]}
    assert {"AGENTS.md", "README.md", "ORDER_001.md", "note.md"}.issubset(internal_names)
    assert {"main.py", "module.py", "test_module.py"}.issubset(code_names)
    assert "external_project_file" not in manifest.source_paths_by_kind


def test_manifest_ingest_stores_text_snapshots_and_core_link(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store = _core_time_axis_store()

    result = record_songryeon_core_source_manifest_ingest(
        trace_store=trace_store,
        data_store=data_store,
        root_path=root,
        turn_id="turn_order_157",
        batch_id="batch_order_157",
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )

    manifest_record = data_store.require_record(result.manifest_data_id)
    assert manifest_record.data_type == SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE
    assert manifest_record.payload["source_kind_counts"] == {
        "internal_document": 4,
        "source_code_file": 3,
    }

    ingest = result.ingest_result
    assert ingest.source_kind_counts == {
        "internal_document": 4,
        "source_code_file": 3,
    }
    assert len(ingest.source_text_snapshot_data_ids) == 7
    assert ingest.source_ingest_time_bundle_node_id
    assert ingest.graph_snapshot_id
    assert ingest.rloop_graph_guide_packet_id

    text_records = [
        data_store.require_record(data_id)
        for data_id in ingest.source_text_snapshot_data_ids
    ]
    assert {record.data_type for record in text_records} == {GRAPH_SOURCE_TEXT_SNAPSHOT_DATA_TYPE}
    payloads = [record.payload for record in text_records]
    assert all(payload["info_class"] == "absolute_copied_source" for payload in payloads)
    assert all(payload["semantic_judgement_status"] == "not_run" for payload in payloads)
    assert all(payload["observed_at"] == OBSERVED_AT for payload in payloads)
    assert any(payload["text"] == "# agent rules\n" for payload in payloads)
    assert any(payload["text"] == "def run():\n    return 1\n" for payload in payloads)

    frame = data_store.require_record(ingest.frame_id)
    assert frame.payload["text_snapshot_status"] == "stored"
    assert set(frame.payload["source_text_snapshot_data_ids"]) == set(
        ingest.source_text_snapshot_data_ids
    )

    report = audit_graph_memory_integrity(data_store)
    assert report.passed, report.to_summary()


def test_manifest_missing_explicit_path_fails(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# readme\n", encoding="utf-8")
    (root / "main.py").write_text("print('main')\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="AGENTS.md"):
        resolve_songryeon_core_source_manifest(
            root_path=root,
            batch_id="batch_order_157_missing",
        )


def test_manifest_glob_absence_is_not_missing_explicit_failure(tmp_path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "AGENTS.md").write_text("# agent rules\n", encoding="utf-8")
    (root / "README.md").write_text("# readme\n", encoding="utf-8")
    (root / "main.py").write_text("print('main')\n", encoding="utf-8")

    manifest = resolve_songryeon_core_source_manifest(
        root_path=root,
        batch_id="batch_order_157_no_globs",
    )

    assert manifest.source_kind_counts == {
        "internal_document": 2,
        "source_code_file": 1,
    }


def test_manifest_ingest_does_not_create_semantic_fields(tmp_path) -> None:
    root = _sample_repo(tmp_path)
    trace_store, data_store = _core_time_axis_store()

    result = record_songryeon_core_source_manifest_ingest(
        trace_store=trace_store,
        data_store=data_store,
        root_path=root,
        turn_id="turn_order_157",
        batch_id="batch_order_157_boundary",
        observed_at=OBSERVED_AT,
        ingested_at=INGESTED_AT,
    )

    checked_payloads = [
        data_store.require_record(data_id).payload
        for data_id in [
            result.manifest_data_id,
            result.ingest_result.frame_id,
            *result.ingest_result.raw_source_node_ids,
            *result.ingest_result.source_text_snapshot_data_ids,
        ]
    ]
    for payload in checked_payloads:
        for forbidden_field in (
            "summary",
            "semantic_topic",
            "importance_score",
            "importance_reason",
            "relevance_reason",
            "meaning_cluster",
        ):
            assert forbidden_field not in payload


def _sample_repo(tmp_path):
    root = tmp_path / "repo"
    (root / "Administrative_Reform_1" / "04_Orders").mkdir(parents=True)
    (root / "Administrative_Reform_1" / "05_Execution_Records").mkdir(parents=True)
    (root / "songryeon_core").mkdir()
    (root / "tests").mkdir()

    (root / "AGENTS.md").write_text("# agent rules\n", encoding="utf-8")
    (root / "README.md").write_text("# readme\n", encoding="utf-8")
    (root / "Administrative_Reform_1" / "04_Orders" / "ORDER_001.md").write_text(
        "# order\n",
        encoding="utf-8",
    )
    (root / "Administrative_Reform_1" / "05_Execution_Records" / "note.md").write_text(
        "# note\n",
        encoding="utf-8",
    )
    (root / "main.py").write_text("print('main')\n", encoding="utf-8")
    (root / "songryeon_core" / "module.py").write_text(
        "def run():\n    return 1\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_module.py").write_text(
        "def test_run():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "external.md").write_text("# external\n", encoding="utf-8")
    return root


def _core_time_axis_store() -> tuple[TraceStore, DataStore]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_157_core",
        batch_id="batch_order_157_core",
        capsules=[_sample_capsule()],
    )
    return trace_store, data_store


def _sample_capsule(turn_id: str = "turn_order_157_previous") -> TurnStateCapsule:
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
