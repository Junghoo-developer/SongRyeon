"""실제 도구 행동과 숨김 원문 기록을 검사한다."""

import pytest

from memory.agent_view import load_agent_memory
from memory.tool_records import save_tool_observation


def test_tool_raw_text_is_exactly_stored_but_hidden_from_agent_view(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_text = "print('한글🙂')\r\nVALUE = 1\n"

    records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "main.py"},
        success=True,
        content=raw_text,
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="tool-turn-1",
        memory_path=memory_path,
    )

    raw_content = next(
        record
        for record in records
        if record["information_type"] == "tool_raw_content"
    )
    assert raw_content["information"] == raw_text
    assert raw_content["information_class"] == "absolute"
    assert raw_content["code_verifiable"] is True

    visible_types = {
        record["information_type"]
        for record in load_agent_memory(
            memory_path,
            max_characters=100_000,
        )
    }
    assert visible_types == {
        "source",
        "action",
        "tool_status",
        "tool_use_count",
    }
    assert not any(
        information_type.startswith("tool_raw_")
        for information_type in visible_types
    )


def test_oversized_visible_tool_arguments_are_not_partially_saved(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"

    with pytest.raises(ValueError, match="시야 예산"):
        save_tool_observation(
            tool_name="read_python_file",
            arguments={"path": "x" * 10_000},
            success=False,
            content="",
            error="잘못된 경로",
            source_node="node1",
            round_number=1,
            attempt_number=1,
            maximum_attempts=3,
            turn_id="oversized-action",
            memory_path=memory_path,
        )

    assert not memory_path.exists()
