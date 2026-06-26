from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.schemas import TurnStateCapsule


def save_turn_capsules(path: str | Path, capsules: list[TurnStateCapsule]) -> Path:
    """TurnStateCapsule 목록을 JSON으로 저장한다."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps([asdict(capsule) for capsule in capsules], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def load_turn_capsules(path: str | Path) -> list[TurnStateCapsule]:
    """JSON에서 TurnStateCapsule 목록을 복원한다."""

    source = Path(path)
    if not source.exists():
        return []
    records = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("capsule json root must be a list")
    return [TurnStateCapsule(**record) for record in records]
