"""송련의 원본 기억과 에이전트 시야를 관리하는 공개 진입점.

처음 코드를 읽을 때는 아래 순서로 보면 된다.

1. :mod:`memory.record` - 원자 기록 7필드를 만든다.
2. :mod:`memory.store` - 완성된 기록을 ``memory.jsonl``에 추가한다.
3. :mod:`memory.agent_view` - 원본에서 에이전트에게 보여줄 부분만 고른다.
"""

from .agent_view import (
    AGENT_VIEW_FIELDS,
    AGENT_VISIBLE_FIELDS,
    AgentMemoryFloor,
    AgentMemoryFloorError,
    TurnMemoryContext,
    TurnMemoryContextError,
    freeze_agent_memory_floor,
    format_agent_memory,
    load_frozen_agent_memory,
    load_agent_memory,
    load_turn_memory_context,
)
from .conversation_records import (
    save_final_delivery,
    save_node3_answer,
    save_user_input,
)
from .record import create_information_record
from .settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)
from .store import (
    MemoryLogCorruptionError,
    append_information_records,
    save_information_record,
)

__all__ = [
    "AGENT_VISIBLE_FIELDS",
    "AGENT_VIEW_FIELDS",
    "AgentMemoryFloor",
    "AgentMemoryFloorError",
    "DEFAULT_AGENT_VIEW_CHARACTER_LIMIT",
    "DEFAULT_MEMORY_PATH",
    "MemoryLogCorruptionError",
    "TurnMemoryContext",
    "TurnMemoryContextError",
    "append_information_records",
    "create_information_record",
    "freeze_agent_memory_floor",
    "format_agent_memory",
    "load_agent_memory",
    "load_frozen_agent_memory",
    "load_turn_memory_context",
    "save_final_delivery",
    "save_information_record",
    "save_node3_answer",
    "save_user_input",
]
