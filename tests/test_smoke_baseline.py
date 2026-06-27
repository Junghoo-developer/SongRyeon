from __future__ import annotations

import pytest

from songryeon_core.runtime.smoke_test import run_smoke_tests


@pytest.mark.smoke
def test_smoke_test_baseline_status_ok() -> None:
    result = run_smoke_tests()

    assert result["status"] == "SMOKE_TEST_OK"
