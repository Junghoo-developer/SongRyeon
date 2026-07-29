"""모델 원시 교환 기록의 A/R 분류와 시야 숨김을 검사한다."""

import json

import pytest

from memory.agent_view import load_agent_memory
from memory.model_records import save_model_exchange
from memory.settings import MODEL_RAW_INFORMATION_TYPE_PREFIX


def test_model_exchange_is_exactly_recorded_and_hidden(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    system_prompt = "너는 Node1이다.\nA와 R을 구분한다."
    user_prompt = '{"information":"파일을 읽어라"}'
    response = '{"action":"route_node2","reason":"충분하다"}'
    thinking = "확인한 근거를 비교했다."
    metrics = {
        "eval_count": 12,
        "nested": {"done": True},
        "prompt_eval_count": 34,
    }

    records = save_model_exchange(
        node_name="node1",
        model_name="qwen3:14b",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response=response,
        thinking=thinking,
        status="valid",
        attempt=2,
        validation_error=None,
        metrics=metrics,
        turn_id="turn-model-1",
        memory_path=memory_path,
    )
    by_type = {
        record["information_type"]: record
        for record in records
    }

    assert len(records) == 10
    assert all(
        record["information_type"].startswith(
            MODEL_RAW_INFORMATION_TYPE_PREFIX
        )
        for record in records
    )
    for information_type in {
        "model_raw_system_prompt",
        "model_raw_user_prompt",
        "model_raw_response",
        "model_raw_thinking",
    }:
        assert by_type[information_type]["information_class"] == "relative"
        assert by_type[information_type]["code_verifiable"] is False

    for information_type in {
        "model_raw_node",
        "model_raw_model",
        "model_raw_status",
        "model_raw_attempt",
        "model_raw_validation_error",
        "model_raw_metrics",
    }:
        assert by_type[information_type]["information_class"] == "absolute"
        assert by_type[information_type]["code_verifiable"] is True

    assert by_type["model_raw_system_prompt"]["information"] == system_prompt
    assert by_type["model_raw_user_prompt"]["information"] == user_prompt
    assert by_type["model_raw_response"]["information"] == response
    assert by_type["model_raw_thinking"]["information"] == thinking
    assert json.loads(by_type["model_raw_attempt"]["information"]) == {
        "attempt": 2
    }
    assert json.loads(by_type["model_raw_metrics"]["information"]) == metrics
    assert by_type["model_raw_validation_error"]["information"] == ""
    assert load_agent_memory(
        memory_path,
        max_characters=100_000,
    ) == []


def test_model_exchange_accepts_absent_thinking(tmp_path):
    memory_path = tmp_path / "memory.jsonl"

    records = save_model_exchange(
        node_name="node3",
        model_name="qwen3:14b",
        system_prompt="답변하라.",
        user_prompt="질문",
        response="답변",
        thinking=None,
        status="valid",
        attempt=1,
        validation_error="",
        metrics={},
        turn_id="turn-no-thinking",
        memory_path=memory_path,
    )

    thinking_record = next(
        record
        for record in records
        if record["information_type"] == "model_raw_thinking"
    )
    assert thinking_record["information"] == ""


@pytest.mark.parametrize("attempt", [0, -1, True, 1.5])
def test_invalid_attempt_is_not_saved(tmp_path, attempt):
    memory_path = tmp_path / "memory.jsonl"

    with pytest.raises(ValueError, match="attempt"):
        save_model_exchange(
            node_name="node2",
            model_name="qwen3:14b",
            system_prompt="검사하라.",
            user_prompt="기억",
            response="{}",
            thinking="",
            status="invalid",
            attempt=attempt,
            validation_error="형식 오류",
            metrics={},
            turn_id="turn-invalid-attempt",
            memory_path=memory_path,
        )

    assert not memory_path.exists()


def test_non_json_metrics_are_not_partially_saved(tmp_path):
    memory_path = tmp_path / "memory.jsonl"

    with pytest.raises(ValueError, match="정렬 가능한 일반 JSON"):
        save_model_exchange(
            node_name="node4",
            model_name="qwen3:14b",
            system_prompt="대조하라.",
            user_prompt="기억",
            response="{}",
            thinking="",
            status="invalid",
            attempt=1,
            validation_error="",
            metrics={"bad": float("nan")},
            turn_id="turn-invalid-metrics",
            memory_path=memory_path,
        )

    assert not memory_path.exists()
