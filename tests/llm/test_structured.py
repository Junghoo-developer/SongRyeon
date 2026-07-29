"""엄격한 JSON 검증, 제한 재시도와 모델 원문 감사를 검사한다."""

import json

import pytest

from llm import ModelReply
from llm.structured import (
    NodeOutputError,
    parse_strict_json_object,
    request_structured_output,
)
from memory.agent_view import load_agent_memory
from nodes import REVIEW_DECISION_SCHEMA, parse_review_decision


class ScriptedClient:
    """실제 HTTP 없이 응답 문자열이나 전송 예외를 순서대로 반환한다."""

    model_name = "fake-qwen:14b"

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def complete(
        self,
        *,
        system_prompt,
        user_prompt,
        response_schema,
        num_predict,
    ):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "num_predict": num_predict,
            }
        )
        outcome = self.outcomes.pop(0)

        if isinstance(outcome, BaseException):
            raise outcome

        return ModelReply(
            content=outcome,
            thinking="검증 가능한 JSON을 작성했다.",
            model=self.model_name,
            done_reason="stop",
            metrics={"eval_count": 7},
        )


def _raw_records(memory_path):
    return [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]


def _request(client, memory_path, **overrides):
    arguments = {
        "client": client,
        "node_name": "node2",
        "system_prompt": "너는 Node2다.",
        "user_prompt": "현재 증거를 검토하라.",
        "response_schema": REVIEW_DECISION_SCHEMA,
        "parser": parse_review_decision,
        "num_predict": 256,
        "turn_id": "turn-structured",
        "memory_path": memory_path,
    }
    arguments.update(overrides)
    return request_structured_output(**arguments)


@pytest.mark.parametrize(
    "raw_response",
    [
        '{"verdict":"permit","verdict":"reject","reason":"중복"}',
        '{"verdict":NaN,"reason":"표준 JSON 아님"}',
        '설명문 {"verdict":"permit","reason":"충분"}',
        '```json\n{"verdict":"permit","reason":"충분"}\n```',
    ],
)
def test_strict_json_rejects_duplicates_constants_and_prose(raw_response):
    with pytest.raises(ValueError, match="엄격한 JSON 객체"):
        parse_strict_json_object(raw_response)


def test_invalid_output_is_audited_then_retried_without_guessing(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    client = ScriptedClient(
        [
            '{"verdict":"approve","reason":"허용되지 않은 단어"}',
            '{"verdict":"permit","reason":"증거가 충분하다."}',
        ]
    )

    decision = _request(client, memory_path)

    assert decision.verdict == "permit"
    assert len(client.calls) == 2
    assert client.calls[0]["user_prompt"] == "현재 증거를 검토하라."
    assert "[직전 출력 검증 실패]" in client.calls[1]["user_prompt"]
    assert "현재 증거를 검토하라." in client.calls[1]["user_prompt"]

    raw = _raw_records(memory_path)
    statuses = [
        record["information"]
        for record in raw
        if record["information_type"] == "model_raw_status"
    ]
    attempts = [
        json.loads(record["information"])["attempt"]
        for record in raw
        if record["information_type"] == "model_raw_attempt"
    ]
    responses = [
        record
        for record in raw
        if record["information_type"] == "model_raw_response"
    ]
    validation_errors = [
        record
        for record in raw
        if record["information_type"] == "model_raw_validation_error"
    ]

    assert statuses == ["invalid", "valid"]
    assert attempts == [1, 2]
    assert all(
        record["information_class"] == "relative"
        for record in responses
    )
    assert validation_errors[0]["information"]
    assert validation_errors[0]["information_class"] == "absolute"
    assert validation_errors[1]["information"] == ""
    assert load_agent_memory(
        memory_path,
        max_characters=100_000,
    ) == []


def test_retry_exhaustion_is_explicit_and_all_attempts_are_audited(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    client = ScriptedClient(["{}", "[]", "JSON 아님"])

    with pytest.raises(NodeOutputError, match="3회"):
        _request(client, memory_path)

    assert len(client.calls) == 3
    raw = _raw_records(memory_path)
    assert [
        record["information"]
        for record in raw
        if record["information_type"] == "model_raw_status"
    ] == ["invalid", "invalid", "invalid"]
    assert [
        json.loads(record["information"])["attempt"]
        for record in raw
        if record["information_type"] == "model_raw_attempt"
    ] == [1, 2, 3]


def test_transport_error_is_audited_once_and_not_retried(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    transport_error = ConnectionError("local Ollama is offline")
    client = ScriptedClient(
        [
            transport_error,
            '{"verdict":"permit","reason":"호출되면 안 됨"}',
        ]
    )

    with pytest.raises(ConnectionError, match="offline"):
        _request(client, memory_path)

    assert len(client.calls) == 1
    raw = _raw_records(memory_path)
    status = next(
        record
        for record in raw
        if record["information_type"] == "model_raw_status"
    )
    error = next(
        record
        for record in raw
        if record["information_type"] == "model_raw_validation_error"
    )
    assert status["information"] == "transport_error"
    assert status["information_class"] == "absolute"
    assert error["information"] == "MODEL_TRANSPORT_ERROR"
    assert "offline" not in error["information"]


def test_client_execution_identity_is_audited_as_absolute(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    client = ScriptedClient(
        ['{"verdict":"permit","reason":"증거가 충분하다."}']
    )
    client.provider = "openai_compatible"
    client.execution_mode = "external_api_integration"

    _request(client, memory_path)

    raw = _raw_records(memory_path)
    provider = next(
        record
        for record in raw
        if record["information_type"] == "model_raw_provider"
    )
    execution_mode = next(
        record
        for record in raw
        if record["information_type"] == "model_raw_execution_mode"
    )
    assert provider["information"] == "openai_compatible"
    assert execution_mode["information"] == "external_api_integration"
    assert provider["information_class"] == "absolute"
    assert execution_mode["information_class"] == "absolute"
