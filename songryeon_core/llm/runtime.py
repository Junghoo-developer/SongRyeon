from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Literal

from songryeon_core.llm.base import LLMAdapter, LLMRequest
from songryeon_core.llm.fake import FakeLLMAdapter
from songryeon_core.llm.qwen_adapter import QwenLocalHTTPAdapter


LLMMode = Literal["off", "fake", "qwen"]
KNOWN_LLM_MODES = {"off", "fake", "qwen"}


@dataclass
class LLMRuntimeConfig:
    """현재 실행에서 LLM을 어떻게 켤지 정하는 설정값."""

    # 절대 정보: 런타임이 사용할 LLM 모드. off, fake, qwen 중 하나다.
    mode: LLMMode = "off"
    # 절대 정보: 호출 대상 모델 이름. fake/off에서도 기록용으로 둔다.
    model_id: str = "qwen3:14b"
    # 절대 정보: Qwen endpoint가 설정되어 있는지. 실제 URL 본문은 노출하지 않는다.
    endpoint_configured: bool = False
    # 안전 정보: Qwen 호출 방식. endpoint가 있으면 http, 없으면 ollama.
    transport: str = "ollama"
    # 절대 정보: Qwen HTTP 호출 제한 시간.
    timeout_seconds: int = 30
    # 절대 정보: 설정값의 출처.
    source: str = "defaults"


def build_llm_runtime_config(
    *,
    mode: str | None = None,
    model_id: str | None = None,
    endpoint: str | None = None,
    timeout_seconds: int | None = None,
) -> LLMRuntimeConfig:
    """환경 변수와 인자를 합쳐 LLM runtime 설정을 만든다."""

    selected_mode = (mode or os.environ.get("SONGRYEON_LLM_MODE") or "off").strip().lower()
    if selected_mode not in KNOWN_LLM_MODES:
        raise ValueError(f"unknown LLM mode: {selected_mode}")

    selected_model_id = model_id or os.environ.get("QWEN_MODEL_ID") or "qwen3:14b"
    selected_endpoint = endpoint if endpoint is not None else os.environ.get("QWEN_LOCAL_ENDPOINT")
    selected_timeout = timeout_seconds
    if selected_timeout is None:
        selected_timeout = _read_timeout_from_env()
    _validate_timeout(selected_timeout)

    source = "arguments" if any(
        value is not None for value in (mode, model_id, endpoint, timeout_seconds)
    ) else "environment_or_defaults"
    return LLMRuntimeConfig(
        mode=selected_mode,  # type: ignore[arg-type]
        model_id=selected_model_id,
        endpoint_configured=bool(selected_endpoint),
        transport="http" if selected_endpoint else "ollama",
        timeout_seconds=selected_timeout,
        source=source,
    )


def build_llm_adapter(
    config: LLMRuntimeConfig,
    *,
    endpoint: str | None = None,
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


def _read_timeout_from_env() -> int:
    raw_value = os.environ.get("QWEN_TIMEOUT_SECONDS")
    if raw_value is None:
        return 30
    try:
        timeout = int(raw_value)
    except ValueError as exc:
        raise ValueError("QWEN_TIMEOUT_SECONDS must be an integer") from exc
    _validate_timeout(timeout)
    return timeout


def _validate_timeout(timeout_seconds: int) -> None:
    if timeout_seconds <= 0:
        raise ValueError("Qwen timeout must be positive")
