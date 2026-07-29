"""송련이 검색할 소스 코드와 외부 문서를 관리하는 공개 진입점.

학습 순서:

1. ``settings.py`` - 경로와 허용 종류
2. ``source_files.py`` - 파일 탐색·읽기·hash
3. ``database.py`` - SQLite 저장·조회
4. ``memory_log.py`` - 파일 원본을 기억 로그에 보존
5. ``indexer.py`` - 위 단계들의 실행 순서
"""

from .database import (
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
from .memory_log import (
    KNOWLEDGE_RECORD_TYPES,
    load_logged_knowledge_versions,
    save_knowledge_records,
)
from .settings import DOCUMENT, PYTHON_SOURCE

__all__ = [
    "DOCUMENT",
    "KNOWLEDGE_RECORD_TYPES",
    "PYTHON_SOURCE",
    "get_indexed_file",
    "index_documents",
    "index_file",
    "index_python_sources",
    "initialize_knowledge_db",
    "list_indexed_files",
    "load_logged_knowledge_versions",
    "save_knowledge_records",
    "sync_knowledge",
]
