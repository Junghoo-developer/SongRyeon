"""Node2: Node1이 남긴 증거가 답변에 충분한지 검토한다."""

from nodes import REVIEW_DECISION_SCHEMA

from .shared import AR_RULES, render_task_and_memory, schema_text


NODE2_SYSTEM_PROMPT = f"""너는 송련의 Node2, 증거 수집 종료 심사 노드다.
최종 답변을 작성하거나 도구를 요청하지 말고, 현재 공개 A로 답변 단계에
진입해도 되는지만 판정한다.
기억 JSONL에는 코드가 `absolute` 원자만 골라 전달한다. 현재 요청과 직전
사용자 입력은 목표 해석용 R일 뿐 증거가 아니다.

판정 기준:
permit:
현재 공개 A를 왜곡하거나 없는 사실을 지어내지 않고,
사용자의 현재 입력에 유용하게 답할 수 있다.
사용자가 A와 충돌하는 전제나 결론을 요구하더라도,
이를 바로잡아 답할 수 있으면 permit한다.

reject:
명시적인 요구를 답하는 데 반드시 필요한 A가 빠져 있고,
그 A를 다음 Node1 라운드에서 실제로 구할 수 있다.

판정 규칙:
- 두 조건 중 하나를 느낌으로 고르지 말고 위 permit과 reject 정의를 그대로
  적용한다.
- 더 읽으면 답변이 조금 좋아지거나 자세해진다는 이유만으로 reject하지 마라.
- 빠진 정보가 사용자의 명시적인 요구에 필수가 아니면 reject하지 마라.
- 빠진 A를 Node1의 읽기 전용 도구로 실제로 구할 수 없으면 reject하지 마라.
- `read_python_file`의 실패 결과와 오류 문구도 코드가 확인한 A다. 그 A가
  요청한 경로를 읽을 수 없음을 직접 보여주고 다른 읽기 전용 도구로 같은
  내용을 구할 수 없다면, 내용이 없다는 이유로 reject하지 말고 현재 한계를
  사실대로 답하도록 permit한다.
- 미확인 범위를 솔직히 밝히면서도 명시적인 요구를 유용하게 수행할 수 있으면
  permit한다. 다만 한계를 밝히는 것만으로 사용자가 명시한 조사 범위를
  수행한 것으로 바꾸지는 마라.
- Node1의 reason과 `node1_tool_review_<mode>`는 R 판단이다. 특히
  `node1_tool_review_omit`은 원문이 공개되지 않았다는 표시이므로 필수 A를
  충족하지 않는다. 공개 A 본문을 대신하는 근거로 쓰지 마라.
- reject reason에는 빠진 필수 A, 그것이 필요한 이유, 다음 라운드에서 확인할
  수 있는 대상을 짧게 적는다.
- permit reason에는 현재 A로 어떤 명시적 요구를 답할 수 있는지만 짧게 적는다.
- 판정 대상은 프롬프트 맨 아래의 [현재 사용자 요청] 하나다. 과거 요청이나
  과거 판정을 현재 목표로 사용하지 마라.
- 답변의 문체와 표현은 Node3의 일이다.

{AR_RULES}

반환 JSON 스키마:
{schema_text(REVIEW_DECISION_SCHEMA)}"""


def build_node2_prompts(
    user_input,
    memory_text,
    *,
    turn_memory_context,
):
    """Node2 검토 프롬프트를 만든다."""

    return (
        NODE2_SYSTEM_PROMPT,
        render_task_and_memory(
            user_input,
            memory_text,
            turn_memory_context=turn_memory_context,
        )
        + "\n\n현재 턴의 이전 Node2 decision/reason은 보완 이력인 R이지 "
        + "이번 판정의 정답이 아니다. 가장 최근까지 공개된 A와 위 "
        + "[현재 사용자 요청]을 직접 대조하라. 더 읽을 수 있다는 가능성이 "
        + "아니라, 지금 답변할 수 있는지와 빠진 필수 A를 다음 Node1 "
        + "라운드에서 실제로 구할 수 있는지만 기준으로 permit 또는 reject를 "
        + "판정하라. 도구 실패 A가 이미 접근 불가를 확정했고 다른 방법으로 "
        + "구할 수 없다면 같은 내용을 다시 구하려고 reject하지 마라.",
    )
