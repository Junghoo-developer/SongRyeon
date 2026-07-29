"""파일 시스템, SQLite DB와 원본 기억 로그의 동기화 순서를 조정한다.

여기는 업무 흐름 담당이다. 파일 읽기는 ``source_files.py``, SQL은
``database.py``, 원본 로그 형식은 ``memory_log.py``에 맡긴다.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .database import (
    delete_indexed_file,
    indexed_rows_for_source,
    initialize_knowledge_db,
    update_log_marker,
    upsert_prepared_file,
)
from .memory_log import save_knowledge_records
from .settings import (
    DEFAULT_DB_PATH,
    DEFAULT_DOCUMENTS_DIRECTORY,
    DEFAULT_MEMORY_PATH,
    DEFAULT_PROJECT_ROOT,
    DOCUMENT,
    PYTHON_SOURCE,
    validate_source_type,
)
from .source_files import (
    find_document_files,
    find_python_source_files,
    prepare_file,
)


def _memory_log_needs_full_backfill(memory_path):
    """원본 로그가 없거나 비어 있어 DB 내용을 다시 기록해야 하는지 확인한다."""

    path = Path(memory_path)
    return not path.exists() or path.stat().st_size == 0


def _save_and_mark_knowledge_version(
    connection,
    prepared_file,
    source_type,
    status,
    log_marker,
    memory_path,
    force_backfill,
):
    """필요한 파일 버전을 원본 로그에 쓴 뒤 DB에 완료 표시를 남긴다."""

    logged_content_hash, memory_turn_id, logged_memory_path = log_marker
    resolved_memory_path = str(Path(memory_path).resolve())
    needs_log = (
        force_backfill
        or logged_content_hash != prepared_file["content_hash"]
        or memory_turn_id is None
        or logged_memory_path != resolved_memory_path
    )

    if not needs_log:
        return

    log_status = "backfilled" if status == "unchanged" else status
    records = save_knowledge_records(
        source_type=source_type,
        path=prepared_file["path"],
        status=log_status,
        content_hash=prepared_file["content_hash"],
        content=prepared_file["content"],
        memory_path=memory_path,
    )

    update_log_marker(
        connection=connection,
        prepared_file=prepared_file,
        source_type=source_type,
        content_hash=prepared_file["content_hash"],
        memory_turn_id=records[0]["turn_id"],
        memory_path=resolved_memory_path,
    )


def _record_and_delete_removed_files(
    connection,
    source_type,
    current_paths,
    memory_path,
):
    """사라진 파일의 마지막 본문을 로그에 남긴 후 DB에서 삭제한다."""

    removed_count = 0

    for path, content, content_hash in indexed_rows_for_source(
        connection,
        source_type,
    ):
        if path in current_paths:
            continue

        # 로그 저장이 실패하면 아래 DB 삭제까지 진행하지 않는다.
        save_knowledge_records(
            source_type=source_type,
            path=path,
            status="removed",
            content_hash=content_hash,
            content=content,
            memory_path=memory_path,
        )
        delete_indexed_file(connection, source_type, path)
        removed_count += 1

    return removed_count


def index_file(
    file_path,
    source_type,
    root_directory,
    db_path=DEFAULT_DB_PATH,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """허용된 폴더 안의 UTF-8 파일 하나를 색인한다."""

    validate_source_type(source_type)
    prepared_file = prepare_file(file_path, root_directory)
    db = initialize_knowledge_db(db_path)
    indexed_at = datetime.now(timezone.utc).isoformat()
    force_backfill = _memory_log_needs_full_backfill(memory_path)

    with sqlite3.connect(db) as connection:
        status, log_marker = upsert_prepared_file(
            connection,
            prepared_file,
            source_type,
            indexed_at,
        )
        _save_and_mark_knowledge_version(
            connection,
            prepared_file,
            source_type,
            status,
            log_marker,
            memory_path,
            force_backfill,
        )

    return status


def _sync_files(
    files,
    source_type,
    root_directory,
    db_path,
    memory_path,
):
    """한 종류의 현재 파일 목록을 DB·원본 로그와 맞춘다."""

    validate_source_type(source_type)
    prepared_files = [
        prepare_file(file_path, root_directory)
        for file_path in files
    ]
    current_paths = {
        prepared_file["path"]
        for prepared_file in prepared_files
    }
    report = {
        "added": 0,
        "updated": 0,
        "unchanged": 0,
        "removed": 0,
    }
    force_backfill = _memory_log_needs_full_backfill(memory_path)
    db = initialize_knowledge_db(db_path)
    indexed_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(db) as connection:
        for prepared_file in prepared_files:
            status, log_marker = upsert_prepared_file(
                connection,
                prepared_file,
                source_type,
                indexed_at,
            )
            report[status] += 1
            _save_and_mark_knowledge_version(
                connection,
                prepared_file,
                source_type,
                status,
                log_marker,
                memory_path,
                force_backfill,
            )

        report["removed"] = _record_and_delete_removed_files(
            connection,
            source_type,
            current_paths,
            memory_path,
        )

    return report


def index_python_sources(
    project_root=DEFAULT_PROJECT_ROOT,
    db_path=DEFAULT_DB_PATH,
    memory_path=DEFAULT_MEMORY_PATH,
    *,
    documents_directory=None,
):
    """프로젝트의 현재 Python 소스들을 DB와 원본 로그에 동기화한다."""

    root = Path(project_root).resolve()
    return _sync_files(
        find_python_source_files(root, documents_directory),
        PYTHON_SOURCE,
        root,
        db_path,
        memory_path,
    )


def index_documents(
    documents_directory=DEFAULT_DOCUMENTS_DIRECTORY,
    db_path=DEFAULT_DB_PATH,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """외부 문서 폴더의 현재 텍스트 문서들을 동기화한다."""

    root = Path(documents_directory).resolve()
    return _sync_files(
        find_document_files(root),
        DOCUMENT,
        root,
        db_path,
        memory_path,
    )


def sync_knowledge(
    project_root=DEFAULT_PROJECT_ROOT,
    documents_directory=DEFAULT_DOCUMENTS_DIRECTORY,
    db_path=DEFAULT_DB_PATH,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """송련 소스 코드와 외부 문서를 한 번에 동기화한다."""

    return {
        PYTHON_SOURCE: index_python_sources(
            project_root,
            db_path,
            memory_path,
            documents_directory=documents_directory,
        ),
        DOCUMENT: index_documents(
            documents_directory,
            db_path,
            memory_path,
        ),
    }
