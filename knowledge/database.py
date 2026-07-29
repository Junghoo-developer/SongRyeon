"""SQLite 지식 DB의 생성·변경·조회만 담당한다.

원본 ``memory.jsonl`` 기록은 여기서 하지 않는다. DB 변경과 원본 로그의
순서를 조정하는 업무 흐름은 ``indexer.py``가 담당한다.
"""

import sqlite3
from pathlib import Path

from .settings import DEFAULT_DB_PATH, validate_source_type


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_items (
    source_type TEXT NOT NULL
        CHECK (source_type IN ('python_source', 'document')),
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    logged_content_hash TEXT,
    memory_turn_id TEXT,
    logged_memory_path TEXT,
    PRIMARY KEY (source_type, path)
)
"""

LOG_MARKER_COLUMNS = {
    "logged_content_hash": "TEXT",
    "memory_turn_id": "TEXT",
    "logged_memory_path": "TEXT",
}


def initialize_knowledge_db(db_path=DEFAULT_DB_PATH):
    """SQLite 파일과 필요한 테이블·호환 컬럼을 준비한다."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(CREATE_TABLE_SQL)
        existing_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(knowledge_items)"
            )
        }

        # 예전 DB에는 로그 동기화 표시 컬럼이 없을 수 있어 한 번만 추가한다.
        for column_name, column_type in LOG_MARKER_COLUMNS.items():
            if column_name in existing_columns:
                continue

            connection.execute(
                f"""
                ALTER TABLE knowledge_items
                ADD COLUMN {column_name} {column_type}
                """
            )

    return path


def upsert_prepared_file(
    connection,
    prepared_file,
    source_type,
    indexed_at,
):
    """준비된 파일을 추가·갱신하고 상태와 기존 로그 표시를 반환한다."""

    existing = connection.execute(
        """
        SELECT
            content_hash,
            logged_content_hash,
            memory_turn_id,
            logged_memory_path
        FROM knowledge_items
        WHERE source_type = ? AND path = ?
        """,
        (source_type, prepared_file["path"]),
    ).fetchone()

    if existing is None:
        connection.execute(
            """
            INSERT INTO knowledge_items (
                source_type,
                path,
                content,
                content_hash,
                indexed_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_type,
                prepared_file["path"],
                prepared_file["content"],
                prepared_file["content_hash"],
                indexed_at,
            ),
        )
        return "added", (None, None, None)

    if existing[0] == prepared_file["content_hash"]:
        return "unchanged", existing[1:]

    connection.execute(
        """
        UPDATE knowledge_items
        SET content = ?, content_hash = ?, indexed_at = ?
        WHERE source_type = ? AND path = ?
        """,
        (
            prepared_file["content"],
            prepared_file["content_hash"],
            indexed_at,
            source_type,
            prepared_file["path"],
        ),
    )
    return "updated", existing[1:]


def update_log_marker(
    connection,
    prepared_file,
    source_type,
    content_hash,
    memory_turn_id,
    memory_path,
):
    """DB 행에 어느 원본 로그 버전까지 저장했는지 표시한다."""

    connection.execute(
        """
        UPDATE knowledge_items
        SET
            logged_content_hash = ?,
            memory_turn_id = ?,
            logged_memory_path = ?
        WHERE source_type = ? AND path = ?
        """,
        (
            content_hash,
            memory_turn_id,
            memory_path,
            source_type,
            prepared_file["path"],
        ),
    )


def indexed_rows_for_source(connection, source_type):
    """삭제 여부를 비교할 수 있도록 한 종류의 모든 행을 반환한다."""

    return connection.execute(
        """
        SELECT path, content, content_hash
        FROM knowledge_items
        WHERE source_type = ?
        ORDER BY path
        """,
        (source_type,),
    ).fetchall()


def delete_indexed_file(connection, source_type, path):
    """원본 로그 저장이 끝난 파일 행 하나를 DB에서 삭제한다."""

    cursor = connection.execute(
        """
        DELETE FROM knowledge_items
        WHERE source_type = ? AND path = ?
        """,
        (source_type, path),
    )

    if cursor.rowcount != 1:
        raise RuntimeError(
            f"삭제 대상 지식 행을 정확히 하나 지우지 못했습니다: {path}"
        )


def list_indexed_files(db_path=DEFAULT_DB_PATH, source_type=None):
    """색인된 파일의 본문 이외 메타정보를 경로순으로 반환한다."""

    if source_type is not None:
        validate_source_type(source_type)

    path = initialize_knowledge_db(db_path)

    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row

        if source_type is None:
            rows = connection.execute(
                """
                SELECT source_type, path, content_hash, indexed_at
                FROM knowledge_items
                ORDER BY source_type, path
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT source_type, path, content_hash, indexed_at
                FROM knowledge_items
                WHERE source_type = ?
                ORDER BY path
                """,
                (source_type,),
            ).fetchall()

    return [dict(row) for row in rows]


def get_indexed_file(path, source_type, db_path=DEFAULT_DB_PATH):
    """종류와 상대경로가 일치하는 색인 파일 하나를 반환한다."""

    validate_source_type(source_type)
    db = initialize_knowledge_db(db_path)

    with sqlite3.connect(db) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT source_type, path, content, content_hash, indexed_at
            FROM knowledge_items
            WHERE source_type = ? AND path = ?
            """,
            (source_type, Path(path).as_posix()),
        ).fetchone()

    if row is None:
        return None

    return dict(row)
