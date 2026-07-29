"""이전 ``metadata`` import를 위한 호환 패키지.

원자 기록은 송련의 기억 형식이므로 실제 구현은 이제 ``memory``에 있다.
새 코드는 ``from memory import ...`` 형태를 사용하면 된다.
"""

from memory.record import create_information_record
from memory.store import append_information_records, save_information_record

__all__ = [
    "append_information_records",
    "create_information_record",
    "save_information_record",
]
