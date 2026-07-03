from __future__ import annotations

import json
import subprocess
import sys

from songryeon_core.core.data_store import DataStore
from songryeon_core.runtime.night_changed_source_summary import (
    NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_DATA_TYPE,
    run_night_changed_source_summary,
)


def test_one_at_a_time_processes_one_leaf_per_run_and_resumes_queue(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"

    first = run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_170_one",
        turn_id="turn_order_170_one_001",
        llm_mode="fake",
        one_at_a_time=True,
    )
    second = run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_170_one",
        turn_id="turn_order_170_one_002",
        llm_mode="fake",
        one_at_a_time=True,
    )

    assert first["execution_mode"] == "one_at_a_time"
    assert first["one_at_a_time_queue_status"] == "created"
    assert first["selected_source_leaf_count"] == 4
    assert first["summary_success_count"] == 1
    assert first["one_at_a_time_processed_this_run"] == 1
    assert first["one_at_a_time_queue_processed_count_after"] == 1
    assert first["one_at_a_time_queue_pending_count_after"] == 3

    assert second["one_at_a_time_queue_status"] == "existing"
    assert second["source_observation_status_counts"] == {"new_source_version": 4}
    assert second["summary_success_count"] == 1
    assert second["one_at_a_time_queue_processed_count_before"] == 1
    assert second["one_at_a_time_queue_processed_count_after"] == 2
    assert second["one_at_a_time_queue_pending_count_after"] == 2

    data_store = DataStore.load_json(store_dir / "data_store.json")
    summary_records = [
        record
        for record in data_store.list_records()
        if record.data_type == "graph_memory:node:summary"
    ]
    queue_records = [
        record
        for record in data_store.list_records()
        if record.data_type == NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_QUEUE_DATA_TYPE
    ]
    assert len(summary_records) == 2
    assert len(queue_records) == 1


def test_one_at_a_time_reports_complete_after_queue_is_exhausted(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"

    results = [
        run_night_changed_source_summary(
            root_path=root,
            store_dir=store_dir,
            batch_id="batch_order_170_complete",
            turn_id=f"turn_order_170_complete_{index:03d}",
            llm_mode="fake",
            one_at_a_time=True,
        )
        for index in range(1, 6)
    ]

    assert [result["one_at_a_time_processed_this_run"] for result in results] == [
        1,
        1,
        1,
        1,
        0,
    ]
    assert results[-1]["one_at_a_time_completion_status"] == "complete"
    assert results[-1]["one_at_a_time_queue_processed_count_after"] == 4
    assert results[-1]["one_at_a_time_queue_pending_count_after"] == 0
    assert results[-1]["summary_success_count"] == 0


def test_one_at_a_time_main_cli_runs_single_step_with_fake_mode(tmp_path) -> None:
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
            "batch_order_170_cli",
            "--turn-id",
            "turn_order_170_cli",
            "--llm-mode",
            "fake",
            "--one-at-a-time",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "NIGHT_CHANGED_SOURCE_SUMMARY_OK"
    assert payload["execution_mode"] == "one_at_a_time"
    assert payload["summary_success_count"] == 1
    assert payload["one_at_a_time_processed_this_run"] == 1
    assert payload["one_at_a_time_queue_pending_count_after"] == 3


def _minimal_songryeon_root(root) -> object:
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "README.md").write_text("# Readme\n", encoding="utf-8")
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs = root / "Administrative_Reform_1" / "04_Orders"
    docs.mkdir(parents=True)
    (docs / "ORDER_TEST.md").write_text("# Test order\n", encoding="utf-8")
    return root
