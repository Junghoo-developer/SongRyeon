from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.runtime.terminal_view import render_chat_answer


@dataclass
class ChatSessionMemory:
    """qwen-chat 한 세션 안에서 다음 턴의 ZeroState로 넘길 최소 기억 상태."""

    turn_index: int = 1
    recent_raw_conversation: list[dict[str, str]] = field(default_factory=list)
    previous_turn_capsules: list[TurnStateCapsule] = field(default_factory=list)


def current_chat_turn_id(session_memory: ChatSessionMemory) -> str:
    return f"turn_chat_{session_memory.turn_index:04d}"


def attach_chat_session_snapshot(
    *,
    result: dict[str, object],
    session_memory: ChatSessionMemory,
    current_turn_id: str,
) -> None:
    result["session_memory"] = {
        "current_turn_id": current_turn_id,
        "recent_raw_conversation_count": len(session_memory.recent_raw_conversation),
        "previous_turn_capsule_count": len(session_memory.previous_turn_capsules),
    }


def store_chat_turn_result(
    *,
    session_memory: ChatSessionMemory,
    current_turn_id: str,
    user_input: str,
    result: dict[str, object],
) -> bool:
    capsule = turn_capsule_from_result(result)
    stored = False
    if capsule is not None:
        assistant_text = render_chat_answer(result, user_input=user_input)
        session_memory.recent_raw_conversation.append(
            {
                "turn_id": current_turn_id,
                "user_text": user_input,
                "assistant_text": assistant_text,
            }
        )
        session_memory.previous_turn_capsules.append(capsule)
        stored = True
    session_memory.turn_index += 1
    return stored


def turn_capsule_from_result(result: dict[str, object]) -> TurnStateCapsule | None:
    payload = result.get("turn_capsule")
    if not isinstance(payload, dict):
        return None
    movements_payload = payload.get("node_movements")
    movements: list[NodeMovement] = []
    if isinstance(movements_payload, list):
        for item in movements_payload:
            if isinstance(item, NodeMovement):
                movements.append(item)
            elif isinstance(item, dict):
                movements.append(NodeMovement(**item))
    return TurnStateCapsule(
        turn_id=str(payload.get("turn_id") or ""),
        node_movements=movements,
        trace_event_ids=_string_list(payload.get("trace_event_ids")),
        user_input_trace_id=_optional_text(payload.get("user_input_trace_id")),
        final_response_trace_id=_optional_text(payload.get("final_response_trace_id")),
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _optional_text(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
