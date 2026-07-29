"""사용자 입력, Node3 답변과 최종 전달 선택을 원자 기록으로 남긴다.

자연어의 내용은 코드가 참·거짓을 판단할 수 없으므로 상대정보(R)다.
반면 누가 말했는지와 런타임이 어느 답변 ID를 최종 선택했는지는 코드가
직접 확인한 사실이므로 절대정보(A)로 기록한다.
"""

import json
from pathlib import Path

from .audit import canonical_json, new_audit_record, validate_visible_batch
from .settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)
from .store import append_information_records


def _require_nonempty_text(value, field_name):
    """공개 대화 기록에 비어 있는 문자열이 들어가지 않게 한다."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}은 비어 있지 않은 문자열이어야 합니다.")


def _save_visible_records(records, memory_path):
    """시야 예산을 먼저 검사한 뒤 기록 묶음을 한 번에 저장한다."""

    validate_visible_batch(
        records,
        DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    )
    return append_information_records(records, memory_path)


def save_user_input(
    user_input,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """사용자가 입력했다는 A와 입력 내용 R을 함께 저장한다."""

    _require_nonempty_text(user_input, "user_input")
    _require_nonempty_text(turn_id, "turn_id")
    records = [
        new_audit_record("user", "absolute", "source", turn_id),
        new_audit_record(
            user_input,
            "relative",
            "user_input",
            turn_id,
        ),
    ]
    return _save_visible_records(records, memory_path)


def save_node3_answer(
    answer,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """Node3가 답했다는 A와 아직 검증 대상인 답변 내용 R을 저장한다."""

    _require_nonempty_text(answer, "answer")
    _require_nonempty_text(turn_id, "turn_id")
    records = [
        new_audit_record("node3", "absolute", "source", turn_id),
        new_audit_record(
            answer,
            "relative",
            "node3_answer",
            turn_id,
        ),
    ]
    return _save_visible_records(records, memory_path)


def save_final_delivery(
    answer_information_id,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """런타임이 최종 전달 대상으로 고른 Node3 답변 ID를 저장한다."""

    _require_nonempty_text(answer_information_id, "answer_information_id")
    _require_nonempty_text(turn_id, "turn_id")
    _verify_node3_answer(memory_path, answer_information_id)
    final_link = canonical_json(
        {"answer_information_id": answer_information_id}
    )
    records = [
        new_audit_record("runtime", "absolute", "source", turn_id),
        new_audit_record(
            final_link,
            "absolute",
            "final_delivery",
            turn_id,
        ),
    ]
    return _save_visible_records(records, memory_path)


def _verify_node3_answer(memory_path, answer_information_id):
    """최종 A 링크를 만들기 전에 대상이 실제 Node3 답변인지 다시 확인한다."""

    path = Path(memory_path)

    if not path.exists():
        raise ValueError("최종 전달할 Node3 답변 기록을 찾을 수 없습니다.")

    matches = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)

            if record.get("information_id") == answer_information_id:
                matches.append(record)

    if len(matches) != 1:
        raise ValueError(
            "최종 답변 ID는 원본 로그의 기록 하나와 정확히 일치해야 합니다."
        )

    answer_record = matches[0]

    if (
        answer_record.get("information_type") != "node3_answer"
        or answer_record.get("information_class") != "relative"
        or answer_record.get("code_verifiable") is not False
        or not isinstance(answer_record.get("information"), str)
    ):
        raise ValueError(
            "최종 전달 대상은 저장된 Node3 상대정보 답변이어야 합니다."
        )
