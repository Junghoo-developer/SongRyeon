"""원본 기억을 에이전트에게 보여주는 시야 가공 규칙을 검사한다."""

import json

import pytest

from knowledge.memory_log import save_knowledge_records
from memory.agent_view import (
    AGENT_VIEW_FIELDS,
    AgentMemoryFloor,
    AgentMemoryFloorError,
    freeze_agent_memory_floor,
    format_agent_memory,
    load_frozen_agent_memory,
    load_agent_memory,
)
from memory.settings import DEFAULT_AGENT_VIEW_CHARACTER_LIMIT
from memory.store import save_information_record


def test_agent_view_shows_only_visible_fields(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    save_information_record(
        "README 읽기",
        "absolute",
        "action",
        "turn-1",
        memory_path,
    )
    save_information_record(
        "다른 작업",
        "relative",
        "user_input",
        "turn-2",
        memory_path,
    )

    agent_memory = load_agent_memory(memory_path, turn_id="turn-1")

    assert agent_memory == [
        {
            "memory_index": 1,
            "information": "README 읽기",
            "information_type": "action",
            "information_class": "absolute",
            "code_verifiable": True,
        }
    ]
    assert tuple(agent_memory[0]) == AGENT_VIEW_FIELDS

    # 감춰진 필드가 사라진 것은 원본 삭제가 아니라 시야 가공의 결과다.
    raw_record = json.loads(
        memory_path.read_text(encoding="utf-8").splitlines()[0]
    )
    assert "information_id" in raw_record
    assert "turn_id" in raw_record
    assert "created_at" in raw_record
    assert "memory_index" not in raw_record


def test_memory_index_keeps_original_line_order_across_hidden_records(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    save_information_record(
        "첫 공개 원자",
        "absolute",
        "action",
        "turn-1",
        memory_path,
    )
    save_information_record(
        "숨긴 감사 원자",
        "absolute",
        "tool_raw_content",
        "turn-1",
        memory_path,
    )
    save_information_record(
        "둘째 공개 원자",
        "relative",
        "reason",
        "turn-1",
        memory_path,
    )

    agent_memory = load_agent_memory(
        memory_path,
        max_characters=100_000,
    )

    assert [record["memory_index"] for record in agent_memory] == [1, 3]
    assert [record["information"] for record in agent_memory] == [
        "첫 공개 원자",
        "둘째 공개 원자",
    ]


def test_agent_view_returns_empty_list_when_file_does_not_exist(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    assert load_agent_memory(memory_path) == []


def test_agent_view_keeps_latest_records_within_character_limit(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    for number in range(1, 4):
        save_information_record(
            f"{number}번 정보",
            "absolute",
            "action",
            "turn-1",
            memory_path,
        )

    all_records = load_agent_memory(
        memory_path,
        max_characters=100_000,
    )
    expected_records = all_records[-2:]
    character_limit = len(format_agent_memory(expected_records))

    limited_records = load_agent_memory(
        memory_path,
        max_characters=character_limit,
    )

    assert limited_records == expected_records
    assert [record["information"] for record in limited_records] == [
        "2번 정보",
        "3번 정보",
    ]
    assert len(format_agent_memory(limited_records)) <= character_limit


def test_agent_view_rejects_an_atom_larger_than_limit(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    save_information_record(
        "아주 긴 정보",
        "relative",
        "user_input",
        "turn-1",
        memory_path,
    )

    with pytest.raises(ValueError):
        load_agent_memory(memory_path, max_characters=1)


def test_agent_view_excludes_knowledge_records(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    save_information_record(
        "README 읽기",
        "absolute",
        "action",
        "turn-1",
        memory_path,
    )
    save_knowledge_records(
        source_type="document",
        path="README.md",
        status="added",
        content_hash="abc123",
        content="검색할 원본" * 1_000,
        memory_path=memory_path,
    )

    agent_memory = load_agent_memory(
        memory_path,
        max_characters=1_000,
    )

    assert [record["information"] for record in agent_memory] == [
        "README 읽기"
    ]


def test_frozen_floor_keeps_its_oldest_atom_after_the_view_grows(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    saved_records = []

    for number in range(1, 11):
        saved_records.append(
            save_information_record(
                f"before-{number}-" + ("x" * 900),
                "absolute",
                "action",
                "turn-before",
                memory_path,
            )
        )

    initial = load_agent_memory(memory_path)
    floor = freeze_agent_memory_floor(memory_path)
    frozen_initial = load_frozen_agent_memory(floor, memory_path)
    initial_information = [
        record["information"]
        for record in initial
    ]

    assert isinstance(floor, AgentMemoryFloor)
    assert frozen_initial == initial
    assert (
        len(format_agent_memory(initial))
        <= DEFAULT_AGENT_VIEW_CHARACTER_LIMIT
    )
    assert initial_information[0] != saved_records[0]["information"]
    expected_anchor = next(
        record["information_id"]
        for record in saved_records
        if record["information"] == initial_information[0]
    )
    assert floor.anchor_information_id == expected_anchor

    appended_information = []

    for number in range(1, 3):
        information = f"after-{number}-" + ("y" * 1_500)
        appended_information.append(information)
        save_information_record(
            information,
            "absolute",
            "action",
            "turn-after",
            memory_path,
        )

    grown = load_frozen_agent_memory(floor, memory_path)
    grown_information = [
        record["information"]
        for record in grown
    ]
    latest_information = [
        record["information"]
        for record in load_agent_memory(memory_path)
    ]

    assert grown_information == initial_information + appended_information
    assert (
        len(format_agent_memory(grown))
        > DEFAULT_AGENT_VIEW_CHARACTER_LIMIT
    )
    assert initial_information[0] not in latest_information
    assert saved_records[0]["information"] not in grown_information


def test_frozen_floor_excludes_hidden_records_before_and_after_freeze(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    save_information_record(
        "VISIBLE_FLOOR",
        "absolute",
        "action",
        "turn-1",
        memory_path,
    )
    hidden_records = []

    for prefix in ("knowledge_", "tool_raw_", "model_raw_"):
        hidden_records.append(
            save_information_record(
                prefix + ("SECRET" * 2_000),
                "absolute",
                prefix + "secret",
                "turn-1",
                memory_path,
            )
        )

    save_information_record(
        "VISIBLE_LATEST",
        "relative",
        "reason",
        "turn-1",
        memory_path,
    )
    floor = freeze_agent_memory_floor(memory_path)

    for prefix in ("knowledge_", "tool_raw_", "model_raw_"):
        save_information_record(
            prefix + ("LATER_SECRET" * 1_000),
            "absolute",
            prefix + "later_secret",
            "turn-1",
            memory_path,
        )

    save_information_record(
        "VISIBLE_AFTER",
        "absolute",
        "action",
        "turn-1",
        memory_path,
    )
    frozen = load_frozen_agent_memory(floor, memory_path)
    rendered = format_agent_memory(frozen)

    assert [record["information"] for record in frozen] == [
        "VISIBLE_FLOOR",
        "VISIBLE_LATEST",
        "VISIBLE_AFTER",
    ]
    assert "SECRET" not in rendered
    assert "LATER_SECRET" not in rendered

    hidden_floor = AgentMemoryFloor(
        hidden_records[0]["information_id"]
    )

    with pytest.raises(AgentMemoryFloorError, match="기준점"):
        load_frozen_agent_memory(hidden_floor, memory_path)


def test_frozen_floor_fails_closed_when_its_anchor_is_invalid(
    tmp_path,
):
    empty_path = tmp_path / "empty.jsonl"
    empty_floor = freeze_agent_memory_floor(empty_path)

    assert empty_floor == AgentMemoryFloor(None)
    assert load_frozen_agent_memory(empty_floor, empty_path) == []

    save_information_record(
        "after-empty-freeze",
        "absolute",
        "action",
        "turn-1",
        empty_path,
    )
    assert [
        record["information"]
        for record in load_frozen_agent_memory(empty_floor, empty_path)
    ] == ["after-empty-freeze"]

    with pytest.raises(AgentMemoryFloorError, match="기준점"):
        load_frozen_agent_memory(
            AgentMemoryFloor("missing-information-id"),
            empty_path,
        )

    duplicate_path = tmp_path / "duplicate.jsonl"
    duplicated_record = save_information_record(
        "duplicate-anchor",
        "absolute",
        "action",
        "turn-1",
        duplicate_path,
    )
    duplicate_floor = freeze_agent_memory_floor(duplicate_path)

    with duplicate_path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(duplicated_record, ensure_ascii=False)
            + "\n"
        )

    with pytest.raises(AgentMemoryFloorError, match="중복"):
        load_frozen_agent_memory(duplicate_floor, duplicate_path)

    corrupt_path = tmp_path / "corrupt.jsonl"
    save_information_record(
        "valid-anchor",
        "absolute",
        "action",
        "turn-1",
        corrupt_path,
    )
    corrupt_floor = freeze_agent_memory_floor(corrupt_path)

    with corrupt_path.open("a", encoding="utf-8") as file:
        file.write('{"broken":\n')

    with pytest.raises(json.JSONDecodeError):
        load_frozen_agent_memory(corrupt_floor, corrupt_path)


def test_a_new_freeze_chooses_a_new_latest_floor(tmp_path):
    memory_path = tmp_path / "memory.jsonl"

    for number in range(1, 11):
        save_information_record(
            f"old-{number}-" + ("x" * 900),
            "absolute",
            "action",
            "turn-old",
            memory_path,
        )

    first_floor = freeze_agent_memory_floor(memory_path)
    first_view = load_frozen_agent_memory(first_floor, memory_path)
    first_oldest = first_view[0]["information"]

    for number in range(1, 4):
        save_information_record(
            f"new-{number}-" + ("y" * 1_200),
            "absolute",
            "action",
            "turn-new",
            memory_path,
        )

    second_floor = freeze_agent_memory_floor(memory_path)
    second_view = load_frozen_agent_memory(second_floor, memory_path)
    second_oldest = second_view[0]["information"]

    assert second_floor != first_floor
    assert first_oldest not in [
        record["information"]
        for record in second_view
    ]
    assert (
        len(format_agent_memory(second_view))
        <= DEFAULT_AGENT_VIEW_CHARACTER_LIMIT
    )

    save_information_record(
        "newest-" + ("z" * 1_500),
        "absolute",
        "action",
        "turn-new",
        memory_path,
    )

    assert load_frozen_agent_memory(
        second_floor,
        memory_path,
    )[0]["information"] == second_oldest
