from __future__ import annotations

from types import SimpleNamespace

from songryeon_core.llm.base import LLMRequest
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.llm.openai_responses_adapter import OpenAIResponsesAdapter
from songryeon_core.llm.runtime import build_llm_runtime_config, ping_openai
from songryeon_core.runtime.user_turn import run_openai_user_turn
from songryeon_core.runtime.terminal_view import render_pretty_turn


class _FakeResponses:
    def __init__(self) -> None:
        self.last_kwargs: dict[str, object] | None = None

    def create(self, **kwargs: object) -> object:
        self.last_kwargs = kwargs
        usage = SimpleNamespace(input_tokens=11, output_tokens=7, total_tokens=18)
        return SimpleNamespace(
            id="resp_order_244",
            model="gpt-5.3-codex",
            output_text='{"ping": "pong"}',
            usage=usage,
        )


class _FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()


class _FailingResponses:
    def create(self, **kwargs: object) -> object:
        error = RuntimeError("quota unavailable")
        error.code = "insufficient_quota"  # type: ignore[attr-defined]
        raise error


class _FailingOpenAIClient:
    def __init__(self) -> None:
        self.responses = _FailingResponses()


def test_openai_adapter_uses_responses_json_mode_without_storing() -> None:
    client = _FakeOpenAIClient()
    adapter = OpenAIResponsesAdapter(client=client, max_output_tokens=2048)

    response = adapter.complete(
        LLMRequest(prompt="JSON only", input_payload={"hello": "송련"})
    )

    assert response.text == '{"ping": "pong"}'
    assert client.responses.last_kwargs is not None
    assert client.responses.last_kwargs["model"] == "gpt-5.3-codex"
    assert client.responses.last_kwargs["store"] is False
    assert client.responses.last_kwargs["text"] == {
        "format": {"type": "json_object"}
    }
    assert "송련" in str(client.responses.last_kwargs["input"])
    assert str(client.responses.last_kwargs["input"]).startswith("JSON input payload:")
    assert adapter.usage_snapshot() == {
        "attempted_api_call_count": 1,
        "completed_api_call_count": 1,
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
        "last_response_id": "resp_order_244",
        "last_failure_type": None,
        "last_failure_reason": None,
    }


def test_openai_runtime_records_key_presence_not_secret(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-must-not-appear")

    config = build_llm_runtime_config(mode="openai")
    status_text = str(config)

    assert config.api_key_configured is True
    assert config.model_id == "gpt-5.3-codex"
    assert config.transport == "openai_responses_api"
    assert "test-secret-must-not-appear" not in status_text


def test_openai_adapter_preserves_failed_attempt_diagnostics() -> None:
    adapter = OpenAIResponsesAdapter(client=_FailingOpenAIClient())

    try:
        adapter.complete(LLMRequest(prompt="JSON only", input_payload={"ping": True}))
    except RuntimeError:
        pass
    else:
        raise AssertionError("failing client must raise")

    usage = adapter.usage_snapshot()
    assert usage["attempted_api_call_count"] == 1
    assert usage["completed_api_call_count"] == 0
    assert usage["last_failure_type"] == "insufficient_quota"


def test_openai_ping_missing_key_is_honest(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = ping_openai(max_output_tokens=256)

    assert result["ok"] is False
    assert result["status"] == "config_missing"
    assert result["runtime"]["api_key_configured"] is False


def test_openai_ping_names_quota_failure(monkeypatch) -> None:
    class _QuotaError(Exception):
        code = "insufficient_quota"

    class _QuotaAdapter:
        model_id = "gpt-5.3-codex"

        def complete(self, request: LLMRequest) -> object:
            raise _QuotaError("quota unavailable")

        def usage_snapshot(self) -> dict[str, int]:
            return {
                "attempted_api_call_count": 1,
                "completed_api_call_count": 0,
            }

    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-must-not-appear")
    monkeypatch.setattr(
        "songryeon_core.llm.runtime.build_llm_adapter",
        lambda config: _QuotaAdapter(),
    )

    result = ping_openai(max_output_tokens=256)

    assert result["status"] == "adapter_failed"
    assert result["failure_type"] == "insufficient_quota"
    assert result["usage"]["attempted_api_call_count"] == 1
    assert result["usage"]["completed_api_call_count"] == 0


def test_openai_turn_injects_one_adapter_into_existing_all_node_path(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-must-not-appear")
    fake_adapter = SongRyeonAllNodesFakeLLMAdapter()
    monkeypatch.setattr(
        "songryeon_core.runtime.user_turn.build_llm_adapter",
        lambda config: fake_adapter,
    )

    result = run_openai_user_turn(
        user_input="송련이 무엇인지 짧게 설명해줘",
        max_tool_calls=2,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    assert result["status"] in {"ok", "needs_revision", "failed"}
    assert result["runtime"]["mode"] == "openai"
    assert result["runtime"]["api_key_configured"] is True
    assert int(result["llm_call_count"] or 0) >= 3
    assert "test-secret-must-not-appear" not in str(result)


def test_structure_failed_terminal_names_openai_quota_failure() -> None:
    result = {
        "status": "structure_failed",
        "trace_count": 0,
        "data_record_count": 0,
        "structure_failure_reason": "node_1 LLM router failed: adapter_failed",
        "runtime": {
            "mode": "openai",
            "model_id": "gpt-5.3-codex",
            "transport": "openai_responses_api",
            "api_usage": {
                "attempted_api_call_count": 1,
                "completed_api_call_count": 0,
                "last_failure_type": "insufficient_quota",
                "last_failure_reason": "OpenAI API quota is unavailable.",
            },
        },
    }

    rendered = render_pretty_turn(result, user_input="테스트")

    assert "openai_api_failure_type: insufficient_quota" in rendered
    assert "openai_api_calls: attempted=1 / completed=0" in rendered
