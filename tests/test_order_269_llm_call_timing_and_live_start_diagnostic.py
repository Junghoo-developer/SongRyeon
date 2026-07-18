from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import LLMCallFrame, validate_llm_call_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.runtime.terminal_view import render_runtime_view


class TimedSuccessAdapter:
    model_id = "fake-timed-success"
    timeout_seconds = 17

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=json.dumps({"status": "ok"}), model_id=self.model_id)


class TimedFailureAdapter:
    model_id = "fake-timed-failure"
    timeout_seconds = 23

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise TimeoutError("controlled adapter timeout")


def test_llm_call_records_timing_and_live_start_without_extra_trace() -> None:
    observed = []
    trace_store = TraceStore(on_event=observed.append)
    data_store = DataStore()

    result = LLMNodeExecutor(TimedSuccessAdapter()).run(
        node_id="L2",
        prompt="return JSON",
        input_payload={"query": "test"},
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_269_success",
        prompt_ref="songryeon_core/prompts/l2_query_setter_v0.md",
    )

    assert result.failure_type == "none"
    assert [event.event_type for event in observed] == ["llm_call_started", "llm_call"]
    assert observed[0].event_id == observed[1].event_id
    assert len(trace_store.list_events()) == 1
    assert trace_store.list_events()[0].event_type == "llm_call"

    payload = data_store.require_record(result.call_data_id or "").payload
    assert isinstance(payload, dict)
    assert payload["timing_status"] == "recorded"
    assert payload["started_at_utc"].endswith("+00:00")
    assert payload["finished_at_utc"].endswith("+00:00")
    assert payload["execution_duration_ms"] >= 0
    assert payload["configured_timeout_seconds"] == 17
    assert payload["schema_version"] == "0.2"


def test_adapter_failure_still_records_timing() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    result = LLMNodeExecutor(TimedFailureAdapter()).run(
        node_id="L3",
        prompt="return JSON",
        input_payload={"result": "test"},
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_269_failure",
        prompt_ref="songryeon_core/prompts/l3_result_keeper_v0.md",
    )

    payload = data_store.require_record(result.call_data_id or "").payload
    assert result.failure_type == "adapter_failed"
    assert isinstance(payload, dict)
    assert payload["timing_status"] == "recorded"
    assert payload["configured_timeout_seconds"] == 23
    assert payload["failure_type"] == "adapter_failed"
    assert payload["execution_duration_ms"] >= 0


def test_terminal_renders_call_order_total_and_slowest() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "data_records": [
                _timed_call("llm_call:L2:001", "L2", 1200, 30),
                _timed_call("llm_call:L3:002", "L3", 3400, 30),
            ],
        },
        user_input="시간 진단",
    )

    assert "calls=2 / total_ms=4600 / slowest=L3#2:3400ms" in rendered
    assert "01 node=L2 duration=1200ms configured_timeout=30s failure=none" in rendered
    assert "02 node=L3 duration=3400ms configured_timeout=30s failure=none" in rendered


def test_llm_call_schema_v01_timing_compatibility() -> None:
    frame = LLMCallFrame(
        call_id="llm_call:legacy:trace_000001",
        turn_id="turn_legacy",
        node_id="legacy",
        prompt_ref="inline:legacy",
        model_id="fake",
        schema_version="0.1",
    )

    validate_llm_call_frame(frame)
    assert frame.timing_status == "not_recorded"
    assert frame.execution_duration_ms == 0


def _timed_call(
    data_id: str,
    node_id: str,
    duration_ms: int,
    timeout_seconds: int,
) -> dict[str, object]:
    return {
        "data_id": data_id,
        "data_type": "llm_call",
        "payload": {
            "node_id": node_id,
            "prompt_ref": f"prompt/{node_id}.md",
            "failure_type": "none",
            "timing_status": "recorded",
            "execution_duration_ms": duration_ms,
            "configured_timeout_seconds": timeout_seconds,
        },
    }
