"""LLM에 보낸 원문과 받은 원문을 에이전트 시야 밖의 감사 로그로 남긴다.

모든 ``information_type``은 ``model_raw_``로 시작한다. 따라서 원본
``memory.jsonl``에는 그대로 보존되지만 공개 에이전트 시야에는 들어가지
않는다.
"""

from .audit import canonical_json, new_audit_record, validate_visible_batch
from .settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)
from .store import append_information_records


def _require_nonempty_text(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}은 비어 있지 않은 문자열이어야 합니다.")


def _require_text(value, field_name):
    if not isinstance(value, str):
        raise ValueError(f"{field_name}은 문자열이어야 합니다.")


def save_model_exchange(
    *,
    node_name,
    model_name,
    system_prompt,
    user_prompt,
    response,
    thinking,
    status,
    attempt,
    validation_error,
    metrics,
    turn_id,
    provider="unspecified",
    execution_mode="unspecified",
    memory_path=DEFAULT_MEMORY_PATH,
):
    """모델 호출 한 번의 입출력과 코드가 확인한 실행 상태를 저장한다."""

    _require_nonempty_text(node_name, "node_name")
    _require_nonempty_text(model_name, "model_name")
    _require_nonempty_text(provider, "provider")
    _require_nonempty_text(execution_mode, "execution_mode")
    _require_nonempty_text(status, "status")
    _require_nonempty_text(turn_id, "turn_id")
    _require_text(system_prompt, "system_prompt")
    _require_text(user_prompt, "user_prompt")
    _require_text(response, "response")

    if thinking is None:
        thinking = ""
    _require_text(thinking, "thinking")

    if validation_error is None:
        validation_error = ""
    _require_text(validation_error, "validation_error")

    if (
        not isinstance(attempt, int)
        or isinstance(attempt, bool)
        or attempt < 1
    ):
        raise ValueError("attempt는 1 이상의 정수여야 합니다.")

    if not isinstance(metrics, dict):
        raise ValueError("metrics는 JSON 객체여야 합니다.")

    # 구조가 있는 코드 사실은 정렬된 JSON으로 고정해 다시 비교할 수 있게 한다.
    attempt_json = canonical_json({"attempt": attempt})
    metrics_json = canonical_json(metrics)
    records = [
        new_audit_record(
            node_name,
            "absolute",
            "model_raw_node",
            turn_id,
        ),
        new_audit_record(
            model_name,
            "absolute",
            "model_raw_model",
            turn_id,
        ),
        new_audit_record(
            provider,
            "absolute",
            "model_raw_provider",
            turn_id,
        ),
        new_audit_record(
            execution_mode,
            "absolute",
            "model_raw_execution_mode",
            turn_id,
        ),
        new_audit_record(
            system_prompt,
            "relative",
            "model_raw_system_prompt",
            turn_id,
        ),
        new_audit_record(
            user_prompt,
            "relative",
            "model_raw_user_prompt",
            turn_id,
        ),
        new_audit_record(
            response,
            "relative",
            "model_raw_response",
            turn_id,
        ),
        new_audit_record(
            thinking,
            "relative",
            "model_raw_thinking",
            turn_id,
        ),
        new_audit_record(
            status,
            "absolute",
            "model_raw_status",
            turn_id,
        ),
        new_audit_record(
            attempt_json,
            "absolute",
            "model_raw_attempt",
            turn_id,
        ),
        new_audit_record(
            validation_error,
            "absolute",
            "model_raw_validation_error",
            turn_id,
        ),
        new_audit_record(
            metrics_json,
            "absolute",
            "model_raw_metrics",
            turn_id,
        ),
    ]

    # 현재는 전부 숨김이지만 prefix 정책이 바뀌어도 같은 안전 검사를 거친다.
    validate_visible_batch(
        records,
        DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    )
    return append_information_records(records, memory_path)
