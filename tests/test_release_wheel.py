"""Release wheel이 대회 재현 자료를 싣고 비밀 산출물은 빼는지 검사한다."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest

from evals.source_identity import current_system_source_identity


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HOLDOUT_FILES = {
    "evals/contest_holdout_v1/HUMAN_AUDIT_TEMPLATE.json",
    "evals/contest_holdout_v1/PROTOCOL.md",
    "evals/contest_holdout_v1/README.md",
    "evals/contest_holdout_v1/RUN_PLAN.json",
    "evals/contest_holdout_v1/SCORING_RUBRIC.md",
    "evals/contest_holdout_v1/manifest.json",
    "evals/contest_holdout_v1/project/acorn.py",
    "evals/contest_holdout_v1/project/zephyr.py",
}
PRIVATE_FILENAMES = {
    ".env",
    "blind_key.json",
    "capture.json",
    "checkpoint.json",
    "knowledge.db",
    "memory.jsonl",
}
RESEARCH_ONLY_PATH_FRAGMENTS = {
    "evals/arm_mechanism_cases/",
    "evals/evidence_laundering",
    "evals/mechanism_",
    "evals/node4_ablation_cases/",
}


def test_release_wheel_contains_holdout_resources_without_private_artifacts(
    tmp_path: Path,
) -> None:
    """실제 wheel 목록을 열어 package-data 계약을 검증한다."""

    if importlib.util.find_spec("wheel") is None:
        pytest.skip("wheel build backend is not installed")

    wheel_directory = tmp_path / "wheel"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_directory),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    wheels = list(wheel_directory.glob("*.whl"))
    assert len(wheels) == 1
    with ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())

    assert REQUIRED_HOLDOUT_FILES <= names
    private_entries = [
        name
        for name in names
        if name.rsplit("/", 1)[-1].casefold() in PRIVATE_FILENAMES
        or "/raw/" in f"/{name.casefold()}"
        or "/transcripts/" in f"/{name.casefold()}"
        or name.casefold().endswith(".memory.jsonl")
        or any(
            fragment in name.casefold()
            for fragment in RESEARCH_ONLY_PATH_FRAGMENTS
        )
    ]
    assert private_entries == []

    public_blind_packets = [
        name
        for name in names
        if name.rsplit("/", 1)[-1].casefold() == "blind_packet.json"
    ]
    assert all(
        name.startswith("evals/contest_holdout_v1/frozen/")
        for name in public_blind_packets
    )

    installed_directory = tmp_path / "installed"
    with ZipFile(wheels[0]) as archive:
        archive.extractall(installed_directory)

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(installed_directory)
    smoke = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from evals.source_identity import current_system_source_identity; "
                "print(json.dumps(current_system_source_identity(), sort_keys=True))"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    identity = json.loads(smoke.stdout)
    assert identity["file_count"] > 0
    assert len(identity["tree_sha256"]) == 64
    assert identity == current_system_source_identity()
