import argparse
import json

import pytest

from evals.hybrid_audit_v1 import run
from llm.client import ModelReply


def _case():
    return {
        "case_id": "case-1",
        "local_draft": "상수 선언만으로 제한 집행은 확인되지 않습니다.",
        "audit_input": {
            "a_records": [
                {
                    "provenance_id": "A-" + "1" * 64,
                    "tool_name": "read_python_file",
                    "arguments": {"path": "sample.py"},
                    "success": True,
                    "content": "LIMIT = 4\n",
                    "error": None,
                    "information_class": "absolute",
                    "code_verifiable": True,
                }
            ]
        },
    }


class _FakeClient:
    model_name = "fake-requested-model"

    def __init__(self, *, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def complete(self, **arguments):
        self.calls.append(arguments)
        if self.error is not None:
            raise self.error
        return self.reply


def test_run_case_records_one_strict_valid_attempt():
    client = _FakeClient(
        reply=ModelReply(
            content='{"verdict":"permit","reason":"A 범위를 넘지 않음"}',
            thinking="",
            model="fake",
            done_reason="stop",
            metrics={"input_tokens": 10, "output_tokens": 4},
        )
    )

    checkpoints = []
    row = run._run_case(
        client,
        _case(),
        runner_attempt=1,
        checkpoint_before_invocation=lambda value: checkpoints.append(dict(value)),
    )

    assert row["state"] == "valid"
    assert row["runner_attempt"] == 1
    assert row["parsed_output"]["verdict"] == "permit"
    assert row["error"] is None
    assert row["requested_model"] == "fake-requested-model"
    assert row["client_reported_model"] == "fake"
    assert row["client_done_reason"] == "stop"
    assert len(checkpoints) == 1
    assert checkpoints[0]["state"] == "invocation_reserved"
    assert checkpoints[0]["raw_response"] == ""
    assert len(client.calls) == 1
    assert client.calls[0]["num_predict"] == run.AUDIT_NUM_PREDICT
    assert "expected_audit_verdict" not in client.calls[0]["user_prompt"]


def test_run_case_preserves_failure_without_retry():
    client = _FakeClient(error=RuntimeError("transport failed"))

    row = run._run_case(
        client,
        _case(),
        runner_attempt=1,
        checkpoint_before_invocation=lambda value: None,
    )

    assert row["state"] == "failed"
    assert row["parsed_output"] is None
    assert row["error"] == {
        "type": "RuntimeError",
        "message": "transport failed",
    }
    assert len(client.calls) == 1


def test_run_case_projects_before_prompt_and_excludes_poison_hidden_fields():
    case = _case()
    case.update(
        {
            "active_goal": "POISON_ACTIVE_GOAL",
            "expected_audit_verdict": "POISON_ORACLE_VERDICT",
            "oracle": "POISON_ORACLE_REASON",
            "historical_reference": {
                "local_evidence_reviewer": "POISON_REVIEWER_REASON"
            },
            "source_packet": {
                "payload": {"fixture_memory": ["POISON_R_MEMORY"]}
            },
        }
    )
    client = _FakeClient(
        reply=ModelReply(
            content='{"verdict":"permit","reason":"A only"}',
            thinking="",
            model="fake",
            done_reason="stop",
            metrics={},
        )
    )

    run._run_case(
        client,
        case,
        runner_attempt=1,
        checkpoint_before_invocation=lambda value: None,
    )

    rendered = (
        client.calls[0]["system_prompt"] + "\n" + client.calls[0]["user_prompt"]
    )
    for poison in (
        "POISON_ACTIVE_GOAL",
        "POISON_ORACLE_VERDICT",
        "POISON_ORACLE_REASON",
        "POISON_REVIEWER_REASON",
        "POISON_R_MEMORY",
    ):
        assert poison not in rendered


def test_checkpoint_failure_prevents_model_invocation():
    client = _FakeClient(error=AssertionError("model must not be called"))

    with pytest.raises(OSError, match="checkpoint failed"):
        run._run_case(
            client,
            _case(),
            runner_attempt=1,
            checkpoint_before_invocation=lambda value: (_ for _ in ()).throw(
                OSError("checkpoint failed")
            ),
        )

    assert client.calls == []


def test_attempt_reservation_is_exclusive(tmp_path):
    output = tmp_path / "condition.json"

    lock = run._reserve_attempt(output)

    assert lock.exists()
    with pytest.raises(FileExistsError, match="이미 예약"):
        run._reserve_attempt(output)


@pytest.mark.parametrize("value", ["secret", ""])
def test_codex_account_condition_rejects_api_token_environment(value):
    with pytest.raises(RuntimeError, match="API/access-token"):
        run._validate_no_cloud_api_auth({"OPENAI_API_KEY": value})


def test_local_client_contract_is_fixed_but_transport_options_remain_configurable(
    monkeypatch,
):
    captured = {}

    class FakeOllama:
        provider = "ollama"
        execution_mode = "contest_local_or_self_hosted"

        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.temperature = kwargs["temperature"]
            self.seed = kwargs["seed"]
            self.num_ctx = kwargs["num_ctx"]

        def check_ready(self):
            return {
                "server_version": "test",
                "model_name": run.LOCAL_MODEL,
                "model_digest": "a" * 64,
            }

    monkeypatch.setattr(run, "OllamaClient", FakeOllama)
    args = argparse.Namespace(
        base_url="http://127.0.0.1:9999",
        timeout_seconds=321,
        keep_alive="27m",
        num_ctx=999,
    )

    _, readiness = run._build_client(run.LOCAL_CONDITION, args)

    assert captured == {
        "base_url": "http://127.0.0.1:9999",
        "model_name": run.LOCAL_MODEL,
        "timeout_seconds": 321,
        "num_ctx": 16_384,
        "keep_alive": "27m",
        "temperature": 0,
        "seed": 42,
    }
    assert readiness["num_ctx"] == 16_384
    assert readiness["temperature"] == 0
    assert readiness["seed"] == 42


def test_cloud_readiness_explicitly_records_tools_are_not_allowed(monkeypatch):
    for name in run.FORBIDDEN_CLOUD_AUTH_ENV:
        monkeypatch.delenv(name, raising=False)

    class FakeCodexAccountClient:
        def __init__(self, *, model_name, reasoning_effort):
            self.model_name = model_name
            self.reasoning_effort = reasoning_effort

        def check_configuration(self):
            return {
                "provider": "openai_codex",
                "execution_mode": "codex_account_integration",
                "model_name": self.model_name,
                "reasoning_effort": self.reasoning_effort,
            }

    monkeypatch.setattr(
        run,
        "CodexAccountIntegrationClient",
        FakeCodexAccountClient,
    )

    _, readiness = run._build_client(
        run.CLOUD_CONDITION,
        argparse.Namespace(),
    )

    assert readiness["tools_allowed"] is False


def test_cli_has_no_num_ctx_override():
    parser = run._build_parser()

    args = parser.parse_args([run.LOCAL_CONDITION])

    assert not hasattr(args, "num_ctx")
    with pytest.raises(SystemExit):
        parser.parse_args([run.LOCAL_CONDITION, "--num-ctx", "8192"])


def test_run_condition_checkpoints_readiness_and_reserved_row_before_call(
    monkeypatch,
    tmp_path,
):
    source = {"snapshot_id": "snapshot-1", "cases": [_case()]}
    freeze = {"freeze_payload_sha256": "f" * 64}
    reply = ModelReply(
        content='{"verdict":"permit","reason":"A only"}',
        thinking="",
        model="fake-observed-model",
        done_reason="stop",
        metrics={"input_tokens": 10},
    )

    class InspectingClient(_FakeClient):
        def __init__(self):
            super().__init__(reply=reply)
            self.pre_invocation_artifact = None
            self.closed = False

        def complete(self, **arguments):
            output = next(tmp_path.rglob(f"{run.LOCAL_CONDITION}.json"))
            self.pre_invocation_artifact = json.loads(output.read_text("utf-8"))
            return super().complete(**arguments)

        def close(self):
            self.closed = True

    client = InspectingClient()
    readiness = {
        "provider": "fake-provider",
        "execution_mode": "test",
        "model_name": client.model_name,
    }
    monkeypatch.setattr(
        run,
        "_verify_freeze",
        lambda: (freeze, source, "s" * 64),
    )
    monkeypatch.setattr(
        run,
        "_build_client",
        lambda condition, args: (client, readiness),
    )
    monkeypatch.setattr(run, "OUTPUT_ROOT", tmp_path)

    output = run.run_condition(run.LOCAL_CONDITION, argparse.Namespace())

    reserved = client.pre_invocation_artifact
    assert reserved["model_readiness"] == readiness
    assert reserved["run_state"] == "running"
    assert reserved["rows"][0]["runner_attempt"] == 1
    assert reserved["rows"][0]["state"] == "invocation_reserved"
    assert reserved["rows"][0]["raw_response"] == ""
    final = json.loads(output.read_text("utf-8"))
    assert final["run_state"] == "complete"
    assert final["rows"][0]["state"] == "valid"
    assert client.closed is True


def test_row_summary_counts_failed_rows_instead_of_dropping_them():
    rows = [
        {
            "state": "valid",
            "latency_ms": 10,
            "metrics": {"input_tokens": 5},
        },
        {
            "state": "failed",
            "latency_ms": 20,
            "metrics": {},
        },
    ]

    summary = run._summarize_rows(rows)

    assert summary["planned_rows"] == 2
    assert summary["state_counts"] == {"valid": 1, "failed": 1}
    assert summary["latency_ms_sum"] == 30
    assert summary["metric_totals"] == {"input_tokens": 5}
