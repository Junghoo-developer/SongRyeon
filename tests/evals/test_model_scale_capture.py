"""외부 model-ceiling evidence pack의 격리·동결·검증 계약."""

import json
from datetime import datetime, timezone

import pytest

from evals.model_scale_capture import (
    ARTIFACT_MANIFEST_FILENAME,
    BLIND_KEY_FILENAME,
    BLIND_REVIEW_FILENAME,
    CAPTURE_FILENAME,
    CHECKPOINT_FILENAME,
    DEFAULT_MODEL_CEILING_MANIFEST,
    MECHANICAL_SUMMARY_FILENAME,
    PROTOCOL_FILENAME,
    REPORT_FILENAME,
    capture_model_scale_comparison,
)
from evals.model_scale_verify import verify_evidence_pack
from evals.runner import load_manifest
from llm import ModelReply


class FakeLocalClient:
    provider = "ollama"
    execution_mode = "contest_local_or_self_hosted"

    def __init__(
        self,
        *,
        base_url,
        model_name,
        timeout_seconds,
        num_ctx,
        keep_alive,
        temperature,
        seed,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self.temperature = temperature
        self.seed = seed

    def check_ready(self):
        return {
            "server_version": "test-ollama",
            "model_name": self.model_name,
            "model_digest": "a" * 64,
        }

    def complete(self, **kwargs):
        return _fake_reply(self.model_name, kwargs["response_schema"])


class FakeAccountClient:
    provider = "openai_codex"
    execution_mode = "codex_account_integration"
    instances = []

    def __init__(self, *, model_name, reasoning_effort):
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort
        self.close_calls = 0
        self.instances.append(self)

    def check_configuration(self):
        return {
            "provider": self.provider,
            "execution_mode": self.execution_mode,
            "model_name": self.model_name,
            "reasoning_effort": self.reasoning_effort,
            "sdk_version": "test-sdk",
        }

    def complete(self, **kwargs):
        return _fake_reply(self.model_name, kwargs["response_schema"])

    def close(self):
        self.close_calls += 1


def _fake_reply(model_name, schema):
    properties = schema.get("properties", {})
    if set(properties) == {"action", "reason", "tool_name", "arguments"}:
        payload = {
            "action": "route_node2",
            "reason": "합성 capture 계약 검사다.",
            "tool_name": None,
            "arguments": None,
        }
    elif set(properties) == {"verdict", "reason"}:
        payload = {
            "verdict": "permit",
            "reason": "합성 capture 계약에서 통과한다.",
        }
    elif set(properties) == {"answer"}:
        payload = {"answer": "합성 evidence-pack 답변입니다."}
    else:
        raise AssertionError(f"예상하지 못한 schema: {properties}")
    return ModelReply(
        content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        thinking="",
        model=model_name,
        done_reason="stop",
        metrics={"output_tokens": 12},
    )


def test_heldout_manifest_is_frozen_before_live_execution():
    manifest = load_manifest(DEFAULT_MODEL_CEILING_MANIFEST)

    assert manifest.manifest_id == "songryeon-model-ceiling-heldout-v1"
    assert manifest.case_set_status == "frozen-v1"
    assert len(manifest.cases) == 12
    assert len(manifest.source_fixtures) == 9
    assert {tag for case in manifest.cases for tag in case.tags} >= {
        "held_out",
        "positive_control",
        "negative_control",
        "declaration_trap",
        "import_trap",
        "prompt_injection",
        "path_safety",
        "follow_up_turns",
        "subjective_requests",
    }


def test_model_scale_capture_is_separate_blinded_and_hash_verified(tmp_path):
    FakeAccountClient.instances = []
    output_dir = tmp_path / "evidence-pack"

    result = capture_model_scale_comparison(
        output_dir=output_dir,
        local_client_factory=FakeLocalClient,
        account_client_factory=FakeAccountClient,
        now_factory=lambda: datetime(2026, 8, 2, tzinfo=timezone.utc),
        blind_seed="frozen-test-seed",
    )

    expected_files = {
        ARTIFACT_MANIFEST_FILENAME,
        BLIND_KEY_FILENAME,
        BLIND_REVIEW_FILENAME,
        CAPTURE_FILENAME,
        CHECKPOINT_FILENAME,
        MECHANICAL_SUMMARY_FILENAME,
        PROTOCOL_FILENAME,
        REPORT_FILENAME,
    }
    assert expected_files <= {path.name for path in output_dir.iterdir()}
    capture = result["capture"]
    assert capture["publishable"] is False
    assert capture["official_contest_score"] is False
    assert capture["uses_external_service"] is True
    assert capture["coverage"] == {
        "case_count": 12,
        "system_count": 2,
        "repetitions": 1,
        "planned_run_count": 24,
        "captured_run_count": 24,
        "complete_case_system_repetition_matrix": True,
        "completed_run_count": 24,
        "failed_run_count": 0,
    }
    assert len({run["run_id"] for run in capture["captures"]}) == 24
    assert len(
        {
            run["raw_memory_artifact"]["path"]
            for run in capture["captures"]
        }
    ) == 24
    assert [
        item["order_in_case_pair"]
        for item in capture["schedule"][:4]
    ] == [1, 2, 1, 2]
    assert capture["schedule"][0]["system_name"] != (
        capture["schedule"][2]["system_name"]
    )

    protocol = json.loads(
        (output_dir / PROTOCOL_FILENAME).read_text(encoding="utf-8")
    )
    assert protocol["protocol_status"] == "frozen_before_first_inference"
    assert protocol["comparability"]["same_songryeon_wrapper"] is True
    assert protocol["comparability"]["backend_prompt_equivalent"] is False
    assert protocol["case_isolation"]["actual_user_memory_used"] is False
    assert protocol["git"]["source_snapshot_is_authoritative"] is True
    assert protocol["source_snapshot"]["file_count"] > 0

    blind_review = json.loads(
        (output_dir / BLIND_REVIEW_FILENAME).read_text(encoding="utf-8")
    )
    assert blind_review["packet_status"] == "unscored_blind_review"
    assert len(blind_review["items"]) == 24
    assert {item["blind_system_alias"] for item in blind_review["items"]} == {
        "System A",
        "System B",
    }
    assert all(
        "system_name" not in item for item in blind_review["items"]
    )

    verification = verify_evidence_pack(output_dir)
    assert verification["verified"] is True
    assert verification["run_count"] == 24
    assert FakeAccountClient.instances[0].close_calls == 1


def test_evidence_verifier_rejects_a_tampered_raw_log(tmp_path):
    output_dir = tmp_path / "evidence-pack"
    result = capture_model_scale_comparison(
        output_dir=output_dir,
        local_client_factory=FakeLocalClient,
        account_client_factory=FakeAccountClient,
        now_factory=lambda: datetime(2026, 8, 2, tzinfo=timezone.utc),
        blind_seed="tamper-test-seed",
    )
    raw_relative = result["capture"]["captures"][0][
        "raw_memory_artifact"
    ]["path"]
    raw_path = output_dir / raw_relative
    raw_path.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="byte_count|SHA-256"):
        verify_evidence_pack(output_dir)
