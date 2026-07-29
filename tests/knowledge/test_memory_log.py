"""지식 파일 원본이 memory.jsonl에 추적 가능하게 남는지 검사한다."""

import hashlib
import json
import sqlite3

from knowledge.indexer import index_python_sources
from knowledge.memory_log import (
    KNOWLEDGE_RECORD_TYPES,
    load_logged_knowledge_versions,
    save_knowledge_records,
)


RECORD_FIELDS = {
    "information",
    "information_class",
    "code_verifiable",
    "information_type",
    "turn_id",
    "information_id",
    "created_at",
}


def test_knowledge_file_is_saved_as_five_absolute_atomic_records(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"
    content = "첫 번째 줄\r\n두 번째 줄\n"

    saved_records = save_knowledge_records(
        source_type="python_source",
        path="memory/example.py",
        status="added",
        content_hash="abc123",
        content=content,
        memory_path=memory_path,
    )

    stored_records = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]

    assert stored_records == saved_records
    assert len(stored_records) == 5
    assert [
        record["information_type"]
        for record in stored_records
    ] == list(KNOWLEDGE_RECORD_TYPES)
    assert all(set(record) == RECORD_FIELDS for record in stored_records)
    assert all(
        record["information_class"] == "absolute"
        for record in stored_records
    )
    assert all(
        record["code_verifiable"] is True
        for record in stored_records
    )

    turn_ids = {
        record["turn_id"]
        for record in stored_records
    }
    assert len(turn_ids) == 1
    assert next(iter(turn_ids)).startswith("knowledge-")

    information_ids = {
        record["information_id"]
        for record in stored_records
    }
    assert len(information_ids) == 5

    content_record = stored_records[-1]
    assert content_record["information_type"] == "knowledge_content"
    assert content_record["information"] == content


def test_python_sync_logs_only_added_and_updated_file_versions(tmp_path):
    project_root = tmp_path / "project"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    project_root.mkdir()

    source_file = project_root / "main.py"
    source_file.write_bytes(b"VERSION = 1\n")

    added_report = index_python_sources(
        project_root,
        db_path,
        memory_path,
    )
    records_after_add = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]

    assert added_report["added"] == 1
    assert len(records_after_add) == 5
    assert records_after_add[2]["information"] == "added"
    assert records_after_add[4]["information"] == "VERSION = 1\n"

    unchanged_report = index_python_sources(
        project_root,
        db_path,
        memory_path,
    )
    records_after_unchanged = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]

    assert unchanged_report["unchanged"] == 1
    assert records_after_unchanged == records_after_add

    source_file.write_bytes(b"VERSION = 2\n")

    updated_report = index_python_sources(
        project_root,
        db_path,
        memory_path,
    )
    records_after_update = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]

    assert updated_report["updated"] == 1
    assert len(records_after_update) == 10
    assert records_after_update[7]["information"] == "updated"
    assert records_after_update[9]["information"] == "VERSION = 2\n"
    assert (
        records_after_update[0]["turn_id"]
        != records_after_update[5]["turn_id"]
    )


def test_existing_index_is_backfilled_once_when_original_log_is_missing(
    tmp_path,
):
    project_root = tmp_path / "project"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    project_root.mkdir()
    raw_content = b"VALUE = 1\n"
    (project_root / "main.py").write_bytes(raw_content)

    # 과거 버전처럼 로그 표시 컬럼이 없는 DB를 직접 만든다.
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE knowledge_items (
                source_type TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                PRIMARY KEY (source_type, path)
            )
            """
        )
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
                "python_source",
                "main.py",
                raw_content.decode("utf-8"),
                hashlib.sha256(raw_content).hexdigest(),
                "2026-01-01T00:00:00+00:00",
            ),
        )

    backfill_report = index_python_sources(
        project_root,
        db_path,
        memory_path,
    )
    records_after_backfill = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]

    assert backfill_report["unchanged"] == 1
    assert len(records_after_backfill) == 5
    assert records_after_backfill[2]["information"] == "backfilled"
    assert load_logged_knowledge_versions(memory_path) == {
        ("python_source", "main.py", records_after_backfill[3]["information"])
    }

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(knowledge_items)"
            )
        }
        marker = connection.execute(
            """
            SELECT
                logged_content_hash,
                memory_turn_id,
                logged_memory_path
            FROM knowledge_items
            WHERE source_type = 'python_source'
              AND path = 'main.py'
            """
        ).fetchone()

    assert {
        "logged_content_hash",
        "memory_turn_id",
        "logged_memory_path",
    }.issubset(columns)
    assert marker[0] == hashlib.sha256(raw_content).hexdigest()
    assert marker[1] == records_after_backfill[0]["turn_id"]
    assert marker[2] == str(memory_path.resolve())

    index_python_sources(
        project_root,
        db_path,
        memory_path,
    )
    records_after_second_sync = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]

    assert records_after_second_sync == records_after_backfill
