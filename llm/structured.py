"""모델의 JSON 출력을 엄격히 검증하고 모든 시도를 원본에 기록한다.

이 모듈은 잘못된 JSON을 임의로 고치지 않는다. 같은 노드에 검증 오류를
알려 최대 세 번 다시 요청하고, 끝까지 계약을 지키지 못하면 명시적으로
중단한다. 전송 오류는 재시도하지 않는다.
"""

import json
from uuid import uuid4

from memory.model_records import save_model_exchange

from .client import ModelClient


DEFAULT_NODE_OUTPUT_ATTEMPTS = 3
TRANSPORT_ERROR_AUDIT_CODE = "MODEL_TRANSPORT_ERROR"


class NodeOutputError(RuntimeError):
    """모델이 정해진 횟수 안에 유효한 노드 출력을 만들지 못했다."""


def _client_audit_value(client, attribute):
    """가짜 client도 깨지 않게 안전한 실행 식별자만 감사에 넘긴다."""

    try:
        value = getattr(client, attribute, "unspecified")
    except Exception:
        return "unspecified"
    if not isinstance(value, str) or not value.strip():
        return "unspecified"
    if not value.isascii() or len(value) > 80 or any(
        not (character.isalnum() or character in "._-")
        for character in value
    ):
        return "unspecified"
    return value


def _reject_json_constant(value):
    """표준 JSON에 없는 NaN과 Infinity를 거부한다."""

    raise ValueError(f"표준 JSON에 없는 값입니다: {value}")


def _object_without_duplicate_keys(pairs):
    """같은 key를 두 번 쓴 JSON을 조용히 덮어쓰지 않는다."""

    result = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON key가 중복됐습니다: {key}")
        result[key] = value

    return result


def parse_strict_json_object(raw_response):
    """설명문·코드펜스·중복 key 없이 JSON 객체 하나만 허용한다."""

    if not isinstance(raw_response, str):
        raise TypeError("모델 응답은 문자열이어야 합니다.")

    try:
        value = json.loads(
            raw_response,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError("모델 응답이 엄격한 JSON 객체가 아닙니다.") from error

    if not isinstance(value, dict):
        raise ValueError("모델 응답의 최상위 값은 JSON 객체여야 합니다.")

    return value


def _retry_prompt(original_user_prompt, validation_error):
    """원래 요청을 유지한 채 직전 형식 오류만 모델에 알려준다."""

    return (
        original_user_prompt
        + "\n\n[직전 출력 검증 실패]\n"
        + validation_error
        + "\n출력 내용을 추측해서 고치지 말고, 요구된 JSON 스키마에 맞춰 "
        + "전체 JSON 객체를 처음부터 다시 반환하라."
    )


def request_structured_output(
    *,
    client,
    node_name,
    system_prompt,
    user_prompt,
    response_schema,
    parser,
    num_predict,
    turn_id,
    memory_path,
    max_attempts=DEFAULT_NODE_OUTPUT_ATTEMPTS,
):
    """모델 응답을 domain 객체로 바꾸고 실패 시 같은 노드만 제한 재요청한다."""

    if not isinstance(client, ModelClient):
        raise TypeError("client는 ModelClient 계약을 구현해야 합니다.")

    if not isinstance(node_name, str) or not node_name.strip():
        raise ValueError("node_name은 비어 있지 않은 문자열이어야 합니다.")

    if not callable(parser):
        raise TypeError("parser는 호출 가능한 함수여야 합니다.")

    if (
        not isinstance(max_attempts, int)
        or isinstance(max_attempts, bool)
        or max_attempts <= 0
    ):
        raise ValueError("max_attempts는 1 이상의 정수여야 합니다.")

    validation_error = ""
    provider = _client_audit_value(client, "provider")
    execution_mode = _client_audit_value(client, "execution_mode")

    for attempt in range(1, max_attempts + 1):
        current_user_prompt = (
            user_prompt
            if not validation_error
            else _retry_prompt(user_prompt, validation_error)
        )
        record_turn_id = (
            f"{turn_id}-model-{node_name}-{uuid4()}"
        )

        try:
            reply = client.complete(
                system_prompt=system_prompt,
                user_prompt=current_user_prompt,
                response_schema=response_schema,
                num_predict=num_predict,
            )
        except Exception:
            # 전송 실패를 형식 오류처럼 재요청하지 않는다. 실패 사실만 숨김 원본에 남긴다.
            save_model_exchange(
                node_name=node_name,
                model_name=client.model_name,
                system_prompt=system_prompt,
                user_prompt=current_user_prompt,
                response="",
                thinking="",
                status="transport_error",
                attempt=attempt,
                validation_error=TRANSPORT_ERROR_AUDIT_CODE,
                metrics={},
                turn_id=record_turn_id,
                provider=provider,
                execution_mode=execution_mode,
                memory_path=memory_path,
            )
            raise

        try:
            payload = parse_strict_json_object(reply.content)
            parsed_output = parser(payload)
        except (KeyError, TypeError, ValueError) as error:
            validation_error = str(error) or type(error).__name__
            save_model_exchange(
                node_name=node_name,
                model_name=reply.model,
                system_prompt=system_prompt,
                user_prompt=current_user_prompt,
                response=reply.content,
                thinking=reply.thinking,
                status="invalid",
                attempt=attempt,
                validation_error=validation_error,
                metrics=reply.metrics,
                turn_id=record_turn_id,
                provider=provider,
                execution_mode=execution_mode,
                memory_path=memory_path,
            )
            continue

        save_model_exchange(
            node_name=node_name,
            model_name=reply.model,
            system_prompt=system_prompt,
            user_prompt=current_user_prompt,
            response=reply.content,
            thinking=reply.thinking,
            status="valid",
            attempt=attempt,
            validation_error="",
            metrics=reply.metrics,
            turn_id=record_turn_id,
            provider=provider,
            execution_mode=execution_mode,
            memory_path=memory_path,
        )
        return parsed_output

    raise NodeOutputError(
        f"{node_name}가 {max_attempts}회 안에 유효한 JSON 출력을 만들지 못했습니다. "
        f"마지막 오류: {validation_error}"
    )
