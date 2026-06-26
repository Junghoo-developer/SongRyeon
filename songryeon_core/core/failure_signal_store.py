from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import FailureSignalFrame, validate_failure_signal_frame
from songryeon_core.core.trace_store import TraceStore


def record_failure_signal(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    failure_id: str,
    type: str,
    severity: str,
    raised_by: str,
    recoverable: bool,
    source_trace_ids: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    message: str = "",
) -> str:
    """실패 신호를 trace와 DataStore에 함께 기록한다."""

    frame = FailureSignalFrame(
        failure_id=failure_id,
        turn_id=turn_id,
        type=type,
        severity=severity,
        raised_by=raised_by,
        recoverable=recoverable,
        source_trace_ids=source_trace_ids or [],
        source_data_ids=source_data_ids or [],
        message=message,
    )
    validate_failure_signal_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=raised_by,
        event_type="failure_signal",
        input_ref=source_trace_ids or [],
        output_ref=[failure_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=failure_id,
        data_type="failure_signal",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id
