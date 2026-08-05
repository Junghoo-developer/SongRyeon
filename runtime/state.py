"""한 사용자 턴 동안 코드가 보존하는 카운터와 결과 형식.

이 파일에는 모델 호출이나 파일 저장이 없다. 런타임이 기억해야 할 상태를
작은 dataclass로 이름 붙이는 층이다. 먼저 이 자료형을 읽고 ``runner.py``를
보면 각 분기에서 무엇이 변하는지 추적하기 쉽다.
"""

from dataclasses import dataclass, field
from uuid import uuid4

from agent_tools import ToolResult
from nodes.common import validate_relative_text


NODE1 = "node1"
NODE2 = "node2"
NODE3 = "node3"
NODE4 = "node4"
FINAL = "final"

MAX_NODE1_TOOL_CALLS_PER_ROUND = 3
MAX_REJECTIONS_PER_GATE = 3


@dataclass(frozen=True)
class ToolObservation:
    """숨김 저장이 끝나 Node1이 이번 호출에서 직접 검토할 결과."""

    record_turn_id: str
    source_information_id: str
    memory_path: str
    result: ToolResult
    round_number: int
    attempt_number: int


@dataclass(frozen=True)
class OmittedToolCandidate:
    """Node1이 omit했지만 최종 보존 때 다시 열 수 있는 성공 원문."""

    observation: ToolObservation
    review: str

    def __post_init__(self):
        if not isinstance(self.observation, ToolObservation):
            raise TypeError("observation은 ToolObservation이어야 합니다.")

        if not self.observation.result.success:
            raise ValueError("성공한 도구 결과만 복구 후보가 될 수 있습니다.")

        validate_relative_text(self.review, "review")


@dataclass
class TurnState:
    """사용자 입력 하나를 처리하는 동안 코드가 보존할 카운터."""

    # Node1 라운드는 Node2가 reject를 실제 적용할 때만 증가한다.
    turn_id: str
    node1_round: int = 1
    node1_tool_calls_in_round: int = 0
    # 실행이 끝난 정확한 도구 요청은 라운드가 바뀌어도 턴 동안 유지한다.
    node1_tool_request_signatures: set[str] = field(default_factory=set)
    node2_rejections: int = 0
    node4_rejections: int = 0
    node1_omit_recovery_used: bool = False
    node2_limit_exhausted: bool = False
    node4_limit_exhausted: bool = False


@dataclass(frozen=True)
class GateResolution:
    """Node2 또는 Node4 판단을 코드 규칙으로 적용한 결과."""

    reviewer: str
    next_node: str
    outcome: str
    rejection_count: int
    rejection_ignored: bool


@dataclass(frozen=True)
class RouteResolution:
    """Node1 요청과 도구 상한을 코드가 적용한 실제 다음 경로."""

    requested_action: str
    next_node: str
    outcome: str
    forced_by_tool_limit: bool


def create_turn_state(turn_id=None):
    """고유 ID를 가진 새 사용자 턴 상태를 만든다."""

    if turn_id is None:
        turn_id = f"turn-{uuid4()}"

    if not isinstance(turn_id, str) or not turn_id.strip():
        raise ValueError("turn_id는 비어 있지 않은 문자열이어야 합니다.")

    return TurnState(turn_id=turn_id)
