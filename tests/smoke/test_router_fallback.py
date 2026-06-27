from __future__ import annotations

import pytest

from songryeon_core.runtime.smoke_cases.router_fallback import (
    run_router_fallback_honesty_smoke,
)


@pytest.mark.smoke
def test_router_fallback_smoke_case() -> None:
    smoke = run_router_fallback_honesty_smoke()

    assert smoke["fallback_policy"] == "dev_smoke_router_fallback_allowed"
    assert smoke["failure_type"] == "parse_failed"
    assert smoke["terminal_distinct"] is True
    assert smoke["strict_blocked"] is True
