from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import LLMCallFrame, validate_llm_call_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.llm.node_executor import (
    INPUT_PAYLOAD_PREVIEW_JSON_CHAR_LIMIT,
    LLMNodeExecutor,
)


class PayloadEchoAdapter:
    """테스트용 LLM adapter: 항상 통과 가능한 JSON만 돌려준다."""

    model_id = "fake-payload-echo"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps({"status": "ok", "seen_keys": sorted(request.input_payload.keys())}),
            model_id=self.model_id,
        )


def test_llm_call_records_input_payload_audit_snapshot() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    executor = LLMNodeExecutor(PayloadEchoAdapter())

    result = executor.run(
        node_id="R2_vessel_node_selector",
        prompt="select one graph node",
        input_payload={
            "available_surface_refs": ["surface_001", "surface_002"],
            "candidate_records_by_surface_ref": {
                "surface_001": [{"node_ref": "node_001", "summary": "시간축"}],
            },
            "user_question": "그래프 기억 구조를 내려가며 설명해줘",
        },
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_225",
        prompt_ref="songryeon_core/prompts/r2_vessel_node_selector_v0.md",
        input_ref=["trace:user_input"],
        source_data_ids=["r_loop:vessel_candidate_layer:001"],
        payload_validator=lambda payload: None,
    )

    assert result.failure_type == "none"
    assert result.call_data_id is not None
    record = data_store.require_record(result.call_data_id)
    payload = record.payload

    assert isinstance(payload, dict)
    assert payload["input_payload_audit_status"] == "recorded"
    assert isinstance(payload["input_payload_sha256"], str)
    assert len(payload["input_payload_sha256"]) == 64
    assert payload["input_payload_json_char_count"] > 0
    assert payload["input_payload_top_level_keys"] == [
        "available_surface_refs",
        "candidate_records_by_surface_ref",
        "user_question",
    ]
    assert '"available_surface_refs"' in payload["input_payload_preview_json"]
    assert '"surface_001"' in payload["input_payload_preview_json"]
    assert len(payload["input_payload_preview_json"]) <= INPUT_PAYLOAD_PREVIEW_JSON_CHAR_LIMIT


def test_llm_call_frame_without_input_payload_audit_keeps_compatibility() -> None:
    frame = LLMCallFrame(
        call_id="llm_call:compat:trace_000001",
        turn_id="turn_compat",
        node_id="compat_node",
        prompt_ref="inline:compat_node",
        model_id="fake",
        response_format="json",
        raw_text="{}",
        parse_status="passed",
        validation_status="passed",
        failure_type="none",
    )

    validate_llm_call_frame(frame)
    assert frame.input_payload_audit_status == "not_recorded"
    assert frame.input_payload_sha256 is None
    assert frame.input_payload_json_char_count == 0
