"""Copy the first canonical run artifact into tracked public evidence."""

from __future__ import annotations

import os
import sys


def _prepare_seal_imports():
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True
    experiment_root = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(experiment_root))
    offenders = []
    for root in (experiment_root, os.path.join(workspace_root, "llm")):
        for current, directories, files in os.walk(root):
            offenders.extend(
                os.path.join(current, name)
                for name in directories
                if name == "__pycache__"
            )
            offenders.extend(
                os.path.join(current, name)
                for name in files
                if name.lower().endswith((".pyc", ".pyo"))
            )
    if offenders:
        raise RuntimeError(f"evidence seal refuses Python bytecode caches: {offenders}")


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("seal tool must be executed by direct file path, not -m")
if __name__ == "__main__":
    _prepare_seal_imports()
else:
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artifacts import validate_artifact_document
from freeze_v3 import sha256, verify_freeze, verify_freeze_publication
from schemas import load_strict_json, strict_json_loads


def canonical_run_path(freeze_sha, stage):
    return (
        WORKSPACE_ROOT
        / ".tmp"
        / "evals"
        / "semantic_calibration_v3"
        / freeze_sha
        / f"{stage}.json"
    )


def public_evidence_path(freeze_sha, stage):
    return (
        WORKSPACE_ROOT
        / "evidence"
        / "semantic_calibration_v3"
        / freeze_sha
        / f"{stage}.json"
    )


def write_bytes_once(destination, payload):
    """Atomically publish bytes without ever replacing an existing artifact."""

    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("public evidence artifact already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        destination.name + f".{uuid.uuid4().hex}.tmp"
    )
    try:
        with temporary.open("xb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def verify_public_evidence(artifact, freeze_sha, stage, remote_ref):
    artifact = Path(artifact).resolve()
    evidence = public_evidence_path(freeze_sha, stage).resolve()
    if not evidence.is_file():
        raise FileNotFoundError("sealed public evidence artifact is missing")
    if sha256(evidence) != sha256(artifact):
        raise ValueError("sealed public evidence differs from canonical artifact")
    relative = evidence.relative_to(WORKSPACE_ROOT).as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if tracked.returncode != 0:
        raise RuntimeError("sealed public evidence must be committed")
    commit = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    contains = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, remote_ref],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if not commit or contains.returncode != 0:
        raise RuntimeError("sealed public evidence commit must be pushed")
    return {
        "path": relative,
        "sha256": sha256(evidence),
        "commit": commit,
        "remote_ref": remote_ref,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    args = parser.parse_args()

    freeze = verify_freeze(args.freeze)
    freeze_sha = sha256(args.freeze)
    payload = args.artifact.read_bytes()
    artifact_sha = hashlib.sha256(payload).hexdigest()
    try:
        document = strict_json_loads(payload.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError("canonical artifact is not UTF-8") from error
    if not isinstance(document, dict):
        raise ValueError("run artifact must be a JSON object")
    stage = document.get("stage")
    if stage not in {"contract", "semantic"}:
        raise ValueError("run artifact stage is invalid")
    if args.artifact.resolve() != canonical_run_path(freeze_sha, stage).resolve():
        raise ValueError("only the canonical freeze-scoped run artifact can be sealed")
    publication = document.get("freeze_publication")
    verify_freeze_publication(publication, args.freeze)
    plan_path = ROOT / "control" / "run_plan.json"
    plan = load_strict_json(plan_path)
    validate_artifact_document(
        document,
        units=plan[f"{stage}_units"],
        expected_stage=stage,
        expected_freeze_sha=freeze_sha,
        expected_freeze_publication=publication,
        expected_plan_sha=sha256(plan_path),
        expected_model_contract=freeze["model_contract"],
        expected_readiness=freeze["model_readiness"],
        expected_contract_preflight=document.get("contract_preflight"),
        require_exact_rows=True,
        allow_started=False,
        allowed_run_states={"complete"},
    )
    destination = public_evidence_path(freeze_sha, stage)
    write_bytes_once(destination, payload)
    if sha256(destination) != artifact_sha:
        raise RuntimeError("sealed evidence hash differs from canonical artifact")
    print(
        json.dumps(
            {
                "evidence": str(destination.resolve()),
                "sha256": artifact_sha,
                "stage": stage,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
