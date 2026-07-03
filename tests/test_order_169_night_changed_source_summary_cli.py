from __future__ import annotations

import json
import subprocess
import sys

from songryeon_core.runtime.night_changed_source_summary import (
    run_night_changed_source_summary,
)


def test_night_changed_source_summary_first_run_summarizes_manifest_leaves(
    tmp_path,
) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"

    result = run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_169_first",
        turn_id="turn_order_169_first",
        llm_mode="fake",
    )

    assert result["status"] == "NIGHT_CHANGED_SOURCE_SUMMARY_OK"
    assert result["source_observation_status_counts"] == {"new_source_version": 4}
    assert result["selected_source_leaf_count"] == 4
    assert result["summary_success_count"] == 4
    assert result["summary_failed_count"] == 0
    assert len(result["summary_graph_node_ids"]) == 4
    assert result["write_plan_status"] == "ready_to_write"
    assert (store_dir / "trace_store.json").exists()
    assert (store_dir / "data_store.json").exists()


def test_night_changed_source_summary_second_run_skips_unchanged(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_169_unchanged_001",
        turn_id="turn_order_169_unchanged_001",
        llm_mode="fake",
    )

    result = run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_169_unchanged_002",
        turn_id="turn_order_169_unchanged_002",
        llm_mode="fake",
    )

    assert result["source_observation_status_counts"] == {"unchanged": 4}
    assert result["selected_source_leaf_count"] == 0
    assert result["skipped_unchanged_source_leaf_count"] == 4
    assert result["summary_success_count"] == 0
    assert result["summary_graph_node_ids"] == []


def test_night_changed_source_summary_only_summarizes_changed_file(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_169_change_001",
        turn_id="turn_order_169_change_001",
        llm_mode="fake",
    )
    (root / "main.py").write_text("VALUE = 2\n", encoding="utf-8")

    result = run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_169_change_002",
        turn_id="turn_order_169_change_002",
        llm_mode="fake",
    )

    assert result["source_observation_status_counts"] == {
        "unchanged": 3,
        "content_changed": 1,
    }
    assert result["selected_source_leaf_count"] == 1
    assert result["summary_success_count"] == 1
    assert len(result["summary_graph_node_ids"]) == 1


def test_night_changed_source_summary_main_cli_runs_with_fake_mode(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "night-summarize-changed-sources",
            "--root",
            str(root),
            "--store-dir",
            str(store_dir),
            "--batch-id",
            "batch_order_169_cli",
            "--turn-id",
            "turn_order_169_cli",
            "--llm-mode",
            "fake",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "NIGHT_CHANGED_SOURCE_SUMMARY_OK"
    assert payload["summary_success_count"] == 4
    assert payload["write_vessel_requested"] is False
    assert payload["write_result"] is None


def _minimal_songryeon_root(root) -> object:
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "README.md").write_text("# Readme\n", encoding="utf-8")
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs = root / "Administrative_Reform_1" / "04_Orders"
    docs.mkdir(parents=True)
    (docs / "ORDER_TEST.md").write_text("# Test order\n", encoding="utf-8")
    return root
