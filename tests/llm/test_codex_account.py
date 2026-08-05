"""Codex 계정 모델 체급 비교 client의 격리·출력 계약을 검사한다."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from llm import ModelCallError, ModelClient, ModelResponseError
from llm.codex_account import (
    CodexAccountIntegrationClient,
    _CodexSdkBindings,
)


class ChatgptAccount:
    pass


class ApiKeyAccount:
    pass


class AgentMessageThreadItem:
    pass


class CommandExecutionThreadItem:
    pass


class FakeModel:
    def __init__(self, model):
        self.model = model


class FakeThread:
    def __init__(self, owner):
        self.owner = owner

    def run(self, user_prompt, **kwargs):
        self.owner.run_call = (user_prompt, kwargs)
        return self.owner.result


class FakeCodex:
    def __init__(self, *, account_root=None, models=None, result=None):
        self.account_root = account_root or ChatgptAccount()
        self.models_data = models or [FakeModel("gpt-5.6-sol")]
        self.result = result or completed_result()
        self.thread_start_call = None
        self.run_call = None
        self.close_calls = 0

    def account(self):
        return SimpleNamespace(
            account=SimpleNamespace(root=self.account_root),
        )

    def models(self, *, include_hidden):
        assert include_hidden is True
        return SimpleNamespace(data=self.models_data)

    def thread_start(self, **kwargs):
        self.thread_start_call = kwargs
        return FakeThread(self)

    def close(self):
        self.close_calls += 1


def completed_result(*, item_root=None, output_tokens=20):
    return SimpleNamespace(
        status=SimpleNamespace(value="completed"),
        error=None,
        final_response='{"verdict":"permit","reason":"충분하다."}',
        items=[
            SimpleNamespace(root=item_root or AgentMessageThreadItem())
        ],
        usage=SimpleNamespace(
            total=SimpleNamespace(
                cached_input_tokens=10,
                input_tokens=100,
                output_tokens=output_tokens,
                reasoning_output_tokens=5,
                total_tokens=125,
            )
        ),
    )


def make_client(fake_codex):
    bindings = _CodexSdkBindings(
        codex_factory=lambda: fake_codex,
        sandbox_read_only="read-only",
        approval_deny_all="deny-all",
        version="test-sdk",
    )
    return CodexAccountIntegrationClient(
        sdk_loader=lambda: bindings,
    )


def test_complete_uses_chatgpt_account_empty_ephemeral_thread_and_schema():
    fake_codex = FakeCodex()
    client = make_client(fake_codex)
    schema = {
        "type": "object",
        "properties": {"verdict": {"type": "string"}},
        "required": ["verdict"],
        "additionalProperties": False,
    }

    ready = client.check_configuration()
    reply = client.complete(
        system_prompt="검사 노드다.",
        user_prompt="증거를 검사하라.",
        response_schema=schema,
        num_predict=256,
    )

    assert ready == {
        "provider": "openai_codex",
        "execution_mode": "codex_account_integration",
        "model_name": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "sdk_version": "test-sdk",
    }
    thread_call = fake_codex.thread_start_call
    run_prompt, run_call = fake_codex.run_call
    assert thread_call["model"] == "gpt-5.6-sol"
    assert thread_call["base_instructions"] == "검사 노드다."
    assert thread_call["ephemeral"] is True
    assert thread_call["sandbox"] == "read-only"
    assert thread_call["approval_mode"] == "deny-all"
    assert "도구" in thread_call["developer_instructions"]
    assert run_prompt == "증거를 검사하라."
    assert run_call["output_schema"] == schema
    assert run_call["effort"] == "medium"
    assert run_call["model"] == "gpt-5.6-sol"
    assert run_call["cwd"] == thread_call["cwd"]
    isolation_path = Path(run_call["cwd"])
    assert isolation_path.exists()
    assert reply.content == (
        '{"verdict":"permit","reason":"충분하다."}'
    )
    assert reply.model == "gpt-5.6-sol"
    assert reply.thinking == ""
    assert reply.done_reason == "stop"
    assert reply.metrics == {
        "cached_input_tokens": 10,
        "input_tokens": 100,
        "output_tokens": 20,
        "reasoning_output_tokens": 5,
        "total_tokens": 125,
    }
    assert client.provider == "openai_codex"
    assert client.execution_mode == "codex_account_integration"
    assert isinstance(client, ModelClient)

    client.close()
    assert not isolation_path.exists()


def test_configuration_requires_chatgpt_account_and_exact_model():
    api_key_client = make_client(FakeCodex(account_root=ApiKeyAccount()))
    missing_model_client = make_client(
        FakeCodex(models=[FakeModel("gpt-5.6-terra")])
    )

    with pytest.raises(ModelCallError, match="ChatGPT 계정"):
        api_key_client.check_configuration()
    with pytest.raises(ModelCallError, match="요청 모델"):
        missing_model_client.check_configuration()


def test_tool_activity_is_rejected_even_when_final_json_is_valid():
    fake_codex = FakeCodex(
        result=completed_result(item_root=CommandExecutionThreadItem()),
    )
    client = make_client(fake_codex)

    with pytest.raises(ModelResponseError, match="도구"):
        client.complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=256,
        )


def test_reported_output_over_num_predict_is_rejected():
    fake_codex = FakeCodex(result=completed_result(output_tokens=257))
    client = make_client(fake_codex)

    with pytest.raises(ModelResponseError, match="num_predict"):
        client.complete(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
            num_predict=256,
        )


def test_close_is_idempotent():
    fake_codex = FakeCodex()
    client = make_client(fake_codex)
    client.check_configuration()

    client.close()
    client.close()

    assert fake_codex.close_calls == 1
