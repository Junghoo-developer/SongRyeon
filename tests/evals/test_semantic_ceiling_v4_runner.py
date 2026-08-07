"""No-network contract tests for the frozen Semantic Ceiling v4 runner.

These tests deliberately substitute the account client.  They exercise the
artifact/attempt protocol, not a target-model inference call.
"""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
V4 = ROOT / "evals" / "semantic_ceiling_v4"


def _runner():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(V4))
    spec = importlib.util.spec_from_file_location(
        "semantic_ceiling_v4_run_test", V4 / "run_v4.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _freeze(run):
    return {
        "tree_sha256": "1" * 64,
        "source_commit": "2" * 40,
        "model_contract": deepcopy(run.EXPECTED_READINESS),
        "study_sha256": "3" * 64,
        "manifest_sha256": "4" * 64,
        "plan_sha256": "5" * 64,
        "oracle_sha256": "6" * 64,
        "protocol_sha256": "7" * 64,
    }


def _metrics(run):
    return {
        "cached_input_tokens": 2,
        "input_tokens": 10,
        "output_tokens": 8,
        "reasoning_output_tokens": 3,
        "total_tokens": 18,
    }


def _valid_answer(run, unit, expected):
    from schemas_v4 import encode_wire_observation

    return json.dumps(
        {
            "claims": [
                {
                    "id": claim_id,
                    "verdict": expected[unit["plan_id"]][claim_id]["verdict"],
                    "observation": encode_wire_observation(
                        expected[unit["plan_id"]][claim_id]["observation"]
                    ),
                    "reason": "fixture-derived prediction",
                }
                for claim_id in unit["expected_ids"]
            ]
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


class _FakeClient:
    """A deterministic stand-in for the Codex account client."""

    outcomes: list[object] = []
    readiness_values: list[object] = []
    instances: list["_FakeClient"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.last_item_types = ()
        self.calls = []
        self.closed = False
        type(self).instances.append(self)

    def check_configuration(self):
        values = type(self).readiness_values
        value = values.pop(0) if values else deepcopy(_runner().EXPECTED_READINESS)
        if isinstance(value, Exception):
            raise value
        return value

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        outcome = type(self).outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        self.last_item_types = ("UserMessageThreadItem", "AgentMessageThreadItem")
        return SimpleNamespace(content=outcome, metrics=_metrics(_runner()))

    def close(self) -> None:
        self.closed = True


def _install_fake_runtime(monkeypatch: pytest.MonkeyPatch, run, tmp_path: Path):
    """Patch only external/freeze boundaries; preserve real control parsing."""

    freeze = _freeze(run)
    output = tmp_path / "output" / "run.json"
    publication = "a" * 40
    monkeypatch.setattr(run, "validate_no_api_auth", lambda: None)
    monkeypatch.setattr(run, "validate_source_import_provenance", lambda: None)
    monkeypatch.setattr(run, "validate_sdk_import_provenance", lambda: None)
    monkeypatch.setattr(run, "verify_freeze", lambda: freeze)
    monkeypatch.setattr(run, "sha256", lambda path: "f" * 64)
    monkeypatch.setattr(run, "canonical_artifact_path", lambda digest: output)
    monkeypatch.setattr(
        run,
        "validate_published_clean_head",
        lambda: {"live_commit": publication},
    )
    monkeypatch.setattr(
        run,
        "_verify_freeze_publication",
        lambda path, current: publication,
    )
    _FakeClient.outcomes = []
    _FakeClient.readiness_values = []
    _FakeClient.instances = []
    return freeze, output


def _run_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    run = _runner()
    freeze, output = _install_fake_runtime(monkeypatch, run, tmp_path)
    plan = run.load_strict_json(run.PLAN_PATH)
    expected = run.build_expected_claims(plan, run.load_strict_json(run.ORACLE_PATH))
    _FakeClient.outcomes = [
        _valid_answer(run, unit, expected) for unit in plan["units"]
    ]
    _FakeClient.readiness_values = [
        deepcopy(run.EXPECTED_READINESS),
        deepcopy(run.EXPECTED_READINESS),
    ]
    document = run.run_v4(client_factory=_FakeClient)
    return run, freeze, plan, document, output


def test_build_expected_claims_accepts_real_frozen_controls():
    run = _runner()
    plan = run.load_strict_json(run.PLAN_PATH)
    oracle = run.load_strict_json(run.ORACLE_PATH)
    expected = run.build_expected_claims(plan, oracle)
    assert list(expected) == [unit["plan_id"] for unit in plan["units"]]
    assert len(expected) == run.MAX_REQUESTS
    assert {claim for values in expected.values() for claim in values} == {
        claim_id for unit in plan["units"] for claim_id in unit["expected_ids"]
    }


@pytest.mark.parametrize(
    ("parsed", "scores", "ready", "unsupported", "label"),
    [
        (7, [3] * 7, True, 10, "output_or_runtime_failure"),
        (8, [3] * 8, False, 12, "output_or_runtime_failure"),
        (8, [3] * 8, True, 12, "ceiling_persists"),
        (8, [3] * 7 + [0], True, 9, "near_ceiling"),
        (8, [3, 3, 3, 3, 2, 2, 2, 2], True, 4, "anti_ceiling_pass"),
        (8, [3, 3, 3, 3, 2, 2, 2, 2], True, 3, "shape_inconclusive"),
        (8, [3, 3, 3, 3, 3, 3, 0, 0], True, 8, "semantic_floor_or_topic_cliff"),
        (8, [3, 3, 3, 3, 3, 2, 2, 1], True, 4, "shape_inconclusive"),
    ],
)
def test_classification_boundaries(parsed, scores, ready, unsupported, label):
    run = _runner()
    assert run.classify_result(
        parsed_units=parsed,
        cluster_scores=scores,
        readiness_match=ready,
        unsupported_joint_correct=unsupported,
    ) == label


@pytest.mark.parametrize(
    ("parsed", "scores", "ready", "unsupported"),
    [
        (True, [3] * 8, True, 12),
        (9, [3] * 8, True, 12),
        (8, [3] * 7, True, 12),
        (8, [3] * 7 + [4], True, 12),
        (8, [3] * 7 + [None], True, 12),
        (8, [3] * 8, 1, 12),
        (8, [3] * 8, True, True),
        (8, [3] * 8, True, 13),
    ],
)
def test_classification_rejects_invalid_inputs(parsed, scores, ready, unsupported):
    run = _runner()
    with pytest.raises(ValueError, match="classification inputs"):
        run.classify_result(
            parsed_units=parsed,
            cluster_scores=scores,
            readiness_match=ready,
            unsupported_joint_correct=unsupported,
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda doc: doc["rows"][0].__setitem__("answer", "not JSON"),
            "stored parse error differs",
        ),
        (
            lambda doc: doc["rows"][0]["claims"][0].__setitem__(
                "joint_correct", False
            ),
            "stored claim scores differ",
        ),
        (
            lambda doc: doc["rows"][0].__setitem__("parse_error", "forged"),
            "stored parse error differs",
        ),
    ],
)
def test_artifact_validator_rejects_raw_answer_or_score_tampering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, change, message
):
    run, freeze, plan, document, _ = _run_success(monkeypatch, tmp_path)
    changed = deepcopy(document)
    change(changed)
    with pytest.raises(ValueError, match=message):
        run.validate_artifact_document(
            changed,
            freeze=freeze,
            freeze_sha="f" * 64,
            plan=plan,
            oracle=run.load_strict_json(run.ORACLE_PATH),
        )


@pytest.mark.parametrize(
    ("alter", "message"),
    [
        (lambda usage: usage.pop("total_tokens"), "usage fields"),
        (lambda usage: usage.__setitem__("input_tokens", True), "nonnegative"),
        (lambda usage: usage.__setitem__("input_tokens", -1), "nonnegative"),
        (lambda usage: usage.__setitem__("total_tokens", 17), "total_tokens"),
        (lambda usage: usage.__setitem__("cached_input_tokens", 11), "cached"),
        (lambda usage: usage.__setitem__("reasoning_output_tokens", 9), "reasoning"),
        (
            lambda usage: usage.update(
                output_tokens=2401,
                total_tokens=usage["input_tokens"] + 2401,
            ),
            "budget",
        ),
    ],
)
def test_usage_contract_rejects_every_invariant(alter, message):
    run = _runner()
    usage = _metrics(run)
    alter(usage)
    with pytest.raises(ValueError, match=message):
        run._validate_usage(usage, enforce_budget=True)


def test_usage_without_budget_allows_only_the_budget_difference():
    run = _runner()
    usage = _metrics(run)
    usage["output_tokens"] = 2401
    usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    assert run._validate_usage(usage, enforce_budget=False) == usage


def test_structurally_valid_usage_from_an_error_row_is_still_counted():
    run = _runner()
    usage = _metrics(run)
    row = {"error": {"type": "ModelResponseError", "message": "budget"}, "model_metrics": usage}
    assert run._sum_usage([row]) == usage


def test_reservation_is_persistent_and_never_overwrites_artifact(tmp_path: Path):
    run = _runner()
    artifact = tmp_path / "f" / "run.json"
    lock = run.reserve_attempt(artifact, "a" * 64)
    assert lock == artifact.with_name("attempt.lock")
    assert json.loads(lock.read_text(encoding="utf-8"))["status"] == "canonical_attempt_reserved"
    with pytest.raises(FileExistsError, match="already reserved"):
        run.reserve_attempt(artifact, "a" * 64)
    lock.unlink()
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError, match="artifact already exists"):
        run.reserve_attempt(artifact, "a" * 64)
    assert artifact.read_text(encoding="utf-8") == "existing"


@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"])
def test_empty_forbidden_auth_key_is_still_forbidden(name):
    run = _runner()
    with pytest.raises(RuntimeError, match=name):
        run.validate_no_api_auth({name: ""})


def test_initial_readiness_failure_does_not_reserve_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    run = _runner()
    _, output = _install_fake_runtime(monkeypatch, run, tmp_path)
    wrong = deepcopy(run.EXPECTED_READINESS)
    wrong["sdk_version"] = "wrong"
    _FakeClient.readiness_values = [wrong]
    with pytest.raises(RuntimeError, match="initial Codex"):
        run.run_v4(client_factory=_FakeClient)
    assert not output.exists()
    assert not run.attempt_lock_path(output).exists()
    assert _FakeClient.instances[0].closed


def test_successful_fake_client_runs_all_eight_and_has_exact_shapes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    run, freeze, plan, document, output = _run_success(monkeypatch, tmp_path)
    assert output.exists()
    assert set(document) == run.COMPLETE_DOCUMENT_KEYS
    assert len(document["rows"]) == run.MAX_REQUESTS
    assert document["summary"]["classification"] == "ceiling_persists"
    assert document["summary"]["joint_correct"] == run.CLAIM_COUNT
    assert len(_FakeClient.instances[0].calls) == run.MAX_REQUESTS
    assert all(set(row) == run.ROW_KEYS for row in document["rows"])
    assert all(set(score) == run.CLAIM_SCORE_KEYS for row in document["rows"] for score in row["claims"])
    assert run.validate_artifact_document(
        document,
        freeze=freeze,
        freeze_sha="f" * 64,
        plan=plan,
        oracle=run.load_strict_json(run.ORACLE_PATH),
    )


def test_parse_failure_is_recorded_but_remaining_units_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    run = _runner()
    _, _ = _install_fake_runtime(monkeypatch, run, tmp_path)
    plan = run.load_strict_json(run.PLAN_PATH)
    expected = run.build_expected_claims(plan, run.load_strict_json(run.ORACLE_PATH))
    _FakeClient.outcomes = ["not JSON"] + [
        _valid_answer(run, unit, expected) for unit in plan["units"][1:]
    ]
    _FakeClient.readiness_values = [
        deepcopy(run.EXPECTED_READINESS), deepcopy(run.EXPECTED_READINESS)
    ]
    document = run.run_v4(client_factory=_FakeClient)
    assert len(document["rows"]) == 8
    assert document["rows"][0]["parse_error"] == "answer_is_not_strict_json"
    assert document["rows"][0]["claims"] == []
    assert len(_FakeClient.instances[0].calls) == 8
    assert document["summary"]["classification"] == "output_or_runtime_failure"


def test_runtime_error_on_third_call_stops_at_the_final_error_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    run = _runner()
    _, _ = _install_fake_runtime(monkeypatch, run, tmp_path)
    plan = run.load_strict_json(run.PLAN_PATH)
    expected = run.build_expected_claims(plan, run.load_strict_json(run.ORACLE_PATH))
    _FakeClient.outcomes = [
        _valid_answer(run, unit, expected) for unit in plan["units"][:2]
    ] + [RuntimeError("transport stopped")]
    _FakeClient.readiness_values = [
        deepcopy(run.EXPECTED_READINESS), deepcopy(run.EXPECTED_READINESS)
    ]
    document = run.run_v4(client_factory=_FakeClient)
    assert len(document["rows"]) == 3
    assert document["rows"][-1]["error"] == {
        "type": "RuntimeError", "message": "transport stopped"
    }
    assert len(_FakeClient.instances[0].calls) == 3
    assert document["summary"]["stopped_early"] is True
    assert document["summary"]["classification"] == "output_or_runtime_failure"


def test_final_readiness_drift_is_complete_but_an_output_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    run = _runner()
    _, _ = _install_fake_runtime(monkeypatch, run, tmp_path)
    plan = run.load_strict_json(run.PLAN_PATH)
    expected = run.build_expected_claims(plan, run.load_strict_json(run.ORACLE_PATH))
    _FakeClient.outcomes = [
        _valid_answer(run, unit, expected) for unit in plan["units"]
    ]
    drift = deepcopy(run.EXPECTED_READINESS)
    drift["model_name"] = "other-model"
    _FakeClient.readiness_values = [deepcopy(run.EXPECTED_READINESS), drift]
    document = run.run_v4(client_factory=_FakeClient)
    assert document["run_state"] == "complete"
    assert document["final_readiness"]["ok"] is False
    assert document["summary"]["readiness_match"] is False
    assert document["summary"]["classification"] == "output_or_runtime_failure"


def test_final_readiness_error_is_complete_but_an_output_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    run = _runner()
    _, _ = _install_fake_runtime(monkeypatch, run, tmp_path)
    plan = run.load_strict_json(run.PLAN_PATH)
    expected = run.build_expected_claims(plan, run.load_strict_json(run.ORACLE_PATH))
    _FakeClient.outcomes = [
        _valid_answer(run, unit, expected) for unit in plan["units"]
    ]
    _FakeClient.readiness_values = [
        deepcopy(run.EXPECTED_READINESS), RuntimeError("readiness transport")
    ]
    document = run.run_v4(client_factory=_FakeClient)
    assert document["run_state"] == "complete"
    assert document["final_readiness"] == {
        "ok": False,
        "value": None,
        "error": {"type": "RuntimeError", "message": "readiness transport"},
    }
    assert document["summary"]["classification"] == "output_or_runtime_failure"


def test_direct_runner_requires_dash_b_before_frozen_imports():
    runner = V4 / "run_v4.py"
    environment = dict(os.environ)
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    completed = subprocess.run(
        [sys.executable, str(runner), "--help"],
        cwd=ROOT,
        capture_output=True,
        env=environment,
        timeout=20,
    )
    assert completed.returncode != 0
    assert b"must be executed with python -B" in completed.stderr


def test_module_execution_is_rejected():
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "evals.semantic_ceiling_v4.run_v4",
            "--help",
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=20,
    )
    assert completed.returncode != 0
    assert b"direct file path" in completed.stderr


def test_isolated_direct_help_reaches_the_cli_without_importing_a_model():
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(V4 / "run_v4.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert b"--output" in completed.stdout


def test_startup_guard_rejects_cache_directories(tmp_path: Path):
    run = _runner()
    experiment = tmp_path / "experiment"
    llm = tmp_path / "llm"
    (experiment / "__pycache__").mkdir(parents=True)
    llm.mkdir()
    with pytest.raises(RuntimeError, match="refuses Python bytecode"):
        run.reject_startup_caches(str(experiment), str(llm))


def test_audited_client_captures_forbidden_item_before_rejection():
    run = _runner()
    client = run.AuditedCodexClient()
    agent_type = type("AgentMessageThreadItem", (), {})
    tool_type = type("ToolCallThreadItem", (), {})
    result = SimpleNamespace(
        items=[
            SimpleNamespace(root=agent_type()),
            SimpleNamespace(root=tool_type()),
        ],
        usage=SimpleNamespace(total=SimpleNamespace(**_metrics(run))),
    )
    with pytest.raises(run.ModelResponseError, match="forbidden activity"):
        client._parse_result(result, num_predict=run.MAX_OUTPUT_TOKENS)
    assert client.last_item_types == (
        "AgentMessageThreadItem",
        "ToolCallThreadItem",
    )
    assert client.last_model_metrics == _metrics(run)


def test_forbidden_item_usage_survives_the_runtime_error_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    run = _runner()
    _, output = _install_fake_runtime(monkeypatch, run, tmp_path)

    class ForbiddenItemClient(run.AuditedCodexClient):
        def __init__(self, **kwargs) -> None:
            self.last_item_types = ()
            self.last_model_metrics = {}

        def check_configuration(self):
            return deepcopy(run.EXPECTED_READINESS)

        def complete(self, **kwargs):
            agent_type = type("AgentMessageThreadItem", (), {})
            tool_type = type("ToolCallThreadItem", (), {})
            result = SimpleNamespace(
                items=[
                    SimpleNamespace(root=agent_type()),
                    SimpleNamespace(root=tool_type()),
                ],
                usage=SimpleNamespace(total=SimpleNamespace(**_metrics(run))),
            )
            return self._parse_result(result, num_predict=kwargs["num_predict"])

        def close(self) -> None:
            pass

    document = run.run_v4(client_factory=ForbiddenItemClient)
    row = document["rows"][0]
    assert row["error"]["type"] == "ModelResponseError"
    assert row["model_metrics"] == _metrics(run)
    assert document["summary"]["usage"] == _metrics(run)
    assert json.loads(output.read_text(encoding="utf-8")) == document


def test_transport_error_cannot_reuse_previous_call_usage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    run = _runner()
    _, _ = _install_fake_runtime(monkeypatch, run, tmp_path)
    plan = run.load_strict_json(run.PLAN_PATH)
    expected = run.build_expected_claims(plan, run.load_strict_json(run.ORACLE_PATH))

    class SuccessThenTransportErrorClient(run.AuditedCodexClient):
        def __init__(self, **kwargs) -> None:
            self.model_name = kwargs["model_name"]
            self.last_item_types = ()
            self.last_model_metrics = {}
            self.call_count = 0

        def check_configuration(self):
            return deepcopy(run.EXPECTED_READINESS)

        def complete(self, **kwargs):
            self.call_count += 1
            if self.call_count == 2:
                raise RuntimeError("transport failed before result parsing")
            agent_type = type("AgentMessageThreadItem", (), {})
            result = SimpleNamespace(
                status=SimpleNamespace(value="completed"),
                error=None,
                items=[SimpleNamespace(root=agent_type())],
                final_response=_valid_answer(run, plan["units"][0], expected),
                usage=SimpleNamespace(total=SimpleNamespace(**_metrics(run))),
            )
            return self._parse_result(result, num_predict=kwargs["num_predict"])

        def close(self) -> None:
            pass

    document = run.run_v4(client_factory=SuccessThenTransportErrorClient)
    assert document["rows"][0]["model_metrics"] == _metrics(run)
    assert document["rows"][1]["error"]["type"] == "RuntimeError"
    assert document["rows"][1]["model_metrics"] == {}
    assert document["summary"]["usage"] == _metrics(run)


def test_interrupted_started_call_is_indeterminate_and_never_retried(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    run = _runner()
    _, output = _install_fake_runtime(monkeypatch, run, tmp_path)
    _FakeClient.outcomes = [KeyboardInterrupt()]
    _FakeClient.readiness_values = [deepcopy(run.EXPECTED_READINESS)]
    with pytest.raises(KeyboardInterrupt):
        run.run_v4(client_factory=_FakeClient)
    checkpoint = json.loads(output.read_text(encoding="utf-8"))
    assert checkpoint["run_state"] == "running"
    assert checkpoint["rows"][0]["state"] == "started"
    assert checkpoint["rows"][0]["model_call_count"] == 1
    assert run.attempt_lock_path(output).exists()
    with pytest.raises(FileExistsError):
        run.reserve_attempt(output, "f" * 64)
