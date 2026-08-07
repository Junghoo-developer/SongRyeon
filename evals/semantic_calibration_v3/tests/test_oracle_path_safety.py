from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_oracle


def test_build_oracle_rejects_manifest_source_outside_root(tmp_path, monkeypatch):
    calibration_root = tmp_path / "calibration"
    calibration_root.mkdir()
    (tmp_path / "outside.py").write_text(
        "def observe():\n    return True\n",
        encoding="utf-8",
    )
    manifest = {
        "cases": [
            {
                "case_id": "outside-source",
                "difficulty": "anchor",
                "source": "../outside.py",
                "claims": [
                    {
                        "id": "outside-1",
                        "function": "observe",
                        "proposition": {
                            "kind": "return",
                            "value": True,
                            "exception": None,
                        },
                    }
                ],
            }
        ]
    }
    (calibration_root / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_oracle, "ROOT", calibration_root)

    with pytest.raises(ValueError, match="manifest source escapes calibration root"):
        build_oracle.build_oracle()
