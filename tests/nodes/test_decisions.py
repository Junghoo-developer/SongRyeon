"""LLM 결정 형식과 원문 복사 규칙의 경계값을 검사한다."""

import pytest

from nodes import (
    Node1Action,
    Node1ToolDecision,
    RetentionDecision,
    ReviewDecision,
    build_text_chunks,
    select_retained_content,
)
from nodes.decisions import MAX_REVIEW_CHARACTERS


def test_full_and_omit_keep_the_exact_contract():
    raw_text = " 앞 공백\r\n한글🙂\n마지막 줄\n"

    full = RetentionDecision(
        mode="full",
        review="전체가 짧고 관련 있다.",
    )
    omit = RetentionDecision(
        mode="omit",
        review="현재 질문과 관련이 없다.",
    )

    assert select_retained_content(raw_text, full) == raw_text
    assert select_retained_content(raw_text, omit) is None


def test_excerpt_uses_the_requested_occurrence_without_rewriting():
    raw_text = "같은 문장\n중간\n같은 문장\n"
    start = raw_text.rindex("같은 문장")
    end = start + len("같은 문장\n")
    decision = RetentionDecision(
        mode="excerpt",
        review="두 번째 발생 지점이 관련 있다.",
        start=start,
        end=end,
    )

    selected = select_retained_content(raw_text, decision)

    assert selected == raw_text[start:end]
    assert selected == "같은 문장\n"


def test_chunks_preserve_the_exact_raw_text_and_prefer_line_boundaries():
    raw_text = "FIRST\nSECOND\nTHIRD-LINE-IS-LONG\nLAST\n"
    chunks = build_text_chunks(raw_text, max_characters=13)

    assert [chunk.chunk_id for chunk in chunks] == [
        "chunk-0001",
        "chunk-0002",
        "chunk-0003",
    ]
    assert all(len(chunk.content) <= 13 for chunk in chunks)
    assert "".join(chunk.content for chunk in chunks) == raw_text
    assert chunks[0].content == "FIRST\nSECOND\n"
    assert chunks[-1].content.endswith("LAST\n")


def test_chunk_selection_uses_only_a_known_deterministic_id():
    raw_text = "A" * 12 + "\nB\n"
    chunks = build_text_chunks(raw_text, max_characters=5)
    decision = RetentionDecision(
        mode="chunk",
        review="둘째 청크가 필요하다.",
        chunk_id=chunks[1].chunk_id,
    )

    assert select_retained_content(
        raw_text,
        decision,
        max_chunk_characters=5,
    ) == chunks[1].content

    unknown = RetentionDecision(
        mode="chunk",
        review="없는 청크다.",
        chunk_id="chunk-9999",
    )
    with pytest.raises(ValueError, match="청크 목록"):
        select_retained_content(
            raw_text,
            unknown,
            max_chunk_characters=5,
        )


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (-1, 1),
        (0, 0),
        (2, 1),
        (0, 100),
    ],
)
def test_excerpt_rejects_an_invalid_range(start, end):
    decision = RetentionDecision(
        mode="excerpt",
        review="범위 검사",
        start=start,
        end=end,
    )

    with pytest.raises(ValueError):
        select_retained_content("짧은 원문", decision)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (True, 2),
        (0, False),
        (None, 2),
        (0, None),
    ],
)
def test_excerpt_rejects_non_plain_integer_positions(start, end):
    with pytest.raises(ValueError):
        RetentionDecision(
            mode="excerpt",
            review="잘못된 위치",
            start=start,
            end=end,
        )


def test_full_and_omit_reject_unnecessary_positions():
    with pytest.raises(ValueError):
        RetentionDecision(
            mode="full",
            review="잘못된 요청",
            start=0,
            end=1,
        )


def test_decisions_require_known_values_and_short_reasons():
    with pytest.raises(ValueError):
        RetentionDecision("unknown", "이유")

    with pytest.raises(ValueError):
        ReviewDecision("approve", "permit 또는 reject만 사용한다.")

    with pytest.raises(ValueError):
        ReviewDecision("reject", " ")

    with pytest.raises(ValueError):
        ReviewDecision(
            "permit",
            "가" * (MAX_REVIEW_CHARACTERS + 1),
        )


def test_node1_action_requires_tool_fields_only_for_tool_use():
    tool_action = Node1Action(
        action="use_tool",
        reason="파일 목록을 먼저 확인한다.",
        tool_name="list_python_files",
        arguments={},
    )
    route_action = Node1Action(
        action="route_node2",
        reason="필요한 근거를 모두 확인했다.",
    )
    combined = Node1ToolDecision(
        retention=RetentionDecision(
            mode="omit",
            review="목록 본문은 다음 노드에 필요하지 않다.",
        ),
        next_action=route_action,
    )

    assert tool_action.tool_name == "list_python_files"
    assert route_action.tool_name is None
    assert combined.next_action is route_action

    with pytest.raises(ValueError):
        Node1Action(
            action="use_tool",
            reason="도구 이름이 없다.",
            arguments={},
        )

    with pytest.raises(ValueError):
        Node1Action(
            action="route_node2",
            reason="라우팅에는 도구 인자가 없어야 한다.",
            tool_name="read_python_file",
            arguments={"path": "main.py"},
        )

    with pytest.raises(ValueError):
        Node1Action(
            action="use_tool",
            reason="JSON key가 문자열이 아니다.",
            tool_name="read_python_file",
            arguments={1: "main.py"},
        )

    with pytest.raises(ValueError):
        Node1Action(
            action="use_tool",
            reason="인자가 지나치게 길다.",
            tool_name="read_python_file",
            arguments={"path": "x" * 2_000},
        )
