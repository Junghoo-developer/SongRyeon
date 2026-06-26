from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import LLMCallFrame, validate_llm_call_frame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter, LLMRequest
from songryeon_core.llm.json_validation import JSONValidationResult, parse_json_object


PayloadValidator = Callable[[dict[str, object]], None]


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
            result = self._run_once(
                node_id=node_id,
                prompt=prompt,
                input_payload=input_payload,
                payload_validator=payload_validator,
            )
            result.retry_count = attempt_index
            if trace_store is not None and data_store is not None and turn_id is not None:
                trace_event_id, call_data_id = self._record_call(
                    trace_store=trace_store,
                    data_store=data_store,
                    turn_id=turn_id,
                    node_id=node_id,
                    prompt_ref=prompt_ref or f"inline:{node_id}",
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
        node_id: str,
        prompt_ref: str,
        input_ref: list[str],
        source_data_ids: list[str],
        result: LLMNodeExecutionResult,
    ) -> tuple[str, str]:
        event_id = trace_store.next_event_id()
        call_data_id = f"llm_call:{node_id}:{event_id}"
        parse_status = "passed" if result.validation.ok or result.failure_type == "schema_failed" else "failed"
        validation_status = "passed" if result.failure_type == "none" else "failed"
        if result.failure_type == "parse_failed":
            validation_status = "not_checked"
        if result.failure_type == "adapter_failed":
            parse_status = "not_checked"
            validation_status = "not_checked"

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
        )
        validate_llm_call_frame(frame)
        event = trace_store.create_event(
            event_id=event_id,
            turn_id=turn_id,
            actor=f"llm:{node_id}",
            event_type="llm_call",
            input_ref=input_ref,
            output_ref=[call_data_id],
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
