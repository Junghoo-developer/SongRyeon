"""OpenAI-compatible 외부 API를 위한 격리된 통합시험 client.

이 client는 대회 제출용 기본 실행 경로가 아니다. 호출하려면 CLI에서
통합시험 모드를 명시해야 하며, API key는 이름이 지정된 환경 변수에서만
읽는다.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from .client import (
    ModelCallError,
    ModelConnectionError,
    ModelReply,
    ModelResponseError,
)


DEFAULT_EXTERNAL_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_EXTERNAL_TIMEOUT_SECONDS = 180

_ENVIRONMENT_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_USAGE_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
)


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Authorization header가 다른 위치로 재전송되지 않게 redirect를 거부한다."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_RejectRedirectHandler())


class OpenAICompatibleIntegrationClient:
    """HTTPS OpenAI-compatible ``chat/completions`` 통합시험 client."""

    provider = "openai_compatible"
    execution_mode = "external_api_integration"

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        api_key_env: str = DEFAULT_EXTERNAL_API_KEY_ENV,
        timeout_seconds: int = DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
        temperature: int | float = 0,
        seed: int = 42,
        opener: Callable | None = None,
    ) -> None:
        self.base_url = _validate_https_base_url(base_url)

        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name은 비어 있지 않은 문자열이어야 합니다.")
        if (
            not isinstance(api_key_env, str)
            or _ENVIRONMENT_NAME_PATTERN.fullmatch(api_key_env) is None
        ):
            raise ValueError("api_key_env는 유효한 환경 변수 이름이어야 합니다.")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds < 1
        ):
            raise ValueError("timeout_seconds는 1 이상의 정수여야 합니다.")
        if (
            not isinstance(temperature, (int, float))
            or isinstance(temperature, bool)
        ):
            raise ValueError("temperature는 숫자여야 합니다.")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed는 정수여야 합니다.")
        if opener is not None and not callable(opener):
            raise TypeError("opener는 호출 가능해야 합니다.")

        self.model_name = model_name.strip()
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.seed = seed
        self._opener = opener or _NO_REDIRECT_OPENER.open

    def __repr__(self) -> str:
        """환경 변수의 실제 key 값은 객체 표현에 절대 포함하지 않는다."""

        return (
            f"{type(self).__name__}("
            f"base_url={self.base_url!r}, "
            f"model_name={self.model_name!r}, "
            f"api_key_env={self.api_key_env!r}, "
            f"timeout_seconds={self.timeout_seconds!r})"
        )

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict,
        num_predict: int,
    ) -> ModelReply:
        """외부 API를 한 번 호출하고 비스트리밍 응답을 엄격히 검사한다."""

        if not isinstance(system_prompt, str):
            raise TypeError("system_prompt는 문자열이어야 합니다.")
        if not isinstance(user_prompt, str):
            raise TypeError("user_prompt는 문자열이어야 합니다.")
        if not isinstance(response_schema, dict):
            raise TypeError("response_schema는 dict여야 합니다.")
        if (
            not isinstance(num_predict, int)
            or isinstance(num_predict, bool)
            or num_predict < 1
        ):
            raise ValueError("num_predict는 1 이상의 정수여야 합니다.")

        _encode_json(response_schema, "response_schema")
        api_key = self._load_api_key()
        request_body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "songryeon_node_output",
                    "strict": True,
                    "schema": response_schema,
                },
            },
            "stream": False,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_tokens": num_predict,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=_encode_json(request_body, "외부 API 요청"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        payload = self._open_json(request)
        return self._parse_chat_reply(payload)

    def check_configuration(self) -> dict[str, str]:
        """네트워크나 기억 쓰기 전에 key 설정만 안전하게 확인한다."""

        self._load_api_key()
        return {
            "provider": self.provider,
            "execution_mode": self.execution_mode,
            "model_name": self.model_name,
        }

    def _load_api_key(self) -> str:
        api_key = os.environ.get(self.api_key_env)
        if (
            not isinstance(api_key, str)
            or not api_key.strip()
            or api_key != api_key.strip()
            or any(
                not 33 <= ord(character) <= 126
                for character in api_key
            )
        ):
            raise ModelCallError(
                f"외부 API key 환경 변수 {self.api_key_env}가 없거나 유효하지 않습니다."
            )
        return api_key

    def _open_json(self, request: urllib.request.Request) -> dict:
        try:
            with self._opener(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_body = response.read()
        except urllib.error.HTTPError as error:
            # 공급자 오류 본문에는 prompt나 민감정보가 들어갈 수 있어 읽거나 전파하지 않는다.
            raise ModelCallError(
                f"외부 API HTTP 오류({error.code})"
            ) from None
        except (TimeoutError, urllib.error.URLError, OSError):
            raise ModelConnectionError(
                "외부 API에 연결하지 못했거나 응답 시간이 초과됐습니다."
            ) from None

        if not isinstance(raw_body, bytes):
            raise ModelResponseError("외부 API HTTP 응답이 bytes가 아닙니다.")

        try:
            payload = json.loads(
                raw_body.decode("utf-8"),
                parse_constant=_reject_non_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise ModelResponseError(
                "외부 API 응답이 유효한 UTF-8 JSON이 아닙니다."
            ) from None

        if not isinstance(payload, dict):
            raise ModelResponseError(
                "외부 API 응답 JSON의 최상위 값은 객체여야 합니다."
            )
        return payload

    def _parse_chat_reply(self, payload: dict) -> ModelReply:
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ModelResponseError(
                "외부 API 응답에는 choice가 정확히 하나 있어야 합니다."
            )

        choice = choices[0]
        if not isinstance(choice, dict):
            raise ModelResponseError(
                "외부 API 응답 choice는 객체여야 합니다."
            )

        finish_reason = choice.get("finish_reason")
        if finish_reason == "length":
            raise ModelResponseError(
                "외부 API 출력이 num_predict 상한에서 잘렸습니다."
            )
        if finish_reason != "stop":
            raise ModelResponseError(
                "외부 API 응답이 정상 종료 상태가 아닙니다."
            )

        message = choice.get("message")
        if not isinstance(message, dict):
            raise ModelResponseError(
                "외부 API 응답에 message 객체가 없습니다."
            )
        if message.get("role") != "assistant":
            raise ModelResponseError(
                "외부 API 응답 message의 role이 assistant가 아닙니다."
            )

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ModelResponseError(
                "외부 API 응답에 비어 있지 않은 message.content가 필요합니다."
            )
        try:
            json.loads(
                content,
                parse_constant=_reject_non_json_constant,
            )
        except (json.JSONDecodeError, ValueError):
            raise ModelResponseError(
                "외부 API message.content가 유효한 JSON이 아닙니다."
            ) from None

        returned_model = payload.get("model")
        if not isinstance(returned_model, str) or not returned_model:
            raise ModelResponseError(
                "외부 API 응답에 유효한 model이 없습니다."
            )
        if returned_model != self.model_name:
            raise ModelResponseError(
                "외부 API가 요청과 다른 모델 이름을 반환했습니다."
            )

        usage = payload.get("usage", {})
        if not isinstance(usage, dict):
            raise ModelResponseError(
                "외부 API 응답의 usage는 객체여야 합니다."
            )
        metrics: dict[str, int] = {}
        for field in _USAGE_FIELDS:
            if field not in usage:
                continue
            value = usage[field]
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ModelResponseError(
                    f"외부 API usage.{field}는 음이 아닌 정수여야 합니다."
                )
            metrics[field] = value

        # 공급자별 reasoning 필드는 감사 로그에 복제하지 않는다.
        return ModelReply(
            content=content,
            thinking="",
            model=returned_model,
            done_reason=finish_reason,
            metrics=metrics,
        )


def _validate_https_base_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("외부 API base_url은 비어 있지 않은 문자열이어야 합니다.")
    if value != value.strip() or any(ord(character) < 32 for character in value):
        raise ValueError("외부 API base_url 형식이 유효하지 않습니다.")

    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError("외부 API base_url 형식이 유효하지 않습니다.") from None

    if parsed.scheme != "https":
        raise ValueError("외부 API base_url은 HTTPS여야 합니다.")
    if not parsed.hostname or port is not None and not 1 <= port <= 65_535:
        raise ValueError("외부 API base_url의 host 또는 port가 유효하지 않습니다.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("외부 API base_url에 사용자 정보를 넣을 수 없습니다.")
    if parsed.query or parsed.fragment:
        raise ValueError("외부 API base_url에 query 또는 fragment를 넣을 수 없습니다.")

    normalized_path = parsed.path.rstrip("/")
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            normalized_path,
            "",
            "",
        )
    )


def _encode_json(value: object, label: str) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as error:
        raise ValueError(
            f"{label}은 일반 JSON으로 직렬화할 수 있어야 합니다."
        ) from error


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"JSON 표준에 없는 상수입니다: {value}")
