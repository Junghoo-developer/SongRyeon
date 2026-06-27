from __future__ import annotations

import pytest

from songryeon_core.runtime.smoke_cases.runtime_view import (
    run_live_trace_progress_stream_smoke,
    run_runtime_count_consistency_smoke,
)


@pytest.mark.smoke
def test_runtime_count_consistency_smoke_case() -> None:
    smoke = run_runtime_count_consistency_smoke()

    assert smoke["reportable_document_count"] == 2
    assert smoke["raw_document_extract_record_count"] == 3
    assert smoke["empty_document_extract_record_count"] == 1


@pytest.mark.smoke
def test_live_trace_progress_stream_smoke_case() -> None:
    smoke = run_live_trace_progress_stream_smoke()

    assert smoke["line_count"] >= 1
    assert smoke["matches_trace_count"] is True
    assert smoke["no_report_body"] is True
