"""이전 import 경로를 위한 호환 모듈.

실제 7필드 기록 생성 과정은 ``memory.record``에 한눈에 보이도록 모았다.
"""

from memory.record import create_information_record

__all__ = ["create_information_record"]
