"""Node1 도구 3회 제한과 정확한 본문 선택 흐름을 검사한다."""

import json

import pytest

import runtime.tool_flow as tool_flow
import runtime.retention_recovery as retention_recovery
from agent_tools import (
    LIST_PYTHON_FILES,
    READ_PYTHON_FILE,
    FileToolbox,
)
from nodes import Node1Action, RetentionDecision, ReviewDecision
from runtime import (
    NODE2,
    OmittedToolCandidate,
    ToolCallLimitExceeded,
    apply_gate_decision,
    begin_node1_omit_recovery,
    create_turn_state,
    execute_node1_tool,
    retain_node1_tool_result,
    recover_node1_omitted_result,
    route_after_node1,
    should_recover_omitted_results,
)


def _make_toolbox(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    raw_content = "FIRST = 1\r\nSECOND = 2\n"
    (project / "main.py").write_bytes(raw_content.encode("utf-8"))
    return FileToolbox(project), raw_content


def test_failed_and_successful_tools_share_the_same_three_call_budget(
    tmp_path,
):
    toolbox, _ = _make_toolbox(tmp_path)
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-tool-budget")

    failed = execute_node1_tool(
        state,
        toolbox,
        "unknown_tool",
        {},
        memory_path,
    )
    execute_node1_tool(
        state,
        toolbox,
        LIST_PYTHON_FILES,
        {},
        memory_path,
    )
    execute_node1_tool(
        state,
        toolbox,
        READ_PYTHON_FILE,
        {"path": "main.py"},
        memory_path,
    )

    assert failed.result.success is False
    assert state.node1_tool_calls_in_round == 3
    route = route_after_node1(
        state,
        Node1Action(
            action="use_tool",
            reason="다른 파일도 확인하려 했다.",
            tool_name=LIST_PYTHON_FILES,
            arguments={},
        ),
        memory_path,
    )
    assert route.next_node == NODE2
    assert route.forced_by_tool_limit is True

    with pytest.raises(ToolCallLimitExceeded):
        execute_node1_tool(
            state,
            toolbox,
            LIST_PYTHON_FILES,
            {},
            memory_path,
        )


def test_node1_excerpt_is_copied_from_the_transient_tool_result(
    tmp_path,
):
    toolbox, raw_content = _make_toolbox(tmp_path)
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-retention")
    observation = execute_node1_tool(
        state,
        toolbox,
        READ_PYTHON_FILE,
        {"path": "main.py"},
        memory_path,
    )
    start = raw_content.index("SECOND")
    decision = RetentionDecision(
        mode="excerpt",
        review="두 번째 상수만 현재 질문과 관련 있다.",
        start=start,
        end=len(raw_content),
    )

    selected, records = retain_node1_tool_result(
        observation,
        decision,
        memory_path,
    )

    assert selected == raw_content[start:]
    selected_record = next(
        record
        for record in records
        if record["information_type"] == "tool_result_content"
    )
    assert selected_record["information"] == raw_content[start:]


def test_node1_route_request_and_applied_route_are_both_logged(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-node1-route")
    action = Node1Action(
        action="use_tool",
        reason="실제 코드를 열람해야 한다.",
        tool_name=READ_PYTHON_FILE,
        arguments={"path": "main.py"},
    )

    resolution = route_after_node1(
        state,
        action,
        memory_path,
    )

    assert resolution.next_node != NODE2
    assert resolution.outcome == "tool_request_allowed"

    records = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]
    by_type = {
        record["information_type"]: record
        for record in records
    }
    assert by_type["node1_next_action"]["information_class"] == "relative"
    assert by_type["reason"]["code_verifiable"] is False
    assert by_type["runtime_route"]["information_class"] == "absolute"


def test_same_tool_request_is_blocked_for_the_whole_turn(tmp_path):
    toolbox, _ = _make_toolbox(tmp_path)
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-duplicate-tool")
    repeated_action = Node1Action(
        action="use_tool",
        reason="같은 목록을 다시 요청했다.",
        tool_name=LIST_PYTHON_FILES,
        arguments={},
    )

    execute_node1_tool(
        state,
        toolbox,
        LIST_PYTHON_FILES,
        {},
        memory_path,
    )
    first_resolution = route_after_node1(
        state,
        repeated_action,
        memory_path,
    )

    assert first_resolution.next_node == NODE2
    assert first_resolution.outcome == "tool_request_blocked_duplicate"
    assert state.node1_tool_calls_in_round == 1

    apply_gate_decision(
        state,
        NODE2,
        ReviewDecision(
            verdict="reject",
            reason="다른 파일의 근거가 더 필요하다.",
        ),
        memory_path,
    )
    second_resolution = route_after_node1(
        state,
        repeated_action,
        memory_path,
    )

    assert state.node1_round == 2
    assert state.node1_tool_calls_in_round == 0
    assert second_resolution.next_node == NODE2
    assert second_resolution.outcome == "tool_request_blocked_duplicate"


def test_same_tool_with_different_arguments_is_not_a_duplicate(tmp_path):
    toolbox, _ = _make_toolbox(tmp_path)
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-different-tool-arguments")

    execute_node1_tool(
        state,
        toolbox,
        READ_PYTHON_FILE,
        {"path": "main.py"},
        memory_path,
    )
    resolution = route_after_node1(
        state,
        Node1Action(
            action="use_tool",
            reason="다른 파일을 읽는다.",
            tool_name=READ_PYTHON_FILE,
            arguments={"path": "other.py"},
        ),
        memory_path,
    )

    assert resolution.next_node != NODE2
    assert resolution.outcome == "tool_request_allowed"


def test_turn_tool_limit_blocks_a_new_request_after_round_reset(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-total-tool-limit")
    action = Node1Action(
        action="use_tool",
        reason="다음 파일을 읽는다.",
        tool_name=READ_PYTHON_FILE,
        arguments={"path": "other.py"},
    )

    resolution = route_after_node1(
        state,
        action,
        memory_path,
        total_tool_calls=3,
        maximum_total_tool_calls=3,
    )

    assert resolution.next_node == NODE2
    assert resolution.outcome == "tool_request_blocked_total_limit"
    assert resolution.forced_by_tool_limit is True

    route_record = next(
        record
        for record in (
            json.loads(line)
            for line in memory_path.read_text(encoding="utf-8").splitlines()
        )
        if record["information_type"] == "runtime_route"
    )
    assert json.loads(route_record["information"])["outcome"] == (
        "tool_request_blocked_total_limit"
    )


def test_retention_cannot_be_written_to_a_different_memory_log(
    tmp_path,
):
    toolbox, _ = _make_toolbox(tmp_path)
    original_memory = tmp_path / "original.jsonl"
    other_memory = tmp_path / "other.jsonl"
    state = create_turn_state("turn-memory-boundary")
    observation = execute_node1_tool(
        state,
        toolbox,
        READ_PYTHON_FILE,
        {"path": "main.py"},
        original_memory,
    )

    with pytest.raises(ValueError, match="로그가 다릅니다"):
        retain_node1_tool_result(
            observation,
            RetentionDecision(
                mode="omit",
                review="다른 로그에 쓰면 안 된다.",
            ),
            other_memory,
        )

    assert not other_memory.exists()


def test_tool_log_failure_does_not_change_the_counter(
    tmp_path,
    monkeypatch,
):
    toolbox, _ = _make_toolbox(tmp_path)
    state = create_turn_state("turn-tool-log-failure")

    def fail_to_save(**kwargs):
        raise OSError("도구 로그 저장 실패")

    monkeypatch.setattr(
        tool_flow,
        "save_tool_observation",
        fail_to_save,
    )

    with pytest.raises(OSError, match="도구 로그 저장 실패"):
        execute_node1_tool(
            state,
            toolbox,
            LIST_PYTHON_FILES,
            {},
            tmp_path / "memory.jsonl",
        )

    assert state.node1_tool_calls_in_round == 0


def test_omit_recovery_does_not_reexecute_or_increment_tool_budget(
    tmp_path,
):
    toolbox, raw_content = _make_toolbox(tmp_path)
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-omit-recovery")
    observation = execute_node1_tool(
        state,
        toolbox,
        READ_PYTHON_FILE,
        {"path": "main.py"},
        memory_path,
    )
    omit = RetentionDecision(
        mode="omit",
        review="처음에는 원문을 생략했다.",
    )
    selected, _ = retain_node1_tool_result(
        observation,
        omit,
        memory_path,
    )
    candidate = OmittedToolCandidate(
        observation=observation,
        review=omit.review,
    )
    route_action = Node1Action(
        action="route_node2",
        reason="도구 확인을 마쳤다.",
    )
    repeated_action = Node1Action(
        action="use_tool",
        reason="같은 파일을 다시 요청했다.",
        tool_name=READ_PYTHON_FILE,
        arguments={"path": "main.py"},
    )

    assert selected is None
    assert should_recover_omitted_results(
        state,
        route_action,
        [candidate],
        round_has_retained_content=False,
    )
    assert should_recover_omitted_results(
        state,
        repeated_action,
        [candidate],
        round_has_retained_content=False,
    )
    assert should_recover_omitted_results(
        state,
        Node1Action(
            action="use_tool",
            reason="전체 도구 예산의 마지막 요청입니다.",
            tool_name=READ_PYTHON_FILE,
            arguments={"path": "other.py"},
        ),
        [candidate],
        round_has_retained_content=False,
        total_tool_calls=3,
        maximum_total_tool_calls=3,
    )
    begin_node1_omit_recovery(
        state,
        [candidate],
        memory_path,
    )
    recovered, _ = recover_node1_omitted_result(
        candidate,
        RetentionDecision(
            mode="full",
            review="후속 노드가 볼 전체 원문을 복구한다.",
        ),
        1,
        memory_path,
    )

    assert recovered == raw_content
    assert state.node1_tool_calls_in_round == 1
    assert state.node1_omit_recovery_used is True
    assert not should_recover_omitted_results(
        state,
        route_action,
        [candidate],
        round_has_retained_content=False,
    )


def test_recovery_detection_log_failure_does_not_consume_chance(
    tmp_path,
    monkeypatch,
):
    toolbox, _ = _make_toolbox(tmp_path)
    memory_path = tmp_path / "memory.jsonl"
    state = create_turn_state("turn-recovery-log-failure")
    observation = execute_node1_tool(
        state,
        toolbox,
        READ_PYTHON_FILE,
        {"path": "main.py"},
        memory_path,
    )
    candidate = OmittedToolCandidate(
        observation=observation,
        review="복구 후보다.",
    )

    def fail_to_save(**kwargs):
        raise OSError("복구 감지 로그 저장 실패")

    monkeypatch.setattr(
        retention_recovery,
        "save_node1_all_omit_detection",
        fail_to_save,
    )

    with pytest.raises(OSError, match="복구 감지"):
        begin_node1_omit_recovery(
            state,
            [candidate],
            memory_path,
        )

    assert state.node1_omit_recovery_used is False
