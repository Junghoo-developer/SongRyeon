from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


FAST_TEST_PROFILES = {"core", "graph"}


@dataclass(frozen=True)
class FastTestStep:
    name: str
    command: list[str]


def build_fast_test_steps(
    *,
    profile: str = "graph",
    skip_compileall: bool = False,
) -> list[FastTestStep]:
    if profile not in FAST_TEST_PROFILES:
        raise ValueError(f"unknown fast-test profile: {profile}")

    steps: list[FastTestStep] = []
    if not skip_compileall:
        steps.append(
            FastTestStep(
                name="compileall",
                command=[
                    sys.executable,
                    "-m",
                    "compileall",
                    "songryeon_core",
                    "main.py",
                ],
            )
        )

    pytest_files = [
        "tests/test_import_baseline.py",
        "tests/test_schema_split_compat.py",
    ]
    if profile == "graph":
        pytest_files.extend(
            [
                "tests/test_order_146_r_route_experimental_gate.py",
                "tests/test_order_147_r_result_to_node3_brief.py",
                "tests/test_order_152_raw_capsule_activity_graph_link.py",
                "tests/test_order_153_graph_memory_integrity.py",
                "tests/test_order_155_graph_source_kind_ingest.py",
                "tests/test_order_156_graph_source_observation_time_and_core_link.py",
                "tests/test_order_157_songryeon_core_source_manifest.py",
                "tests/test_order_158_graph_memory_export_packet.py",
                "tests/test_order_159_vessel_adapter_boundary.py",
                "tests/test_order_160_local_vessel_neo4j_writer.py",
                "tests/test_order_162_vessel_readback_verification.py",
                "tests/test_order_163_vessel_inspect_manual_walk.py",
                "tests/test_order_164_source_version_lineage_and_invalidation.py",
                "tests/test_order_165_same_content_observation_ledger.py",
                "tests/test_order_166_night_time_bundle_summary_node.py",
                "tests/test_order_168_night_summarize_changed_source_leaves.py",
                "tests/test_order_169_night_changed_source_summary_cli.py",
                "tests/test_order_170_night_changed_source_one_at_a_time.py",
                "tests/test_order_171_night_token_budget_layer_summary.py",
                "tests/test_order_172_night_token_layer_auto_reduce.py",
                "tests/test_order_173_night_checkpointed_long_runner.py",
                "tests/test_order_174_vessel_inspect_summary_layer_view.py",
                "tests/test_order_175_vessel_backed_r_read_packet.py",
                "tests/test_order_176_vessel_r_one_step_traversal.py",
                "tests/test_order_177_r1_candidate_text_blindness.py",
                "tests/test_order_178_r_vessel_candidate_layer_surface.py",
                "tests/test_order_179_r2_vessel_selection_id_disambiguation.py",
                "tests/test_order_180_r2_prompt_example_id_removal.py",
                "tests/test_order_181_r2_official_selection_ref_map.py",
                "tests/test_order_182_r_core_ego_start_surface.py",
                "tests/test_order_183_r_vessel_hierarchical_child_surface.py",
                "tests/test_order_184_r_vessel_multi_step_traversal.py",
                "tests/test_order_185_r_terminal_material_guard.py",
                "tests/test_order_186_r_vessel_exact_child_expansion.py",
                "tests/test_order_187_r_vessel_summary_layer_before_raw.py",
                "tests/test_order_188_r_vessel_raw_original_cap.py",
                "tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py",
                "tests/test_order_191_r2_branch_role_surface_stability.py",
                "tests/test_order_192_r1_user_question_anchor_copy.py",
            ]
        )
    steps.append(
        FastTestStep(
            name=f"pytest:{profile}",
            command=[
                sys.executable,
                "-m",
                "pytest",
                "-q",
                *pytest_files,
            ],
        )
    )
    return steps


def run_fast_tests(
    *,
    profile: str = "graph",
    skip_compileall: bool = False,
    dry_run: bool = False,
    cwd: str | Path | None = None,
) -> dict[str, object]:
    root = Path(cwd) if cwd is not None else Path.cwd()
    steps = build_fast_test_steps(
        profile=profile,
        skip_compileall=skip_compileall,
    )
    if dry_run:
        return {
            "status": "FAST_TEST_PLAN",
            "profile": profile,
            "step_count": len(steps),
            "steps": [_step_plan(step) for step in steps],
        }

    started = time.perf_counter()
    results: list[dict[str, object]] = []
    failed = False
    for step in steps:
        step_started = time.perf_counter()
        completed = subprocess.run(
            step.command,
            cwd=root,
            text=True,
            capture_output=True,
        )
        step_duration = time.perf_counter() - step_started
        if completed.returncode != 0:
            failed = True
        results.append(
            {
                "name": step.name,
                "command": step.command,
                "returncode": completed.returncode,
                "duration_seconds": round(step_duration, 3),
                "stdout_tail": _tail(completed.stdout),
                "stderr_tail": _tail(completed.stderr),
            }
        )
        if failed:
            break

    duration = time.perf_counter() - started
    return {
        "status": "FAST_TEST_FAILED" if failed else "FAST_TEST_OK",
        "profile": profile,
        "duration_seconds": round(duration, 3),
        "step_count": len(steps),
        "steps": results,
    }


def _step_plan(step: FastTestStep) -> dict[str, object]:
    return {
        "name": step.name,
        "command": step.command,
    }


def _tail(text: str, *, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


__all__ = [
    "FAST_TEST_PROFILES",
    "FastTestStep",
    "build_fast_test_steps",
    "run_fast_tests",
]
