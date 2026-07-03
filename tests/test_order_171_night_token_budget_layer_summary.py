from __future__ import annotations

import json
import subprocess
import sys

from songryeon_core.core.data_store import DataStore
from songryeon_core.runtime.night_changed_source_summary import (
    run_night_changed_source_summary,
)
from songryeon_core.runtime.night_token_budget_layer_summary import (
    NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE,
    run_night_token_budget_layer_summary,
)


def test_token_budget_layer_processes_one_bundle_per_run(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_171_sources",
        turn_id="turn_order_171_sources",
        llm_mode="fake",
    )

    first = run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_171_layer",
        turn_id="turn_order_171_layer_001",
        max_bundle_chars=90,
        llm_mode="fake",
    )
    second = run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_171_layer",
        turn_id="turn_order_171_layer_002",
        max_bundle_chars=90,
        llm_mode="fake",
    )

    assert first["status"] == "NIGHT_TOKEN_BUDGET_LAYER_SUMMARY_OK"
    assert first["execution_mode"] == "one_bundle_at_a_time"
    assert first["budget_unit"] == "characters"
    assert first["source_summary_count"] == 4
    assert first["bundle_count"] >= 2
    assert first["processed_this_run"] == 1
    assert first["processed_count_after"] == 1
    assert first["pending_count_after"] == first["bundle_count"] - 1
    assert first["summary_status"] == "ran"

    assert second["queue_status"] == "existing"
    assert second["processed_this_run"] == 1
    assert second["processed_count_before"] == 1
    assert second["processed_count_after"] == 2

    data_store = DataStore.load_json(store_dir / "data_store.json")
    queue_records = [
        record
        for record in data_store.list_records()
        if record.data_type == NIGHT_TOKEN_BUDGET_LAYER_QUEUE_DATA_TYPE
    ]
    bundle_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:token_budget_summary_bundle"
    ]
    token_summary_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:summary"
        and isinstance(record.payload, dict)
        and record.payload.get("data_kind") == "token_budget_bundle_summary"
    ]
    assert len(queue_records) == 1
    assert len(bundle_records) == 2
    assert len(token_summary_records) == 2
    assert token_summary_records[0].payload["info_class"] == "mixed"
    assert token_summary_records[0].payload["semantic_judgement_status"] == "ran"


def test_token_budget_layer_reports_no_candidates_without_leaf_summaries(tmp_path) -> None:
    store_dir = tmp_path / "empty_store"

    result = run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_171_empty",
        turn_id="turn_order_171_empty",
        max_bundle_chars=90,
        llm_mode="fake",
    )

    assert result["source_summary_count"] == 0
    assert result["bundle_count"] == 0
    assert result["processed_this_run"] == 0
    assert result["completion_status"] == "no_candidates"


def test_token_budget_layer_main_cli_runs_one_step(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_171_cli_sources",
        turn_id="turn_order_171_cli_sources",
        llm_mode="fake",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "night-summarize-token-layer",
            "--store-dir",
            str(store_dir),
            "--batch-id",
            "batch_order_171_cli_layer",
            "--turn-id",
            "turn_order_171_cli_layer",
            "--max-bundle-chars",
            "90",
            "--llm-mode",
            "fake",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "NIGHT_TOKEN_BUDGET_LAYER_SUMMARY_OK"
    assert payload["processed_this_run"] == 1
    assert payload["summary_status"] == "ran"
    assert payload["summary_graph_node_id"].startswith("graph:summary:token_budget_bundle:")


def _minimal_songryeon_root(root) -> object:
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "README.md").write_text("# Readme\n", encoding="utf-8")
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs = root / "Administrative_Reform_1" / "04_Orders"
    docs.mkdir(parents=True)
    (docs / "ORDER_TEST.md").write_text("# Test order\n", encoding="utf-8")
    return root
