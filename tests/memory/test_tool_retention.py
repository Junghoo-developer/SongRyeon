"""Node1 보존 요청과 코드가 복사한 공개 본문 기록을 검사한다."""

import json

import pytest

from memory.agent_view import load_agent_memory
from memory.tool_records import (
    save_node1_omit_recovery,
    save_node1_retention,
    save_tool_observation,
)
from nodes import RetentionDecision, build_text_chunks


def _load_raw_records(memory_path):
    return [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]


def test_excerpt_records_relative_request_and_exact_absolute_copy(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_text = "앞부분\r\n선택할 부분🙂\n뒷부분"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "main.py"},
        success=True,
        content=raw_text,
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="tool-turn-2",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )
    start = raw_text.index("선택할")
    end = raw_text.index("뒷부분")
    selected = raw_text[start:end]

    selected_result, selection_records = save_node1_retention(
        decision=RetentionDecision(
            mode="excerpt",
            review="선택한 부분이 현재 질문과 관련 있다.",
            start=start,
            end=end,
        ),
        source_information_id=source_record["information_id"],
        turn_id="tool-turn-2",
        memory_path=memory_path,
    )
    records_by_type = {
        record["information_type"]: record
        for record in selection_records
    }

    assert records_by_type["node1_tool_review"]["information_class"] == (
        "relative"
    )
    assert records_by_type["node1_retention_request"][
        "code_verifiable"
    ] is False
    assert records_by_type["tool_retention_applied"][
        "code_verifiable"
    ] is True
    assert selected_result == selected
    assert records_by_type["tool_result_content"]["information"] == selected
    assert records_by_type["tool_result_content"][
        "information_class"
    ] == "absolute"

    applied = json.loads(
        records_by_type["tool_retention_applied"]["information"]
    )
    assert applied == {
        "arguments": {"path": "main.py"},
        "end": end,
        "mode": "excerpt",
        "start": start,
        "tool_name": "read_python_file",
    }
    assert {
        record["turn_id"]
        for record in raw_records + selection_records
    } == {"tool-turn-2"}
    visible_json = json.dumps(
        load_agent_memory(
            memory_path,
            max_characters=100_000,
        ),
        ensure_ascii=False,
    )
    assert source_record["information_id"] not in visible_json


def test_chunk_id_is_relative_but_applied_range_and_copy_are_absolute(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_text = "".join(
        f"LINE_{index:04d} = {index}\n"
        for index in range(500)
    )
    chunks = build_text_chunks(raw_text)
    selected_chunk = chunks[1]
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "long.py"},
        success=True,
        content=raw_text,
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="chunk-tool-turn",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )

    selected, records = save_node1_retention(
        decision=RetentionDecision(
            mode="chunk",
            review="둘째 청크가 사용자 요청과 직접 관련 있다.",
            chunk_id=selected_chunk.chunk_id,
        ),
        source_information_id=source_record["information_id"],
        turn_id="chunk-tool-turn",
        memory_path=memory_path,
    )
    by_type = {
        record["information_type"]: record
        for record in records
    }
    requested = json.loads(
        by_type["node1_retention_request"]["information"]
    )
    applied = json.loads(
        by_type["tool_retention_applied"]["information"]
    )

    assert selected == selected_chunk.content
    assert requested == {
        "chunk_id": selected_chunk.chunk_id,
        "mode": "chunk",
    }
    assert by_type["node1_retention_request"]["information_class"] == (
        "relative"
    )
    assert applied["chunk_id"] == selected_chunk.chunk_id
    assert applied["start"] == selected_chunk.start
    assert applied["end"] == selected_chunk.end
    assert by_type["tool_retention_applied"]["information_class"] == (
        "absolute"
    )
    assert by_type["tool_result_content"]["information"] == (
        raw_text[selected_chunk.start:selected_chunk.end]
    )


def test_omit_does_not_create_a_visible_content_record(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "unused.py"},
        success=True,
        content="UNUSED = True\n",
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="tool-turn-3",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )

    selected, records = save_node1_retention(
        decision=RetentionDecision(
            mode="omit",
            review="관련 없는 결과다.",
        ),
        source_information_id=source_record["information_id"],
        turn_id="tool-turn-3",
        memory_path=memory_path,
    )

    assert selected is None
    assert "tool_result_content" not in {
        record["information_type"]
        for record in records
    }


def test_visible_budget_failure_writes_no_partial_selection_records(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "large.py"},
        success=True,
        content="가" * 10_000,
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="tool-turn-4",
        memory_path=memory_path,
    )
    original_lines = len(_load_raw_records(memory_path))
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )

    with pytest.raises(ValueError, match="시야 예산"):
        save_node1_retention(
            decision=RetentionDecision(
                mode="full",
                review="전체를 공개하려 했다.",
            ),
            source_information_id=source_record["information_id"],
            turn_id="tool-turn-4",
            memory_path=memory_path,
        )

    assert len(_load_raw_records(memory_path)) == original_lines
    assert "가" * 100 not in json.dumps(
        load_agent_memory(
            memory_path,
            max_characters=100_000,
        ),
        ensure_ascii=False,
    )


def test_retention_requires_a_matching_saved_raw_source(tmp_path):
    memory_path = tmp_path / "memory.jsonl"

    with pytest.raises(ValueError, match="기억 로그"):
        save_node1_retention(
            decision=RetentionDecision(
                mode="omit",
                review="원문이 없는 가짜 선택이다.",
            ),
            source_information_id="missing-source",
            turn_id="missing-turn",
            memory_path=memory_path,
        )

    assert not memory_path.exists()


def test_retention_rejects_a_source_from_another_turn(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "main.py"},
        success=True,
        content="VALUE = 1\n",
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="real-tool-turn",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )

    with pytest.raises(ValueError, match="turn_id"):
        save_node1_retention(
            decision=RetentionDecision(
                mode="full",
                review="다른 턴의 원문을 사용하려 했다.",
            ),
            source_information_id=source_record["information_id"],
            turn_id="wrong-tool-turn",
            memory_path=memory_path,
        )


def test_same_tool_result_cannot_receive_two_retention_decisions(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "main.py"},
        success=True,
        content="VALUE = 1\n",
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="duplicate-tool-turn",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )
    decision = RetentionDecision(
        mode="omit",
        review="본문은 필요하지 않다.",
    )

    save_node1_retention(
        decision=decision,
        source_information_id=source_record["information_id"],
        turn_id="duplicate-tool-turn",
        memory_path=memory_path,
    )
    lines_after_first = len(_load_raw_records(memory_path))

    with pytest.raises(ValueError, match="이미"):
        save_node1_retention(
            decision=decision,
            source_information_id=source_record["information_id"],
            turn_id="duplicate-tool-turn",
            memory_path=memory_path,
        )

    assert len(_load_raw_records(memory_path)) == lines_after_first


def test_omit_recovery_appends_exact_content_without_overwriting_history(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_text = "FIRST\nSECOND\nTHIRD\n"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "main.py"},
        success=True,
        content=raw_text,
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="omit-recovery-turn",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )
    save_node1_retention(
        decision=RetentionDecision(
            mode="omit",
            review="처음에는 원문을 생략했다.",
        ),
        source_information_id=source_record["information_id"],
        turn_id="omit-recovery-turn",
        memory_path=memory_path,
    )
    before_recovery = memory_path.read_bytes()
    start = raw_text.index("SECOND")
    end = raw_text.index("THIRD")

    selected, recovery_records = save_node1_omit_recovery(
        decision=RetentionDecision(
            mode="excerpt",
            review="둘째 줄을 후속 검증용 A로 복구한다.",
            start=start,
            end=end,
        ),
        candidate_number=1,
        source_information_id=source_record["information_id"],
        turn_id="omit-recovery-turn",
        memory_path=memory_path,
    )

    assert selected == "SECOND\n"
    assert memory_path.read_bytes().startswith(before_recovery)
    assert next(
        record
        for record in recovery_records
        if record["information_type"] == "tool_result_content"
    )["information"] == "SECOND\n"

    all_records = _load_raw_records(memory_path)
    initial_request = json.loads(
        next(
            record
            for record in all_records
            if record["information_type"] == "node1_retention_request"
        )["information"]
    )
    recovered_request = json.loads(
        next(
            record
            for record in all_records
            if record["information_type"] == "node1_omit_recovery_request"
        )["information"]
    )
    applied = json.loads(
        next(
            record
            for record in all_records
            if record["information_type"] == "tool_omit_recovery_applied"
        )["information"]
    )

    assert initial_request == {
        "end": None,
        "mode": "omit",
        "start": None,
    }
    assert recovered_request == {
        "candidate_number": 1,
        "end": end,
        "mode": "excerpt",
        "start": start,
    }
    assert applied["previous_mode"] == "omit"
    assert applied["tool_name"] == "read_python_file"


def test_omit_recovery_rejects_second_use_and_non_omit_source(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "main.py"},
        success=True,
        content="VALUE = 1\n",
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="single-recovery-turn",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )
    save_node1_retention(
        decision=RetentionDecision(
            mode="omit",
            review="최초 선택은 omit이다.",
        ),
        source_information_id=source_record["information_id"],
        turn_id="single-recovery-turn",
        memory_path=memory_path,
    )
    recovery = RetentionDecision(
        mode="full",
        review="한 번만 전체를 복구한다.",
    )
    save_node1_omit_recovery(
        decision=recovery,
        candidate_number=1,
        source_information_id=source_record["information_id"],
        turn_id="single-recovery-turn",
        memory_path=memory_path,
    )
    lines_after_recovery = len(_load_raw_records(memory_path))

    with pytest.raises(ValueError, match="이미 omit 복구"):
        save_node1_omit_recovery(
            decision=recovery,
            candidate_number=1,
            source_information_id=source_record["information_id"],
            turn_id="single-recovery-turn",
            memory_path=memory_path,
        )

    assert len(_load_raw_records(memory_path)) == lines_after_recovery

    other_memory = tmp_path / "non-omit.jsonl"
    other_raw = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "kept.py"},
        success=True,
        content="KEPT = True\n",
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="non-omit-turn",
        memory_path=other_memory,
    )
    other_source = next(
        record
        for record in other_raw
        if record["information_type"] == "tool_raw_content"
    )
    save_node1_retention(
        decision=RetentionDecision(
            mode="full",
            review="처음부터 전체를 보존했다.",
        ),
        source_information_id=other_source["information_id"],
        turn_id="non-omit-turn",
        memory_path=other_memory,
    )
    before_invalid_recovery = other_memory.read_bytes()

    with pytest.raises(ValueError, match="정확한 omit"):
        save_node1_omit_recovery(
            decision=RetentionDecision(
                mode="full",
                review="이미 보존된 결과를 복구하려 한다.",
            ),
            candidate_number=1,
            source_information_id=other_source["information_id"],
            turn_id="non-omit-turn",
            memory_path=other_memory,
        )

    assert other_memory.read_bytes() == before_invalid_recovery


def test_omit_recovery_budget_failure_appends_no_partial_records(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_records = save_tool_observation(
        tool_name="read_python_file",
        arguments={"path": "large.py"},
        success=True,
        content="가" * 10_000,
        error=None,
        source_node="node1",
        round_number=1,
        attempt_number=1,
        maximum_attempts=3,
        turn_id="large-recovery-turn",
        memory_path=memory_path,
    )
    source_record = next(
        record
        for record in raw_records
        if record["information_type"] == "tool_raw_content"
    )
    save_node1_retention(
        decision=RetentionDecision(
            mode="omit",
            review="큰 원문을 처음에는 생략했다.",
        ),
        source_information_id=source_record["information_id"],
        turn_id="large-recovery-turn",
        memory_path=memory_path,
    )
    before_recovery = memory_path.read_bytes()

    with pytest.raises(ValueError, match="시야 예산"):
        save_node1_omit_recovery(
            decision=RetentionDecision(
                mode="full",
                review="너무 큰 원문 전체를 복구하려 한다.",
            ),
            candidate_number=1,
            source_information_id=source_record["information_id"],
            turn_id="large-recovery-turn",
            memory_path=memory_path,
        )

    assert memory_path.read_bytes() == before_recovery
