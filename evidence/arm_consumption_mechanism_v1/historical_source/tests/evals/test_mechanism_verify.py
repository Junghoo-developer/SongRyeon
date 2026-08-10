"""Mechanism verifier가 실제 30×3 capture 계약을 fail-close하는지 검사한다."""

import json

import pytest

from evals import mechanism_capture as capture
from evals.mechanism_packets import write_exact_evidence_packet_set
from evals.mechanism_verify import main, verify_capture
from llm import ModelReply


class _FakeMechanismClient:
    provider = "fake_ollama"
    execution_mode = "test"

    def __init__(self, seed):
        self.seed = seed
        self.model_name = "gemma4:26b"
        self.base_url = "http://127.0.0.1:11434"
        self.num_ctx = 16_384
        self.temperature = 0
        self.timeout_seconds = 180
        self.keep_alive = "10m"

    def check_ready(self):
        return {
            "server_version": "0.32.5",
            "model_name": self.model_name,
            "model_digest": (
                "5571076f3d70050487b26b341705799e"
                "0ab29b808164f90d20d4cf84f699d251"
            ),
        }

    def complete(
        self,
        *,
        system_prompt,
        user_prompt,
        response_schema,
        num_predict,
    ):
        if response_schema == capture.ANSWER_SCHEMA:
            answer = (
                "consumer draft"
                if "각 기록은 검증 범위 안에서만 소비하라" in system_prompt
                else "condition answer"
            )
            content = json.dumps({"answer": answer}, ensure_ascii=False)
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
                    "reason": "근거 범위를 넘어선 주장이다.",
                    "revised_answer": "공개된 근거 범위 안에서만 답한다.",
                },
                ensure_ascii=False,
            )
        return ModelReply(
            content=content,
            thinking="",
            model=self.model_name,
            done_reason="stop",
            metrics={"eval_count": 1},
        )


def test_verify_capture_accepts_full_grid_and_rejects_raw_tampering(tmp_path):
    packet_path = tmp_path / "packets.json"
    _, packet_summary = write_exact_evidence_packet_set(packet_path)
    assert packet_summary["packet_count"] == 30
    assert packet_summary["request_count"] == 32

    capture_path, document = capture.capture_mechanism_replays(
        json.loads(packet_path.read_text(encoding="utf-8")),
        output_dir=tmp_path / "capture",
        client_factory=_FakeMechanismClient,
    )

    result = verify_capture(capture_path, packet_path)
    assert result["independent_confirmatory"] is False
    assert result["unit_count"] == 90
    assert result["evidence_request_count"] == 32
    assert result["answer_call_count"] == 360
    assert result["reviewer_call_count"] == 180
    assert result["model_attempt_count"] == 540

    first = document["raw_artifacts"][0]
    raw_path = capture_path.parent / first["path"]
    raw_path.write_bytes(raw_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw artifact"):
        verify_capture(capture_path, packet_path)


def test_cli_returns_one_for_missing_capture(tmp_path, capsys):
    result = main(
        [
            "--capture",
            str(tmp_path / "missing-capture.json"),
            "--packets",
            str(tmp_path / "missing-packets.json"),
        ]
    )

    assert result == 1
    assert "검증 실패" in capsys.readouterr().err
