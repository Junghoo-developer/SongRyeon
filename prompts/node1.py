"""Node1: 필요한 코드 증거를 모으고 다음 행동을 고른다."""

import json

from agent_tools import LIST_PYTHON_FILES, READ_PYTHON_FILE
from nodes import (
    DEFAULT_MAX_SELECTED_CHARACTERS,
    NODE1_ACTION_SCHEMA,
    NODE1_RECOVERY_CHOICE_SCHEMA,
    build_text_chunks,
    node1_recovery_retention_schema,
    node1_tool_decision_schema,
)

from .shared import AR_RULES, render_task_and_memory, schema_text


NODE1_SYSTEM_PROMPT = f"""너는 송련의 Node1, 유일한 증거 수집 노드이자 원문 공개 관문이다.
에이전트 루프에서 읽기 전용 도구를 사용할 수 있는 노드는 Node1뿐이다.
Node2, Node3, Node4는 도구를 사용할 수 없고 Node1이 남기지 않은 원문을 직접 확인할 수 없다.
사용자 요청에 답하고 검증하는 데 충분한 증거를 확보할 때까지 읽기 전용 도구를 사용한다.
한 라운드에서 도구를 최대 3회 요청할 수 있고, 세 번째 뒤에는 코드가 Node2로 보낸다.
현재 사용자 턴 전체에서 같은 도구와 같은 arguments를 반복 요청하지 마라.
코드는 이미 실행한 동일 요청을 다시 실행하지 않고 Node2로 보낸다.
`아무 코드나` 검토하라는 요청에서 실제 구현 본문을 하나 보존했다면 파일
목록을 다시 읽지 말고 Node2로 라우팅하라.
도구 원문을 본 뒤에는 다음 노드에 남길 본문과 짧은 review를 정한다.
Node2는 증거를 고르지 않는다. 무엇을 남길지는 Node1의 책임이다.
공유 기억의 `node1_tool_review_omit`은 원문 없는 과거 R 단서다. 그 내용을
확인된 코드 사실로 취급하지 말고, 필요한 공개 A를 고르는 데만 참고하라.
현재 턴 범위에 Node2의 reject가 있으면 그 이유를 이번 라운드의 필수
보완 단서로 취급하되, 현재 사용자 요청 안에서 빠진 범위를 채우는 데만
사용하라. reason이 사용자 요청 밖의 새 요구를 추가하면 그 부분은 따르지
마라. 과거 턴의 reject와 도구 횟수는 현재 상태로
간주하지 마라. 필요한 도구를 다시 사용하지 않은 채 같은 route_node2를
반복하지 마라.
판단 대상은 사용자 프롬프트 맨 아래의 [현재 사용자 요청] 하나뿐이다.
사용자가 확인하라고 명시한 정확한 `.py` 경로는 파일 목록에서 확인되지
않았더라도 {READ_PYTHON_FILE}로 직접 시도하라. 호출의 성공·실패 결과와
오류 문구 자체가 다음 노드가 사용할 공개 A다. 경로의 존재 여부나 허용
여부를 미리 추측하지 말고 도구의 실제 결과로 확인하라.

사용 가능한 도구:
- {LIST_PYTHON_FILES}: arguments={{}}
- {READ_PYTHON_FILE}: arguments={{"path":"사용자가 명시한 정확한 .py 경로 또는 목록에서 확인한 상대경로.py"}}

{AR_RULES}"""


def _long_raw_chunks(raw_text):
    """런타임과 같은 규칙으로 긴 원문의 청크를 만든다."""

    return build_text_chunks(
        raw_text,
        DEFAULT_MAX_SELECTED_CHARACTERS,
    )


def _render_chunked_raw(chunks):
    """모델이 문자 위치 계산 없이 ID와 본문을 대응시켜 보게 한다."""

    return "\n".join(
        (
            f'<TOOL_CHUNK id="{chunk.chunk_id}" '
            f'character_length="{len(chunk.content)}">\n'
            f"{chunk.content}"
            f'\n</TOOL_CHUNK id="{chunk.chunk_id}">'
        )
        for chunk in chunks
    )


def build_node1_action_prompts(
    user_input,
    memory_text,
    *,
    turn_memory_context,
):
    """도구 사용 전 Node1의 첫 행동 프롬프트를 만든다."""

    system_prompt = (
        NODE1_SYSTEM_PROMPT
        + "\n\n반환 JSON 스키마:\n"
        + schema_text(NODE1_ACTION_SCHEMA)
    )
    user_prompt = (
        render_task_and_memory(
            user_input,
            memory_text,
            turn_memory_context=turn_memory_context,
        )
        + "\n\n위 [현재 사용자 요청]에 지금 필요한 다음 행동 하나만 JSON으로 반환하라. "
        "코드를 볼 필요가 없거나 증거가 충분하면 route_node2를 선택하라."
    )
    return system_prompt, user_prompt


def build_node1_tool_prompts(
    user_input,
    memory_text,
    *,
    turn_memory_context,
    tool_name,
    tool_success,
    raw_text,
    response_schema=None,
):
    """도구 원문을 이번 호출에서만 Node1에게 보여주는 프롬프트를 만든다."""

    if not isinstance(raw_text, str):
        raise TypeError("raw_text는 문자열이어야 합니다.")

    allow_full = len(raw_text) <= DEFAULT_MAX_SELECTED_CHARACTERS
    chunks = [] if allow_full else _long_raw_chunks(raw_text)
    if response_schema is None:
        response_schema = node1_tool_decision_schema(
            allow_full=allow_full,
            chunk_ids=[
                chunk.chunk_id
                for chunk in chunks
            ] or None,
        )

    if allow_full:
        raw_section = (
            "<TOOL_RAW_TEXT>\n"
            + raw_text
            + "\n</TOOL_RAW_TEXT>"
        )
        retention_rules = (
            "- 다음 노드가 답변하거나 검증할 때 원문이 필요하지 않은 경우에만 "
            "omit하라.\n"
            "- Node1이 이해했거나 review로 요약했다는 이유만으로 원문을 "
            "omit하지 마라.\n"
            f"- 사용자가 특정 파일의 역할이나 규칙을 물었고 원문이 "
            f"{DEFAULT_MAX_SELECTED_CHARACTERS:,}자 이하라면 일부만 자르지 "
            "말고 full로 남겨라.\n"
            "- 원문 전체가 꼭 필요할 때만 full을 사용하라.\n"
            "- excerpt는 Python 문자열 기준 start 포함, end 미포함 위치를 "
            f"사용하고 선택 길이를 {DEFAULT_MAX_SELECTED_CHARACTERS:,}자 "
            "이하로 하라.\n"
            "- full 또는 omit이면 start와 end를 모두 null로 반환하고, "
            "excerpt일 때만 두 값을 정수로 반환하라.\n"
        )
    else:
        raw_section = (
            "[코드가 결정론적으로 나눈 도구 원문 청크]\n"
            + _render_chunked_raw(chunks)
        )
        retention_rules = (
            "- 다음 노드가 답변하거나 검증할 때 원문이 필요하지 않은 경우에만 "
            "omit하고 chunk_id는 null로 반환하라.\n"
            "- 원문이 필요하면 표시된 chunk_id 하나를 그대로 선택하라.\n"
            "- 문자 start/end를 계산하거나 원문 일부를 새로 작성하지 마라.\n"
            f"- 각 청크는 코드가 줄 경계를 우선해 "
            f"{DEFAULT_MAX_SELECTED_CHARACTERS:,}자 이하로 만들었다.\n"
            "- Node1이 이해했거나 review로 요약했다는 이유만으로 원문을 "
            "omit하지 마라.\n"
            f"- 이 원문은 {DEFAULT_MAX_SELECTED_CHARACTERS:,}자를 초과하므로 "
            "full과 문자 위치 excerpt는 허용되지 않는다.\n"
        )
    system_prompt = (
        NODE1_SYSTEM_PROMPT
        + "\n\n반환 JSON 스키마:\n"
        + schema_text(response_schema)
    )
    user_prompt = (
        render_task_and_memory(
            user_input,
            memory_text,
            turn_memory_context=turn_memory_context,
        )
        + "\n\n[이번 호출에서만 볼 수 있는 도구 원문]\n"
        + f"tool_name={tool_name}\n"
        + f"success={tool_success}\n"
        + f"character_length={len(raw_text)}\n"
        + raw_section
        + "\n\n"
        + "원문을 검토하고 retention과 next_action을 반환하라.\n"
        + retention_rules
        + "- review는 원문을 복사하는 곳이 아니라 무엇을 확인했는지 적는 R 판단이다.\n"
        + "- 설명·검토·개선 요청에서는 다음 노드가 실제 답을 만들 수 있도록 "
        + "관련 심볼이나 동작, 확인한 문제 또는 결론을 구체적으로 적어라.\n"
        + "- 개선 요청이면 review를 `현재 동작: ...; 개선 후보: ...; 이유: ...` "
        + "형식으로 간단히 쓴다. 현재 기능을 개선점이라고 부르지 말고, "
        + "원문에서 확인한 동작과 네가 제안하는 변경을 분리하라. 개선 후보와 "
        + "이유는 R 판단이며 보존 본문에 그 제안이 이미 적혀 있을 필요는 없다.\n"
        + "- 여러 청크 중 하나를 남길 때는 첫 청크를 자동 선택하지 말고 "
        + "review의 핵심 결론을 직접 뒷받침하는 청크를 선택하라."
    )
    return system_prompt, user_prompt


NODE1_RECOVERY_SYSTEM_PROMPT = f"""너는 송련의 Node1, 유일한 원문 공개 관문이다.
코드가 현재 라운드의 성공한 도구 원문이 전부 omit됐음을 확인했다.
Node2, Node3, Node4는 omit된 원문을 직접 볼 수 없으므로 Node2로 보내기 전에
후속 답변과 검증에 가장 중요한 원문 하나를 최종적으로 복구해야 한다.
이 절차에서는 새 도구를 요청하거나 라우팅을 바꿀 수 없다.

{AR_RULES}"""


def build_node1_recovery_choice_prompts(
    user_input,
    memory_text,
    candidate_summaries,
    *,
    turn_memory_context,
):
    """숨긴 원문 자체를 합치지 않고 Node1이 복구 후보 하나를 고르게 한다."""

    if not isinstance(candidate_summaries, list) or not candidate_summaries:
        raise ValueError("candidate_summaries에는 후보가 하나 이상 필요합니다.")

    candidate_text = "\n".join(
        json.dumps(
            summary,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for summary in candidate_summaries
    )
    system_prompt = (
        NODE1_RECOVERY_SYSTEM_PROMPT
        + "\n\n반환 JSON 스키마:\n"
        + schema_text(NODE1_RECOVERY_CHOICE_SCHEMA)
    )
    user_prompt = (
        render_task_and_memory(
            user_input,
            memory_text,
            turn_memory_context=turn_memory_context,
        )
        + "\n\n[최종 보존 재선택 후보]\n"
        + candidate_text
        + "\n\n후보 목록에는 원문이 아니라 이전 review와 도구 정보만 있다. "
        + "사용자 목표를 완수하는 데 가장 중요한 원문 하나의 "
        + "candidate_number를 반환하라."
    )
    return system_prompt, user_prompt


def build_node1_recovery_retention_prompts(
    user_input,
    memory_text,
    *,
    turn_memory_context,
    candidate_summary,
    raw_text,
    response_schema=None,
):
    """고른 원문을 다시 보여주고 짧으면 기존 방식, 길면 청크로 복구한다."""

    if not isinstance(candidate_summary, dict):
        raise TypeError("candidate_summary는 dict여야 합니다.")

    if not isinstance(raw_text, str):
        raise TypeError("raw_text는 문자열이어야 합니다.")

    allow_full = len(raw_text) <= DEFAULT_MAX_SELECTED_CHARACTERS
    chunks = [] if allow_full else _long_raw_chunks(raw_text)
    if response_schema is None:
        response_schema = node1_recovery_retention_schema(
            allow_full=allow_full,
            chunk_ids=[
                chunk.chunk_id
                for chunk in chunks
            ] or None,
        )

    if allow_full:
        raw_section = (
            "<TOOL_RAW_TEXT>\n"
            + raw_text
            + "\n</TOOL_RAW_TEXT>"
        )
        allowed_retention_text = "full 또는 excerpt"
        retention_rules = (
            "- omit은 사용할 수 없다.\n"
            f"- 원문 전체가 필요하고 {DEFAULT_MAX_SELECTED_CHARACTERS:,}자 "
            "이하라면 full을 사용하라.\n"
            "- 일부만 필요하면 start 포함, end 미포함 위치로 excerpt를 "
            "선택하라.\n"
            f"- 선택 길이는 {DEFAULT_MAX_SELECTED_CHARACTERS:,}자 이하여야 한다.\n"
            "- full이면 start와 end를 모두 null로 반환하고, excerpt일 때만 "
            "두 값을 정수로 반환하라.\n"
        )
    else:
        raw_section = (
            "[코드가 결정론적으로 나눈 최종 복구 원문 청크]\n"
            + _render_chunked_raw(chunks)
        )
        allowed_retention_text = "chunk"
        retention_rules = (
            "- omit, full, 문자 위치 excerpt는 사용할 수 없다.\n"
            "- 표시된 chunk_id 하나를 그대로 선택하라.\n"
            "- 문자 start/end를 계산하거나 원문 일부를 새로 작성하지 마라.\n"
            f"- 각 청크는 코드가 줄 경계를 우선해 "
            f"{DEFAULT_MAX_SELECTED_CHARACTERS:,}자 이하로 만들었다.\n"
        )
    summary_text = json.dumps(
        candidate_summary,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    system_prompt = (
        NODE1_RECOVERY_SYSTEM_PROMPT
        + "\n\n반환 JSON 스키마:\n"
        + schema_text(response_schema)
    )
    user_prompt = (
        render_task_and_memory(
            user_input,
            memory_text,
            turn_memory_context=turn_memory_context,
        )
        + "\n\n[최종 보존 대상으로 고른 도구 결과]\n"
        + summary_text
        + "\ncharacter_length="
        + str(len(raw_text))
        + "\n"
        + raw_section
        + "\n\n"
        + "retention 객체에서 후속 노드가 사용할 정확한 A 원문을 "
        + allowed_retention_text
        + "로 남겨라.\n"
        + retention_rules
        + "- review에는 무엇을 보존했고 사용자 목표에 왜 필요한지 적어라.\n"
        + "- 설명·검토·개선 요청이면 관련 심볼이나 동작과 확인한 결론을 "
        + "구체적으로 적고, 그 결론을 직접 뒷받침하는 본문을 선택하라.\n"
        + "- 개선 요청이면 review를 `현재 동작: ...; 개선 후보: ...; 이유: ...` "
        + "형식으로 쓰고, 개선 후보와 이유는 R 판단으로 제안하라."
    )
    return system_prompt, user_prompt
