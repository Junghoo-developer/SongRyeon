from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from songryeon_core.runtime.local_launcher import (
    build_default_chat_cli_args,
    load_local_env,
    resolve_main_cli_args,
)


def test_local_env_loads_values_without_overwriting_process_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "EXISTING_VALUE=file-value\n"
        "NEW_VALUE='new-value'\n"
        "VALUE_WITH_EQUALS=a=b=c\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EXISTING_VALUE", "process-value")
    monkeypatch.delenv("NEW_VALUE", raising=False)
    monkeypatch.delenv("VALUE_WITH_EQUALS", raising=False)

    result = load_local_env(env_path)

    assert result.status == "loaded"
    assert os.environ["EXISTING_VALUE"] == "process-value"
    assert os.environ["NEW_VALUE"] == "new-value"
    assert os.environ["VALUE_WITH_EQUALS"] == "a=b=c"
    assert result.loaded_keys == ("NEW_VALUE", "VALUE_WITH_EQUALS")
    assert result.preserved_process_keys == ("EXISTING_VALUE",)


def test_default_chat_args_enable_vessel_only_when_local_config_is_complete() -> None:
    complete_env = {
        "QWEN_MODEL_ID": "qwen3:14b",
        "SONGRYEON_DEFAULT_TIMEOUT_SECONDS": "180",
        "SONGRYEON_DEFAULT_LIVE_TRACE": "true",
        "SONGRYEON_DEFAULT_ENABLE_VESSEL_R": "auto",
        "SONGRYEON_NEO4J_URI": "bolt://localhost:7787",
        "SONGRYEON_NEO4J_USER": "neo4j",
        "SONGRYEON_NEO4J_PASSWORD": "configured-only-for-test",
        "SONGRYEON_NEO4J_DATABASE": "neo4j",
    }

    args = build_default_chat_cli_args(environ=complete_env)

    assert args[:3] == ["qwen-chat", "--timeout", "180"]
    assert ["--model-id", "qwen3:14b"] == args[3:5]
    assert "--live-trace" in args
    assert "--enable-r-route-experimental" in args
    assert "--enable-vessel-r-route" in args

    incomplete_env = dict(complete_env)
    incomplete_env.pop("SONGRYEON_NEO4J_PASSWORD")
    incomplete_args = build_default_chat_cli_args(environ=incomplete_env)
    assert "--enable-r-route-experimental" not in incomplete_args
    assert "--enable-vessel-r-route" not in incomplete_args


def test_explicit_cli_args_are_not_replaced_by_default_chat() -> None:
    resolved, default_launch = resolve_main_cli_args(
        ["quick-smoke"],
        environ={},
    )

    assert resolved == ["quick-smoke"]
    assert default_launch is False


def test_python_main_without_subcommand_starts_chat_and_can_exit() -> None:
    env = os.environ.copy()
    env["SONGRYEON_DEFAULT_ENABLE_VESSEL_R"] = "false"
    env["SONGRYEON_DEFAULT_LIVE_TRACE"] = "false"
    completed = subprocess.run(
        [sys.executable, "main.py"],
        cwd=Path(__file__).resolve().parents[1],
        input="/exit\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0
    assert "SongRyeon qwen-chat" in completed.stdout
    assert "간편 실행:" in completed.stdout
    assert "송련> 종료" in completed.stdout
