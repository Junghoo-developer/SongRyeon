from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schema_parts.trace_data import MemoryPacketFrom0
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.llm.qwen_adapter import QwenLocalHTTPAdapter
from songryeon_core.llm.runtime import build_llm_runtime_config, llm_runtime_status
from songryeon_core.nodes.l1_goal_setter import run_l1_goal_setter
from songryeon_core.runtime.terminal_view import render_runtime_view


class RecordingOllamaClient:
    def __init__(self, capture: dict[str, object]) -> None:
        self.capture = capture

    def chat(self, **kwargs):
        self.capture["chat_kwargs"] = kwargs
        return {"message": {"content": "{}"}}


class TimeoutOllamaClient:
    def chat(self, **kwargs):
        raise TimeoutError("controlled transport timeout")


def test_direct_ollama_client_receives_timeout_and_keeps_request_contract() -> None:
    captured: dict[str, object] = {}

    def factory(**kwargs):
        captured["client_kwargs"] = kwargs
        return RecordingOllamaClient(captured)

    adapter = QwenLocalHTTPAdapter(
        timeout_seconds=7,
        num_ctx=8192,
        ollama_client_factory=factory,
    )
    response = adapter.complete(
        LLMRequest(
            prompt="system prompt",
            input_payload={"question": "hello"},
            response_format="json",
        )
    )

    assert response.text == "{}"
    assert captured["client_kwargs"] == {"timeout": 7}
    chat_kwargs = captured["chat_kwargs"]
    assert chat_kwargs["format"] == "json"
    assert chat_kwargs["options"] == {"temperature": 0, "num_ctx": 8192}


def test_direct_ollama_timeout_is_recorded_as_adapter_failure() -> None:
    adapter = QwenLocalHTTPAdapter(
        timeout_seconds=3,
        ollama_client_factory=lambda **kwargs: TimeoutOllamaClient(),
    )
    trace_store = TraceStore()
    data_store = DataStore()

    result = LLMNodeExecutor(adapter).run(
        node_id="L1",
        prompt="return JSON",
        input_payload={"question": "timeout"},
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_270_executor_timeout",
        prompt_ref="songryeon_core/prompts/l1_goal_setter_v0.md",
    )

    payload = data_store.require_record(result.call_data_id or "").payload
    assert result.failure_type == "adapter_failed"
    assert isinstance(payload, dict)
    assert payload["failure_type"] == "adapter_failed"
    assert "direct Ollama transport timed out after configured 3 seconds" in payload["error_message"]
    assert payload["timing_status"] == "recorded"


def test_l1_timeout_recovers_only_with_explicit_rule_stub() -> None:
    adapter = QwenLocalHTTPAdapter(
        timeout_seconds=2,
        ollama_client_factory=lambda **kwargs: TimeoutOllamaClient(),
    )
    trace_store = TraceStore()
    data_store = DataStore()
    user_event = trace_store.create_event(
        turn_id="turn_order_270_l1_fallback",
        actor="user",
        event_type="user_input",
    )

    run_l1_goal_setter(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_270_l1_fallback",
        memory_packet=MemoryPacketFrom0(target="L", trace_evidence_ids=[user_event.event_id]),
        user_query="workspace_policy.py를 읽어줘",
        adapter=adapter,
    )

    goal_payload = data_store.require_record("L1:goal_frame").payload
    assert isinstance(goal_payload, dict)
    assert goal_payload["goal_generation_source"] == "RULE_STUB"
    assert goal_payload["llm_goal_judgement_status"] == "not_run"
    llm_calls = [record for record in data_store.list_records() if record.data_type == "llm_call"]
    assert len(llm_calls) == 1
    assert llm_calls[0].payload["failure_type"] == "adapter_failed"


def test_runtime_and_terminal_expose_timeout_enforcement_and_l1_failure() -> None:
    config = build_llm_runtime_config(mode="qwen", timeout_seconds=11)
    runtime = llm_runtime_status(config)
    assert runtime["timeout_enforcement_status"] == "enforced_by_ollama_httpx_client"

    rendered = render_runtime_view(
        {
            "status": "model_fallback",
            "runtime": runtime,
            "data_records": [
                {
                    "data_id": "llm_call:L1:trace_000001",
                    "data_type": "llm_call",
                    "payload": {
                        "node_id": "L1",
                        "prompt_ref": "songryeon_core/prompts/l1_goal_setter_v0.md",
                        "failure_type": "adapter_failed",
                        "parse_status": "not_checked",
                        "validation_status": "not_checked",
                        "error_message": "direct Ollama transport timed out",
                    },
                }
            ],
        },
        user_input="timeout 표시",
    )

    assert "configured=11s" in rendered
    assert "enforcement=enforced_by_ollama_httpx_client" in rendered
    assert "node=L1 failure=adapter_failed" in rendered
