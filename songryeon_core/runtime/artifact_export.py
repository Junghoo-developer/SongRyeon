from __future__ import annotations

import json
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore


def export_runtime_artifacts(
    *,
    output_dir: str | Path,
    trace_store: TraceStore,
    data_store: DataStore,
    report: str,
    summary: dict[str, object],
) -> Path:
    """한 번의 런타임 실행 산출물을 파일로 저장한다."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    trace_store.save_json(target / "trace.json")
    data_store.save_json(target / "data.json")
    (target / "report.md").write_text(report, encoding="utf-8")
    (target / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
