from __future__ import annotations

from songryeon_core.core.schemas import FailureSignal


KNOWN_FAILURE_TYPES = {
    "memory_insufficient",
    "schema_failed",
    "tool_failed",
    "llm_failed",
    "route_failed",
    "metainfo_boundary_failed",
    "unknown_state",
}


def create_failure_signal(
    *,
    raised_by: str,
    type: str,
    evidence_trace_ids: list[str] | None = None,
) -> FailureSignal:
    """실패/부족 신호를 만든다."""

    if not raised_by:
        raise ValueError("raised_by must not be empty")
    if type not in KNOWN_FAILURE_TYPES:
        raise ValueError(f"unknown failure type: {type}")
    return FailureSignal(
        raised_by=raised_by,
        type=type,
        evidence_trace_ids=evidence_trace_ids or [],
    )
