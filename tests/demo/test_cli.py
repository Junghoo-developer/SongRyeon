"""실제 Ollama를 호출하지 않는 데모 CLI 설정 테스트."""

from pathlib import Path

import pytest

from demo import cli
from llm.client import (
    DEFAULT_BASE_URL,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_MODEL_NAME,
    DEFAULT_NUM_CTX,
    DEFAULT_TIMEOUT_SECONDS,
)
from memory import DEFAULT_MEMORY_PATH


def test_parser_uses_large_local_model_defaults():
    args = cli._build_parser().parse_args(["질문"])

    assert args.model == DEFAULT_MODEL_NAME == "gemma4:26b"
    assert args.base_url == DEFAULT_BASE_URL
    assert args.num_ctx == DEFAULT_NUM_CTX
    assert args.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert args.keep_alive == DEFAULT_KEEP_ALIVE


def test_main_passes_self_hosted_runtime_options_to_client(
    monkeypatch,
    capsys,
):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.num_ctx = kwargs["num_ctx"]

        def check_ready(self):
            return {
                "server_version": "0.32.4",
                "model_name": self.model_name,
                "model_digest": "a" * 64,
            }

        @property
        def model_name(self):
            return captured["client"]["model_name"]

    monkeypatch.setattr(cli, "OllamaClient", FakeClient)
    monkeypatch.setattr(cli, "FileToolbox", lambda **kwargs: object())
    monkeypatch.setattr(
        cli,
        "_run_one",
        lambda question, **kwargs: captured.setdefault("question", question),
    )

    exit_code = cli.main(
        [
            "--model",
            "qwen3:14b",
            "--base-url",
            "https://ollama.example.test",
            "--num-ctx",
            "32768",
            "--timeout-seconds",
            "600",
            "--keep-alive",
            "30m",
            "코드를",
            "검토해줘",
        ]
    )

    assert exit_code == 0
    assert captured["client"] == {
        "base_url": "https://ollama.example.test",
        "model_name": "qwen3:14b",
        "num_ctx": 32768,
        "timeout_seconds": 600,
        "keep_alive": "30m",
    }
    assert captured["question"] == "코드를 검토해줘"
    assert (
        "backend=Ollama 0.32.4 / model=qwen3:14b / "
        "digest=aaaaaaaaaaaa / num_ctx=32768 준비 완료"
    ) in capsys.readouterr().out


def test_external_integration_is_explicit_one_shot_with_temporary_memory(
    monkeypatch,
    capsys,
):
    captured = {}

    class FakeExternalClient:
        provider = "openai_compatible"
        execution_mode = "external_api_integration"

        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.model_name = kwargs["model_name"]

        def check_configuration(self):
            captured["configuration_checked"] = True

    def fake_run_one(question, **kwargs):
        memory_path = Path(kwargs["memory_path"])
        captured["question"] = question
        captured["memory_path"] = memory_path
        captured["memory_parent_existed_during_run"] = (
            memory_path.parent.exists()
        )

    monkeypatch.setattr(
        cli,
        "OpenAICompatibleIntegrationClient",
        FakeExternalClient,
    )
    monkeypatch.setattr(cli, "OllamaClient", lambda **kwargs: pytest.fail(
        "외부 통합시험에서 Ollama fallback을 만들면 안 됩니다."
    ))
    monkeypatch.setattr(cli, "FileToolbox", lambda **kwargs: object())
    monkeypatch.setattr(cli, "_run_one", fake_run_one)

    exit_code = cli.main(
        [
            "--external-api-integration",
            "--external-api-base-url",
            "https://provider.example/v1",
            "--external-api-model",
            "provider/large-model",
            "한",
            "번만",
            "검사해줘",
        ]
    )

    assert exit_code == 0
    assert captured["client"] == {
        "base_url": "https://provider.example/v1",
        "model_name": "provider/large-model",
        "api_key_env": "OPENAI_API_KEY",
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
    }
    assert captured["configuration_checked"] is True
    assert captured["question"] == "한 번만 검사해줘"
    assert captured["memory_path"].resolve() != DEFAULT_MEMORY_PATH.resolve()
    assert captured["memory_parent_existed_during_run"] is True
    assert not captured["memory_path"].parent.exists()
    assert "mode=external_api_integration" in capsys.readouterr().out


def test_external_integration_requires_question_before_client_creation(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        cli,
        "OpenAICompatibleIntegrationClient",
        lambda **kwargs: pytest.fail("client를 만들면 안 됩니다."),
    )

    exit_code = cli.main(
        [
            "--external-api-integration",
            "--external-api-base-url",
            "https://provider.example/v1",
            "--external-api-model",
            "provider/large-model",
        ]
    )

    assert exit_code == 1
    assert "단발 질문" in capsys.readouterr().err


def test_external_missing_key_fails_before_toolbox_or_memory(
    monkeypatch,
    capsys,
):
    missing_env = "SONGRYEON_DEFINITELY_MISSING_API_KEY"
    monkeypatch.delenv(missing_env, raising=False)
    monkeypatch.setattr(
        cli,
        "FileToolbox",
        lambda **kwargs: pytest.fail("toolbox를 만들면 안 됩니다."),
    )
    monkeypatch.setattr(
        cli,
        "_run_one",
        lambda *args, **kwargs: pytest.fail("memory를 쓰면 안 됩니다."),
    )

    exit_code = cli.main(
        [
            "--external-api-integration",
            "--external-api-base-url",
            "https://provider.example/v1",
            "--external-api-model",
            "provider/large-model",
            "--external-api-key-env",
            missing_env,
            "질문",
        ]
    )

    assert exit_code == 1
    assert missing_env in capsys.readouterr().err


def test_external_integration_rejects_real_memory_before_client_creation(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        cli,
        "OpenAICompatibleIntegrationClient",
        lambda **kwargs: pytest.fail("client를 만들면 안 됩니다."),
    )

    exit_code = cli.main(
        [
            "--external-api-integration",
            "--external-api-base-url",
            "https://provider.example/v1",
            "--external-api-model",
            "provider/large-model",
            "--memory",
            str(DEFAULT_MEMORY_PATH),
            "질문",
        ]
    )

    assert exit_code == 1
    assert "실제 memory/memory.jsonl" in capsys.readouterr().err


def test_external_options_without_opt_in_are_rejected(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "OllamaClient",
        lambda **kwargs: pytest.fail("Ollama를 시작하면 안 됩니다."),
    )

    exit_code = cli.main(
        [
            "--external-api-base-url",
            "https://provider.example/v1",
            "질문",
        ]
    )

    assert exit_code == 1
    assert "--external-api-integration" in capsys.readouterr().err


def test_api_key_in_environment_never_auto_selects_external_backend(
    monkeypatch,
):
    captured = {}

    class FakeOllamaClient:
        num_ctx = DEFAULT_NUM_CTX

        def __init__(self, **kwargs):
            captured["ollama"] = kwargs
            self.model_name = kwargs["model_name"]

        def check_ready(self):
            return {
                "server_version": "test",
                "model_name": self.model_name,
                "model_digest": "a" * 64,
            }

    monkeypatch.setenv("OPENAI_API_KEY", "secret-that-must-not-trigger-api")
    monkeypatch.setattr(cli, "OllamaClient", FakeOllamaClient)
    monkeypatch.setattr(
        cli,
        "OpenAICompatibleIntegrationClient",
        lambda **kwargs: pytest.fail(
            "명시 플래그 없이 외부 client를 만들면 안 됩니다."
        ),
    )
    monkeypatch.setattr(cli, "FileToolbox", lambda **kwargs: object())
    monkeypatch.setattr(
        cli,
        "_run_one",
        lambda question, **kwargs: captured.setdefault("question", question),
    )

    assert cli.main(["로컬로", "실행해"]) == 0
    assert captured["ollama"]["model_name"] == "gemma4:26b"
    assert captured["question"] == "로컬로 실행해"
