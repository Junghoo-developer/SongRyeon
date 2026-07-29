"""이전 import 경로를 위한 호환 모듈.

새 코드는 소문자 파일인 ``memory.agent_view`` 또는 ``memory`` 패키지에서
가져온다. 이 파일은 기존 학습 코드가 한 번에 깨지지 않도록 재수출만 한다.
"""

from .agent_view import (
    AGENT_VIEW_FIELDS,
    AGENT_VISIBLE_FIELDS,
    format_agent_memory,
    load_agent_memory,
)
from .settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    KNOWLEDGE_INFORMATION_TYPE_PREFIX,
    QWEN3_14B_CONTEXT_TOKENS,
)

# 예전 이름을 사용하던 코드도 같은 8,000자 정책을 보게 한다.
DEFAULT_MEMORY_CHARACTER_LIMIT = DEFAULT_AGENT_VIEW_CHARACTER_LIMIT

__all__ = [
    "AGENT_VIEW_FIELDS",
    "AGENT_VISIBLE_FIELDS",
    "DEFAULT_MEMORY_CHARACTER_LIMIT",
    "KNOWLEDGE_INFORMATION_TYPE_PREFIX",
    "QWEN3_14B_CONTEXT_TOKENS",
    "format_agent_memory",
    "load_agent_memory",
]
