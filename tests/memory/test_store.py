"""완성된 원자 기록이 원본 JSONL에 안전하게 추가되는지 검사한다."""

import json
from pathlib import Path

import pytest

from memory.record import create_information_record
from memory.store import (
    append_information_records,
    save_information_record,
)


def test_save_two_records(tmp_path):
    memory_path = tmp_path / "memory" / "memory.jsonl"

    save_information_record(
        "첫 번째 정보",
        "absolute",
        "source",
        "turn-1",
        memory_path,
    )
    save_information_record(
        "두 번째 정보",
        "relative",
        "user_input",
        "turn-1",
        memory_path,
    )

    lines = memory_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["information"] == "첫 번째 정보"
    assert json.loads(lines[1])["information"] == "두 번째 정보"
    assert json.loads(lines[0])["information_type"] == "source"
    assert json.loads(lines[1])["information_type"] == "user_input"
    assert json.loads(lines[0])["turn_id"] == "turn-1"
    assert json.loads(lines[1])["turn_id"] == "turn-1"


def test_append_information_records_uses_one_write(tmp_path, monkeypatch):
    memory_path = tmp_path / "memory" / "memory.jsonl"
    records = [
        create_information_record(
            f"{number}번 정보",
            "absolute",
            "test",
            "turn-1",
        )
        for number in range(1, 6)
    ]
    original_open = Path.open
    written_payloads = []

    class CountingFile:
        """실제 파일을 감싸면서 write 호출 횟수만 기록한다."""

        def __init__(self, file):
            self.file = file

        def __enter__(self):
            self.file.__enter__()
            return self

        def __exit__(self, exception_type, exception, traceback):
            return self.file.__exit__(
                exception_type,
                exception,
                traceback,
            )

        def write(self, payload):
            written_payloads.append(payload)
            return self.file.write(payload)

        def __getattr__(self, name):
            return getattr(self.file, name)

    def counting_open(path, *args, **kwargs):
        return CountingFile(original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", counting_open)

    saved_records = append_information_records(records, memory_path)

    assert saved_records == records
    assert len(written_payloads) == 1
    assert len(written_payloads[0].splitlines()) == 5


def test_short_write_rolls_back_to_the_original_file_size(
    tmp_path,
    monkeypatch,
):
    memory_path = tmp_path / "memory.jsonl"
    original_payload = b'{"existing":true}\n'
    memory_path.write_bytes(original_payload)
    record = create_information_record(
        "새 정보",
        "absolute",
        "test",
        "turn-2",
    )
    original_open = Path.open

    class ShortWriteFile:
        """실제 파일에는 일부만 쓰고 짧은 write 결과를 흉내 낸다."""

        def __init__(self, file):
            self.file = file

        def __enter__(self):
            self.file.__enter__()
            return self

        def __exit__(self, exception_type, exception, traceback):
            return self.file.__exit__(
                exception_type,
                exception,
                traceback,
            )

        def write(self, payload):
            partial_payload = payload[: max(1, len(payload) // 2)]
            return self.file.write(partial_payload)

        def __getattr__(self, name):
            return getattr(self.file, name)

    def short_open(path, *args, **kwargs):
        return ShortWriteFile(original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", short_open)

    with pytest.raises(OSError):
        append_information_records([record], memory_path)

    with original_open(memory_path, "rb") as file:
        assert file.read() == original_payload
