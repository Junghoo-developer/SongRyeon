"""공개 대화 기록의 A/R 구분과 임시 로그 저장을 검사한다."""

import json

import pytest

from memory import (
    load_agent_memory,
    save_final_delivery,
    save_node3_answer,
    save_user_input,
)


RAW_FIELDS = {
    "information",
    "information_class",
    "code_verifiable",
    "information_type",
    "turn_id",
    "information_id",
    "created_at",
}


def test_conversation_records_separate_content_from_code_facts(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    user_records = save_user_input(
        "main.py를 확인해 줘.",
        "turn-conversation",
        memory_path,
    )
    answer_records = save_node3_answer(
        "main.py의 VALUE는 1입니다.",
        "turn-conversation",
        memory_path,
    )
    answer_record = next(
        record
        for record in answer_records
        if record["information_type"] == "node3_answer"
    )
    final_records = save_final_delivery(
        answer_record["information_id"],
        "turn-conversation",
        memory_path,
    )

    assert user_records[0]["information"] == "user"
    assert user_records[0]["information_class"] == "absolute"
    assert user_records[1]["information_type"] == "user_input"
    assert user_records[1]["information_class"] == "relative"
    assert answer_record["information_class"] == "relative"
    assert final_records[0]["information"] == "runtime"
    assert json.loads(final_records[1]["information"]) == {
        "answer_information_id": answer_record["information_id"]
    }
    assert final_records[1]["information_class"] == "absolute"

    raw_records = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(raw_records) == 6
    assert all(set(record) == RAW_FIELDS for record in raw_records)
    assert len({record["information_id"] for record in raw_records}) == 6

    visible = load_agent_memory(
        memory_path,
        max_characters=100_000,
    )
    assert [record["information_type"] for record in visible] == [
        "source",
        "user_input",
        "source",
        "node3_answer",
        "source",
        "final_delivery",
    ]


def test_oversized_user_input_is_not_partially_saved(tmp_path):
    memory_path = tmp_path / "memory.jsonl"

    with pytest.raises(ValueError, match="시야 예산"):
        save_user_input(
            "가" * 10_000,
            "turn-large-input",
            memory_path,
        )

    assert not memory_path.exists()


def test_final_delivery_rejects_unknown_or_non_answer_ids(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    user_records = save_user_input(
        "질문",
        "turn-final-source",
        memory_path,
    )

    with pytest.raises(ValueError, match="정확히 일치"):
        save_final_delivery(
            "missing-id",
            "turn-final",
            memory_path,
        )

    with pytest.raises(ValueError, match="Node3 상대정보"):
        save_final_delivery(
            user_records[1]["information_id"],
            "turn-final",
            memory_path,
        )

    raw_records = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(raw_records) == 2


@pytest.mark.parametrize(
    ("function", "value"),
    [
        (save_user_input, ""),
        (save_node3_answer, "   "),
        (save_final_delivery, ""),
    ],
)
def test_conversation_records_reject_empty_primary_values(
    tmp_path,
    function,
    value,
):
    memory_path = tmp_path / "memory.jsonl"

    with pytest.raises(ValueError):
        function(value, "turn-empty", memory_path)

    assert not memory_path.exists()
