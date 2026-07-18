from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_LOCAL_TIMEOUT_SECONDS = 180
DEFAULT_VESSEL_R_MODE = "auto"
_ENV_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class LocalEnvLoadResult:
    """로컬 .env에서 값 자체를 노출하지 않고 로드 상태만 돌려준다."""

    status: str
    path: str
    loaded_keys: tuple[str, ...]
    preserved_process_keys: tuple[str, ...]


def load_local_env(path: str | Path) -> LocalEnvLoadResult:
    """단순 KEY=VALUE .env를 읽되 이미 존재하는 프로세스 값을 우선한다."""

    source = Path(path)
    if not source.exists():
        return LocalEnvLoadResult(
            status="missing",
            path=str(source),
            loaded_keys=(),
            preserved_process_keys=(),
        )

    loaded_keys: list[str] = []
    preserved_keys: list[str] = []
    for line_number, raw_line in enumerate(
        source.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"invalid local .env entry at line {line_number}")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if _ENV_KEY_PATTERN.fullmatch(key) is None:
            raise ValueError(f"invalid local .env key at line {line_number}")
        value = _parse_env_value(raw_value.strip(), line_number=line_number)
        if key in os.environ:
            preserved_keys.append(key)
            continue
        os.environ[key] = value
        loaded_keys.append(key)

    return LocalEnvLoadResult(
        status="loaded",
        path=str(source),
        loaded_keys=tuple(loaded_keys),
        preserved_process_keys=tuple(preserved_keys),
    )


def resolve_main_cli_args(
    explicit_args: Sequence[str],
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[list[str], bool]:
    """명시 인자가 없을 때만 간편 qwen-chat 인자를 생성한다."""

    if explicit_args:
        return list(explicit_args), False
    return build_default_chat_cli_args(environ=environ), True


def build_default_chat_cli_args(
    *,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """로컬 기본값을 기존 argparse가 이해하는 qwen-chat 인자로 바꾼다."""

    values = os.environ if environ is None else environ
    timeout_seconds = _positive_int(
        values.get("SONGRYEON_DEFAULT_TIMEOUT_SECONDS"),
        default=DEFAULT_LOCAL_TIMEOUT_SECONDS,
        name="SONGRYEON_DEFAULT_TIMEOUT_SECONDS",
    )
    args = ["qwen-chat", "--timeout", str(timeout_seconds)]

    model_id = str(values.get("QWEN_MODEL_ID") or "").strip()
    if model_id:
        args.extend(["--model-id", model_id])
    if _bool_value(
        values.get("SONGRYEON_DEFAULT_LIVE_TRACE"),
        default=True,
        name="SONGRYEON_DEFAULT_LIVE_TRACE",
    ):
        args.append("--live-trace")
    if _vessel_r_enabled(values):
        args.extend(["--enable-r-route-experimental", "--enable-vessel-r-route"])
    workspace_root = str(values.get("SONGRYEON_WORKSPACE_ROOT") or "").strip()
    if workspace_root:
        args.extend(["--workspace", workspace_root])
    return args


def _vessel_r_enabled(values: Mapping[str, str]) -> bool:
    mode = str(
        values.get("SONGRYEON_DEFAULT_ENABLE_VESSEL_R") or DEFAULT_VESSEL_R_MODE
    ).strip().lower()
    if mode in _TRUE_VALUES:
        return True
    if mode in _FALSE_VALUES:
        return False
    if mode != "auto":
        raise ValueError(
            "SONGRYEON_DEFAULT_ENABLE_VESSEL_R must be auto, true, or false"
        )
    return all(
        str(values.get(name) or "").strip()
        for name in (
            "SONGRYEON_NEO4J_URI",
            "SONGRYEON_NEO4J_USER",
            "SONGRYEON_NEO4J_PASSWORD",
            "SONGRYEON_NEO4J_DATABASE",
        )
    )


def _parse_env_value(raw_value: str, *, line_number: int) -> str:
    if not raw_value:
        return ""
    if raw_value[0] not in {'"', "'"}:
        return raw_value
    quote = raw_value[0]
    if len(raw_value) < 2 or raw_value[-1] != quote:
        raise ValueError(f"unterminated local .env quote at line {line_number}")
    return raw_value[1:-1]


def _bool_value(value: str | None, *, default: bool, name: str) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be true or false")


def _positive_int(value: str | None, *, default: int, name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed
