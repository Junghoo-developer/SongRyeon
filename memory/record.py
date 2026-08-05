"""원본 기억에 저장할 원자 기록 하나를 만든다.

이 파일의 책임은 오직 7필드 기록 생성이다. 파일 저장은 ``store.py``가,
에이전트에게 보여줄 필드 선택은 ``agent_view.py``가 담당한다.

학습할 때는 이 파일을 가장 먼저 읽는다. 이 함수는 파일이나 모델에 접근하지
않고 입력값을 새 딕셔너리로 바꾸는 **순수한 생성 단계**다. 여기서 만든
기록이 이후 모든 저장·시야·감사 기능의 공통 재료가 된다.

현재 정보 철학:

- ``absolute``: 코드가 값의 존재와 내용을 그대로 확인할 수 있는 정보
- ``relative``: LLM의 판단·해석처럼 코드만으로 내용의 참/거짓을 확정할 수 없는 정보

분류 이름과 ``code_verifiable``을 둘 다 저장하는 이유는 나중에 철학이
바뀌더라도 기존 원본 로그를 다시 해석할 여지를 남기기 위해서다.
"""

from datetime import datetime, timezone
from uuid import uuid4


INFORMATION_CLASS_TO_CODE_VERIFIABLE = {
    "absolute": True,
    "relative": False,
}


def create_information_record(
    information,
    information_class,
    information_type,
    turn_id,
):
    """정보 본문에 분류·종류·턴·ID·UTC 생성 시각을 붙인다.

    반환되는 딕셔너리는 ``memory.jsonl`` 한 줄에 바로 저장할 수 있는
    완성된 원자 기록이다.
    """

    try:
        code_verifiable = INFORMATION_CLASS_TO_CODE_VERIFIABLE[
            information_class
        ]
    except KeyError as error:
        raise ValueError("알 수 없는 정보 분류입니다.") from error

    return {
        "information": information,
        "information_class": information_class,
        "code_verifiable": code_verifiable,
        "information_type": information_type,
        "turn_id": turn_id,
        "information_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
