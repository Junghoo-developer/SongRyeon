from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Literal

from songryeon_core.llm.base import LLMAdapter, LLMRequest
from songryeon_core.llm.fake import FakeLLMAdapter
from songryeon_core.llm.openai_responses_adapter import (
    DEFAULT_OPENAI_MAX_OUTPUT_TOKENS,
    DEFAULT_OPENAI_MODEL_ID,
    DEFAULT_OPENAI_REASONING_EFFORT,
    OpenAIResponsesAdapter,
)
from songryeon_core.llm.qwen_adapter import QwenLocalHTTPAdapter


LLMMode = Literal["off", "fake", "qwen", "openai"]
KNOWN_LLM_MODES = {"off", "fake", "qwen", "openai"}


@dataclass
class LLMRuntimeConfig:
    """현재 실행에서 LLM을 어떻게 켤지 정하는 설정값."""

    # 절대 정보: 런타임이 사용할 LLM 모드. openai는 외부 Responses API다.
    mode: LLMMode = "off"
    # 절대 정보: 호출 대상 모델 이름. fake/off에서도 기록용으로 둔다.
    model_id: str = "qwen3:14b"
    # 절대 정보: Qwen endpoint가 설정되어 있는지. 실제 URL 본문은 노출하지 않는다.
    endpoint_configured: bool = False
    # 안전 정보: Qwen 호출 방식. endpoint가 있으면 http, 없으면 ollama.
    transport: str = "ollama"
    # 절대 정보: Qwen HTTP 호출 제한 시간.
    timeout_seconds: int = 30
    # 절대 정보: 외부 API 키의 실제 값이 아니라 설정 여부만 보존한다.
    api_key_configured: bool = False
    # 절대 정보: OpenAI reasoning/output 상한. Qwen 모드에서는 사용하지 않는다.
    reasoning_effort: str = DEFAULT_OPENAI_REASONING_EFFORT
    max_output_tokens: int = DEFAULT_OPENAI_MAX_OUTPUT_TOKENS
    # 절대 정보: 설정값의 출처.
    source: str = "defaults"


def build_llm_runtime_config(
    *,
    mode: str | None = None,
    model_id: str | None = None,
    endpoint: str | None = None,
    timeout_seconds: int | None = None,
    api_key: str | None = None,
    reasoning_effort: str | None = None,
    max_output_tokens: int | None = None,
) -> LLMRuntimeConfig:
    """환경 변수와 인자를 합쳐 LLM runtime 설정을 만든다."""

    selected_mode = (mode or os.environ.get("SONGRYEON_LLM_MODE") or "off").strip().lower()
    if selected_mode not in KNOWN_LLM_MODES:
        raise ValueError(f"unknown LLM mode: {selected_mode}")

    if selected_mode == "openai":
        selected_model_id = (
            model_id or os.environ.get("OPENAI_MODEL_ID") or DEFAULT_OPENAI_MODEL_ID
        )
    else:
        selected_model_id = model_id or os.environ.get("QWEN_MODEL_ID") or "qwen3:14b"
    selected_endpoint = endpoint if endpoint is not None else os.environ.get("QWEN_LOCAL_ENDPOINT")
    selected_timeout = timeout_seconds
    if selected_timeout is None:
        selected_timeout = _read_timeout_from_env(selected_mode)
    _validate_timeout(selected_timeout)
    if selected_mode == "openai":
        selected_reasoning_effort = (
            reasoning_effort
            or os.environ.get("OPENAI_REASONING_EFFORT")
            or DEFAULT_OPENAI_REASONING_EFFORT
        )
        if selected_reasoning_effort not in {"low", "medium", "high", "xhigh"}:
            raise ValueError("unknown OpenAI reasoning effort")
        selected_max_output_tokens = max_output_tokens
        if selected_max_output_tokens is None:
            selected_max_output_tokens = _read_openai_max_output_tokens_from_env()
        if selected_max_output_tokens <= 0:
            raise ValueError("OPENAI_MAX_OUTPUT_TOKENS must be positive")
        selected_api_key = (
            api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        )
    else:
        selected_reasoning_effort = DEFAULT_OPENAI_REASONING_EFFORT
        selected_max_output_tokens = DEFAULT_OPENAI_MAX_OUTPUT_TOKENS
        selected_api_key = None

    source = "arguments" if any(
        value is not None
        for value in (
            mode,
            model_id,
            endpoint,
            timeout_seconds,
            api_key,
            reasoning_effort,
            max_output_tokens,
        )
    ) else "environment_or_defaults"
    return LLMRuntimeConfig(
        mode=selected_mode,  # type: ignore[arg-type]
        model_id=selected_model_id,
        endpoint_configured=bool(selected_endpoint),
        transport=(
            "openai_responses_api"
            if selected_mode == "openai"
            else ("http" if selected_endpoint else "ollama")
        ),
        timeout_seconds=selected_timeout,
        api_key_configured=bool(selected_api_key),
        reasoning_effort=selected_reasoning_effort,
        max_output_tokens=selected_max_output_tokens,
        source=source,
    )


def build_llm_adapter(
    config: LLMRuntimeConfig,
    *,
    endpoint: str | None = None,
    api_key: str | None = None,
) -> LLMAdapter | None:
    """LLMRuntimeConfig에 맞는 adapter를 만든다. off 모드는 None을 돌려준다."""

    if config.mode == "off":
        return None
    if config.mode == "fake":
        return FakeLLMAdapter()
    if config.mode == "qwen":
        return QwenLocalHTTPAdapter(
            endpoint=endpoint,
            model_id=config.model_id,
            timeout_seconds=config.timeout_seconds,
        )
    if config.mode == "openai":
        return OpenAIResponsesAdapter(
            api_key=api_key,
            model_id=config.model_id,
            timeout_seconds=config.timeout_seconds,
            reasoning_effort=config.reasoning_effort,
            max_output_tokens=config.max_output_tokens,
        )
    raise ValueError(f"unknown LLM mode: {config.mode}")


def llm_runtime_status(config: LLMRuntimeConfig | None = None) -> dict[str, object]:
    """현재 LLM runtime 설정 상태를 JSON 저장 가능한 dict로 돌려준다."""

    runtime_config = config or build_llm_runtime_config()
    status = asdict(runtime_config)
    status["enabled"] = runtime_config.mode != "off"
    status["adapter_kind"] = runtime_config.mode
    return status


def ping_qwen(
    *,
    endpoint: str | None = None,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, object]:
    """Qwen endpoint 연결 상태를 예외 대신 구조화된 결과로 돌려준다."""

    config = build_llm_runtime_config(
        mode="qwen",
        endpoint=endpoint,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
    )
    result: dict[str, object] = {
        "ok": False,
        "status": "not_checked",
        "runtime": llm_runtime_status(config),
    }

    selected_endpoint = endpoint if endpoint is not None else os.environ.get("QWEN_LOCAL_ENDPOINT")
    adapter = build_llm_adapter(config, endpoint=selected_endpoint)
    if adapter is None:
        result["status"] = "adapter_missing"
        result["error"] = "qwen adapter was not created"
        return result

    try:
        response = adapter.complete(
            LLMRequest(
                prompt="Return JSON only.",
                input_payload={"ping": True, "expected": "pong"},
            )
        )
    except Exception as exc:
        result["status"] = "adapter_failed"
        result["error"] = str(exc)
        result["error_type"] = exc.__class__.__name__
        return result

    result["ok"] = True
    result["status"] = "ok"
    result["model_id"] = response.model_id
    result["text_preview"] = response.text[:300]
    return result


def ping_openai(
    *,
    model_id: str | None = None,
    timeout_seconds: int | None = None,
    reasoning_effort: str | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, object]:
    """OpenAI API를 한 번만 호출하고 키 원문 없이 상태와 사용량을 보고한다."""

    config = build_llm_runtime_config(
        mode="openai",
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        reasoning_effort=reasoning_effort,
        max_output_tokens=max_output_tokens,
    )
    result: dict[str, object] = {
        "ok": False,
        "status": "not_checked",
        "runtime": llm_runtime_status(config),
    }
    if not config.api_key_configured:
        result["status"] = "config_missing"
        result["error"] = "OPENAI_API_KEY is not configured"
        return result

    adapter = build_llm_adapter(config)
    if adapter is None:
        result["status"] = "adapter_missing"
        return result
    try:
        response = adapter.complete(
            LLMRequest(
                prompt="Return one JSON object only.",
                input_payload={"ping": True, "expected": "pong"},
            )
        )
    except Exception as exc:
        result["status"] = "adapter_failed"
        result["failure_type"] = _openai_api_failure_type(exc)
        result["error"] = str(exc)
        result["error_type"] = exc.__class__.__name__
        usage_snapshot = getattr(adapter, "usage_snapshot", None)
        if callable(usage_snapshot):
            result["usage"] = usage_snapshot()
        return result

    result["ok"] = True
    result["status"] = "ok"
    result["model_id"] = response.model_id
    result["text_preview"] = response.text[:300]
    usage_snapshot = getattr(adapter, "usage_snapshot", None)
    if callable(usage_snapshot):
        result["usage"] = usage_snapshot()
    return result


def _read_timeout_from_env(mode: str) -> int:
    env_name = "OPENAI_TIMEOUT_SECONDS" if mode == "openai" else "QWEN_TIMEOUT_SECONDS"
    raw_value = os.environ.get(env_name)
    if raw_value is None:
        return 180 if mode == "openai" else 30
    try:
        timeout = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be an integer") from exc
    _validate_timeout(timeout)
    return timeout


def _read_openai_max_output_tokens_from_env() -> int:
    raw_value = os.environ.get("OPENAI_MAX_OUTPUT_TOKENS")
    if raw_value is None:
        return DEFAULT_OPENAI_MAX_OUTPUT_TOKENS
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("OPENAI_MAX_OUTPUT_TOKENS must be an integer") from exc


def _openai_api_failure_type(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        return code
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        body_code = body.get("code")
        if isinstance(body_code, str) and body_code:
            return body_code
    return exc.__class__.__name__


def _validate_timeout(timeout_seconds: int) -> None:
    if timeout_seconds <= 0:
        raise ValueError("LLM timeout must be positive")
