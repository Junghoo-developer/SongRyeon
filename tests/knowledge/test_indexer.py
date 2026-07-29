"""파일 탐색부터 DB·원본 로그 동기화까지의 업무 흐름을 검사한다."""

import hashlib
import json

import pytest

import knowledge.indexer as knowledge_indexer
from knowledge import (
    DOCUMENT,
    PYTHON_SOURCE,
    get_indexed_file,
    index_documents,
    index_file,
    index_python_sources,
    list_indexed_files,
    sync_knowledge,
)


def test_python_sources_are_indexed_from_project_root(tmp_path):
    project_root = tmp_path / "project"
    db_path = tmp_path / "data" / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    package_directory = project_root / "package"
    cache_directory = project_root / "__pycache__"
    build_directory = project_root / "build" / "lib"
    documents_directory = project_root / "knowledge" / "documents"

    package_directory.mkdir(parents=True)
    cache_directory.mkdir()
    build_directory.mkdir(parents=True)
    documents_directory.mkdir(parents=True)

    raw_main = "print('안녕')\r\n".encode("utf-8")
    (project_root / "main.py").write_bytes(raw_main)
    (package_directory / "helper.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (project_root / "notes.txt").write_text(
        "파이썬 파일이 아님",
        encoding="utf-8",
    )
    (cache_directory / "ignored.py").write_text(
        "무시",
        encoding="utf-8",
    )
    (build_directory / "copied.py").write_text(
        "빌드 산출물",
        encoding="utf-8",
    )
    (documents_directory / "external.py").write_text(
        "외부 문서 폴더",
        encoding="utf-8",
    )

    report = index_python_sources(project_root, db_path, memory_path)

    assert report == {
        "added": 2,
        "updated": 0,
        "unchanged": 0,
        "removed": 0,
    }
    assert [
        item["path"]
        for item in list_indexed_files(db_path, PYTHON_SOURCE)
    ] == [
        "main.py",
        "package/helper.py",
    ]

    indexed_main = get_indexed_file("main.py", PYTHON_SOURCE, db_path)
    assert indexed_main["content"] == raw_main.decode("utf-8")
    assert indexed_main["content_hash"] == hashlib.sha256(raw_main).hexdigest()


def test_python_source_sync_updates_and_removes_old_rows(tmp_path):
    project_root = tmp_path / "project"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    project_root.mkdir()

    first_file = project_root / "first.py"
    second_file = project_root / "second.py"
    first_file.write_text("VERSION = 1\n", encoding="utf-8")
    second_file.write_text("SECOND = True\n", encoding="utf-8")
    second_content = second_file.read_bytes().decode("utf-8")
    second_hash = hashlib.sha256(second_file.read_bytes()).hexdigest()

    index_python_sources(project_root, db_path, memory_path)
    unchanged_report = index_python_sources(
        project_root,
        db_path,
        memory_path,
    )

    assert unchanged_report["unchanged"] == 2

    first_file.write_text("VERSION = 2\n", encoding="utf-8")
    second_file.unlink()

    changed_report = index_python_sources(
        project_root,
        db_path,
        memory_path,
    )

    assert changed_report == {
        "added": 0,
        "updated": 1,
        "unchanged": 0,
        "removed": 1,
    }
    assert get_indexed_file(
        "first.py",
        PYTHON_SOURCE,
        db_path,
    )["content"] == first_file.read_bytes().decode("utf-8")
    assert get_indexed_file("second.py", PYTHON_SOURCE, db_path) is None

    stored_records = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]
    removed_status = next(
        record
        for record in stored_records
        if record["information_type"] == "knowledge_status"
        and record["information"] == "removed"
    )
    removed_records = {
        record["information_type"]: record["information"]
        for record in stored_records
        if record["turn_id"] == removed_status["turn_id"]
    }

    assert removed_records == {
        "knowledge_source_type": "python_source",
        "knowledge_path": "second.py",
        "knowledge_status": "removed",
        "knowledge_hash": second_hash,
        "knowledge_content": second_content,
    }


def test_removed_log_failure_keeps_the_indexed_row(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    project_root.mkdir()

    source_file = project_root / "main.py"
    source_file.write_bytes(b"VALUE = 1\n")
    index_python_sources(project_root, db_path, memory_path)
    source_file.unlink()

    def fail_to_save_removed_records(**kwargs):
        raise RuntimeError("원본 로그 저장 실패")

    # 호출이 실제로 일어나는 업무 흐름 모듈에 실패를 주입한다.
    monkeypatch.setattr(
        knowledge_indexer,
        "save_knowledge_records",
        fail_to_save_removed_records,
    )

    with pytest.raises(RuntimeError, match="원본 로그 저장 실패"):
        index_python_sources(project_root, db_path, memory_path)

    assert get_indexed_file("main.py", PYTHON_SOURCE, db_path) is not None


def test_documents_index_supports_only_declared_text_extensions(tmp_path):
    documents_directory = tmp_path / "documents"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    documents_directory.mkdir()

    (documents_directory / "manual.md").write_text(
        "# 사용법\n",
        encoding="utf-8",
    )
    (documents_directory / "records.jsonl").write_text(
        '{"value": 1}\n',
        encoding="utf-8",
    )
    (documents_directory / "image.png").write_bytes(b"\x89PNG")

    report = index_documents(
        documents_directory,
        db_path,
        memory_path,
    )

    assert report["added"] == 2
    assert [
        item["path"]
        for item in list_indexed_files(db_path, DOCUMENT)
    ] == [
        "manual.md",
        "records.jsonl",
    ]


def test_index_file_rejects_a_path_outside_allowed_root(tmp_path):
    project_root = tmp_path / "project"
    outside_file = tmp_path / "outside.py"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    project_root.mkdir()
    outside_file.write_text("OUTSIDE = True\n", encoding="utf-8")

    with pytest.raises(ValueError):
        index_file(
            outside_file,
            PYTHON_SOURCE,
            project_root,
            db_path,
            memory_path,
        )


def test_sync_excludes_a_custom_document_directory_from_python_sources(
    tmp_path,
):
    project_root = tmp_path / "project"
    documents_directory = project_root / "external_documents"
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory" / "memory.jsonl"
    documents_directory.mkdir(parents=True)

    (project_root / "main.py").write_text(
        "PROJECT = True\n",
        encoding="utf-8",
    )
    (documents_directory / "example.py").write_text(
        "THIS_IS_EXTERNAL = True\n",
        encoding="utf-8",
    )

    report = sync_knowledge(
        project_root,
        documents_directory,
        db_path,
        memory_path,
    )

    assert report[PYTHON_SOURCE]["added"] == 1
    assert [
        item["path"]
        for item in list_indexed_files(db_path, PYTHON_SOURCE)
    ] == ["main.py"]
