"""Seal the sole complete v4 run artifact as exact-byte public evidence."""

from __future__ import annotations

import os
import sys


def _prepare_seal_imports() -> None:
    sys.pycache_prefix = None
    experiment_root = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(experiment_root))
    offenders: list[str] = []
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
        raise RuntimeError(
            "Semantic Ceiling v4 seal refuses Python bytecode caches: "
            + repr(sorted(set(offenders)))
        )


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("seal_v4.py must be executed by direct file path, not -m")
if __name__ == "__main__":
    if not sys.dont_write_bytecode:
        raise RuntimeError("seal_v4.py must be executed with python -B")
    if not sys.flags.isolated:
        raise RuntimeError("seal_v4.py must be executed with python -I -B")
    _prepare_seal_imports()
sys.pycache_prefix = None
sys.dont_write_bytecode = True

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import uuid


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from freeze_v4 import (  # noqa: E402
    FREEZE_PATH,
    ORACLE_PATH,
    PLAN_PATH,
    _verify_freeze_publication,
    load_strict_json,
    sha256,
    validate_published_clean_head,
    verify_freeze,
)


def canonical_artifact_path(freeze_sha: str) -> Path:
    return (
        WORKSPACE_ROOT
        / ".tmp"
        / "evals"
        / "semantic_ceiling_v4"
        / freeze_sha
        / "run.json"
    )


def public_evidence_path(freeze_sha: str) -> Path:
    return (
        WORKSPACE_ROOT
        / "evidence"
        / "semantic_ceiling_v4"
        / freeze_sha
        / "run.json"
    )


def write_bytes_once(destination: Path, payload: bytes) -> None:
    """Publish exact bytes atomically and never replace an existing artifact."""

    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("sealed v4 evidence already exists")
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


def _load_runner_validator():
    module = importlib.import_module("run_v4")
    if Path(module.__file__).resolve() != (ROOT / "run_v4.py").resolve():
        raise RuntimeError("run_v4 import provenance differs from frozen source")
    validator = getattr(module, "validate_artifact_document", None)
    if not callable(validator):
        raise RuntimeError("run_v4.validate_artifact_document is unavailable")
    return validator


def _validate_identity(
    document: dict,
    *,
    freeze: dict,
    freeze_sha: str,
    freeze_publication_commit: str,
) -> None:
    required = {
        "run_state": "complete",
        "freeze_sha256": freeze_sha,
        "freeze_tree_sha256": freeze["tree_sha256"],
        "freeze_source_commit": freeze["source_commit"],
        "freeze_publication_commit": freeze_publication_commit,
        "model_contract": freeze["model_contract"],
        "study_sha256": freeze["study_sha256"],
        "manifest_sha256": freeze["manifest_sha256"],
        "plan_sha256": freeze["plan_sha256"],
        "oracle_sha256": freeze["oracle_sha256"],
        "protocol_sha256": freeze["protocol_sha256"],
    }
    mismatches = [key for key, expected in required.items() if document.get(key) != expected]
    if mismatches:
        raise ValueError(f"run artifact/freeze identity differs: {mismatches}")


def validate_complete_artifact(
    document: dict,
    *,
    freeze: dict,
    freeze_sha: str,
    freeze_path: Path,
) -> None:
    if type(document) is not dict:
        raise ValueError("run artifact must be a JSON object")
    current = validate_published_clean_head()
    publication_commit = _verify_freeze_publication(freeze_path, current)
    _validate_identity(
        document,
        freeze=freeze,
        freeze_sha=freeze_sha,
        freeze_publication_commit=publication_commit,
    )
    plan = load_strict_json(PLAN_PATH)
    oracle = load_strict_json(ORACLE_PATH)
    validator = _load_runner_validator()
    result = validator(
        document,
        freeze=freeze,
        freeze_sha=freeze_sha,
        plan=plan,
        oracle=oracle,
    )
    if result is False:
        raise ValueError("run_v4 artifact validation returned false")


def seal_artifact(artifact: Path, freeze_path: Path = FREEZE_PATH) -> dict[str, str]:
    freeze_path = Path(freeze_path).resolve()
    freeze = verify_freeze(freeze_path)
    freeze_sha = sha256(freeze_path)
    artifact = Path(artifact).resolve()
    expected_artifact = canonical_artifact_path(freeze_sha).resolve()
    if artifact != expected_artifact:
        raise ValueError(
            "only the canonical freeze-scoped v4 run artifact can be sealed: "
            + str(expected_artifact)
        )
    payload = artifact.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("canonical run artifact is not UTF-8") from error
    # Use the same duplicate-key/non-finite parser as the freeze, without
    # rewriting a single artifact byte.
    try:
        document = json.loads(
            text,
            object_pairs_hook=lambda pairs: _pairs_to_unique_object(pairs),
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {token}")
            ),
        )
    except json.JSONDecodeError as error:
        raise ValueError("canonical run artifact is not strict JSON") from error
    validate_complete_artifact(
        document,
        freeze=freeze,
        freeze_sha=freeze_sha,
        freeze_path=freeze_path,
    )
    destination = public_evidence_path(freeze_sha)
    write_bytes_once(destination, payload)
    artifact_sha = hashlib.sha256(payload).hexdigest()
    if destination.read_bytes() != payload or sha256(destination) != artifact_sha:
        raise RuntimeError("sealed public evidence is not an exact-byte copy")
    return {
        "evidence": str(destination.resolve()),
        "sha256": artifact_sha,
        "freeze_sha256": freeze_sha,
    }


def _pairs_to_unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, default=FREEZE_PATH)
    args = parser.parse_args()
    result = seal_artifact(args.artifact, args.freeze)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
