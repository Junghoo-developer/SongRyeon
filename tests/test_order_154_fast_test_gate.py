from __future__ import annotations

import pytest

from songryeon_core.runtime.fast_test import build_fast_test_steps, run_fast_tests


def test_fast_test_core_profile_is_small() -> None:
    steps = build_fast_test_steps(profile="core")

    assert [step.name for step in steps] == ["compileall", "pytest:core"]
    pytest_command = steps[-1].command
    assert "tests/test_import_baseline.py" in pytest_command
    assert "tests/test_schema_split_compat.py" in pytest_command
    assert "tests/test_order_153_graph_memory_integrity.py" not in pytest_command


def test_fast_test_graph_profile_includes_current_graph_boundary_tests() -> None:
    steps = build_fast_test_steps(profile="graph", skip_compileall=True)

    assert [step.name for step in steps] == ["pytest:graph"]
    pytest_command = steps[0].command
    assert "tests/test_order_146_r_route_experimental_gate.py" in pytest_command
    assert "tests/test_order_147_r_result_to_node3_brief.py" in pytest_command
    assert "tests/test_order_152_raw_capsule_activity_graph_link.py" in pytest_command
    assert "tests/test_order_153_graph_memory_integrity.py" in pytest_command
    assert "tests/test_order_155_graph_source_kind_ingest.py" in pytest_command
    assert "tests/test_order_156_graph_source_observation_time_and_core_link.py" in pytest_command
    assert "tests/test_order_157_songryeon_core_source_manifest.py" in pytest_command
    assert "tests/test_order_158_graph_memory_export_packet.py" in pytest_command
    assert "tests/test_order_159_vessel_adapter_boundary.py" in pytest_command


def test_fast_test_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError, match="unknown fast-test profile"):
        build_fast_test_steps(profile="unknown")


def test_fast_test_dry_run_does_not_execute_steps() -> None:
    result = run_fast_tests(profile="core", dry_run=True)

    assert result["status"] == "FAST_TEST_PLAN"
    assert result["profile"] == "core"
    assert result["step_count"] == 2
    assert result["steps"][0]["name"] == "compileall"
