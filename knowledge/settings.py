"""지식 색인 기능이 공유하는 경로와 허용값.

구현 파일의 위치가 바뀌더라도 ``knowledge.db``, ``documents``와
``memory.jsonl`` 위치는 이 파일의 설정만 따라가도록 분리했다.
"""

from pathlib import Path

from memory.settings import DEFAULT_MEMORY_PATH, PROJECT_ROOT


KNOWLEDGE_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_DB_PATH = KNOWLEDGE_DIRECTORY / "knowledge.db"
DEFAULT_DOCUMENTS_DIRECTORY = KNOWLEDGE_DIRECTORY / "documents"
DEFAULT_PROJECT_ROOT = PROJECT_ROOT

PYTHON_SOURCE = "python_source"
DOCUMENT = "document"
SOURCE_TYPES = {PYTHON_SOURCE, DOCUMENT}

DOCUMENT_EXTENSIONS = {
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".codex-remote-attachments",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    "build",
    "dist",
    "tmp",
    "__pycache__",
    "venv",
}


def validate_source_type(source_type):
    """지원하는 지식 종류인지 확인한다."""

    if source_type not in SOURCE_TYPES:
        raise ValueError(f"지원하지 않는 source_type입니다: {source_type}")
