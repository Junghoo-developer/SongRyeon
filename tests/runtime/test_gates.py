"""Node2·Node4의 독립적인 반려 3회와 로그 적용을 검사한다."""

import json

import pytest

import runtime.gates as gates
from agent_tools import LIST_PYTHON_FILES, ToolResult
from memory.agent_view import load_agent_memory
from nodes import ReviewDecision
from runtime import (
    FINAL,
    NODE1,
    NODE2,
    NODE3,
    NODE4,
    apply_gate_decision,
    create_turn_state,
    execute_node1_tool,
)


def test_node2_first_three_rejects_start_new_node1_rounds(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-node2")

    for expected_rejections in range(1, 4):
        state.node1_tool_calls_in_round = 3
        resolution = apply_gate_decision(
            state,
            NODE2,
            ReviewDecision("reject", "자료를 하나 더 확인해야 한다."),
            memory_path,
        )

        assert resolution.next_node == NODE1
        assert resolution.rejection_count == expected_rejections
        assert resolution.rejection_ignored is False
        assert state.node1_tool_calls_in_round == 0
        assert state.node1_round == expected_rejections + 1

    fourth = apply_gate_decision(
        state,
        NODE2,
        ReviewDecision("reject", "그래도 부족하다고 판단했다."),
        memory_path,
    )

    assert fourth.next_node == NODE3
    assert fourth.rejection_count == 3
    assert fourth.rejection_ignored is True
    assert state.node1_round == 4


def test_node2_permit_advances_without_a_rejection(tmp_path):
    state = create_turn_state("turn-node2-permit")

    resolution = apply_gate_decision(
        state,
        NODE2,
        ReviewDecision("permit", "답변에 필요한 근거가 충분하다."),
        tmp_path / "memory.jsonl",
    )

    assert resolution.next_node == NODE3
    assert resolution.outcome == "permit_applied"
    assert state.node2_rejections == 0


def test_node4_counter_is_independent_and_fourth_reject_finishes(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-node4")
    state.node2_rejections = 2

    for expected_rejections in range(1, 4):
        resolution = apply_gate_decision(
            state,
            NODE4,
            ReviewDecision("reject", "답변이 로그와 충돌한다."),
            memory_path,
        )
        assert resolution.next_node == NODE3
        assert resolution.rejection_count == expected_rejections

    fourth = apply_gate_decision(
        state,
        NODE4,
        ReviewDecision("reject", "여전히 충돌한다고 판단했다."),
        memory_path,
    )

    assert fourth.next_node == FINAL
    assert fourth.outcome == "reject_ignored_limit"
    assert fourth.rejection_ignored is True
    assert state.node4_rejections == 3
    assert state.node2_rejections == 2


def test_gate_log_separates_relative_judgement_from_absolute_action(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-gate-log")

    apply_gate_decision(
        state,
        NODE2,
        ReviewDecision("reject", "확인한 파일이 부족하다."),
        memory_path,
    )
    visible = load_agent_memory(
        memory_path,
        max_characters=100_000,
    )
    by_type = {
        record["information_type"]: record
        for record in visible
    }

    assert by_type["decision"]["information"] == "reject"
    assert by_type["decision"]["information_class"] == "relative"
    assert by_type["reason"]["code_verifiable"] is False
    assert by_type["action"]["information_class"] == "absolute"
    action = json.loads(by_type["action"]["information"])
    assert action["next_node"] == NODE1
    assert action["outcome"] == "reject_applied"


def test_gate_log_failure_does_not_change_state(tmp_path, monkeypatch):
    state = create_turn_state("turn-log-failure")
    state.node1_tool_calls_in_round = 2

    def fail_to_save(**kwargs):
        raise OSError("로그 저장 실패")

    monkeypatch.setattr(gates, "save_gate_review", fail_to_save)

    with pytest.raises(OSError, match="로그 저장 실패"):
        apply_gate_decision(
            state,
            NODE2,
            ReviewDecision("reject", "보완이 필요하다."),
            tmp_path / "memory.jsonl",
        )

    assert state.node2_rejections == 0
    assert state.node1_round == 1
    assert state.node1_tool_calls_in_round == 2


def test_three_node2_rejects_allow_at_most_twelve_tool_calls(
    tmp_path,
):
    class FakeToolbox:
        def __init__(self):
            self.calls = 0

        def execute(self, tool_name, arguments):
            self.calls += 1
            return ToolResult(
                tool_name=tool_name,
                arguments=arguments,
                success=True,
                content="",
            )

    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-maximum-tools")
    toolbox = FakeToolbox()

    for round_number in range(1, 5):
        assert state.node1_round == round_number

        for _ in range(3):
            execute_node1_tool(
                state,
                toolbox,
                LIST_PYTHON_FILES,
                {},
                memory_path,
            )

        resolution = apply_gate_decision(
            state,
            NODE2,
            ReviewDecision("reject", "한 번 더 보완한다."),
            memory_path,
        )

        if round_number < 4:
            assert resolution.next_node == NODE1
        else:
            assert resolution.next_node == NODE3
            assert resolution.rejection_ignored is True

    assert toolbox.calls == 12
