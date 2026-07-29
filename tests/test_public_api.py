"""새 공개 API와 예전 import 호환 파일이 같은 구현을 가리키는지 검사한다."""

from knowledge import index_python_sources, save_knowledge_records
from knowledge.knowledge_log import (
    save_knowledge_records as legacy_save_knowledge_records,
)
from knowledge.knowledge_store import (
    index_python_sources as legacy_index_python_sources,
)
from memory import (
    create_information_record,
    load_agent_memory,
    save_information_record,
)
from memory.Agent_memory import (
    DEFAULT_MEMORY_CHARACTER_LIMIT,
    KNOWLEDGE_INFORMATION_TYPE_PREFIX,
    QWEN3_14B_CONTEXT_TOKENS,
    load_agent_memory as legacy_load_agent_memory,
)
from metadata.create_information_record import (
    create_information_record as legacy_create_information_record,
)
from metadata.save_information_record import (
    save_information_record as legacy_save_information_record,
)


def test_legacy_imports_reexport_the_new_implementations():
    assert legacy_create_information_record is create_information_record
    assert legacy_save_information_record is save_information_record
    assert legacy_load_agent_memory is load_agent_memory
    assert legacy_save_knowledge_records is save_knowledge_records
    assert legacy_index_python_sources is index_python_sources


def test_legacy_agent_memory_constants_remain_available():
    assert DEFAULT_MEMORY_CHARACTER_LIMIT == 8_000
    assert QWEN3_14B_CONTEXT_TOKENS == 40_960
    assert KNOWLEDGE_INFORMATION_TYPE_PREFIX == "knowledge_"
