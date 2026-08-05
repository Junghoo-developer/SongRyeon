"""ChatGPT에 로그인된 Codex를 쓰는 격리된 모델 체급 비교 client.

이 경로는 대회 제출용 기본 실행 경로가 아니다. Codex SDK 자체가 하나의
에이전트이므로, 빈 임시 작업 폴더와 읽기 전용 sandbox에서 실행하고 도구
사용 흔적이 하나라도 있으면 결과를 폐기한다. 이로써 송련이 제공한 prompt
외의 프로젝트 파일을 Codex가 직접 읽어 증거 경계를 우회하지 못하게 한다.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .client import ModelCallError, ModelReply, ModelResponseError


DEFAULT_CODEX_ACCOUNT_MODEL = "gpt-5.6-sol"
DEFAULT_CODEX_REASONING_EFFORT = "medium"
CODEX_REASONING_EFFORTS = (
    "none",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
)

_PASSIVE_ITEM_TYPE_NAMES = frozenset(
    {
        "AgentMessageThreadItem",
        "ReasoningThreadItem",
        "UserMessageThreadItem",
    }
)
_BACKEND_DEVELOPER_INSTRUCTIONS = """\
송련의 구조화 출력 모델 백엔드로만 작동하라.
도구, shell, 웹 검색, 파일 열람, 하위 에이전트 또는 외부 연결을 사용하지 마라.
현재 thread에 제공된 base instructions와 사용자 입력만 처리하라.
최종 출력은 요청된 JSON schema를 만족하는 JSON 객체 하나여야 한다.
"""


@dataclass(frozen=True)
class _CodexSdkBindings:
    """선택 의존성을 늦게 불러오고 테스트에서는 가짜 SDK로 바꾸는 경계."""

    codex_factory: Callable[[], object]
    sandbox_read_only: object
    approval_deny_all: object
    version: str


def _load_codex_sdk() -> _CodexSdkBindings:
    try:
        import openai_codex
        from openai_codex import ApprovalMode, Codex, Sandbox
    except ImportError:
        raise ModelCallError(
            "Codex 계정 통합시험에는 선택 의존성이 필요합니다. "
            "송련 전용 가상환경에서 python -m pip install -e \".[codex]\"를 "
            "실행하세요."
        ) from None

    return _CodexSdkBindings(
        codex_factory=Codex,
        sandbox_read_only=Sandbox.read_only,
        approval_deny_all=ApprovalMode.deny_all,
        version=openai_codex.__version__,
    )


class CodexAccountIntegrationClient:
    """저장된 ChatGPT 인증으로 Codex SDK를 호출하는 통합시험 client."""

    provider = "openai_codex"
    execution_mode = "codex_account_integration"

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_CODEX_ACCOUNT_MODEL,
        reasoning_effort: str = DEFAULT_CODEX_REASONING_EFFORT,
        sdk_loader: Callable[[], _CodexSdkBindings] = _load_codex_sdk,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name은 비어 있지 않은 문자열이어야 합니다.")
        if reasoning_effort not in CODEX_REASONING_EFFORTS:
            raise ValueError(
                "reasoning_effort는 "
                + ", ".join(CODEX_REASONING_EFFORTS)
                + " 중 하나여야 합니다."
            )
        if not callable(sdk_loader):
            raise TypeError("sdk_loader는 호출 가능해야 합니다.")

        self.model_name = model_name.strip()
        self.reasoning_effort = reasoning_effort
        self._sdk_loader = sdk_loader
        self._bindings: _CodexSdkBindings | None = None
        self._codex = None
        self._configuration_checked = False
        self._isolation_directory = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"model_name={self.model_name!r}, "
            f"reasoning_effort={self.reasoning_effort!r})"
        )

    def check_configuration(self) -> dict[str, str]:
        """ChatGPT 인증과 요청 모델 노출 여부만 확인한다."""

        bindings, codex = self._ensure_codex()
        try:
            account_response = codex.account()
            account = getattr(account_response, "account", None)
            account_root = getattr(account, "root", None)
            if type(account_root).__name__ != "ChatgptAccount":
                raise ModelCallError(
                    "Codex SDK가 ChatGPT 계정으로 로그인돼 있지 않습니다."
                )

            models_response = codex.models(include_hidden=True)
            model_ids = {
                model_id
                for model in getattr(models_response, "data", [])
                if (model_id := _read_model_id(model)) is not None
            }
        except ModelCallError:
            raise
        except Exception:
            raise ModelCallError(
                "Codex 계정 인증 또는 모델 목록을 확인하지 못했습니다."
            ) from None

        if self.model_name not in model_ids:
            raise ModelCallError(
                "현재 Codex 계정에서 요청 모델을 사용할 수 없습니다: "
                f"{self.model_name}"
            )

        self._configuration_checked = True
        return {
            "provider": self.provider,
            "execution_mode": self.execution_mode,
            "model_name": self.model_name,
            "reasoning_effort": self.reasoning_effort,
            "sdk_version": bindings.version,
        }

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict,
        num_predict: int,
    ) -> ModelReply:
        """빈 임시 폴더의 일회성 thread에서 구조화 출력을 받는다."""

        _validate_complete_arguments(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            num_predict=num_predict,
        )
        if not self._configuration_checked:
            self.check_configuration()
        bindings, codex = self._ensure_codex()
        cwd = self._ensure_isolation_cwd()

        try:
            thread = codex.thread_start(
                approval_mode=bindings.approval_deny_all,
                base_instructions=system_prompt,
                cwd=cwd,
                developer_instructions=_BACKEND_DEVELOPER_INSTRUCTIONS,
                ephemeral=True,
                model=self.model_name,
                sandbox=bindings.sandbox_read_only,
            )
            result = thread.run(
                user_prompt,
                approval_mode=bindings.approval_deny_all,
                cwd=cwd,
                effort=self.reasoning_effort,
                model=self.model_name,
                output_schema=response_schema,
                sandbox=bindings.sandbox_read_only,
            )
        except Exception as error:
            raise ModelCallError(
                "Codex 계정 모델 호출을 완료하지 못했습니다. "
                f"오류 종류: {type(error).__name__}"
            ) from None

        return self._parse_result(result, num_predict=num_predict)

    def close(self) -> None:
        """SDK 하위 process를 종료한다. 여러 번 호출해도 안전하다."""

        codex = self._codex
        isolation_directory = self._isolation_directory
        self._codex = None
        self._isolation_directory = None
        self._configuration_checked = False
        if codex is not None:
            try:
                codex.close()
            except Exception:
                # 이미 끝난 하위 process 정리 실패가 모델 결과를 덮어쓰지 않게 한다.
                pass
        if isolation_directory is not None:
            _remove_isolation_directory(isolation_directory)

    def _ensure_codex(self):
        if self._bindings is None:
            self._bindings = self._sdk_loader()
        if not isinstance(self._bindings, _CodexSdkBindings):
            raise TypeError("sdk_loader는 _CodexSdkBindings를 반환해야 합니다.")

        if self._codex is None:
            try:
                self._codex = self._bindings.codex_factory()
            except Exception:
                raise ModelCallError(
                    "Codex SDK process를 시작하지 못했습니다."
                ) from None
        return self._bindings, self._codex

    def _ensure_isolation_cwd(self) -> str:
        """Windows에서도 SDK 종료 전까지 삭제하지 않을 빈 작업 폴더."""

        if self._isolation_directory is None:
            self._isolation_directory = Path(tempfile.mkdtemp(
                prefix="songryeon-codex-account-",
            ))
        return str(self._isolation_directory.resolve())

    def _parse_result(self, result, *, num_predict: int) -> ModelReply:
        status = getattr(getattr(result, "status", None), "value", None)
        if status != "completed" or getattr(result, "error", None) is not None:
            raise ModelResponseError(
                "Codex 계정 모델의 turn이 정상 완료되지 않았습니다."
            )

        for item in getattr(result, "items", []):
            item_root = getattr(item, "root", None)
            item_type = type(item_root).__name__
            if item_type not in _PASSIVE_ITEM_TYPE_NAMES:
                raise ModelResponseError(
                    "Codex 계정 모델이 허용되지 않은 도구 또는 부가 작업을 "
                    "시도해 결과를 폐기했습니다."
                )

        content = getattr(result, "final_response", None)
        if not isinstance(content, str) or not content.strip():
            raise ModelResponseError(
                "Codex 계정 모델에 비어 있지 않은 최종 응답이 필요합니다."
            )
        try:
            decoded = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            raise ModelResponseError(
                "Codex 계정 모델의 최종 응답이 유효한 JSON이 아닙니다."
            ) from None
        if not isinstance(decoded, dict):
            raise ModelResponseError(
                "Codex 계정 모델의 최종 응답은 JSON 객체여야 합니다."
            )

        metrics = _read_usage_metrics(getattr(result, "usage", None))
        output_tokens = metrics.get("output_tokens")
        if output_tokens is not None and output_tokens > num_predict:
            raise ModelResponseError(
                "Codex 계정 모델 출력이 num_predict 상한을 넘었습니다."
            )

        return ModelReply(
            content=content,
            thinking="",
            model=self.model_name,
            done_reason="stop",
            metrics=metrics,
        )


def _read_model_id(model) -> str | None:
    model_id = getattr(model, "model", None)
    if isinstance(model_id, str) and model_id:
        return model_id

    model_dump = getattr(model, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            model_id = dumped.get("model") or dumped.get("id")
            if isinstance(model_id, str) and model_id:
                return model_id
    return None


def _read_usage_metrics(usage) -> dict[str, int]:
    total = getattr(usage, "total", None)
    if total is None:
        return {}

    metrics = {}
    for field in (
        "cached_input_tokens",
        "input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
    ):
        value = getattr(total, field, None)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            metrics[field] = value
    return metrics


def _remove_isolation_directory(directory: Path) -> None:
    """Windows 하위 process가 cwd handle을 놓을 짧은 시간을 허용한다."""

    for _ in range(5):
        try:
            shutil.rmtree(directory)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(0.05)

    # 정리 실패가 이미 받은 모델 결과나 CLI 종료를 망치지 않게 한다.
    shutil.rmtree(directory, ignore_errors=True)


def _validate_complete_arguments(
    *,
    system_prompt,
    user_prompt,
    response_schema,
    num_predict,
) -> None:
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
    try:
        json.dumps(response_schema, allow_nan=False)
    except (RecursionError, TypeError, ValueError):
        raise ValueError(
            "response_schema는 일반 JSON으로 직렬화할 수 있어야 합니다."
        ) from None
