"""지식 파일 한 버전을 원본 기억의 다섯 원자로 보존한다.

DB는 빠른 조회용 복사본이고 ``memory.jsonl``이 추적 가능한 원본 로그다.
지식 본문은 ``knowledge_*`` 종류이므로 평상시 에이전트 시야에서는 숨겨진다.
"""

import json
from pathlib import Path
from uuid import uuid4

from memory.record import create_information_record
from memory.settings import DEFAULT_MEMORY_PATH
from memory.store import append_information_records


KNOWLEDGE_RECORD_TYPES = (
    "knowledge_source_type",
    "knowledge_path",
    "knowledge_status",
    "knowledge_hash",
    "knowledge_content",
)

KNOWLEDGE_VERSION_RECORD_TYPES = {
    "knowledge_source_type",
    "knowledge_path",
    "knowledge_hash",
}


def load_logged_knowledge_versions(memory_path=DEFAULT_MEMORY_PATH):
    """원본 로그에 이미 보존된 파일 버전 식별자들을 반환한다."""

    path = Path(memory_path)

    if not path.exists():
        return set()

    records_by_turn = {}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)
            information_type = record.get("information_type")

            if information_type not in KNOWLEDGE_VERSION_RECORD_TYPES:
                continue

            turn_records = records_by_turn.setdefault(
                record["turn_id"],
                {},
            )
            turn_records[information_type] = record["information"]

    logged_versions = set()

    for turn_records in records_by_turn.values():
        if not KNOWLEDGE_VERSION_RECORD_TYPES.issubset(turn_records):
            continue

        logged_versions.add(
            (
                turn_records["knowledge_source_type"],
                turn_records["knowledge_path"],
                turn_records["knowledge_hash"],
            )
        )

    return logged_versions


def save_knowledge_records(
    source_type,
    path,
    status,
    content_hash,
    content,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """파일 한 버전을 같은 turn의 다섯 절대 원자로 저장한다."""

    turn_id = f"knowledge-{uuid4()}"
    information_by_type = (
        (KNOWLEDGE_RECORD_TYPES[0], source_type),
        (KNOWLEDGE_RECORD_TYPES[1], Path(path).as_posix()),
        (KNOWLEDGE_RECORD_TYPES[2], status),
        (KNOWLEDGE_RECORD_TYPES[3], content_hash),
        (KNOWLEDGE_RECORD_TYPES[4], content),
    )

    records = [
        create_information_record(
            information=information,
            information_class="absolute",
            information_type=information_type,
            turn_id=turn_id,
        )
        for information_type, information in information_by_type
    ]

    return append_information_records(records, memory_path)
