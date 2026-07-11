from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from songryeon_core.llm.base import LLMRequest
from songryeon_core.llm.codex_sdk_adapter import CodexSDKAdapter


class _FakeThread:
    def __init__(self, *, item_type: str = "agentMessage") -> None:
        self.id = "thread_order_245"
        self.item_type = item_type
        self.run_kwargs: dict[str, object] | None = None

    def run(self, prompt: str, **kwargs: object) -> object:
        self.run_kwargs = kwargs
        payload = {"route": "2", "route_reason": "test"}
        wrapper = {"payload_json": json.dumps(payload, ensure_ascii=False)}
        total = SimpleNamespace(
            input_tokens=100,
            cached_input_tokens=40,
            output_tokens=20,
            reasoning_output_tokens=10,
            total_tokens=120,
        )
        return SimpleNamespace(
            id="turn_order_245",
            final_response=json.dumps(wrapper, ensure_ascii=False),
            items=[SimpleNamespace(root=SimpleNamespace(type=self.item_type))],
            usage=SimpleNamespace(total=total),
        )


class _FakeCodex:
    def __init__(self, *, item_type: str = "agentMessage") -> None:
        self.thread = _FakeThread(item_type=item_type)
        self.thread_start_kwargs: dict[str, object] | None = None
        self.closed = False

    def account(self, *, refresh_token: bool) -> object:
        root = SimpleNamespace(
            type="chatgpt",
            plan_type=SimpleNamespace(value="pro"),
        )
        return SimpleNamespace(account=SimpleNamespace(root=root))

    def thread_start(self, **kwargs: object) -> _FakeThread:
        self.thread_start_kwargs = kwargs
        return self.thread

    def close(self) -> None:
        self.closed = True


def test_codex_sdk_adapter_uses_chatgpt_read_only_isolated_transport(
    monkeypatch,
) -> None:
    fake = _FakeCodex()
    factory_environment: dict[str, str | None] = {}

    def factory(config: object) -> _FakeCodex:
        factory_environment["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
        factory_environment["SONGRYEON_NEO4J_PASSWORD"] = os.environ.get(
            "SONGRYEON_NEO4J_PASSWORD"
        )
        return fake

    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-child")
    monkeypatch.setenv("SONGRYEON_NEO4J_PASSWORD", "must-not-reach-child")
    adapter = CodexSDKAdapter(codex_factory=factory)

    response = adapter.complete(
        LLMRequest(prompt="Return route JSON", input_payload={"question": "test"})
    )

    assert json.loads(response.text)["route"] == "2"
    assert factory_environment == {
        "OPENAI_API_KEY": None,
        "SONGRYEON_NEO4J_PASSWORD": None,
    }
    assert os.environ["OPENAI_API_KEY"] == "must-not-reach-child"
    assert fake.thread_start_kwargs is not None
    assert fake.thread_start_kwargs["ephemeral"] is True
    assert str(fake.thread_start_kwargs["sandbox"]).endswith("read_only")
    assert str(fake.thread_start_kwargs["approval_mode"]).endswith("deny_all")
    assert fake.thread.run_kwargs is not None
    assert fake.thread.run_kwargs["output_schema"]["required"] == ["payload_json"]
    usage = adapter.usage_snapshot()
    assert usage["auth_type"] == "chatgpt"
    assert usage["plan_type"] == "pro"
    assert usage["attempted_turn_count"] == 1
    assert usage["completed_turn_count"] == 1
    assert usage["accepted_response_count"] == 1
    assert usage["total_tokens"] == 120
    adapter.close()
    assert fake.closed is True


def test_codex_sdk_adapter_rejects_any_tool_activity() -> None:
    fake = _FakeCodex(item_type="commandExecution")
    adapter = CodexSDKAdapter(codex_factory=lambda config: fake)

    with pytest.raises(RuntimeError, match="forbidden tool"):
        adapter.complete(LLMRequest(prompt="JSON only", input_payload={"x": 1}))

    usage = adapter.usage_snapshot()
    assert usage["completed_turn_count"] == 1
    assert usage["accepted_response_count"] == 0
    assert usage["last_tool_activity_count"] == 1
    adapter.close()


def test_codex_sdk_adapter_rejects_non_chatgpt_auth() -> None:
    fake = _FakeCodex()
    fake.account = lambda **kwargs: SimpleNamespace(  # type: ignore[method-assign]
        account=SimpleNamespace(root=SimpleNamespace(type="apiKey"))
    )
    adapter = CodexSDKAdapter(codex_factory=lambda config: fake)

    with pytest.raises(RuntimeError, match="not authenticated with ChatGPT"):
        adapter.complete(LLMRequest(prompt="JSON only", input_payload={"x": 1}))

    adapter.close()
