import json

import pytest

from evals.hybrid_audit_v1.prompts import (
    AUDIT_SCHEMA,
    build_audit_prompts,
    parse_audit_output,
)


def _a_record():
    return {
        "provenance_id": "A-example-1",
        "tool_name": "read_python_file",
        "arguments": {"path": "example.py"},
        "success": True,
        "content": "LIMIT = 4\n\ndef accept(value):\n    return value\n",
        "error": None,
        "information_class": "absolute",
        "code_verifiable": True,
    }


def test_audit_prompt_contains_only_explicit_a_and_candidate_r():
    system_prompt, user_prompt = build_audit_prompts(
        a_records=[_a_record()],
        candidate_draft="LIMIT이 4이므로 함수가 제한을 집행합니다.",
    )

    assert "A-example-1" in user_prompt
    assert "example.py" in user_prompt
    assert "로컬 모델 초안 R" in user_prompt
    assert '"information_class":"absolute"' in user_prompt
    assert '"code_verifiable":true' in user_prompt
    assert "expected_audit_verdict" not in user_prompt
    assert "historical_reference" not in user_prompt
    assert "active_goal" not in user_prompt
    assert "fixture_memory" not in user_prompt
    assert "사용자 요구를 추측" in system_prompt
    assert AUDIT_SCHEMA["required"] == ["verdict", "reason"]


def test_audit_prompt_rejects_extra_or_malformed_a_fields():
    record = _a_record()
    record["oracle"] = "reject"

    with pytest.raises(ValueError, match="A 기록 필드"):
        build_audit_prompts(
            a_records=[record],
            candidate_draft="후보",
        )


@pytest.mark.parametrize(
    "raw",
    [
        '{"verdict":"permit","reason":"맞음","extra":1}',
        '{"verdict":"approve","reason":"맞음"}',
        '{"verdict":"permit","reason":""}',
        '{"verdict":"permit","verdict":"reject","reason":"중복"}',
        '```json\n{"verdict":"permit","reason":"맞음"}\n```',
    ],
)
def test_parse_audit_output_rejects_noncontract_json(raw):
    with pytest.raises(ValueError):
        parse_audit_output(raw)


def test_parse_audit_output_returns_normalized_contract():
    raw = json.dumps(
        {"verdict": "reject", "reason": "  상수만으로 집행을 증명하지 못함  "},
        ensure_ascii=False,
    )

    assert parse_audit_output(raw) == {
        "verdict": "reject",
        "reason": "상수만으로 집행을 증명하지 못함",
    }
