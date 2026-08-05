"""가짜 모델과 도구로 Node1→Node4 데모 전체 흐름을 검사한다."""

import json

from agent_tools import (
    LIST_PYTHON_FILES,
    READ_PYTHON_FILE,
    ToolResult,
)
from llm import ModelReply
from memory.agent_view import (
    format_agent_memory,
    load_agent_memory,
)
from memory.conversation_records import save_user_input
from memory.settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)
from memory.store import save_information_record
from nodes import (
    NODE3_ANSWER_SCHEMA,
    REVIEW_DECISION_SCHEMA,
    build_text_chunks,
)
from runtime import run_demo_turn


def _json(payload):
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _route_action(reason="필요한 근거를 모두 확인했다."):
    return {
        "action": "route_node2",
        "reason": reason,
        "tool_name": None,
        "arguments": None,
    }


def _tool_action(tool_name, arguments, reason="도구 확인이 필요하다."):
    return {
        "action": "use_tool",
        "reason": reason,
        "tool_name": tool_name,
        "arguments": arguments,
    }


_LEGACY_RETENTION = object()


def _tool_decision(
    mode,
    review,
    next_action,
    *,
    start=None,
    end=None,
    chunk_id=_LEGACY_RETENTION,
):
    if chunk_id is not _LEGACY_RETENTION:
        retention = {
            "mode": mode,
            "review": review,
            "chunk_id": chunk_id,
        }
    else:
        retention = {
            "mode": mode,
            "review": review,
            "start": start,
            "end": end,
        }

    return {
        "retention": retention,
        "next_action": next_action,
    }


def _recovery_choice(candidate_number):
    return {"candidate_number": candidate_number}


def _recovery_retention(
    mode,
    review,
    *,
    start=None,
    end=None,
    chunk_id=_LEGACY_RETENTION,
):
    if chunk_id is not _LEGACY_RETENTION:
        retention = {
            "mode": mode,
            "review": review,
            "chunk_id": chunk_id,
        }
    else:
        retention = {
            "mode": mode,
            "review": review,
            "start": start,
            "end": end,
        }

    return {"retention": retention}


def _review(verdict, reason):
    return {"verdict": verdict, "reason": reason}


def _answer(text):
    return {"answer": text}


def _request_label(system_prompt, response_schema):
    """프롬프트와 schema로 실제로 호출된 노드 단계를 식별한다."""

    if system_prompt.startswith("너는 송련의 Node1"):
        schema_properties = set(response_schema["properties"])
        if schema_properties == {
            "action",
            "reason",
            "tool_name",
            "arguments",
        }:
            return "node1_action"
        if schema_properties == {"retention", "next_action"}:
            return "node1_tool"
        if schema_properties == {"candidate_number"}:
            return "node1_recovery_choice"
        assert schema_properties == {"retention"}
        return "node1_recovery_retention"
    if system_prompt.startswith("너는 송련의 Node2"):
        assert response_schema is REVIEW_DECISION_SCHEMA
        return "node2"
    if system_prompt.startswith("너는 송련의 Node3"):
        assert response_schema is NODE3_ANSWER_SCHEMA
        return "node3"
    if system_prompt.startswith("너는 송련의 Node4"):
        assert response_schema is REVIEW_DECISION_SCHEMA
        return "node4"
    raise AssertionError("알 수 없는 모델 호출")


class ScriptedModel:
    """정해진 전역 순서를 벗어난 노드 호출을 즉시 실패시킨다."""

    model_name = "fake-qwen:14b"

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def complete(
        self,
        *,
        system_prompt,
        user_prompt,
        response_schema,
        num_predict,
    ):
        actual_label = _request_label(system_prompt, response_schema)
        expected_label, payload = self.script.pop(0)
        assert actual_label == expected_label
        self.calls.append(
            {
                "label": actual_label,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "num_predict": num_predict,
            }
        )
        return ModelReply(
            content=_json(payload),
            thinking=f"{actual_label}의 판단",
            model=self.model_name,
            done_reason="stop",
            metrics={"eval_count": 5},
        )

    def assert_finished(self):
        assert self.script == []


class RecordingToolbox:
    """예상한 도구와 인자만 받고 미리 정한 ToolResult를 반환한다."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def execute(self, tool_name, arguments):
        expected_name, expected_arguments, result = self.script.pop(0)
        assert tool_name == expected_name
        assert arguments == expected_arguments
        self.calls.append((tool_name, arguments))
        return result

    def assert_finished(self):
        assert self.script == []


def _success(tool_name, arguments, content):
    return ToolResult(
        tool_name=tool_name,
        arguments=arguments,
        success=True,
        content=content,
    )


def _failure(tool_name, arguments, error):
    return ToolResult(
        tool_name=tool_name,
        arguments=arguments,
        success=False,
        content="",
        error=error,
    )


def _raw_records(memory_path):
    return [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]


def _records_of_type(records, information_type):
    return [
        record
        for record in records
        if record["information_type"] == information_type
    ]


def _visible_memory_from_prompt(user_prompt):
    """프롬프트의 공통 기억 구역에서 다섯 필드 JSON 원자만 꺼낸다."""

    records = []
    memory_heading = "[현재 노드에 제공된 기억 JSONL]\n"
    _, memory_and_rest = user_prompt.split(memory_heading, maxsplit=1)
    memory_text, _ = memory_and_rest.split(
        "[공유 기억 끝]",
        maxsplit=1,
    )

    for line in memory_text.splitlines():
        if not line.startswith("{"):
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if set(record) == {
            "memory_index",
            "information",
            "information_type",
            "information_class",
            "code_verifiable",
        }:
            records.append(record)

    return records


def test_happy_path_uses_two_tools_and_preserves_visibility_boundaries(
    tmp_path,
):
    memory_path = tmp_path / "demo" / "memory.jsonl"
    default_existed = DEFAULT_MEMORY_PATH.exists()
    default_before = (
        DEFAULT_MEMORY_PATH.read_bytes()
        if default_existed
        else None
    )
    list_raw = "LIST_RAW_SECRET\nmain.py"
    code_raw = "VALUE = 1\n"
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    LIST_PYTHON_FILES,
                    {},
                    "Python 파일 목록을 먼저 확인한다.",
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "목록에서 main.py를 확인했다.",
                    _tool_action(
                        READ_PYTHON_FILE,
                        {"path": "main.py"},
                        "main.py 원문을 확인한다.",
                    ),
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "VALUE의 정확한 값을 확인했다.",
                    _route_action(),
                ),
            ),
            ("node2", _review("permit", "답변 근거가 충분하다.")),
            ("node3", _answer("코드에서 확인된 VALUE는 1입니다.")),
            ("node4", _review("permit", "A 기록과 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                LIST_PYTHON_FILES,
                {},
                _success(LIST_PYTHON_FILES, {}, list_raw),
            ),
            (
                READ_PYTHON_FILE,
                {"path": "main.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "main.py"},
                    code_raw,
                ),
            ),
        ]
    )

    result = run_demo_turn(
        "main.py의 VALUE를 알려줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert [call["label"] for call in model.calls] == [
        "node1_action",
        "node1_tool",
        "node1_tool",
        "node2",
        "node3",
        "node4",
    ]
    assert result.answer == "코드에서 확인된 VALUE는 1입니다."
    assert result.total_tool_calls == 2
    assert result.node1_rounds == 1
    assert result.node2_rejections == 0
    assert result.node3_drafts == 1
    assert result.node4_rejections == 0
    assert result.node2_limit_exhausted is False
    assert result.node4_limit_exhausted is False
    assert result.final_outcome == "permit_applied"

    first_tool_prompt = model.calls[1]["user_prompt"]
    second_tool_prompt = model.calls[2]["user_prompt"]
    node2_prompt = model.calls[3]["user_prompt"]
    node3_prompt = model.calls[4]["user_prompt"]
    node4_prompt = model.calls[5]["user_prompt"]
    assert list_raw in first_tool_prompt
    assert code_raw in second_tool_prompt
    assert "<TOOL_RAW_TEXT>" in first_tool_prompt
    assert "LIST_RAW_SECRET" not in node2_prompt
    assert "<TOOL_RAW_TEXT>" not in node2_prompt
    # 공개 기억은 JSONL이므로 원문의 줄바꿈은 ``\n``으로 escape된다.
    assert code_raw.strip() in node2_prompt
    assert code_raw.strip() in node4_prompt
    assert "VALUE의 정확한 값을 확인했다." not in node2_prompt
    assert "VALUE의 정확한 값을 확인했다." in node3_prompt
    assert "VALUE의 정확한 값을 확인했다." not in node4_prompt

    for evidence_prompt in (node2_prompt, node4_prompt):
        evidence_memory = _visible_memory_from_prompt(evidence_prompt)
        assert evidence_memory
        assert all(
            record["information_class"] == "absolute"
            and record["code_verifiable"] is True
            for record in evidence_memory
        )
        assert not any(
            record["information_type"].startswith(
                "node1_tool_review"
            )
            for record in evidence_memory
        )

    assert any(
        record["information_class"] == "relative"
        for record in _visible_memory_from_prompt(node3_prompt)
    )

    raw = _raw_records(memory_path)
    visible = load_agent_memory(
        memory_path,
        max_characters=100_000,
    )
    visible_types = {
        record["information_type"]
        for record in visible
    }
    assert not any(
        information_type.startswith(("model_raw_", "tool_raw_"))
        for information_type in visible_types
    )
    assert "node3_answer" in visible_types
    assert "final_delivery" in visible_types
    assert _records_of_type(raw, "user_input")[0][
        "information_class"
    ] == "relative"
    assert _records_of_type(raw, "node1_tool_review_full")[0][
        "information_class"
    ] == "relative"
    assert "node1_tool_review_omit" in visible_types
    assert "node1_tool_review_full" in visible_types
    assert _records_of_type(raw, "tool_result_content")[0][
        "information_class"
    ] == "absolute"
    assert _records_of_type(raw, "node3_answer")[0][
        "information_class"
    ] == "relative"
    assert _records_of_type(raw, "final_delivery")[0][
        "information_class"
    ] == "absolute"
    assert all(
        record["information_class"] == "relative"
        for record in _records_of_type(raw, "model_raw_response")
    )
    assert all(
        record["information_class"] == "absolute"
        for record in _records_of_type(raw, "model_raw_status")
    )

    answer_record = _records_of_type(raw, "node3_answer")[0]
    final_link = json.loads(
        _records_of_type(raw, "final_delivery")[0]["information"]
    )
    assert final_link["answer_information_id"] == (
        answer_record["information_id"]
    )

    if default_existed:
        assert DEFAULT_MEMORY_PATH.read_bytes() == default_before
    else:
        assert not DEFAULT_MEMORY_PATH.exists()


def test_all_omitted_results_are_reselected_before_node2(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    list_raw = "LIST_ONLY_SECRET\nmain.py"
    code_raw = "VALUE = 7\n"
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    LIST_PYTHON_FILES,
                    {},
                    "파일 후보를 찾는다.",
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "main.py를 다음 열람 대상으로 골랐다.",
                    _tool_action(
                        READ_PYTHON_FILE,
                        {"path": "main.py"},
                        "실제 코드 원문을 확인한다.",
                    ),
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "VALUE 값을 확인했지만 처음에는 생략했다.",
                    _route_action(),
                ),
            ),
            ("node1_recovery_choice", _recovery_choice(2)),
            (
                "node1_recovery_retention",
                _recovery_retention(
                    "full",
                    "main.py 전체를 후속 검증용 A로 복구한다.",
                ),
            ),
            ("node2", _review("permit", "복구된 코드 A가 충분하다.")),
            ("node3", _answer("코드에서 확인된 VALUE는 7입니다.")),
            ("node4", _review("permit", "복구된 A와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                LIST_PYTHON_FILES,
                {},
                _success(LIST_PYTHON_FILES, {}, list_raw),
            ),
            (
                READ_PYTHON_FILE,
                {"path": "main.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "main.py"},
                    code_raw,
                ),
            ),
        ]
    )

    result = run_demo_turn(
        "main.py의 VALUE를 알려줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert [call["label"] for call in model.calls] == [
        "node1_action",
        "node1_tool",
        "node1_tool",
        "node1_recovery_choice",
        "node1_recovery_retention",
        "node2",
        "node3",
        "node4",
    ]
    assert result.total_tool_calls == 2

    choice_prompt = model.calls[3]["user_prompt"]
    recovery_prompt = model.calls[4]["user_prompt"]
    node2_prompt = model.calls[5]["user_prompt"]
    assert list_raw not in choice_prompt
    assert code_raw not in choice_prompt
    assert "main.py" in choice_prompt
    assert code_raw in recovery_prompt
    assert list_raw not in recovery_prompt
    assert code_raw.strip() in node2_prompt
    assert list_raw not in node2_prompt

    raw = _raw_records(memory_path)
    assert len(_records_of_type(raw, "node1_retention_request")) == 2
    assert all(
        json.loads(record["information"])["mode"] == "omit"
        for record in _records_of_type(raw, "node1_retention_request")
    )
    assert len(_records_of_type(raw, "node1_all_omit_detected")) == 1
    assert len(_records_of_type(raw, "node1_omit_recovery_request")) == 1
    assert len(_records_of_type(raw, "tool_omit_recovery_applied")) == 1
    recovered = _records_of_type(raw, "tool_result_content")
    assert [record["information"] for record in recovered] == [code_raw]


def test_long_tool_result_selects_one_deterministic_chunk_id(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    code_raw = "".join(
        f"LINE_{index:04d} = {index}\n"
        for index in range(600)
    )
    chunks = build_text_chunks(code_raw)
    selected_chunk = chunks[1]
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "long.py"},
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "chunk",
                    "개선점 검토에 필요한 둘째 청크를 정확히 남긴다.",
                    _route_action(),
                    chunk_id=selected_chunk.chunk_id,
                ),
            ),
            ("node2", _review("permit", "코드 A가 공개됐다.")),
            ("node3", _answer("공개된 코드에서 개선점을 찾았습니다.")),
            ("node4", _review("permit", "공개된 A와 모순되지 않는다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "long.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "long.py"},
                    code_raw,
                ),
            ),
        ]
    )

    result = run_demo_turn(
        "아무 코드나 읽고 개선점을 알려줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 1
    retention_branches = model.calls[1]["response_schema"]["properties"][
        "retention"
    ]["anyOf"]
    retention_modes = [
        branch["properties"]["mode"]["enum"][0]
        for branch in retention_branches
    ]
    assert retention_modes == ["chunk", "omit"]
    assert '"enum":["chunk"]' in model.calls[1]["system_prompt"]
    assert '"enum":["omit"]' in model.calls[1]["system_prompt"]
    chunk_id_values = retention_branches[0]["properties"]["chunk_id"][
        "enum"
    ]
    assert selected_chunk.chunk_id in chunk_id_values

    raw = _raw_records(memory_path)
    assert len(_records_of_type(raw, "tool_raw_content")) == 1
    retained = _records_of_type(raw, "tool_result_content")
    assert [record["information"] for record in retained] == [
        selected_chunk.content
    ]
    request = json.loads(
        _records_of_type(raw, "node1_retention_request")[0][
            "information"
        ]
    )
    applied = json.loads(
        _records_of_type(raw, "tool_retention_applied")[0][
            "information"
        ]
    )
    assert request == {
        "chunk_id": selected_chunk.chunk_id,
        "mode": "chunk",
    }
    assert applied["start"] == selected_chunk.start
    assert applied["end"] == selected_chunk.end


def test_long_omit_recovery_schema_allows_only_chunk_id(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    code_raw = "x" * 3_000
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "long.py"},
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "처음에는 긴 원문을 생략했다.",
                    _route_action(),
                    chunk_id=None,
                ),
            ),
            ("node1_recovery_choice", _recovery_choice(1)),
            (
                "node1_recovery_retention",
                _recovery_retention(
                    "chunk",
                    "후속 노드가 볼 수 있게 앞부분을 복구한다.",
                    chunk_id="chunk-0001",
                ),
            ),
            ("node2", _review("permit", "복구된 코드 A가 충분하다.")),
            ("node3", _answer("복구된 원문을 기준으로 답합니다.")),
            ("node4", _review("permit", "복구된 A와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "long.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "long.py"},
                    code_raw,
                ),
            ),
        ]
    )

    result = run_demo_turn(
        "긴 코드를 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 1
    recovery_call = next(
        call
        for call in model.calls
        if call["label"] == "node1_recovery_retention"
    )
    assert recovery_call["response_schema"]["properties"]["retention"][
        "properties"
    ]["mode"]["enum"] == ["chunk"]
    assert '"enum":["chunk"]' in recovery_call["system_prompt"]

    raw = _raw_records(memory_path)
    retained = _records_of_type(raw, "tool_result_content")
    assert [record["information"] for record in retained] == [
        code_raw[:2_000]
    ]


def test_omit_recovery_runs_only_once_across_node1_rounds(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    first_raw = "FIRST = 1\n"
    second_raw = "SECOND = 2\n"
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "first.py"},
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "첫 파일을 처음에는 생략했다.",
                    _route_action(),
                ),
            ),
            ("node1_recovery_choice", _recovery_choice(1)),
            (
                "node1_recovery_retention",
                _recovery_retention(
                    "full",
                    "첫 파일을 최종 복구한다.",
                ),
            ),
            ("node2", _review("reject", "second.py의 A가 빠졌다.")),
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "second.py"},
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "둘째 파일도 생략하고 기존 A로 검사를 요청한다.",
                    _route_action(),
                ),
            ),
            ("node2", _review("permit", "현재 공개 A로 진행한다.")),
            ("node3", _answer("첫 파일에서 FIRST는 1입니다.")),
            ("node4", _review("permit", "공개된 첫 A와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "first.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "first.py"},
                    first_raw,
                ),
            ),
            (
                READ_PYTHON_FILE,
                {"path": "second.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "second.py"},
                    second_raw,
                ),
            ),
        ]
    )

    result = run_demo_turn(
        "두 파일을 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.node1_rounds == 2
    assert result.total_tool_calls == 2
    assert [
        call["label"]
        for call in model.calls
        if call["label"].startswith("node1_recovery")
    ] == [
        "node1_recovery_choice",
        "node1_recovery_retention",
    ]
    raw = _raw_records(memory_path)
    assert len(_records_of_type(raw, "node1_all_omit_detected")) == 1
    assert [
        record["information"]
        for record in _records_of_type(raw, "tool_result_content")
    ] == [first_raw]


def test_failed_omitted_result_does_not_trigger_recovery(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "missing.py"},
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "파일 열람 실패를 확인했다.",
                    _route_action(),
                ),
            ),
            ("node2", _review("permit", "실패 상태 자체를 확인했다.")),
            ("node3", _answer("파일을 열람하지 못했습니다.")),
            ("node4", _review("permit", "도구 실패 A와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "missing.py"},
                _failure(
                    READ_PYTHON_FILE,
                    {"path": "missing.py"},
                    "요청한 파일이 없습니다.",
                ),
            )
        ]
    )

    result = run_demo_turn(
        "missing.py를 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 1
    assert all(
        not call["label"].startswith("node1_recovery")
        for call in model.calls
    )
    assert not _records_of_type(
        _raw_records(memory_path),
        "node1_all_omit_detected",
    )


def test_each_demo_turn_freezes_and_then_recalculates_its_view(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    floor_marker = "TURN1_FROZEN_FLOOR_" + ("m" * 1_200)
    first_code = "FIRST_CODE_" + ("a" * 1_700)
    second_code = "SECOND_CODE_" + ("b" * 1_700)
    save_information_record(
        floor_marker,
        "absolute",
        "tool_result_content",
        "older-turn",
        memory_path,
    )
    first_model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "first.py"},
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "첫 파일을 보존했다.",
                    _tool_action(
                        READ_PYTHON_FILE,
                        {"path": "second.py"},
                    ),
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "둘째 파일도 보존했다.",
                    _route_action(),
                ),
            ),
            ("node2", _review("permit", "두 코드 근거가 충분하다.")),
            ("node3", _answer("두 파일을 확인했습니다.")),
            ("node4", _review("permit", "A 기록과 일치한다.")),
        ]
    )
    first_toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "first.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "first.py"},
                    first_code,
                ),
            ),
            (
                READ_PYTHON_FILE,
                {"path": "second.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "second.py"},
                    second_code,
                ),
            ),
        ]
    )

    run_demo_turn(
        "두 파일을 확인해줘.",
        client=first_model,
        toolbox=first_toolbox,
        memory_path=memory_path,
    )

    first_model.assert_finished()
    first_toolbox.assert_finished()
    assert floor_marker in first_model.calls[0]["user_prompt"]

    for call in first_model.calls[3:]:
        assert floor_marker in call["user_prompt"]
        assert first_code in call["user_prompt"]
        assert second_code in call["user_prompt"]

    latest_after_first_turn = format_agent_memory(
        load_agent_memory(memory_path)
    )
    assert floor_marker not in latest_after_first_turn

    second_model = ScriptedModel(
        [
            ("node1_action", _route_action()),
            ("node2", _review("permit", "현재 기록으로 충분하다.")),
            ("node3", _answer("두 번째 턴입니다.")),
            ("node4", _review("permit", "A를 왜곡하지 않았다.")),
        ]
    )
    second_toolbox = RecordingToolbox([])

    run_demo_turn(
        "두 번째 질문",
        client=second_model,
        toolbox=second_toolbox,
        memory_path=memory_path,
    )

    second_model.assert_finished()
    second_toolbox.assert_finished()
    second_first_prompt = second_model.calls[0]["user_prompt"]
    assert "두 번째 질문" in second_first_prompt
    assert floor_marker not in second_first_prompt


def test_demo_freezes_after_saving_the_current_user_input(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    oldest_marker = "OLDEST_BEFORE_INPUT_" + ("m" * 700)

    for number in range(10):
        information = (
            oldest_marker
            if number == 0
            else f"older-{number}-" + ("o" * 700)
        )
        save_information_record(
            information,
            "absolute",
            "action",
            "older-turn",
            memory_path,
        )

    user_input = "CURRENT_LONG_INPUT_" + ("q" * 900)
    model = ScriptedModel(
        [
            ("node1_action", _route_action()),
            ("node2", _review("permit", "현재 기록으로 충분하다.")),
            ("node3", _answer("현재 입력을 확인했습니다.")),
            ("node4", _review("permit", "A를 왜곡하지 않았다.")),
        ]
    )

    run_demo_turn(
        user_input,
        client=model,
        toolbox=RecordingToolbox([]),
        memory_path=memory_path,
    )

    model.assert_finished()
    first_memory = _visible_memory_from_prompt(
        model.calls[0]["user_prompt"]
    )
    first_information = [
        record["information"]
        for record in first_memory
    ]

    assert (
        len(format_agent_memory(first_memory))
        <= DEFAULT_AGENT_VIEW_CHARACTER_LIMIT
    )
    assert user_input in first_information
    assert oldest_marker not in first_information


def test_demo_pins_previous_input_and_exposes_current_turn_boundary(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    previous_input = "README를 더 읽어 줘."
    save_user_input(
        previous_input,
        "previous-turn",
        memory_path,
    )

    for number in range(3):
        save_information_record(
            f"오래된 반복 판단-{number}-" + ("x" * 3_000),
            "relative",
            "reason",
            "previous-turn",
            memory_path,
        )

    assert previous_input not in format_agent_memory(
        load_agent_memory(memory_path)
    )
    line_count_before_turn = len(
        memory_path.read_text(encoding="utf-8").splitlines()
    )
    expected_turn_start = line_count_before_turn + 1
    model = ScriptedModel(
        [
            ("node1_action", _route_action()),
            ("node2", _review("permit", "현재 요청에 답할 수 있다.")),
            ("node3", _answer("직전 요청을 이어서 확인하겠습니다.")),
            ("node4", _review("permit", "기억의 경계를 왜곡하지 않았다.")),
        ]
    )

    run_demo_turn(
        "더 읽어봐",
        client=model,
        toolbox=RecordingToolbox([]),
        memory_path=memory_path,
    )

    model.assert_finished()
    expected_boundary = (
        f"current_turn_start_index={expected_turn_start}"
    )

    for call in model.calls[:3]:
        prompt = call["user_prompt"]
        assert expected_boundary in prompt
        assert previous_input in prompt

    node4_prompt = model.calls[3]["user_prompt"]
    assert expected_boundary in node4_prompt
    assert previous_input not in node4_prompt
    assert "더 읽어봐" not in node4_prompt
    assert "[현재 사용자 요청" not in node4_prompt
    assert "[직전 사용자 입력" not in node4_prompt

    first_prompt = model.calls[0]["user_prompt"]
    first_memory = _visible_memory_from_prompt(first_prompt)
    first_information = [
        record["information"]
        for record in first_memory
    ]
    assert previous_input not in first_information
    assert {
        "memory_index": expected_turn_start,
        "information": "user",
        "information_type": "source",
        "information_class": "absolute",
        "code_verifiable": True,
    } in first_memory
    assert {
        "memory_index": expected_turn_start + 1,
        "information": "더 읽어봐",
        "information_type": "user_input",
        "information_class": "relative",
        "code_verifiable": False,
    } in first_memory


def test_node2_and_node4_rejects_return_to_the_correct_nodes(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    node2_reason = "근거가 부족하므로 Node1이 다시 판단해야 한다."
    node4_reason = "첫 답변이 A의 범위를 넘어서 단정했다."
    first_answer = "검증되지 않은 내용까지 모두 사실입니다."
    revised_answer = "확인된 기록 안에서는 결론을 단정할 수 없습니다."
    model = ScriptedModel(
        [
            ("node1_action", _route_action("우선 검토를 요청한다.")),
            ("node2", _review("reject", node2_reason)),
            ("node1_action", _route_action("반려 이유를 반영했다.")),
            ("node2", _review("permit", "일반 답변에 충분하다.")),
            ("node3", _answer(first_answer)),
            ("node4", _review("reject", node4_reason)),
            ("node3", _answer(revised_answer)),
            ("node4", _review("permit", "수정 답변은 A를 왜곡하지 않는다.")),
        ]
    )
    toolbox = RecordingToolbox([])

    result = run_demo_turn(
        "현재 기록만으로 답해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert [call["label"] for call in model.calls] == [
        "node1_action",
        "node2",
        "node1_action",
        "node2",
        "node3",
        "node4",
        "node3",
        "node4",
    ]
    assert node2_reason in model.calls[2]["user_prompt"]
    assert node4_reason in model.calls[6]["user_prompt"]
    assert first_answer in model.calls[6]["user_prompt"]
    assert result.answer == revised_answer
    assert result.node1_rounds == 2
    assert result.node2_rejections == 1
    assert result.node3_drafts == 2
    assert result.node4_rejections == 1
    assert result.total_tool_calls == 0


def test_third_tool_result_forces_node2_before_a_fourth_execution(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    tool_actions = [
        _tool_action(
            READ_PYTHON_FILE,
            {"path": f"file-{number}.py"},
            f"{number}번 파일을 확인한다.",
        )
        for number in range(1, 5)
    ]
    model = ScriptedModel(
        [
            ("node1_action", tool_actions[0]),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "첫 결과를 확인했다.",
                    tool_actions[1],
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "둘째 결과를 확인했다.",
                    tool_actions[2],
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "셋째 결과를 확인했다.",
                    tool_actions[3],
                ),
            ),
            ("node1_recovery_choice", _recovery_choice(3)),
            (
                "node1_recovery_retention",
                _recovery_retention(
                    "full",
                    "셋째 결과를 최종 증거로 복구한다.",
                ),
            ),
            ("node2", _review("permit", "세 번의 확인으로 충분하다.")),
            ("node3", _answer("도구는 세 번까지만 실행됐습니다.")),
            ("node4", _review("permit", "실행 로그와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": f"file-{number}.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": f"file-{number}.py"},
                    f"result-{number}",
                ),
            )
            for number in range(1, 4)
        ]
    )

    result = run_demo_turn(
        "세 번 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 3
    assert len(toolbox.calls) == 3
    assert [call["label"] for call in model.calls[4:6]] == [
        "node1_recovery_choice",
        "node1_recovery_retention",
    ]

    raw = _raw_records(memory_path)
    routes = [
        json.loads(record["information"])
        for record in _records_of_type(raw, "runtime_route")
    ]
    assert len(routes) == 4
    assert routes[-1] == {
        "forced_by_tool_limit": True,
        "next_node": "node2",
        "outcome": "tool_request_blocked_limit",
    }


def test_optional_turn_tool_limit_applies_across_node1_rounds(tmp_path):
    memory_path = tmp_path / "memory.jsonl"
    tool_actions = [
        _tool_action(
            READ_PYTHON_FILE,
            {"path": f"file-{number}.py"},
            f"{number}번 파일을 확인한다.",
        )
        for number in range(1, 5)
    ]
    model = ScriptedModel(
        [
            ("node1_action", tool_actions[0]),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "첫 파일을 확인했다.",
                    _route_action(),
                ),
            ),
            ("node2", _review("reject", "다른 파일도 필요하다.")),
            ("node1_action", tool_actions[1]),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "둘째 파일을 확인했다.",
                    tool_actions[2],
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "셋째 파일을 확인했다.",
                    tool_actions[3],
                ),
            ),
            ("node2", _review("permit", "현재 근거로 답할 수 있다.")),
            ("node3", _answer("턴 전체에서 세 파일만 읽었습니다.")),
            ("node4", _review("permit", "실행 기록과 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": f"file-{number}.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": f"file-{number}.py"},
                    f"result-{number}",
                ),
            )
            for number in range(1, 4)
        ]
    )

    result = run_demo_turn(
        "여러 파일을 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
        maximum_total_tool_calls=3,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 3
    assert result.node1_rounds == 2
    assert result.node2_rejections == 1
    routes = [
        json.loads(record["information"])
        for record in _records_of_type(
            _raw_records(memory_path),
            "runtime_route",
        )
    ]
    assert routes[-1]["outcome"] == "tool_request_blocked_total_limit"


def test_turn_tool_limit_recovers_all_omitted_current_round_results(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    tool_actions = [
        _tool_action(
            READ_PYTHON_FILE,
            {"path": f"file-{number}.py"},
            f"Read file {number}.",
        )
        for number in range(1, 5)
    ]
    model = ScriptedModel(
        [
            ("node1_action", tool_actions[0]),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "Keep the first-round evidence.",
                    _route_action(),
                ),
            ),
            ("node2", _review("reject", "Read more evidence.")),
            ("node1_action", tool_actions[1]),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "Omit the second result.",
                    tool_actions[2],
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "Omit the third result.",
                    tool_actions[3],
                ),
            ),
            ("node1_recovery_choice", _recovery_choice(2)),
            (
                "node1_recovery_retention",
                _recovery_retention(
                    "full",
                    "Recover the final result before routing.",
                ),
            ),
            ("node2", _review("permit", "Current evidence is enough.")),
            ("node3", _answer("Three tool calls were recorded.")),
            ("node4", _review("permit", "The answer matches A.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": f"file-{number}.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": f"file-{number}.py"},
                    f"result-{number}",
                ),
            )
            for number in range(1, 4)
        ]
    )

    result = run_demo_turn(
        "Read several files.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
        maximum_total_tool_calls=3,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 3
    assert result.node1_rounds == 2
    assert [call["label"] for call in model.calls[6:8]] == [
        "node1_recovery_choice",
        "node1_recovery_retention",
    ]
    routes = [
        json.loads(record["information"])
        for record in _records_of_type(
            _raw_records(memory_path),
            "runtime_route",
        )
    ]
    assert routes[-1]["outcome"] == "tool_request_blocked_total_limit"
    retained_contents = [
        record["information"]
        for record in _records_of_type(
            _raw_records(memory_path),
            "tool_result_content",
        )
    ]
    assert "result-3" in retained_contents


def test_invalid_excerpt_retries_decision_without_reexecuting_tool(
    tmp_path,
):
    memory_path = tmp_path / "memory.jsonl"
    raw_text = "SHORT\n"
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "main.py"},
                    "원문을 확인한다.",
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "excerpt",
                    "잘못된 범위를 먼저 반환했다.",
                    _route_action(),
                    start=0,
                    end=999,
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "omit",
                    "범위 오류 뒤 본문을 남기지 않기로 했다.",
                    _route_action(),
                ),
            ),
            ("node1_recovery_choice", _recovery_choice(1)),
            (
                "node1_recovery_retention",
                _recovery_retention(
                    "full",
                    "짧은 원문 전체를 최종 보존한다.",
                ),
            ),
            ("node2", _review("permit", "검토 기록으로 충분하다.")),
            ("node3", _answer("도구는 한 번만 실행됐습니다.")),
            ("node4", _review("permit", "로그와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "main.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "main.py"},
                    raw_text,
                ),
            )
        ]
    )

    result = run_demo_turn(
        "main.py를 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 1
    assert len(toolbox.calls) == 1
    assert [call["label"] for call in model.calls[0:3]] == [
        "node1_action",
        "node1_tool",
        "node1_tool",
    ]
    assert "[직전 출력 검증 실패]" in model.calls[2]["user_prompt"]
    assert raw_text in model.calls[2]["user_prompt"]

    raw = _raw_records(memory_path)
    assert len(_records_of_type(raw, "tool_raw_content")) == 1
    assert len(_records_of_type(raw, "tool_retention_applied")) == 1
    assert len(_records_of_type(raw, "node1_retention_request")) == 1
    assert [
        record["information"]
        for record in _records_of_type(raw, "model_raw_status")
    ].count("invalid") == 1


def test_full_with_start_retries_without_reexecuting_tool(tmp_path):
    """실제 회귀 사례인 full + start=0도 도구 재실행 없이 복구한다."""

    memory_path = tmp_path / "memory.jsonl"
    raw_text = "SHORT\n"
    model = ScriptedModel(
        [
            (
                "node1_action",
                _tool_action(
                    READ_PYTHON_FILE,
                    {"path": "main.py"},
                    "원문을 확인한다.",
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "전체 원문을 남긴다.",
                    _route_action(),
                    start=0,
                    end=None,
                ),
            ),
            (
                "node1_tool",
                _tool_decision(
                    "full",
                    "전체 원문을 올바른 위치 계약으로 남긴다.",
                    _route_action(),
                ),
            ),
            ("node2", _review("permit", "보존된 코드 A가 충분하다.")),
            ("node3", _answer("도구 원문을 확인했습니다.")),
            ("node4", _review("permit", "답변이 보존된 A와 일치한다.")),
        ]
    )
    toolbox = RecordingToolbox(
        [
            (
                READ_PYTHON_FILE,
                {"path": "main.py"},
                _success(
                    READ_PYTHON_FILE,
                    {"path": "main.py"},
                    raw_text,
                ),
            )
        ]
    )

    result = run_demo_turn(
        "main.py를 확인해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=memory_path,
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.total_tool_calls == 1
    assert len(toolbox.calls) == 1
    assert [call["label"] for call in model.calls[0:3]] == [
        "node1_action",
        "node1_tool",
        "node1_tool",
    ]
    retry_prompt = model.calls[2]["user_prompt"]
    assert "[직전 출력 검증 실패]" in retry_prompt
    assert "선택 필드 값을 모두 JSON null" in retry_prompt

    raw = _raw_records(memory_path)
    assert [
        record["information"]
        for record in _records_of_type(raw, "tool_result_content")
    ] == [raw_text]
    assert [
        record["information"]
        for record in _records_of_type(raw, "model_raw_status")
    ].count("invalid") == 1


def test_node2_fourth_reject_is_returned_as_unverified_state(tmp_path):
    model = ScriptedModel(
        [
            ("node1_action", _route_action()),
            ("node2", _review("reject", "첫 증거 반려")),
            ("node1_action", _route_action()),
            ("node2", _review("reject", "둘째 증거 반려")),
            ("node1_action", _route_action()),
            ("node2", _review("reject", "셋째 증거 반려")),
            ("node1_action", _route_action()),
            ("node2", _review("reject", "한도 뒤 넷째 반려")),
            ("node3", _answer("검증 미완료 답변")),
            ("node4", _review("permit", "답변 자체는 A를 왜곡하지 않음")),
        ]
    )
    toolbox = RecordingToolbox([])

    result = run_demo_turn(
        "현재 기록으로 답해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=tmp_path / "memory.jsonl",
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.answer == "검증 미완료 답변"
    assert result.node1_rounds == 4
    assert result.node2_rejections == 3
    assert result.node2_limit_exhausted is True
    assert result.node4_limit_exhausted is False
    assert result.final_outcome == "permit_applied"


def test_node4_fourth_reject_marks_delivered_answer_unpermitted(tmp_path):
    model = ScriptedModel(
        [
            ("node1_action", _route_action()),
            ("node2", _review("permit", "증거 충분")),
            ("node3", _answer("첫 답변")),
            ("node4", _review("reject", "첫 답변 반려")),
            ("node3", _answer("둘째 답변")),
            ("node4", _review("reject", "둘째 답변 반려")),
            ("node3", _answer("셋째 답변")),
            ("node4", _review("reject", "셋째 답변 반려")),
            ("node3", _answer("넷째 미허가 답변")),
            ("node4", _review("reject", "한도 뒤 넷째 반려")),
        ]
    )
    toolbox = RecordingToolbox([])

    result = run_demo_turn(
        "현재 기록으로 답해줘.",
        client=model,
        toolbox=toolbox,
        memory_path=tmp_path / "memory.jsonl",
    )

    model.assert_finished()
    toolbox.assert_finished()
    assert result.answer == "넷째 미허가 답변"
    assert result.node3_drafts == 4
    assert result.node4_rejections == 3
    assert result.node2_limit_exhausted is False
    assert result.node4_limit_exhausted is True
    assert result.last_node4_reject_reason == "한도 뒤 넷째 반려"
    assert result.final_outcome == "reject_ignored_limit"
