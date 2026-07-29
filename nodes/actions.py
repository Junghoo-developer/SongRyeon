"""Node1의 다음 도구 또는 Node2 라우팅 출력 계약."""

import json
from dataclasses import dataclass

from .common import validate_short_reason
from .retention import RetentionDecision


NODE1_ACTIONS = {"use_tool", "route_node2"}
MAX_NODE1_ACTION_ARGUMENT_CHARACTERS = 1_024


def _only_string_object_keys(value):
    """LLM JSON 객체처럼 모든 중첩 dict key가 문자열인지 확인한다."""

    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and _only_string_object_keys(child)
            for key, child in value.items()
        )

    if isinstance(value, list):
        return all(_only_string_object_keys(child) for child in value)

    return True


@dataclass(frozen=True)
class Node1Action:
    """Node1이 다음 도구를 요청하거나 Node2로 이동하라는 상대 판단."""

    action: str
    reason: str
    tool_name: str | None = None
    arguments: dict | None = None

    def __post_init__(self):
        if self.action not in NODE1_ACTIONS:
            raise ValueError(f"알 수 없는 Node1 행동입니다: {self.action}")

        validate_short_reason(self.reason, "reason")

        if self.action == "use_tool":
            if not isinstance(self.tool_name, str) or not self.tool_name:
                raise ValueError("use_tool에는 tool_name이 필요합니다.")

            if not isinstance(self.arguments, dict):
                raise ValueError("use_tool에는 arguments 객체가 필요합니다.")

            try:
                valid_keys = _only_string_object_keys(self.arguments)
                serialized_arguments = json.dumps(
                    self.arguments,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            except (RecursionError, TypeError, ValueError) as error:
                raise ValueError(
                    "arguments는 일반 JSON 객체여야 합니다."
                ) from error

            if not valid_keys:
                raise ValueError(
                    "arguments의 모든 JSON 객체 key는 문자열이어야 합니다."
                )

            if (
                len(serialized_arguments)
                > MAX_NODE1_ACTION_ARGUMENT_CHARACTERS
            ):
                raise ValueError("arguments가 최대 길이를 초과했습니다.")

            # 호출 후 외부 dict 변경이 결정 객체에 바로 반영되지 않게 복사한다.
            object.__setattr__(
                self,
                "arguments",
                json.loads(serialized_arguments),
            )
            return

        if self.tool_name is not None or self.arguments is not None:
            raise ValueError(
                "route_node2에는 tool_name이나 arguments가 없어야 합니다."
            )


@dataclass(frozen=True)
class Node1ToolDecision:
    """도구 결과를 본 Node1의 보존 결정과 다음 행동 묶음."""

    retention: RetentionDecision
    next_action: Node1Action

    def __post_init__(self):
        if not isinstance(self.retention, RetentionDecision):
            raise TypeError("retention은 RetentionDecision이어야 합니다.")

        if not isinstance(self.next_action, Node1Action):
            raise TypeError("next_action은 Node1Action이어야 합니다.")
