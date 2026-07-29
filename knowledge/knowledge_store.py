"""이전 ``knowledge.knowledge_store`` import를 위한 호환 모듈.

새 코드는 가능하면 ``knowledge`` 공개 진입점에서 가져온다. 실제 구현은
설정·DB·파일·동기화 모듈로 나뉘어 있어 이 파일에는 로직이 없다.
"""

from .database import (
    CREATE_TABLE_SQL,
    LOG_MARKER_COLUMNS,
    get_indexed_file,
    initialize_knowledge_db,
    list_indexed_files,
)
from .indexer import (
    index_documents,
    index_file,
    index_python_sources,
    sync_knowledge,
)
from .memory_log import save_knowledge_records
from .settings import (
    DEFAULT_DB_PATH,
    DEFAULT_DOCUMENTS_DIRECTORY,
    DEFAULT_MEMORY_PATH,
    DEFAULT_PROJECT_ROOT,
    DOCUMENT,
    DOCUMENT_EXTENSIONS,
    EXCLUDED_DIRECTORY_NAMES,
    KNOWLEDGE_DIRECTORY,
    PYTHON_SOURCE,
    SOURCE_TYPES,
)

__all__ = [
    "CREATE_TABLE_SQL",
    "DEFAULT_DB_PATH",
    "DEFAULT_DOCUMENTS_DIRECTORY",
    "DEFAULT_MEMORY_PATH",
    "DEFAULT_PROJECT_ROOT",
    "DOCUMENT",
    "DOCUMENT_EXTENSIONS",
    "EXCLUDED_DIRECTORY_NAMES",
    "KNOWLEDGE_DIRECTORY",
    "LOG_MARKER_COLUMNS",
    "PYTHON_SOURCE",
    "SOURCE_TYPES",
    "get_indexed_file",
    "index_documents",
    "index_file",
    "index_python_sources",
    "initialize_knowledge_db",
    "list_indexed_files",
    "save_knowledge_records",
    "sync_knowledge",
]
