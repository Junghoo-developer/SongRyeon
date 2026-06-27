from __future__ import annotations

import sys
from typing import TextIO

from songryeon_core.core.schemas import TraceEvent
from songryeon_core.core.trace_store import TraceEventSink


def format_live_trace_event(event: TraceEvent) -> str:
    """TraceEvent를 개발자용 progress line 하나로 바꾼다."""

    return (
        "[trace] "
        f"{event.event_id} "
        f"{event.actor} "
        f"{event.event_type} "
        f"schema={event.schema_status} "
        f"out={_format_refs(event.output_ref)}"
    )


def make_live_trace_sink(*, enabled: bool, stream: TextIO | None = None) -> TraceEventSink | None:
    """live trace가 켜졌을 때만 stderr 출력 sink를 만든다."""

    if not enabled:
        return None
    target = stream or sys.stderr

    def emit(event: TraceEvent) -> None:
        target.write(format_live_trace_event(event) + "\n")
        target.flush()

    return emit


def _format_refs(refs: list[str]) -> str:
    if not refs:
        return "[]"
    if len(refs) <= 3:
        return "[" + ", ".join(refs) + "]"
    head = ", ".join(refs[:3])
    return f"[{head}, ... +{len(refs) - 3}]"
