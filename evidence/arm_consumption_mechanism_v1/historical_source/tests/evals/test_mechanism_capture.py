"""Mechanism replay가 조건 외의 입력을 고정하고 원시 감사를 남기는지 검사한다."""

import copy
import json
from collections import Counter

import pytest

from evals import mechanism_capture as capture
from llm import ModelReply


def _packet_set():
    payload = {
        "active_goal": "alpha.py를 읽고 실제 동작을 설명해라.",
        "fixture_memory": [
            {
                "memory_id": "memory-001",
                "information": "과거에는 제한이 적용됐다고 들었다.",
                "information_class": "relative",
                "code_verifiable": False,
            }
        ],
        "tool_results": [
            {
                "tool_name": "read_python_file",
                "arguments": {"path": "alpha.py"},
                "success": True,
                "content": "LIMIT = 8\n\ndef accept(value):\n    return value\n",
                "error": "",
                "information_class": "absolute",
                "code_verifiable": True,
            }
        ],
    }
    identity = {"case_id": "case-alpha", "payload": payload}
    packet = {
        **identity,
        "packet_sha256": capture.sha256_text(capture.canonical_json(identity)),
    }
    core = {
        "schema_version": 1,
        "packet_set_id": "test-packet-set",
        "source_manifest": {"manifest_sha256": "a" * 64},
        "evidence_plan": {"plan_sha256": "b" * 64},
        "packet_count": 1,
        "packets": [packet],
    }
    return {
        **core,
        "packet_set_sha256": capture.sha256_text(capture.canonical_json(core)),
    }


class FakeClient:
    provider = "fake_ollama"
    execution_mode = "test"

    def __init__(self, seed, *, invalid_opaque=False, forbid_complete=False):
        self.seed = seed
        self.invalid_opaque = invalid_opaque
        self.forbid_complete = forbid_complete
        self.model_name = "gemma4:26b"
        self.base_url = "http://127.0.0.1:11434"
        self.num_ctx = 16_384
        self.temperature = 0
        self.timeout_seconds = 180
        self.keep_alive = "10m"
        self.calls = []

    def check_ready(self):
        return {
            "server_version": "test-1",
            "model_name": self.model_name,
            "model_digest": "c" * 64,
        }

    def complete(self, *, system_prompt, user_prompt, response_schema, num_predict):
        if self.forbid_complete:
            raise AssertionError("resume에서 모델을 다시 호출하면 안 됩니다.")
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": copy.deepcopy(response_schema),
                "num_predict": num_predict,
            }
        )

        if response_schema == capture.ANSWER_SCHEMA:
            if (
                self.invalid_opaque
                and capture._ANSWER_BLOCK_SOURCE[capture.OPAQUE_LABEL]
                in system_prompt
            ):
                content = "not-json"
            elif "각 기록은 검증 범위 안에서만 소비하라" in system_prompt:
                content = json.dumps(
                    {"answer": "consumer draft"},
                    ensure_ascii=False,
                )
            else:
                content = json.dumps(
                    {"answer": "condition answer"},
                    ensure_ascii=False,
                )
        elif "이번 조건에서는 draft의 사실성" in system_prompt:
            content = json.dumps(
                {
                    "verdict": "permit",
                    "reason": "문장이 완결되어 있다.",
                    "revised_answer": "consumer draft",
                },
                ensure_ascii=False,
            )
        else:
            content = json.dumps(
                {
                    "verdict": "reject",
                    "reason": "선언만으로 집행을 단정할 수 없다.",
                    "revised_answer": "제한 상수는 보이지만 집행은 확인되지 않는다.",
                },
                ensure_ascii=False,
            )

        return ModelReply(
            content=content,
            thinking="raw thinking",
            model=self.model_name,
            done_reason="stop",
            metrics={"eval_count": 7, "total_duration": 123},
        )


def _prompt_payload():
    document = _packet_set()
    return capture._coerce_packet_row(document["packets"][0])["prompt_payload"]


def test_answer_conditions_change_only_the_masked_block_and_are_length_matched():
    prompt_payload = _prompt_payload()
    prompts = {
        condition: capture.build_answer_prompts(prompt_payload, condition)
        for condition in capture.ANSWER_CONDITIONS
    }

    assert len({user for _, user in prompts.values()}) == 1
    assert "case-alpha" not in next(iter(prompts.values()))[1]
    assert '"packet_sha256"' not in next(iter(prompts.values()))[1]
    assert '"information_class"' not in next(iter(prompts.values()))[1]
    assert '"code_verifiable"' not in next(iter(prompts.values()))[1]
    assert '"role_token":"K"' in next(iter(prompts.values()))[1]
    assert '"role_token":"M"' in next(iter(prompts.values()))[1]

    masked = {
        capture._masked_prompt_hash(
            system,
            user,
            capture.ANSWER_SCHEMA,
            capture.ANSWER_NUM_PREDICT,
        )
        for system, user in prompts.values()
    }
    assert len(masked) == 1
    lengths = capture.validate_condition_block_lengths(
        capture.ANSWER_CONDITION_BLOCKS
    )
    assert len(set(lengths.values())) == 1


def test_balanced_orders_are_position_balanced_across_30_cases_and_three_seeds():
    answer_positions = [Counter() for _ in range(4)]
    reviewer_positions = [Counter() for _ in range(2)]

    for seed_index in range(3):
        for packet_index in range(30):
            for position, condition in enumerate(
                capture.balanced_answer_order(packet_index, seed_index)
            ):
                answer_positions[position][condition] += 1
            for position, reviewer in enumerate(
                capture.balanced_reviewer_order(packet_index, seed_index)
            ):
                reviewer_positions[position][reviewer] += 1

    for counts in answer_positions:
        assert set(counts) == set(capture.ANSWER_CONDITIONS)
        assert max(counts.values()) - min(counts.values()) <= 1
    for counts in reviewer_positions:
        assert counts == Counter(
            {
                capture.STYLE_PLACEBO_REVIEWER: 45,
                capture.EVIDENCE_REVIEWER: 45,
            }
        )


def test_capture_saves_raw_audit_and_derives_shadow_and_two_enforced_outputs(tmp_path):
    clients = {}

    def factory(seed):
        client = FakeClient(seed)
        clients[seed] = client
        return client

    capture_path, document = capture.capture_mechanism_replays(
        _packet_set(),
        output_dir=tmp_path / "capture",
        client_factory=factory,
        seeds=(42,),
    )

    assert capture_path.is_file()
    assert document["capture_status"] == "complete"
    assert document["completed_unit_count"] == 1
    assert document["publishable"] is False
    assert len(clients[42].calls) == 6

    artifact = document["raw_artifacts"][0]
    raw_path = capture_path.parent / artifact["path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    assert raw["derived_outputs"] == {
        "shadow": "consumer draft",
        "style_placebo_enforced": "consumer draft",
        "evidence_enforced": "제한 상수는 보이지만 집행은 확인되지 않는다.",
    }
    assert len(
        {
            call["masked_prompt_sha256"]
            for call in raw["answer_calls"].values()
        }
    ) == 1
    assert len(
        {
            call["masked_prompt_sha256"]
            for call in raw["reviewer_calls"].values()
        }
    ) == 1

    for call in [
        *raw["answer_calls"].values(),
        *raw["reviewer_calls"].values(),
    ]:
        attempt = call["attempts"][0]
        assert attempt["status"] == "valid"
        assert attempt["system_prompt"]
        assert attempt["user_prompt"]
        assert len(attempt["prompt_sha256"]) == 64
        assert len(attempt["raw_response_sha256"]) == 64
        assert attempt["raw_response"]
        assert attempt["thinking"] == "raw thinking"
        assert attempt["metrics"] == {"eval_count": 7, "total_duration": 123}

    reviewer_calls = [
        call
        for call in clients[42].calls
        if call["response_schema"] == capture.REVIEW_SCHEMA
    ]
    assert len(reviewer_calls) == 2
    assert {call["num_predict"] for call in reviewer_calls} == {
        capture.REVIEW_NUM_PREDICT
    }
    assert len({call["user_prompt"] for call in reviewer_calls}) == 1

    runtime = document["configuration"]["model_runtime"]
    assert runtime == {
        "base_url": "http://127.0.0.1:11434",
        "keep_alive": "10m",
        "model_digest": "c" * 64,
        "num_ctx": 16_384,
        "server_version": "test-1",
        "temperature": 0,
        "timeout_seconds": 180,
    }


def test_invalid_json_is_recorded_three_times_and_does_not_block_other_conditions(tmp_path):
    client = FakeClient(42, invalid_opaque=True)
    _, document = capture.capture_mechanism_replays(
        _packet_set(),
        output_dir=tmp_path / "capture",
        client_factory=lambda seed: client,
        seeds=(42,),
    )
    artifact = document["raw_artifacts"][0]
    raw = json.loads(
        (tmp_path / "capture" / artifact["path"]).read_text(encoding="utf-8")
    )
    opaque = raw["answer_calls"][capture.OPAQUE_LABEL]
    assert opaque["status"] == "invalid_exhausted"
    assert [attempt["status"] for attempt in opaque["attempts"]] == [
        "invalid",
        "invalid",
        "invalid",
    ]
    assert all(
        call["status"] == "valid"
        for condition, call in raw["answer_calls"].items()
        if condition != capture.OPAQUE_LABEL
    )
    assert all(
        call["status"] == "valid" for call in raw["reviewer_calls"].values()
    )
    assert len(client.calls) == 8


def test_permit_must_preserve_exact_draft_and_resume_skips_completed_units(tmp_path):
    with pytest.raises(ValueError, match="정확히 같아야"):
        capture._parse_review(
            {
                "verdict": "permit",
                "reason": "문제없다.",
                "revised_answer": "changed",
            },
            "original",
        )

    output_dir = tmp_path / "capture"
    first = FakeClient(42)
    _, first_document = capture.capture_mechanism_replays(
        _packet_set(),
        output_dir=output_dir,
        client_factory=lambda seed: first,
        seeds=(42,),
    )
    raw_hash = first_document["raw_artifacts"][0]["sha256"]
    assert first_document["in_progress_unit"] is None

    resumed = FakeClient(42, forbid_complete=True)
    _, resumed_document = capture.capture_mechanism_replays(
        _packet_set(),
        output_dir=output_dir,
        client_factory=lambda seed: resumed,
        seeds=(42,),
        resume=True,
    )
    assert resumed.calls == []
    assert resumed_document["completed_unit_count"] == 1
    assert resumed_document["in_progress_unit"] is None
    assert resumed_document["raw_artifacts"][0]["sha256"] == raw_hash


def test_resume_hard_fails_after_mid_unit_interruption_without_recalling_model(tmp_path):
    class InterruptingClient(FakeClient):
        def complete(self, **kwargs):
            raise KeyboardInterrupt

    output_dir = tmp_path / "interrupted"
    with pytest.raises(KeyboardInterrupt):
        capture.capture_mechanism_replays(
            _packet_set(),
            output_dir=output_dir,
            client_factory=lambda seed: InterruptingClient(seed),
            seeds=(42,),
        )

    checkpoint = json.loads(
        (output_dir / capture.CHECKPOINT_FILENAME).read_text(encoding="utf-8")
    )
    assert checkpoint["capture_status"] == "in_progress"
    assert checkpoint["raw_artifacts"] == []
    assert checkpoint["in_progress_unit"] == {
        "case_id": "case-alpha",
        "packet_index": 0,
        "seed": 42,
    }

    factory_called = False

    def forbidden_factory(seed):
        nonlocal factory_called
        factory_called = True
        raise AssertionError("중단 marker가 있으면 client도 만들면 안 됩니다.")

    with pytest.raises(ValueError, match="unit 중간에 중단"):
        capture.capture_mechanism_replays(
            _packet_set(),
            output_dir=output_dir,
            client_factory=forbidden_factory,
            seeds=(42,),
            resume=True,
        )
    assert factory_called is False


def test_packet_and_packet_set_hash_tampering_fail_closed(tmp_path):
    packet_tampered = _packet_set()
    packet_tampered["packets"][0]["payload"]["active_goal"] = "changed"
    with pytest.raises(ValueError, match="packet payload SHA-256"):
        capture.capture_mechanism_replays(
            packet_tampered,
            output_dir=tmp_path / "packet",
            client_factory=lambda seed: FakeClient(seed),
            seeds=(42,),
        )

    set_tampered = _packet_set()
    set_tampered["packet_set_id"] = "changed"
    with pytest.raises(ValueError, match="packet_set_sha256"):
        capture.capture_mechanism_replays(
            set_tampered,
            output_dir=tmp_path / "set",
            client_factory=lambda seed: FakeClient(seed),
            seeds=(42,),
        )
