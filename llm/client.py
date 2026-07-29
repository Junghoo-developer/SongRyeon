"""표준 라이브러리만 사용하는 Ollama JSON 호출부."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL_NAME = "qwen3:14b"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_NUM_CTX = 16_384
DEFAULT_KEEP_ALIVE = "10m"
DEFAULT_TEMPERATURE = 0
DEFAULT_SEED = 42

_METRIC_FIELDS = (
    "total_duration",
    "load_duration",
    "prompt_eval_count",
    "prompt_eval_duration",
    "eval_count",
    "eval_duration",
)


class ModelCallError(RuntimeError):
    """모델 호출을 정상적으로 끝내지 못했다."""


class ModelConnectionError(ModelCallError):
    """Ollama 서버에 연결하지 못했거나 제한 시간을 넘겼다."""


class ModelResponseError(ModelCallError):
    """Ollama가 계약에 맞지 않는 응답을 돌려줬다."""


@dataclass(frozen=True)
class ModelReply:
    """모델 원문과 코드가 확인할 수 있는 응답 계측값."""

    content: str
    thinking: str
    model: str
    done_reason: str | None
    metrics: dict

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content는 문자열이어야 합니다.")
        if not isinstance(self.thinking, str):
            raise TypeError("thinking은 문자열이어야 합니다.")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError("model은 비어 있지 않은 문자열이어야 합니다.")
        if self.done_reason is not None and not isinstance(
            self.done_reason, str
        ):
            raise TypeError("done_reason은 문자열 또는 None이어야 합니다.")
        if not isinstance(self.metrics, dict):
            raise TypeError("metrics는 dict여야 합니다.")

        # 호출자가 전달한 원래 dict를 나중에 바꿔도 응답 객체가 따라 바뀌지 않는다.
        object.__setattr__(self, "metrics", dict(self.metrics))


@runtime_checkable
class ModelClient(Protocol):
    """노드가 구체적인 Ollama 구현을 몰라도 호출할 수 있게 하는 계약."""

    model_name: str

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict,
        num_predict: int,
    ) -> ModelReply:
        """JSON schema에 맞는 모델 응답을 한 번 요청한다."""


class OllamaClient:
    """로컬 Ollama의 ``/api/chat``을 호출하는 작은 HTTP client."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model_name: str = DEFAULT_MODEL_NAME,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        num_ctx: int = DEFAULT_NUM_CTX,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
        temperature: int | float = DEFAULT_TEMPERATURE,
        seed: int = DEFAULT_SEED,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url은 비어 있지 않은 문자열이어야 합니다.")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url은 http:// 또는 https://로 시작해야 합니다.")
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name은 비어 있지 않은 문자열이어야 합니다.")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds < 1
        ):
            raise ValueError("timeout_seconds는 1 이상의 정수여야 합니다.")
        if (
            not isinstance(num_ctx, int)
            or isinstance(num_ctx, bool)
            or num_ctx < 1
        ):
            raise ValueError("num_ctx는 1 이상의 정수여야 합니다.")
        if not isinstance(keep_alive, str) or not keep_alive.strip():
            raise ValueError("keep_alive는 비어 있지 않은 문자열이어야 합니다.")
        if (
            not isinstance(temperature, (int, float))
            or isinstance(temperature, bool)
        ):
            raise ValueError("temperature는 숫자여야 합니다.")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed는 정수여야 합니다.")

        self.base_url = base_url.rstrip("/")
        self.model_name = model_name.strip()
        self.timeout_seconds = timeout_seconds
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self.temperature = temperature
        self.seed = seed

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict,
        num_predict: int,
    ) -> ModelReply:
        """Ollama를 한 번 호출하고 비스트리밍 응답 봉투를 엄격히 검사한다."""

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

        # 전송하기 전에 schema가 실제 JSON 객체인지 확인한다.
        _encode_json(response_schema, "response_schema")

        request_body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": response_schema,
            "stream": False,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
                "num_predict": num_predict,
            },
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=_encode_json(request_body, "Ollama 요청"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = self._open_json(request)
        return self._parse_chat_reply(payload)

    def check_ready(self) -> dict[str, str]:
        """서버 응답과 요청 모델의 로컬 설치 여부를 확인한다.

        이 함수는 추론을 실행하지 않는다. 버전과 설치 모델 목록만 읽는다.
        """

        version_payload = self._get_json("/api/version")
        version = version_payload.get("version")
        if not isinstance(version, str) or not version:
            raise ModelResponseError(
                "Ollama 버전 응답에 유효한 version이 없습니다."
            )

        tags_payload = self._get_json("/api/tags")
        models = tags_payload.get("models")
        if not isinstance(models, list):
            raise ModelResponseError(
                "Ollama 모델 목록 응답에 models 배열이 없습니다."
            )

        installed_names: set[str] = set()
        for model in models:
            if not isinstance(model, dict):
                raise ModelResponseError(
                    "Ollama 모델 목록에 객체가 아닌 항목이 있습니다."
                )
            name = model.get("name")
            if isinstance(name, str) and name:
                installed_names.add(name)

        if self.model_name not in installed_names:
            raise ModelResponseError(
                f"요청 모델이 로컬에 설치되어 있지 않습니다: {self.model_name}"
            )

        return {
            "server_version": version,
            "model_name": self.model_name,
        }

    def _get_json(self, path: str) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        return self._open_json(request)

    def _open_json(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_body = response.read()
        except urllib.error.HTTPError as error:
            detail = _read_http_error_detail(error)
            suffix = f": {detail}" if detail else ""
            raise ModelCallError(
                f"Ollama HTTP 오류({error.code}){suffix}"
            ) from error
        except (TimeoutError, urllib.error.URLError, OSError) as error:
            raise ModelConnectionError(
                "Ollama 서버에 연결하지 못했거나 응답 시간이 초과됐습니다."
            ) from error

        if not isinstance(raw_body, bytes):
            raise ModelResponseError("Ollama HTTP 응답이 bytes가 아닙니다.")

        try:
            decoded = raw_body.decode("utf-8")
            payload = json.loads(
                decoded,
                parse_constant=_reject_non_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ModelResponseError(
                "Ollama 응답이 유효한 UTF-8 JSON이 아닙니다."
            ) from error

        if not isinstance(payload, dict):
            raise ModelResponseError(
                "Ollama 응답 JSON의 최상위 값은 객체여야 합니다."
            )
        return payload

    def _parse_chat_reply(self, payload: dict) -> ModelReply:
        if payload.get("done") is not True:
            raise ModelResponseError(
                "Ollama 비스트리밍 응답이 완료 상태가 아닙니다."
            )

        returned_model = payload.get("model")
        if not isinstance(returned_model, str) or not returned_model:
            raise ModelResponseError(
                "Ollama 응답에 유효한 model이 없습니다."
            )
        if returned_model != self.model_name:
            raise ModelResponseError(
                "Ollama가 요청과 다른 모델 이름을 반환했습니다."
            )

        done_reason = payload.get("done_reason")
        if done_reason is not None and (
            not isinstance(done_reason, str) or not done_reason
        ):
            raise ModelResponseError(
                "Ollama 응답의 done_reason 형식이 잘못됐습니다."
            )
        if done_reason == "length":
            raise ModelResponseError(
                "Ollama 출력이 num_predict 상한에서 잘렸습니다."
            )

        message = payload.get("message")
        if not isinstance(message, dict):
            raise ModelResponseError(
                "Ollama 응답에 message 객체가 없습니다."
            )
        if message.get("role") != "assistant":
            raise ModelResponseError(
                "Ollama 응답 message의 role이 assistant가 아닙니다."
            )

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ModelResponseError(
                "Ollama 응답에 비어 있지 않은 message.content가 필요합니다."
            )
        try:
            json.loads(
                content,
                parse_constant=_reject_non_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as error:
            raise ModelResponseError(
                "Ollama message.content가 유효한 JSON이 아닙니다."
            ) from error

        thinking = message.get("thinking", "")
        if not isinstance(thinking, str):
            raise ModelResponseError(
                "Ollama 응답의 message.thinking이 문자열이 아닙니다."
            )

        metrics: dict[str, int] = {}
        for field in _METRIC_FIELDS:
            if field not in payload:
                continue
            value = payload[field]
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ModelResponseError(
                    f"Ollama 응답의 {field} 값이 유효한 음이 아닌 정수가 아닙니다."
                )
            metrics[field] = value

        return ModelReply(
            content=content,
            thinking=thinking,
            model=returned_model,
            done_reason=done_reason,
            metrics=metrics,
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
        raise ValueError(f"{label}은 일반 JSON으로 직렬화할 수 있어야 합니다.") from error


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"JSON 표준에 없는 상수입니다: {value}")


def _read_http_error_detail(error: urllib.error.HTTPError) -> str:
    """서버 오류 전문을 노출하지 않고 짧은 한 줄만 남긴다."""

    try:
        raw_detail = error.read(300)
    except OSError:
        return ""
    if not isinstance(raw_detail, bytes):
        return ""
    return raw_detail.decode("utf-8", errors="replace").replace(
        "\r", " "
    ).replace("\n", " ").strip()[:300]
