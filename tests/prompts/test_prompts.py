"""노드 역할과 도구 원문 경계가 프롬프트에서 유지되는지 검사한다."""

from memory.agent_view import TurnMemoryContext
from prompts import (
    build_node1_recovery_choice_prompts,
    build_node1_recovery_retention_prompts,
    build_node1_tool_prompts,
    build_node2_prompts,
    build_node3_prompts,
    build_node4_prompts,
)


TURN_MEMORY_CONTEXT = TurnMemoryContext(
    current_turn_start_index=20,
    previous_user_input_index=7,
    previous_user_input="직전 파일을 더 확인해 줘.",
)


def test_only_node1_tool_prompt_receives_transient_raw_text():
    secret_raw = "SECRET_TOOL_RAW"
    _, node1_prompt = build_node1_tool_prompts(
        "파일을 설명해 줘.",
        "",
        tool_name="read_python_file",
        tool_success=True,
        raw_text=secret_raw,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )
    _, node2_prompt = build_node2_prompts(
        "파일을 설명해 줘.",
        "",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )
    _, node3_prompt = build_node3_prompts(
        "파일을 설명해 줘.",
        "",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )
    _, node4_prompt = build_node4_prompts(
        "파일을 설명해 줘.",
        "",
        "답변 후보",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert secret_raw in node1_prompt
    assert secret_raw not in node2_prompt
    assert secret_raw not in node3_prompt
    assert secret_raw not in node4_prompt


def test_node2_explicitly_reviews_evidence_not_final_answer_format():
    system_prompt, _ = build_node2_prompts(
        "x.py를 세 문장으로 설명해 줘.",
        "",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert "최종 답변이 아니라 증거만 검사한다" in system_prompt
    assert "세 문장 설명이 아직 없다는 것은 reject 이유가 아니다" in (
        system_prompt
    )
    assert "빠진 파일 또는 빠진 코드 사실" in system_prompt
    assert "주관적·창작·" in system_prompt
    assert "A 증거가 없어도 즉시 permit" in system_prompt
    assert "증거를 모을 수 없다는 말은 그 자체로 reject" in system_prompt
    assert "파일의 일반\n   역할만 확인됐다는 이유" in system_prompt
    assert "현재\n   동작을 판단할 실제 구현이 하나라도 있으면 permit" in system_prompt
    assert "개선안은 Node3가\n   새로 만드는 R" in system_prompt
    assert "기존 결함이나 개선안이 이미 적혀 있을\n   필요가 없다" in system_prompt
    assert "저장소 전체를 읽지 않았다는 이유로 reject하지 마라" in system_prompt
    assert "아무 코드나 읽고 개선점을 알려줘" not in system_prompt
    assert "개선을 제안할 함수나 동작의 A 본문이 빠져 있다" not in system_prompt


def test_node3_knows_its_user_facing_identity_and_node_boundaries():
    system_prompt, _ = build_node3_prompts(
        "내가 널 어떤 식으로 만들면 좋을까?",
        "",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert "사용자에게 송련으로 말하는 최종 답변 작성 노드" in system_prompt
    assert "네 이름은 송련이다" in system_prompt
    assert "네 노드가 증거 수집·검사·답변·검열" in system_prompt
    assert "기반 모델 하나가 아니라 이 전체" in system_prompt
    assert "이름이나 정체성을 물으면 송련으로서 직접 답한다" in system_prompt
    assert "인공지능 어시스턴트'로만 소개하지 마라" in system_prompt
    assert "묻지 않은 요청에는 자기소개로 답변을 시작하지 마라" in system_prompt
    assert "Node1은 도구로 증거를 수집" in system_prompt
    assert "Node2는 증거가 충분한지만 검사한다" in system_prompt
    assert "내부\n  라우팅 기록" in system_prompt
    assert "현재 턴의 Node4 reject\n  reason만 수정 지시" in system_prompt
    assert "과거 node3_answer를 답변으로" in system_prompt
    assert "현재 턴의 Node1 review는 R 분석 단서" in system_prompt
    assert "선택 보존된 A 본문과 직접 대조" in system_prompt


def test_node3_can_answer_subjective_requests_as_new_relative_information():
    system_prompt, _ = build_node3_prompts(
        "네 생각에 수상 가능해 보여?",
        "",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert "의견·평가·예측·제안은 A가 없어도 새 R" in system_prompt
    assert "의견·평가·예측·제안 요청에는 A가 없어도 새로운 R" in system_prompt
    assert "첫 문장에서 입장이나 조건부 판단을 하나 선택" in system_prompt
    assert "현재 가능한 구체적 행동을 제안" in system_prompt
    assert "송련 자신에 대한 평가나 조언" in system_prompt
    assert "외부 평가 기준이 없다는 사실만으로 판단을 거절하지 마라" in (
        system_prompt
    )
    assert "말만 하고 끝내는 것은 답변이 아니다" in system_prompt
    assert "가능성은 있다.`처럼 조건부 입장을 먼저" in system_prompt
    assert "현재 가장 중요한 구체적 개선" in system_prompt
    assert "현재 요청과 공개 기억에 맞게 답한다" in system_prompt
    assert "사용자가 내부 구조를 직접 질문한 경우가 아니라면" in system_prompt
    assert "파일 역할을 되풀이하는 것으로 끝내지 마라" in system_prompt
    assert "바꿀 내용과 그 이유 또는 trade-off" in system_prompt
    assert "그 자체로 '개선점'이라고 부르지 마라" in system_prompt
    assert "안전 경계는 결함으로 취급하지" in system_prompt


def test_node3_direct_answer_instruction_follows_internal_gate_reason():
    gate_reason_marker = "NODE2_REASON_MARKER_증거가 없어도 permit"
    memory_text = (
        '{"memory_index":21,"information":"'
        + gate_reason_marker
        + '","information_type":"reason","information_class":"relative",'
        '"code_verifiable":false}'
    )

    _, user_prompt = build_node3_prompts(
        "그래서 우승작이 될 수 있을 것 같냐고",
        memory_text,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert gate_reason_marker in user_prompt
    assert user_prompt.rfind("실제 내용에 결론부터 답") > user_prompt.index(
        gate_reason_marker
    )
    assert user_prompt.rfind("실제 판단 또는 구체적 제안을 먼저") > (
        user_prompt.index(gate_reason_marker)
    )


def test_node2_rechecks_latest_a_after_a_repeated_reason():
    repeated_reason_marker = "REPEATED_NODE2_REASON_MARKER"
    memory_text = (
        '{"memory_index":21,"information":"'
        + repeated_reason_marker
        + '","information_type":"reason","information_class":"relative",'
        '"code_verifiable":false}'
    )

    _, user_prompt = build_node2_prompts(
        "코드 개선점을 알려줘.",
        memory_text,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert user_prompt.rfind("이전 reason이나 시스템 예시를 복사하지 말고") > (
        user_prompt.index(repeated_reason_marker)
    )
    assert user_prompt.rfind("개선안 자체가 아직 코드에 없다는 이유로 reject하지 마라") > (
        user_prompt.index(repeated_reason_marker)
    )


def test_node4_does_not_enforce_a_past_task_on_the_current_answer():
    system_prompt, _ = build_node4_prompts(
        "너는 무슨 일을 할 수 있을 것 같아?",
        "",
        "저는 질문에 답하고 문제 해결을 도울 수 있습니다.",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert "과거 사용자 요청을 수행하지 않았다는 이유로 reject하지 마라" in (
        system_prompt
    )
    assert "어떤 문장이 없다는 사실은 A와의 모순이나 변형이 아니다" in (
        system_prompt
    )
    assert "과거 코드 요청을 수행하지 않았다는 것은" in system_prompt


def test_node4_does_not_treat_a_past_node3_answer_as_absolute_truth():
    system_prompt, _ = build_node4_prompts(
        "이름은?",
        "",
        "저는 송련입니다.",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert "`node3_answer`의 내용은 R" in system_prompt
    assert "현재 답변과 다르다는 이유만으로" in system_prompt
    assert "과거 R과 현재 R이 다르다는 것은 A 왜곡이 아니다" in system_prompt
    assert "현재 턴과 과거 턴을 불문하고" in system_prompt
    assert "reason, node1_tool_review의 내용은 R" in system_prompt
    assert "Node2의 decision과 reason은\n라우팅 기록" in system_prompt
    assert "Node4의 판정 이유로\n복사하거나 반복하지 마라" in system_prompt
    assert "개선 제안은 R" in system_prompt
    assert "제안 자체가 A에\n이미 존재하지 않는다는 이유로 reject하지" in system_prompt
    assert "A에 기록된 개선점" in system_prompt
    assert "허용 가능한 새 R" in system_prompt
    assert "두 항목을 구체적으로 지목할 수\n없으면 permit" in system_prompt


def test_node4_final_instruction_follows_repeated_internal_reason_and_answer():
    repeated_reason_marker = "REPEATED_NODE2_REASON_MARKER"
    answer_marker = "CURRENT_NODE3_ANSWER_MARKER"
    memory_text = (
        '{"memory_index":21,"information":"'
        + repeated_reason_marker
        + '","information_type":"reason","information_class":"relative",'
        '"code_verifiable":false}'
    )

    _, user_prompt = build_node4_prompts(
        "코드 개선점을 알려줘.",
        memory_text,
        answer_marker,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    final_instruction_index = user_prompt.rfind(
        "decision, reason, node1_tool_review 문구를 복사하지 말고"
    )
    assert final_instruction_index > user_prompt.index(repeated_reason_marker)
    assert final_instruction_index > user_prompt.index(answer_marker)


def test_node1_recovery_prompts_choose_metadata_then_show_one_raw():
    first_secret = "FIRST_SECRET_RAW"
    second_secret = "SECOND_SECRET_RAW"
    summaries = [
        {
            "arguments": {"path": "first.py"},
            "candidate_number": 1,
            "character_length": len(first_secret),
            "previous_review": "첫 파일을 확인했다.",
            "tool_name": "read_python_file",
        },
        {
            "arguments": {"path": "second.py"},
            "candidate_number": 2,
            "character_length": len(second_secret),
            "previous_review": "둘째 파일을 확인했다.",
            "tool_name": "read_python_file",
        },
    ]

    _, choice_prompt = build_node1_recovery_choice_prompts(
        "코드를 설명해 줘.",
        "",
        summaries,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )
    recovery_system, recovery_prompt = (
        build_node1_recovery_retention_prompts(
            "코드를 설명해 줘.",
            "",
            candidate_summary=summaries[1],
            raw_text=second_secret,
            turn_memory_context=TURN_MEMORY_CONTEXT,
        )
    )

    assert first_secret not in choice_prompt
    assert second_secret not in choice_prompt
    assert "first.py" in choice_prompt
    assert "second.py" in choice_prompt
    assert second_secret in recovery_prompt
    assert first_secret not in recovery_prompt
    assert '"enum":["full","excerpt"]' in recovery_system
    assert "omit은 사용할 수 없다" in recovery_prompt


def test_node1_tool_prompt_has_no_list_specific_omit_example():
    system_prompt, user_prompt = build_node1_tool_prompts(
        "코드를 설명해 줘.",
        "",
        tool_name="list_python_files",
        tool_success=True,
        raw_text="main.py",
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert "목록처럼" not in user_prompt
    assert "같은 도구와 같은 arguments를 반복 요청하지 마라" in system_prompt
    assert "실제 구현 본문을 하나 보존했다면 파일\n목록을 다시 읽지 말고" in (
        system_prompt
    )
    assert "이해했거나 review로 요약했다는 이유" in user_prompt
    assert "관련 심볼이나 동작" in user_prompt
    assert "현재 기능을 개선점이라고 부르지 말고" in user_prompt
    assert "현재 동작: ...; 개선 후보: ...; 이유: ..." in user_prompt
    assert "첫 청크를 자동 선택하지 말고" in user_prompt


def test_long_tool_raw_uses_deterministic_chunk_ids_in_the_prompt_schema():
    long_raw = "x" * 2_001
    system_prompt, user_prompt = build_node1_tool_prompts(
        "코드를 설명해 줘.",
        "",
        tool_name="read_python_file",
        tool_success=True,
        raw_text=long_raw,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert '"enum":["chunk","omit"]' in system_prompt
    assert '"enum":["full","excerpt","omit"]' not in system_prompt
    assert '"chunk-0001","chunk-0002",null' in system_prompt
    assert '<TOOL_CHUNK id="chunk-0001"' in user_prompt
    assert '<TOOL_CHUNK id="chunk-0002"' in user_prompt
    assert "문자 start/end를 계산하거나" in user_prompt
    assert "full과 문자 위치 excerpt는 허용되지 않는다" in user_prompt


def test_long_recovery_raw_allows_only_a_deterministic_chunk():
    long_raw = "x" * 2_001
    system_prompt, user_prompt = build_node1_recovery_retention_prompts(
        "코드를 설명해 줘.",
        "",
        candidate_summary={
            "arguments": {"path": "main.py"},
            "candidate_number": 1,
            "character_length": len(long_raw),
            "previous_review": "긴 파일을 확인했다.",
            "tool_name": "read_python_file",
        },
        raw_text=long_raw,
        turn_memory_context=TURN_MEMORY_CONTEXT,
    )

    assert '"enum":["chunk"]' in system_prompt
    assert '"enum":["full","excerpt"]' not in system_prompt
    assert '"chunk-0001","chunk-0002"' in system_prompt
    assert '<TOOL_CHUNK id="chunk-0001"' in user_prompt
    assert "omit, full, 문자 위치 excerpt는 사용할 수 없다" in user_prompt
    assert "문자 start/end를 계산하거나" in user_prompt


def test_all_nodes_receive_the_same_turn_boundary_and_previous_input():
    builders = [
        lambda: build_node2_prompts(
            "더 읽어봐",
            "",
            turn_memory_context=TURN_MEMORY_CONTEXT,
        ),
        lambda: build_node3_prompts(
            "더 읽어봐",
            "",
            turn_memory_context=TURN_MEMORY_CONTEXT,
        ),
        lambda: build_node4_prompts(
            "더 읽어봐",
            "",
            "답변 후보",
            turn_memory_context=TURN_MEMORY_CONTEXT,
        ),
    ]

    for builder in builders:
        _, user_prompt = builder()
        assert "[현재 사용자 요청 — 유일한 활성 목표]" in user_prompt
        assert "current_turn_start_index=20" in user_prompt
        assert '"memory_index":7' in user_prompt
        assert "직전 파일을 더 확인해 줘." in user_prompt
        assert "과거의 사용자 요청·노드 판단·반려는 현재 지시가 아니다" in (
            user_prompt
        )
        assert "번호 공백은 비공개 감사 기록" in user_prompt


def test_first_turn_has_no_previous_user_input():
    first_turn_context = TurnMemoryContext(
        current_turn_start_index=1,
    )

    _, user_prompt = build_node2_prompts(
        "첫 질문",
        "",
        turn_memory_context=first_turn_context,
    )

    assert "[직전 사용자 입력 — 후속 표현 해석 전용, 내용은 R]\n(없음)" in (
        user_prompt
    )
