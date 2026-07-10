from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from songryeon_core.runtime.quick_smoke import run_quick_smoke_tests


def test_quick_smoke_avoids_expensive_external_surfaces() -> None:
    result = run_quick_smoke_tests()

    assert result["status"] == "QUICK_SMOKE_OK"
    assert result["document_search_ran"] is False
    assert result["qwen_ran"] is False
    assert result["neo4j_ran"] is False
    assert result["full_smoke_included"] is False


def test_quick_smoke_cli_returns_structured_ok() -> None:
    completed = subprocess.run(
        [sys.executable, "main.py", "quick-smoke"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "QUICK_SMOKE_OK"
    assert payload["full_smoke_included"] is False


def test_pytest_default_excludes_full_smoke_marker() -> None:
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "not smoke" in pyproject_text
