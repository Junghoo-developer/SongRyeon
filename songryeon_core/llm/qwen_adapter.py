from __future__ import annotations

import json
import os
import urllib.request

from songryeon_core.llm.base import LLMRequest, LLMResponse


DEFAULT_QWEN_NUM_CTX = 16384
QWEN_NUM_CTX_ENV = "SONGRYEON_QWEN_NUM_CTX"


class QwenLocalHTTPAdapter:
    """Qwen adapter.

    If QWEN_LOCAL_ENDPOINT is set, it calls an OpenAI-compatible HTTP endpoint.
    Otherwise it follows the original SongRyeon_Project pattern and calls Ollama
    directly with ollama.chat(...).
    """

    def __init__(
        self,
        endpoint: str | None = None,
        model_id: str = "qwen3:14b",
        timeout_seconds: int = 30,
        num_ctx: int | None = None,
    ) -> None:
        self.endpoint = endpoint or os.environ.get("QWEN_LOCAL_ENDPOINT")
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.num_ctx = _resolve_num_ctx(num_ctx)

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.endpoint:
            return self._complete_with_ollama(request)
        return self._complete_with_http(request)

    def _complete_with_http(self, request: LLMRequest) -> LLMResponse:
        body = json.dumps(
            {
                "model": self.model_id,
                "messages": [
                    {"role": "system", "content": request.prompt},
                    {"role": "user", "content": json.dumps(request.input_payload, ensure_ascii=False)},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
        text = _extract_text(raw)
        return LLMResponse(text=text, model_id=self.model_id, raw=raw)

    def _complete_with_ollama(self, request: LLMRequest) -> LLMResponse:
        try:
            import ollama
        except Exception as exc:
            raise RuntimeError("ollama python package is not available") from exc

        kwargs: dict[str, object] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": request.prompt},
                {"role": "user", "content": json.dumps(request.input_payload, ensure_ascii=False)},
            ],
            "options": {
                "temperature": 0,
                # Ollama의 모델 최대 context와 실제 실행 context는 별개다.
                # 이 값을 생략하면 4,096으로 실행되어 긴 node_3 코드 재료가 잘릴 수 있다.
                "num_ctx": self.num_ctx,
            },
        }
        if request.response_format == "json":
            kwargs["format"] = "json"
        raw = _json_safe_raw(ollama.chat(**kwargs))
        text = _extract_text(raw)
        return LLMResponse(text=text, model_id=self.model_id, raw=raw)


def _resolve_num_ctx(explicit_num_ctx: int | None) -> int:
    if explicit_num_ctx is not None:
        if explicit_num_ctx < 1:
            raise ValueError("Qwen num_ctx must be at least 1")
        return explicit_num_ctx
    raw_value = os.environ.get(QWEN_NUM_CTX_ENV)
    if raw_value is None or not raw_value.strip():
        return DEFAULT_QWEN_NUM_CTX
    try:
        resolved = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{QWEN_NUM_CTX_ENV} must be an integer") from exc
    if resolved < 1:
        raise ValueError(f"{QWEN_NUM_CTX_ENV} must be at least 1")
    return resolved


def qwen_ping() -> dict[str, object]:
    """Qwen endpoint가 설정되어 있으면 짧은 ping을 시도한다."""

    from songryeon_core.llm.runtime import ping_qwen

    return ping_qwen()


def _extract_text(raw: object) -> str:
    if isinstance(raw, dict):
        message = raw.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
                if isinstance(first.get("text"), str):
                    return first["text"]
    return json.dumps(raw, ensure_ascii=False)


def _json_safe_raw(raw: object) -> object:
    if isinstance(raw, dict):
        return raw
    model_dump = getattr(raw, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    dict_method = getattr(raw, "dict", None)
    if callable(dict_method):
        return dict_method()
    try:
        return dict(raw)  # type: ignore[arg-type]
    except Exception:
        return {"raw_text": str(raw)}
