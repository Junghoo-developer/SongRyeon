"""완성된 원자 기록을 원본 ``memory.jsonl``에 누적 저장한다.

이 파일은 에이전트 시야를 만들지 않는다. 여기서 저장하는 파일은 ID와
시각까지 보존하는 원본 로그이며, 시야 가공은 ``agent_view.py``에서 한다.

학습 포인트는 ``create → encode → append → flush → rollback`` 순서다.
여기에는 A/R 판단이 없다. 이미 완성된 기록을 잃지 않고 덧붙이는 저장
책임만 맡기 때문에 분류 철학이 바뀌어도 파일 쓰기 코드는 거의 그대로다.
"""

import json
import os
from pathlib import Path

from .record import create_information_record
from .settings import DEFAULT_MEMORY_PATH


class MemoryLogCorruptionError(OSError):
    """실패한 쓰기를 원래 크기로 되돌리는 것까지 실패했음을 알린다."""


def append_information_records(
    records,
    file_path=DEFAULT_MEMORY_PATH,
):
    """여러 완성 기록을 JSONL 문자열 하나로 만들어 한 번에 추가한다.

    기록 묶음을 한 번의 ``write``로 쓰므로 지식 파일처럼 여러 원자가
    함께 저장될 때 중간까지만 기록될 가능성을 줄인다.
    """

    completed_records = list(records)

    if not completed_records:
        return []

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(record, ensure_ascii=False) + "\n"
        for record in completed_records
    ).encode("utf-8")

    # JSONL 줄마다 따로 쓰지 않고 payload 전체를 한 번에 쓴다. 그래도 디스크
    # 오류로 일부 byte만 써질 수 있으므로 실패하면 쓰기 전 크기로 되돌린다.
    # 이것은 프로세스 간 잠금이 아니라 단일 writer의 부분 쓰기 복구다.
    with path.open(
        "a+b",
    ) as file:
        file.seek(0, os.SEEK_END)
        original_size = file.tell()

        try:
            written_bytes = file.write(payload)

            if written_bytes != len(payload):
                raise OSError("원본 기록 묶음을 전부 저장하지 못했습니다.")

            file.flush()
            os.fsync(file.fileno())
        except Exception:
            try:
                file.truncate(original_size)
                file.flush()
                os.fsync(file.fileno())
            except Exception as rollback_error:
                raise MemoryLogCorruptionError(
                    "기억 로그 쓰기와 원래 크기 복구가 모두 실패했습니다."
                ) from rollback_error

            raise

    return completed_records


def save_information_record(
    information,
    information_class,
    information_type,
    turn_id,
    file_path=DEFAULT_MEMORY_PATH,
):
    """원자 기록 하나를 생성하고 원본 로그에 저장한 뒤 반환한다."""

    new_record = create_information_record(
        information,
        information_class,
        information_type,
        turn_id,
    )
    append_information_records([new_record], file_path)
    return new_record
