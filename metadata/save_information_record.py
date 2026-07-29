"""이전 import 경로를 위한 호환 모듈.

원본 JSONL 저장 구현은 ``memory.store``로 이동했다.
"""

from memory.store import (
    append_information_records,
    save_information_record,
)

__all__ = [
    "append_information_records",
    "save_information_record",
]
