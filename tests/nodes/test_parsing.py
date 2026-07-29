"""LLM JSON 출력이 보정 없이 노드 계약으로 검증되는지 검사한다."""

import pytest

from nodes import (
    MAX_NODE3_ANSWER_CHARACTERS,
    NODE1_ACTION_SCHEMA,
    NODE1_RECOVERY_CHOICE_SCHEMA,
    NODE1_RECOVERY_RETENTION_SCHEMA,
    NODE1_TOOL_DECISION_SCHEMA,
    NODE3_ANSWER_SCHEMA,
    REVIEW_DECISION_SCHEMA,
    Node1Action,
    Node1ToolDecision,
    Node3Answer,
    ReviewDecision,
    build_text_chunks,
    parse_node1_action,
    parse_node1_recovery_choice,
    parse_node1_recovery_retention,
    parse_node1_tool_decision,
    parse_node3_answer,
    parse_review_decision,
    node1_recovery_retention_schema,
    node1_tool_decision_schema,
)


def _route_action_payload():
    return {
        "action": "route_node2",
        "reason": "검토할 근거가 충분하다.",
        "tool_name": None,
        "arguments": None,
    }


def _tool_decision_payload():
    return {
        "retention": {
            "mode": "excerpt",
            "review": "두 번째 줄이 질문과 직접 관련 있다.",
            "start": 6,
            "end": 11,
        },
        "next_action": _route_action_payload(),
    }


def test_schemas_require_exact_top_level_keys():
    schemas_and_keys = [
        (
            NODE1_ACTION_SCHEMA,
            {"action", "reason", "tool_name", "arguments"},
        ),
        (
            NODE1_TOOL_DECISION_SCHEMA,
            {"retention", "next_action"},
        ),
        (
            NODE1_RECOVERY_CHOICE_SCHEMA,
            {"candidate_number"},
        ),
        (
            NODE1_RECOVERY_RETENTION_SCHEMA,
            {"mode", "review", "start", "end"},
        ),
        (REVIEW_DECISION_SCHEMA, {"verdict", "reason"}),
        (NODE3_ANSWER_SCHEMA, {"answer"}),
    ]

    for schema, expected_keys in schemas_and_keys:
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == expected_keys
        assert set(schema["properties"]) == expected_keys

    retention_schema = NODE1_TOOL_DECISION_SCHEMA["properties"]["retention"]
    assert retention_schema["additionalProperties"] is False
    assert set(retention_schema["required"]) == {
        "mode",
        "review",
        "start",
        "end",
    }
    assert NODE1_RECOVERY_RETENTION_SCHEMA["properties"]["mode"][
        "enum"
    ] == ["full", "excerpt"]


def test_schemas_make_optional_values_explicitly_nullable():
    action_properties = NODE1_ACTION_SCHEMA["properties"]
    retention_properties = NODE1_TOOL_DECISION_SCHEMA[
        "properties"
    ]["retention"]["properties"]

    assert action_properties["tool_name"]["type"] == ["string", "null"]
    assert action_properties["arguments"]["type"] == ["object", "null"]
    assert retention_properties["start"]["type"] == ["integer", "null"]
    assert retention_properties["end"]["type"] == ["integer", "null"]


def test_node1_schemas_remove_full_when_the_current_raw_is_too_long():
    short_tool_schema = node1_tool_decision_schema(allow_full=True)
    chunk_ids = ["chunk-0001", "chunk-0002"]
    long_tool_schema = node1_tool_decision_schema(
        allow_full=False,
        chunk_ids=chunk_ids,
    )
    short_recovery_schema = node1_recovery_retention_schema(
        allow_full=True,
    )
    long_recovery_schema = node1_recovery_retention_schema(
        allow_full=False,
        chunk_ids=chunk_ids,
    )

    assert short_tool_schema is NODE1_TOOL_DECISION_SCHEMA
    assert short_recovery_schema is NODE1_RECOVERY_RETENTION_SCHEMA
    assert long_tool_schema["properties"]["retention"]["properties"][
        "mode"
    ]["enum"] == ["chunk", "omit"]
    assert long_tool_schema["properties"]["retention"]["properties"][
        "chunk_id"
    ]["enum"] == [*chunk_ids, None]
    assert long_recovery_schema["properties"]["mode"]["enum"] == [
        "chunk"
    ]
    assert long_recovery_schema["properties"]["chunk_id"]["enum"] == (
        chunk_ids
    )


@pytest.mark.parametrize(
    "schema_builder",
    [
        node1_tool_decision_schema,
        node1_recovery_retention_schema,
    ],
)
def test_dynamic_node1_schemas_require_an_explicit_boolean(
    schema_builder,
):
    with pytest.raises(TypeError, match="bool"):
        schema_builder(allow_full=1)


def test_parse_node1_action_accepts_tool_and_route_contracts():
    tool_action = parse_node1_action(
        {
            "action": "use_tool",
            "reason": "파일 내용을 확인해야 한다.",
            "tool_name": "read_python_file",
            "arguments": {"path": "main.py"},
        }
    )
    route_action = parse_node1_action(_route_action_payload())

    assert isinstance(tool_action, Node1Action)
    assert tool_action.arguments == {"path": "main.py"}
    assert route_action.action == "route_node2"
    assert route_action.tool_name is None


@pytest.mark.parametrize(
    "payload",
    [
        {
            "action": "route_node2",
            "reason": "근거가 충분하다.",
            "tool_name": None,
        },
        {
            **_route_action_payload(),
            "unexpected": True,
        },
        {
            **_route_action_payload(),
            1: "JSON 객체의 키가 아니다.",
        },
        {
            "action": "use_tool",
            "reason": "파일을 읽는다.",
            "tool_name": 123,
            "arguments": {"path": "main.py"},
        },
    ],
)
def test_parse_node1_action_rejects_missing_extra_or_coerced_values(
    payload,
):
    with pytest.raises(ValueError):
        parse_node1_action(payload)


def test_parse_tool_decision_validates_and_preserves_exact_excerpt():
    raw_text = "FIRST\nSECOND\nTHIRD"
    decision = parse_node1_tool_decision(
        _tool_decision_payload(),
        raw_text,
    )

    assert isinstance(decision, Node1ToolDecision)
    assert decision.retention.start == 6
    assert raw_text[
        decision.retention.start:decision.retention.end
    ] == "SECON"
    assert decision.next_action.action == "route_node2"


def test_parse_tool_decision_rejects_bad_range_and_large_selection():
    invalid_range = _tool_decision_payload()
    invalid_range["retention"] = {
        **invalid_range["retention"],
        "start": 8,
        "end": 99,
    }

    with pytest.raises(ValueError, match="excerpt 범위"):
        parse_node1_tool_decision(invalid_range, "short text")

    full_decision = _tool_decision_payload()
    full_decision["retention"] = {
        "mode": "full",
        "review": "전체가 필요하다.",
        "start": None,
        "end": None,
    }

    with pytest.raises(ValueError, match="chunk_id"):
        parse_node1_tool_decision(
            full_decision,
            "x" * 11,
            max_selected_characters=10,
        )


def test_parse_tool_decision_omit_still_validates_raw_text_and_keys():
    omit_decision = _tool_decision_payload()
    omit_decision["retention"] = {
        "mode": "omit",
        "review": "목록 원문은 다음 노드에 필요하지 않다.",
        "chunk_id": None,
    }

    result = parse_node1_tool_decision(
        omit_decision,
        "x" * 10_000,
        max_selected_characters=1,
    )
    assert result.retention.mode == "omit"

    with pytest.raises(TypeError):
        parse_node1_tool_decision(omit_decision, None)

    extra_retention_key = _tool_decision_payload()
    extra_retention_key["retention"] = {
        **extra_retention_key["retention"],
        "summary": "추가 키",
    }

    with pytest.raises(ValueError, match="추가"):
        parse_node1_tool_decision(
            extra_retention_key,
            "FIRST\nSECOND\nTHIRD",
        )


def test_parse_recovery_choice_and_full_or_excerpt_retention():
    raw_text = "FIRST\nSECOND\n"
    choice = parse_node1_recovery_choice(
        {"candidate_number": 2},
        candidate_count=3,
    )
    full = parse_node1_recovery_retention(
        {
            "mode": "full",
            "review": "전체 원문이 필요하다.",
            "start": None,
            "end": None,
        },
        raw_text,
    )
    excerpt = parse_node1_recovery_retention(
        {
            "mode": "excerpt",
            "review": "둘째 줄을 보존한다.",
            "start": 6,
            "end": 12,
        },
        raw_text,
    )

    assert choice.candidate_number == 2
    assert full.mode == "full"
    assert raw_text[excerpt.start:excerpt.end] == "SECOND"


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (
            {
                "mode": "omit",
                "review": "다시 생략한다.",
                "start": None,
                "end": None,
            },
            "omit",
        ),
        (
            {
                "mode": "excerpt",
                "review": "잘못된 범위다.",
                "start": 0,
                "end": 99,
            },
            "excerpt 범위",
        ),
    ],
)
def test_parse_recovery_retention_rejects_omit_and_bad_range(
    payload,
    error,
):
    with pytest.raises(ValueError, match=error):
        parse_node1_recovery_retention(payload, "SHORT")


def test_parse_recovery_choice_rejects_out_of_range_candidate():
    with pytest.raises(ValueError, match="후보 범위"):
        parse_node1_recovery_choice(
            {"candidate_number": 3},
            candidate_count=2,
        )


def test_parse_recovery_retention_rejects_large_selection():
    raw_text = "FIRST\nSECOND\nTHIRD\n"
    chunks = build_text_chunks(raw_text, max_characters=10)
    selected = parse_node1_recovery_retention(
        {
            "mode": "chunk",
            "review": "둘째 청크를 복구한다.",
            "chunk_id": chunks[1].chunk_id,
        },
        raw_text,
        max_selected_characters=10,
    )

    assert selected.mode == "chunk"
    assert selected.chunk_id == chunks[1].chunk_id

    with pytest.raises(ValueError, match="청크 목록"):
        parse_node1_recovery_retention(
            {
                "mode": "chunk",
                "review": "없는 청크를 요청한다.",
                "chunk_id": "chunk-9999",
            },
            raw_text,
            max_selected_characters=10,
        )


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "20"])
def test_parse_tool_decision_rejects_invalid_selection_limit(limit):
    with pytest.raises(ValueError, match="1 이상의 정수"):
        parse_node1_tool_decision(
            _tool_decision_payload(),
            "FIRST\nSECOND\nTHIRD",
            max_selected_characters=limit,
        )


def test_parse_review_and_node3_answer_contracts():
    review = parse_review_decision(
        {
            "verdict": "permit",
            "reason": "절대정보와 모순되지 않는다.",
        }
    )
    answer = parse_node3_answer(
        {"answer": "검토를 마친 답변입니다."}
    )

    assert isinstance(review, ReviewDecision)
    assert review.verdict == "permit"
    assert isinstance(answer, Node3Answer)
    assert answer.answer == "검토를 마친 답변입니다."


@pytest.mark.parametrize(
    "payload",
    [
        {"verdict": "permit"},
        {
            "verdict": "permit",
            "reason": "통과",
            "extra": "허용하지 않음",
        },
        {"verdict": 1, "reason": "형변환하지 않는다."},
    ],
)
def test_parse_review_rejects_invalid_objects(payload):
    with pytest.raises(ValueError):
        parse_review_decision(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"answer": ""},
        {"answer": 123},
        {"answer": "정상", "extra": "허용하지 않음"},
        {"answer": "x" * (MAX_NODE3_ANSWER_CHARACTERS + 1)},
    ],
)
def test_parse_node3_answer_rejects_invalid_objects(payload):
    with pytest.raises(ValueError):
        parse_node3_answer(payload)
