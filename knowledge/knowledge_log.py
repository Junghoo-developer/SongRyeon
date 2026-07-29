"""이전 import 경로를 위한 호환 모듈.

새 구현은 역할이 더 분명한 ``knowledge.memory_log``에 있다.
"""

from .memory_log import (
    KNOWLEDGE_RECORD_TYPES,
    KNOWLEDGE_VERSION_RECORD_TYPES,
    load_logged_knowledge_versions,
    save_knowledge_records,
)

__all__ = [
    "KNOWLEDGE_RECORD_TYPES",
    "KNOWLEDGE_VERSION_RECORD_TYPES",
    "load_logged_knowledge_versions",
    "save_knowledge_records",
]
