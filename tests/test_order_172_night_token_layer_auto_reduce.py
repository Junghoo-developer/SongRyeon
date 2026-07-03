from __future__ import annotations

import json
import subprocess
import sys

from songryeon_core.core.data_store import DataStore
from songryeon_core.runtime.night_changed_source_summary import (
    run_night_changed_source_summary,
)
from songryeon_core.runtime.night_token_budget_layer_summary import (
    run_night_token_budget_layer_summary,
)


def test_auto_reduce_runs_multiple_layers_until_context_budget(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_172_sources",
        turn_id="turn_order_172_sources",
        llm_mode="fake",
    )

    result = run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_172_layer",
        turn_id="turn_order_172_layer",
        max_bundle_chars=200,
        llm_mode="fake",
        until_context_budget=True,
        target_context_chars=80,
        max_layer_depth=5,
        max_steps=10,
    )

    assert result["status"] == "NIGHT_TOKEN_BUDGET_AUTO_REDUCE_OK"
    assert result["execution_mode"] == "auto_reduce_until_context_budget"
    assert result["auto_reduce_status"] == "target_context_reached"
    assert result["step_count"] >= 2
    assert result["final_layer_depth"] >= 2
    assert result["final_summary_char_count"] <= 80
    assert any(step.get("target_layer_depth") == 3 for step in result["steps"])

    data_store = DataStore.load_json(store_dir / "data_store.json")
    token_summary_depths = sorted(
        {
            record.payload.get("summary_depth")
            for record in data_store.list_records()
            if record.data_type == "graph_memory:node:summary"
            and isinstance(record.payload, dict)
            and record.payload.get("data_kind") == "token_budget_bundle_summary"
        }
    )
    assert max(token_summary_depths) >= 3


def test_auto_reduce_stops_at_max_steps_without_unbounded_run(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_172_max_steps_sources",
        turn_id="turn_order_172_max_steps_sources",
        llm_mode="fake",
    )

    result = run_night_token_budget_layer_summary(
        store_dir=store_dir,
        batch_id="batch_order_172_max_steps_layer",
        turn_id="turn_order_172_max_steps_layer",
        max_bundle_chars=90,
        llm_mode="fake",
        until_context_budget=True,
        target_context_chars=1,
        max_layer_depth=5,
        max_steps=1,
    )

    assert result["auto_reduce_status"] == "max_steps_reached"
    assert result["step_count"] == 1
    assert result["steps"][0]["processed_this_step"] == 1


def test_auto_reduce_main_cli_runs_with_fake_mode(tmp_path) -> None:
    root = _minimal_songryeon_root(tmp_path / "project")
    store_dir = tmp_path / "store"
    run_night_changed_source_summary(
        root_path=root,
        store_dir=store_dir,
        batch_id="batch_order_172_cli_sources",
        turn_id="turn_order_172_cli_sources",
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
            "batch_order_172_cli_layer",
            "--turn-id",
            "turn_order_172_cli_layer",
            "--max-bundle-chars",
            "200",
            "--llm-mode",
            "fake",
            "--until-context-budget",
            "--target-context-chars",
            "80",
            "--max-layer-depth",
            "5",
            "--max-steps",
            "10",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "NIGHT_TOKEN_BUDGET_AUTO_REDUCE_OK"
    assert payload["auto_reduce_status"] == "target_context_reached"
    assert payload["final_summary_char_count"] <= 80


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
