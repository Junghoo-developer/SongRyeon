from __future__ import annotations

import json
import os
from typing import Any

from songryeon_core.llm.base import LLMRequest, LLMResponse


DEFAULT_OPENAI_MODEL_ID = "gpt-5.3-codex"
DEFAULT_OPENAI_REASONING_EFFORT = "medium"
DEFAULT_OPENAI_MAX_OUTPUT_TOKENS = 8192


class OpenAIResponsesAdapter:
    """OpenAI Responses API를 SongRyeon의 공통 LLM 경계에 연결한다.

    API 키는 환경 변수에서 읽되 객체 상태, 응답 raw, trace/data record에
    복사하지 않는다. 이 adapter가 보존하는 절대정보는 호출 횟수와 API가
    돌려준 token usage 합계뿐이다.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_id: str = DEFAULT_OPENAI_MODEL_ID,
        timeout_seconds: int = 180,
        reasoning_effort: str = DEFAULT_OPENAI_REASONING_EFFORT,
        max_output_tokens: int = DEFAULT_OPENAI_MAX_OUTPUT_TOKENS,
        client: object | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("OpenAI timeout must be positive")
        if max_output_tokens <= 0:
            raise ValueError("OpenAI max_output_tokens must be positive")
        if reasoning_effort not in {"low", "medium", "high", "xhigh"}:
            raise ValueError("unknown OpenAI reasoning effort")

        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = client
        self.attempted_call_count = 0
        self.completed_call_count = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.last_response_id: str | None = None
        self.last_failure_type: str | None = None
        self.last_failure_reason: str | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        self.attempted_call_count += 1
        self.last_failure_type = None
        self.last_failure_reason = None
        try:
            response = client.responses.create(
                model=self.model_id,
                instructions=request.prompt,
                # Responses JSON mode는 instructions뿐 아니라 input에도 json 표지를 요구한다.
                # 의미를 덧붙이지 않고 기존 payload 앞에 고정 형식 라벨만 붙인다.
                input=(
                    "JSON input payload:\n"
                    + json.dumps(request.input_payload, ensure_ascii=False)
                ),
                reasoning={"effort": self.reasoning_effort},
                text={"format": {"type": "json_object"}},
                max_output_tokens=self.max_output_tokens,
                store=False,
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            self.last_failure_type = _api_failure_type(exc)
            self.last_failure_reason = _short_failure_reason(exc)
            raise
        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OpenAI Responses API returned no output_text")

        self.completed_call_count += 1
        self.last_response_id = _optional_string(getattr(response, "id", None))
        self._record_usage(getattr(response, "usage", None))
        response_model = _optional_string(getattr(response, "model", None)) or self.model_id
        return LLMResponse(text=text, model_id=response_model, raw=response)

    def usage_snapshot(self) -> dict[str, object]:
        """키나 원문 없이 API 사용량 절대정보만 반환한다."""

        return {
            "attempted_api_call_count": self.attempted_call_count,
            "completed_api_call_count": self.completed_call_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "last_response_id": self.last_response_id,
            "last_failure_type": self.last_failure_type,
            "last_failure_reason": self.last_failure_reason,
        }

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        try:
            from openai import OpenAI
        except Exception as exc:
            raise RuntimeError(
                "openai package is not available; install it with `python -m pip install openai`"
            ) from exc
        self._client = OpenAI(api_key=self._api_key, timeout=self.timeout_seconds)
        return self._client

    def _record_usage(self, usage: object | None) -> None:
        self.input_tokens += _non_negative_int(getattr(usage, "input_tokens", 0))
        self.output_tokens += _non_negative_int(getattr(usage, "output_tokens", 0))
        self.total_tokens += _non_negative_int(getattr(usage, "total_tokens", 0))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _non_negative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _api_failure_type(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        return code
    return exc.__class__.__name__


def _short_failure_reason(exc: Exception, *, limit: int = 500) -> str:
    compact = " ".join((str(exc) or exc.__class__.__name__).split())
    return compact if len(compact) <= limit else f"{compact[: limit - 3]}..."
