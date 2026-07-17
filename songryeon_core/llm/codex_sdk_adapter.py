from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from songryeon_core.llm.base import LLMRequest, LLMResponse


DEFAULT_CODEX_SDK_MODEL_ID = "gpt-5.4"
DEFAULT_CODEX_SDK_REASONING_EFFORT = "low"

_INTERNAL_CODEX_ENV_NAMES = {
    "CODEX_THREAD_ID",
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
    "CODEX_PERMISSION_PROFILE",
    "CODEX_SHELL",
}
_SENSITIVE_ENV_MARKERS = ("API_KEY", "TOKEN", "PASSWORD", "SECRET", "CREDENTIAL")
_TOOL_ITEM_TYPES = {
    "commandExecution",
    "fileChange",
    "mcpToolCall",
    "dynamicToolCall",
    "collabAgentToolCall",
    "webSearch",
    "imageView",
    "imageGeneration",
}
_TRANSPORT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "payload_json": {
            "type": "string",
            "description": "The exact JSON object required by the supplied node prompt.",
        }
    },
    "required": ["payload_json"],
    "additionalProperties": False,
}


class CodexSDKAdapter:
    """ChatGPT 인증을 사용하는 로컬 Codex SDK를 공통 LLM 경계에 연결한다."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_CODEX_SDK_MODEL_ID,
        reasoning_effort: str = DEFAULT_CODEX_SDK_REASONING_EFFORT,
        codex_bin: str | None = None,
        codex_factory: Callable[[object], object] | None = None,
        sdk_symbols: dict[str, object] | None = None,
    ) -> None:
        if reasoning_effort not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
            raise ValueError("unknown Codex SDK reasoning effort")
        self.model_id = model_id
        self.reasoning_effort = reasoning_effort
        self.codex_bin, self.codex_bin_source = resolve_codex_bin(codex_bin)
        self._codex_factory = codex_factory
        # 선택 SDK가 없는 CI에서도 주입된 가짜 transport 경계를 검사할 수 있게 한다.
        # 실제 실행은 override가 없으므로 계속 openai_codex의 공식 symbol만 사용한다.
        self._sdk_symbols_override = sdk_symbols
        self._codex: object | None = None
        self._workdir = tempfile.TemporaryDirectory(prefix="songryeon_codex_sdk_")
        self._account_checked = False
        self.auth_type: str | None = None
        self.plan_type: str | None = None
        self.sanitized_environment_variable_count = 0
        self.attempted_turn_count = 0
        self.completed_turn_count = 0
        self.accepted_response_count = 0
        self.input_tokens = 0
        self.cached_input_tokens = 0
        self.output_tokens = 0
        self.reasoning_output_tokens = 0
        self.total_tokens = 0
        self.last_thread_id: str | None = None
        self.last_turn_id: str | None = None
        self.last_tool_activity_count = 0
        self.last_failure_type: str | None = None
        self.last_failure_reason: str | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.attempted_turn_count += 1
        self.last_failure_type = None
        self.last_failure_reason = None
        try:
            codex = self._get_codex()
            self._verify_chatgpt_account(codex)
            sdk = self._resolved_sdk_symbols()
            thread = codex.thread_start(
                approval_mode=sdk["ApprovalMode"].deny_all,
                base_instructions=_base_instructions(request.prompt),
                cwd=self._workdir.name,
                ephemeral=True,
                model=self.model_id,
                sandbox=sdk["Sandbox"].read_only,
            )
            self.last_thread_id = _optional_string(getattr(thread, "id", None))
            result = thread.run(
                "JSON input payload:\n"
                + json.dumps(request.input_payload, ensure_ascii=False)
                + "\nReturn the required payload through payload_json.",
                approval_mode=sdk["ApprovalMode"].deny_all,
                cwd=self._workdir.name,
                effort=sdk["ReasoningEffort"](self.reasoning_effort),
                model=self.model_id,
                output_schema=_TRANSPORT_OUTPUT_SCHEMA,
                sandbox=sdk["Sandbox"].read_only,
            )
            self.completed_turn_count += 1
            self.last_turn_id = _optional_string(getattr(result, "id", None))
            self._record_usage(getattr(result, "usage", None))
            item_types = _thread_item_types(getattr(result, "items", []))
            self.last_tool_activity_count = sum(
                1 for item_type in item_types if item_type in _TOOL_ITEM_TYPES
            )
            if self.last_tool_activity_count:
                raise RuntimeError("Codex SDK node used a forbidden tool")

            text = _unwrap_payload_json(getattr(result, "final_response", None))
            self.accepted_response_count += 1
            return LLMResponse(text=text, model_id=self.model_id, raw=result)
        except Exception as exc:
            self.last_failure_type = _failure_type(exc)
            self.last_failure_reason = _short_failure_reason(exc)
            raise

    def close(self) -> None:
        codex = self._codex
        self._codex = None
        if codex is not None:
            close = getattr(codex, "close", None)
            if callable(close):
                close()
        self._workdir.cleanup()

    def usage_snapshot(self) -> dict[str, object]:
        return {
            "auth_type": self.auth_type,
            "plan_type": self.plan_type,
            "attempted_turn_count": self.attempted_turn_count,
            "completed_turn_count": self.completed_turn_count,
            "accepted_response_count": self.accepted_response_count,
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_output_tokens": self.reasoning_output_tokens,
            "total_tokens": self.total_tokens,
            "last_thread_id": self.last_thread_id,
            "last_turn_id": self.last_turn_id,
            "last_tool_activity_count": self.last_tool_activity_count,
            "codex_bin_configured": self.codex_bin is not None,
            "codex_bin_source": self.codex_bin_source,
            "sanitized_environment_variable_count": (
                self.sanitized_environment_variable_count
            ),
            "last_failure_type": self.last_failure_type,
            "last_failure_reason": self.last_failure_reason,
        }

    def _get_codex(self) -> object:
        if self._codex is not None:
            return self._codex
        sdk = self._resolved_sdk_symbols()
        config = sdk["CodexConfig"](
            codex_bin=self.codex_bin,
            cwd=self._workdir.name,
        )
        factory = self._codex_factory or sdk["Codex"]
        with _sanitized_child_environment() as removed_count:
            self.sanitized_environment_variable_count = removed_count
            self._codex = factory(config)
        return self._codex

    def _resolved_sdk_symbols(self) -> dict[str, object]:
        override = self._sdk_symbols_override
        if override is None:
            return _sdk_symbols()
        required = {"ApprovalMode", "Codex", "CodexConfig", "ReasoningEffort", "Sandbox"}
        missing = sorted(required.difference(override))
        if missing:
            raise ValueError(f"Codex SDK symbol override is missing: {missing}")
        return override

    def _verify_chatgpt_account(self, codex: object) -> None:
        if self._account_checked:
            return
        account_response = codex.account(refresh_token=False)
        account = getattr(account_response, "account", None)
        root = getattr(account, "root", None)
        auth_type = _optional_string(getattr(root, "type", None))
        if auth_type != "chatgpt":
            raise RuntimeError("Codex SDK is not authenticated with ChatGPT")
        plan = getattr(root, "plan_type", None)
        self.auth_type = auth_type
        self.plan_type = _optional_string(getattr(plan, "value", plan))
        self._account_checked = True

    def _record_usage(self, usage: object | None) -> None:
        total = getattr(usage, "total", None)
        self.input_tokens += _non_negative_int(getattr(total, "input_tokens", 0))
        self.cached_input_tokens += _non_negative_int(
            getattr(total, "cached_input_tokens", 0)
        )
        self.output_tokens += _non_negative_int(getattr(total, "output_tokens", 0))
        self.reasoning_output_tokens += _non_negative_int(
            getattr(total, "reasoning_output_tokens", 0)
        )
        self.total_tokens += _non_negative_int(getattr(total, "total_tokens", 0))


def ping_codex_sdk(
    *,
    model_id: str = DEFAULT_CODEX_SDK_MODEL_ID,
    reasoning_effort: str = DEFAULT_CODEX_SDK_REASONING_EFFORT,
    codex_bin: str | None = None,
) -> dict[str, object]:
    adapter = CodexSDKAdapter(
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        codex_bin=codex_bin,
    )
    result: dict[str, object] = {
        "ok": False,
        "status": "not_checked",
        "model_id": model_id,
        "transport": "codex_sdk_app_server",
        "sandbox": "read-only",
        "approval_mode": "deny_all",
        "api_key_forwarded": False,
    }
    try:
        response = adapter.complete(
            LLMRequest(
                prompt=(
                    "Return a JSON object with ping set to pong and auth_surface set "
                    "to chatgpt_subscription. Do not use tools."
                ),
                input_payload={"ping": True},
            )
        )
        payload = json.loads(response.text)
        if payload.get("ping") != "pong":
            raise ValueError("Codex SDK ping payload mismatch")
        result["ok"] = True
        result["status"] = "ok"
        result["response"] = payload
    except Exception as exc:
        result["status"] = "adapter_failed"
        result["failure_type"] = _failure_type(exc)
        result["failure_reason"] = _short_failure_reason(exc)
    finally:
        result["usage"] = adapter.usage_snapshot()
        adapter.close()
    return result


def resolve_codex_bin(explicit_path: str | None = None) -> tuple[str | None, str]:
    """사용자가 고른 CLI나 저장소 로컬 최신 CLI를 찾는다.

    경로가 없으면 Python SDK에 내장된 CLI 선택으로 돌아간다. 모델 호환성이
    부족할 때 조용히 모델을 낮추지는 않고, SDK가 돌려주는 실패를 그대로 남긴다.
    """

    if explicit_path:
        return _require_codex_bin(explicit_path), "explicit"

    environment_path = os.environ.get("SONGRYEON_CODEX_BIN")
    if environment_path:
        return _require_codex_bin(environment_path), "environment"

    if os.name == "nt":
        cache_root = (
            Path.cwd()
            / ".songryeon_core_cache"
            / "codex_cli"
            / "node_modules"
            / ".pnpm"
        )
        candidates = list(
            cache_root.glob(
                "@openai+codex@*-win32-x64/node_modules/@openai/codex/"
                "vendor/x86_64-pc-windows-msvc/bin/codex.exe"
            )
        )
        if candidates:
            newest = max(candidates, key=lambda path: path.stat().st_mtime_ns)
            return str(newest.resolve()), "workspace_cache"

    return None, "sdk_bundled"


def _require_codex_bin(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.is_file():
        raise ValueError(f"Codex CLI executable does not exist: {path_value}")
    return str(path.resolve())


def _sdk_symbols() -> dict[str, object]:
    try:
        from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox
        from openai_codex.types import ReasoningEffort
    except Exception as exc:
        raise RuntimeError(
            "openai-codex is not installed; run `python -m pip install openai-codex`"
        ) from exc
    return {
        "ApprovalMode": ApprovalMode,
        "Codex": Codex,
        "CodexConfig": CodexConfig,
        "ReasoningEffort": ReasoningEffort,
        "Sandbox": Sandbox,
    }


def _base_instructions(node_prompt: str) -> str:
    return (
        node_prompt
        + "\n\nTRANSPORT BOUNDARY:\n"
        + "- Do not use shell, files, web search, MCP, images, or any other tool.\n"
        + "- Judge only from the supplied JSON input payload.\n"
        + "- Produce the node prompt's JSON object, serialize that object as a JSON string, "
        + "and place the string in payload_json."
    )


def _unwrap_payload_json(final_response: object) -> str:
    if not isinstance(final_response, str) or not final_response.strip():
        raise RuntimeError("Codex SDK returned no final response")
    wrapper = json.loads(final_response)
    if not isinstance(wrapper, dict):
        raise ValueError("Codex SDK transport wrapper must be an object")
    payload_json = wrapper.get("payload_json")
    if not isinstance(payload_json, str):
        raise ValueError("Codex SDK transport wrapper has no payload_json")
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("Codex SDK node payload must be a JSON object")
    return json.dumps(payload, ensure_ascii=False)


def _thread_item_types(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    values: list[str] = []
    for item in items:
        root = getattr(item, "root", item)
        item_type = getattr(root, "type", None)
        if isinstance(item_type, str):
            values.append(item_type)
    return values


@contextmanager
def _sanitized_child_environment() -> Iterator[int]:
    names = {
        name
        for name in os.environ
        if name in _INTERNAL_CODEX_ENV_NAMES
        or any(marker in name.upper() for marker in _SENSITIVE_ENV_MARKERS)
    }
    saved = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ.pop(name, None)
    try:
        yield len(names)
    finally:
        for name, value in saved.items():
            if value is not None:
                os.environ[name] = value


def _failure_type(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    return code if isinstance(code, str) and code else exc.__class__.__name__


def _short_failure_reason(exc: Exception, *, limit: int = 500) -> str:
    compact = " ".join((str(exc) or exc.__class__.__name__).split())
    return compact if len(compact) <= limit else f"{compact[: limit - 3]}..."


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _non_negative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0
