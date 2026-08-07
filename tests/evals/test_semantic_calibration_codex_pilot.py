import json

import pytest

from evals.semantic_calibration_codex_pilot import (
    EXPECTED_DEPENDENCY_HASHES,
    EXPECTED_PLAN_IDS,
    V3_ROOT,
    acquire_attempt_lock,
    build_expected_claims,
    classify_result,
    parse_remote_head,
    select_pilot_units,
    sha256,
    split_upstream_ref,
    validate_no_api_auth,
    validate_output_budget,
    validate_passive_items,
)


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_pilot_selects_exactly_four_frozen_hard_batches_and_twelve_claims():
    plan = load_json(V3_ROOT / "control" / "run_plan.json")
    units = select_pilot_units(plan)

    assert tuple(unit["plan_id"] for unit in units) == EXPECTED_PLAN_IDS
    assert len(units) == 4
    assert all(unit["mode"] == "batch" for unit in units)
    assert all(unit["difficulty"] == "hard" for unit in units)
    assert len({claim for unit in units for claim in unit["expected_ids"]}) == 12

    expected = build_expected_claims(
        units,
        load_json(V3_ROOT / "control" / "oracle_results.json"),
    )
    assert len(expected) == 12
    assert all(set(value) == {"verdict", "observation"} for value in expected.values())


@pytest.mark.parametrize(
    ("parsed_units", "joint_correct", "expected"),
    [
        (4, 12, "harder_v4_triggered"),
        (4, 10, "harder_v4_triggered"),
        (4, 9, "screen_threshold_not_met"),
        (3, 12, "output_or_runtime_failure"),
        (0, 0, "output_or_runtime_failure"),
    ],
)
def test_classification_boundaries(parsed_units, joint_correct, expected):
    assert classify_result(
        parsed_units=parsed_units,
        joint_correct=joint_correct,
    ) == expected


def test_api_and_access_token_environment_variables_fail_closed():
    validate_no_api_auth({})

    for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"):
        with pytest.raises(RuntimeError, match=name):
            validate_no_api_auth({name: "present"})


def test_attempt_lock_is_atomic(tmp_path):
    output = tmp_path / "pilot.json"
    lock = acquire_attempt_lock(output)
    try:
        with pytest.raises(FileExistsError):
            acquire_attempt_lock(output)
    finally:
        lock.unlink()


def test_live_upstream_parsing_is_exact():
    assert split_upstream_ref("origin/codex/topic") == ("origin", "codex/topic")
    with pytest.raises(RuntimeError):
        split_upstream_ref("local-only")

    sha = "a" * 40
    assert parse_remote_head(f"{sha}\trefs/heads/codex/topic", "codex/topic") == sha
    with pytest.raises(RuntimeError):
        parse_remote_head("", "codex/topic")
    with pytest.raises(RuntimeError):
        parse_remote_head(
            f"{'z' * 40}\trefs/heads/codex/topic",
            "codex/topic",
        )


@pytest.mark.parametrize("metrics", [{}, {"output_tokens": None}, {"output_tokens": True}])
def test_missing_or_invalid_output_usage_fails_closed(metrics):
    with pytest.raises(Exception, match="missing or invalid"):
        validate_output_budget(metrics, 2400)


def test_output_budget_boundary():
    assert validate_output_budget({"output_tokens": 2400}, 2400) == 2400
    with pytest.raises(Exception, match="exceeded"):
        validate_output_budget({"output_tokens": 2401}, 2400)


def test_thread_item_audit_requires_passive_items_and_agent_message():
    class AgentMessageThreadItem:
        pass

    class CommandExecutionThreadItem:
        pass

    class Item:
        def __init__(self, root):
            self.root = root

    class Result:
        pass

    result = Result()
    with pytest.raises(Exception, match="missing or invalid"):
        validate_passive_items(result)

    result.items = [Item(AgentMessageThreadItem())]
    assert validate_passive_items(result) == ("AgentMessageThreadItem",)

    result.items = [Item(CommandExecutionThreadItem())]
    with pytest.raises(Exception, match="no final agent message|forbidden"):
        validate_passive_items(result)


def test_frozen_dependency_hashes_still_match():
    workspace = V3_ROOT.parents[1]
    actual = {
        relative: sha256(workspace / relative)
        for relative in EXPECTED_DEPENDENCY_HASHES
    }
    assert actual == EXPECTED_DEPENDENCY_HASHES
