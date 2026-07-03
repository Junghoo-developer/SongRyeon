from __future__ import annotations

import json
import subprocess
import sys

import pytest

from songryeon_core.runtime.night_changed_source_summary import (
    run_night_changed_source_summary,
)
from songryeon_core.runtime.night_token_budget_layer_summary import (
    run_night_token_budget_layer_summary,
)


def test_checkpointed_runner_writes_progress_jsonl(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    progress_path = tmp_path / "progress" / "night-progress.jsonl"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_173_sources",
        turn_id="turn_order_173_sources",
        llm_mode="fake",
    )

    result = run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_173_layer",
        turn_id="turn_order_173_layer",
        max_bundle_chars=90,
        llm_mode="fake",
        until_context_budget=True,
        target_context_chars=1,
        max_layer_depth=5,
        max_steps=2,
        progress_jsonl=progress_path,
        vessel_write_mode="none",
    )

    assert result["status"] == "NIGHT_TOKEN_BUDGET_AUTO_REDUCE_OK"
    assert result["auto_reduce_status"] == "max_steps_reached"
    assert result["step_count"] == 2
    assert result["progress_jsonl_path"] == progress_path.resolve().as_posix()
    assert result["vessel_write_mode"] == "none"
    assert progress_path.exists()

    events = [
        json.loads(line)
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(events) == 2
    assert {event["event_type"] for event in events} == {"auto_reduce_step"}
    assert [event["step_index"] for event in events] == [1, 2]
    assert all(event["processed_this_step"] == 1 for event in events)


def test_checkpointed_runner_rejects_unknown_vessel_write_mode(tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown vessel_write_mode"):
        run_night_token_budget_layer_summary(
            store_dir=tmp_path / "store",
            llm_mode="fake",
            until_context_budget=True,
            vessel_write_mode="sometimes",
        )


def test_checkpointed_runner_main_cli_accepts_new_options(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    progress_path = tmp_path / "cli-progress.jsonl"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_173_cli_sources",
        turn_id="turn_order_173_cli_sources",
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
            "batch_order_173_cli_layer",
            "--turn-id",
            "turn_order_173_cli_layer",
            "--max-bundle-chars",
            "90",
            "--llm-mode",
            "fake",
            "--until-context-budget",
            "--target-context-chars",
            "1",
            "--max-layer-depth",
            "5",
            "--max-steps",
            "1",
            "--max-runtime-minutes",
            "10",
            "--progress-jsonl",
            str(progress_path),
            "--vessel-write-mode",
            "none",
            "--no-stop-on-failure",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "NIGHT_TOKEN_BUDGET_AUTO_REDUCE_OK"
    assert payload["auto_reduce_status"] == "max_steps_reached"
    assert payload["step_count"] == 1
    assert payload["max_runtime_minutes"] == 10.0
    assert payload["stop_on_failure"] is False
    assert payload["vessel_write_mode"] == "none"
    assert progress_path.exists()


def _minimal_songryeon_root(root) -> object:
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "README.md").write_text("# Readme\n", encoding="utf-8")
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    docs = root / "Administrative_Reform_1" / "04_Orders"
    docs.mkdir(parents=True)
    for index in range(1, 9):
        (docs / f"ORDER_TEST_{index:03d}.md").write_text(
            f"# Test order {index}\n",
            encoding="utf-8",
        )
    return root
