from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import LLMCallFrame, validate_llm_call_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter, LLMRequest
from songryeon_core.llm.json_validation import JSONValidationResult, parse_json_object


PayloadValidator = Callable[[dict[str, object]], None]

INPUT_PAYLOAD_PREVIEW_JSON_CHAR_LIMIT = 12000


@dataclass
class LLMNodeExecutionResult:
    """LLM 노드 실행 결과."""

    node_id: str
    model_id: str
    validation: JSONValidationResult
    raw_text: str
    trace_event_id: str | None = None
    call_data_id: str | None = None
    retry_count: int = 0
    failure_type: str = "none"
    timing_status: str = "not_recorded"
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    execution_duration_ms: int = 0
    configured_timeout_seconds: int | None = None


class LLMNodeExecutor:
    """프롬프트, adapter, JSON 검증, 선택적 trace/data 저장을 묶는 실행기."""

    def __init__(self, adapter: LLMAdapter) -> None:
        self.adapter = adapter

    def run(
        self,
        *,
        node_id: str,
        prompt: str,
        input_payload: dict[str, object],
        trace_store: TraceStore | None = None,
        data_store: DataStore | None = None,
        turn_id: str | None = None,
        prompt_ref: str | None = None,
        input_ref: list[str] | None = None,
        source_data_ids: list[str] | None = None,
        max_retries: int = 0,
        payload_validator: PayloadValidator | None = None,
    ) -> LLMNodeExecutionResult:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if (trace_store is None) != (data_store is None):
            raise ValueError("trace_store and data_store must be provided together")
        if trace_store is not None and turn_id is None:
            raise ValueError("turn_id is required when recording LLM calls")

        final_result: LLMNodeExecutionResult | None = None
        for attempt_index in range(max_retries + 1):
            selected_prompt_ref = prompt_ref or f"inline:{node_id}"
            started_at_utc = _utc_now()
            started_monotonic_ns = time.monotonic_ns()
            reserved_event_id: str | None = None
            reserved_call_data_id: str | None = None
            if trace_store is not None and turn_id is not None:
                reserved_event_id = trace_store.next_event_id()
                reserved_call_data_id = f"llm_call:{node_id}:{reserved_event_id}"
                trace_store.emit_live_preview(
                    event_id=reserved_event_id,
                    turn_id=turn_id,
                    actor=f"llm:{node_id}",
                    event_type="llm_call_started",
                    input_ref=input_ref or [],
                    output_ref=[reserved_call_data_id],
                    raw_content_ref=f"prompt={selected_prompt_ref}",
                    schema_status="not_checked",
                    timestamp=started_at_utc,
                )
            try:
                result = self._run_once(
                    node_id=node_id,
                    prompt=prompt,
                    input_payload=input_payload,
                    payload_validator=payload_validator,
                )
            finally:
                finished_at_utc = _utc_now()
                execution_duration_ms = max(
                    0,
                    round((time.monotonic_ns() - started_monotonic_ns) / 1_000_000),
                )
            result.timing_status = "recorded"
            result.started_at_utc = started_at_utc
            result.finished_at_utc = finished_at_utc
            result.execution_duration_ms = execution_duration_ms
            result.configured_timeout_seconds = _configured_timeout_seconds(self.adapter)
            result.retry_count = attempt_index
            if trace_store is not None and data_store is not None and turn_id is not None:
                if reserved_event_id is None or reserved_call_data_id is None:
                    raise RuntimeError("LLM call trace reservation is missing")
                trace_event_id, call_data_id = self._record_call(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    event_id=reserved_event_id,
                    call_data_id=reserved_call_data_id,
                    node_id=node_id,
                    prompt_ref=selected_prompt_ref,
                    input_payload=input_payload,
                    input_ref=input_ref or [],
                    source_data_ids=source_data_ids or [],
                    result=result,
                )
                result.trace_event_id = trace_event_id
                result.call_data_id = call_data_id

            final_result = result
            if result.failure_type == "none":
                break

        if final_result is None:
            raise RuntimeError("LLM execution produced no result")
        return final_result

    def _run_once(
        self,
        *,
        node_id: str,
        prompt: str,
        input_payload: dict[str, object],
        payload_validator: PayloadValidator | None,
    ) -> LLMNodeExecutionResult:
        try:
            response = self.adapter.complete(
                LLMRequest(prompt=prompt, input_payload=input_payload, response_format="json")
            )
        except Exception as exc:
            return LLMNodeExecutionResult(
                node_id=node_id,
                model_id=getattr(self.adapter, "model_id", "unknown-llm"),
                validation=JSONValidationResult(ok=False, error=str(exc)),
                raw_text="",
                failure_type="adapter_failed",
            )

        validation = parse_json_object(response.text)
        failure_type = "none"
        if not validation.ok:
            failure_type = "parse_failed"
        elif payload_validator is not None and validation.payload is not None:
            try:
                payload_validator(validation.payload)
            except Exception as exc:
                validation = JSONValidationResult(
                    ok=False,
                    payload=validation.payload,
                    error=str(exc),
                )
                failure_type = "schema_failed"

        return LLMNodeExecutionResult(
            node_id=node_id,
            model_id=response.model_id,
            validation=validation,
            raw_text=response.text,
            failure_type=failure_type,
        )

    def _record_call(
        self,
        *,
        trace_store: TraceStore,
        data_store: DataStore,
        turn_id: str,
        event_id: str,
        call_data_id: str,
        node_id: str,
        prompt_ref: str,
        input_payload: dict[str, object],
        input_ref: list[str],
        source_data_ids: list[str],
        result: LLMNodeExecutionResult,
    ) -> tuple[str, str]:
        parse_status = "passed" if result.validation.ok or result.failure_type == "schema_failed" else "failed"
        validation_status = "passed" if result.failure_type == "none" else "failed"
        if result.failure_type == "parse_failed":
            validation_status = "not_checked"
        if result.failure_type == "adapter_failed":
            parse_status = "not_checked"
            validation_status = "not_checked"

        input_payload_audit = self._build_input_payload_audit(input_payload)
        frame = LLMCallFrame(
            call_id=call_data_id,
            turn_id=turn_id,
            node_id=node_id,
            prompt_ref=prompt_ref,
            input_data_ids=source_data_ids,
            model_id=result.model_id,
            response_format="json",
            raw_text=result.raw_text,
            parse_status=parse_status,
            validation_status=validation_status,
            retry_count=result.retry_count,
            failure_type=result.failure_type,
            error_message=result.validation.error or "",
            source_trace_ids=input_ref,
            source_data_ids=source_data_ids,
            input_payload_audit_status=input_payload_audit["input_payload_audit_status"],
            input_payload_sha256=input_payload_audit["input_payload_sha256"],
            input_payload_json_char_count=input_payload_audit["input_payload_json_char_count"],
            input_payload_top_level_keys=input_payload_audit["input_payload_top_level_keys"],
            input_payload_preview_json=input_payload_audit["input_payload_preview_json"],
            timing_status=result.timing_status,
            started_at_utc=result.started_at_utc,
            finished_at_utc=result.finished_at_utc,
            execution_duration_ms=result.execution_duration_ms,
            configured_timeout_seconds=result.configured_timeout_seconds,
        )
        validate_llm_call_frame(frame)
        event = trace_store.create_event(
            event_id=event_id,
            turn_id=turn_id,
            actor=f"llm:{node_id}",
            event_type="llm_call",
            input_ref=input_ref,
            output_ref=[call_data_id],
            raw_content_ref=(
                f"duration_ms={result.execution_duration_ms};"
                f"failure={result.failure_type}"
            ),
            schema_status="passed" if result.failure_type == "none" else "failed",
        )
        data_store.create_record(
            data_id=call_data_id,
            data_type="llm_call",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
        return event.event_id, call_data_id

    def _build_input_payload_audit(self, input_payload: dict[str, object]) -> dict[str, object]:
        """LLM에 넘긴 입력 봉투를 사후 감사할 수 있게 작은 절대정보로 줄인다."""

        payload_json = json.dumps(
            input_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        return {
            "input_payload_audit_status": "recorded",
            "input_payload_sha256": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
            "input_payload_json_char_count": len(payload_json),
            "input_payload_top_level_keys": sorted(input_payload.keys()),
            "input_payload_preview_json": payload_json[:INPUT_PAYLOAD_PREVIEW_JSON_CHAR_LIMIT],
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _configured_timeout_seconds(adapter: LLMAdapter) -> int | None:
    value = getattr(adapter, "timeout_seconds", None)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None
