"""Freeze and verify the paired A-only audit pilot before model calls."""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .prompts import canonical_json
from .schemas import select_escalation_case_ids, validate_source_snapshot


EXPERIMENT_ID = "songryeon-hybrid-a-only-audit-pilot-v1-2"
ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
SOURCE_PATH = ROOT / "source_snapshot.json"
FREEZE_PATH = ROOT / "FREEZE.json"
CODEX_SDK_DISTRIBUTION = "openai-codex"
GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")

# This is the exact repository-local dependency closure for building, running,
# and scoring the frozen study.  Package initializers are included because
# Python executes them before the imported modules.
FROZEN_RELATIVE_PATHS = (
    "evals/hybrid_audit_v1/ABORTED_ATTEMPT_V1.json",
    "evals/hybrid_audit_v1/ABORTED_ATTEMPT_V1_1.json",
    "evals/hybrid_audit_v1/__init__.py",
    "evals/hybrid_audit_v1/PROTOCOL.md",
    "evals/hybrid_audit_v1/source_snapshot.json",
    "evals/hybrid_audit_v1/source_builder.py",
    "evals/hybrid_audit_v1/schemas.py",
    "evals/hybrid_audit_v1/prompts.py",
    "evals/hybrid_audit_v1/freeze.py",
    "evals/hybrid_audit_v1/run.py",
    "evals/hybrid_audit_v1/score.py",
    "llm/__init__.py",
    "llm/client.py",
    "llm/codex_account.py",
    "llm/openai_compatible.py",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=WORKSPACE_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _git_bytes(*arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=WORKSPACE_ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _git_commit_is_ancestor(ancestor: str, descendant: str = "HEAD") -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=WORKSPACE_ROOT,
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise RuntimeError("git could not verify the source commit ancestry")


def _installed_sdk_distribution() -> dict[str, Any]:
    """Read package metadata without importing or starting the Codex SDK."""

    try:
        version = metadata.version(CODEX_SDK_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return {
            "distribution": CODEX_SDK_DISTRIBUTION,
            "version": None,
            "metadata_available": False,
        }
    if not isinstance(version, str) or not version:
        raise RuntimeError("Codex SDK distribution metadata has no version")
    return {
        "distribution": CODEX_SDK_DISTRIBUTION,
        "version": version,
        "metadata_available": True,
    }


def _atomic_write(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write((canonical_json(document) + "\n").encode("utf-8"))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_source_commit(source_commit: str) -> None:
    if not isinstance(source_commit, str) or GIT_COMMIT.fullmatch(source_commit) is None:
        raise ValueError("source_commit must be a 40-character lowercase Git commit")


def _freeze_payload_sha256(freeze: Mapping[str, Any]) -> str:
    payload = dict(freeze)
    payload.pop("freeze_payload_sha256", None)
    return _sha256_text(canonical_json(payload))


def build_freeze(source_commit: str) -> dict[str, Any]:
    """Build a freeze document only from a clean, committed source state."""

    _validate_source_commit(source_commit)
    if _git("rev-parse", "HEAD") != source_commit:
        raise RuntimeError("current HEAD does not match the declared source commit")
    if _git("status", "--porcelain"):
        raise RuntimeError("the Git worktree must be clean before freezing")
    if FREEZE_PATH.exists():
        raise FileExistsError("FREEZE.json already exists")

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    validate_source_snapshot(source)
    case_ids = [case["case_id"] for case in source["cases"]]
    if len(case_ids) != 30 or len(set(case_ids)) != 30:
        raise RuntimeError("the frozen cohort must contain 30 unique cases")

    files: dict[str, str] = {}
    for relative_path in FROZEN_RELATIVE_PATHS:
        path = WORKSPACE_ROOT / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"frozen file is missing: {relative_path}")
        current_bytes = path.read_bytes()
        try:
            _git_bytes("cat-file", "-e", f"{source_commit}:{relative_path}")
        except subprocess.CalledProcessError:
            raise RuntimeError(
                f"frozen file is not tracked in source_commit: {relative_path}"
            ) from None
        files[relative_path] = _sha256_bytes(current_bytes)

    expected_counts = {"permit": 0, "reject": 0}
    for case in source["cases"]:
        expected_counts[case["expected_audit_verdict"]] += 1

    escalation_ids = select_escalation_case_ids(source["cases"], count=8)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "study_status": "retrospective_paired_feasibility_pilot",
        "source_commit": source_commit,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_snapshot_id": source["snapshot_id"],
        "source_seed": 42,
        "case_count": 30,
        "expected_audit_verdict_counts": expected_counts,
        "planned_case_ids": case_ids,
        "planned_case_order_sha256": _sha256_text(canonical_json(case_ids)),
        "selective_escalation_count": 8,
        "selective_escalation_case_ids": escalation_ids,
        "selective_escalation_order_sha256": _sha256_text(
            canonical_json(escalation_ids)
        ),
        "conditions": [
            "no-audit",
            "local-a-only-auditor",
            "cloud-a-only-auditor",
            "selective-hybrid-8-of-30",
        ],
        # This is intentionally the observable runner contract.  The SDK or
        # transport may retry internally, and this runner cannot observe that.
        "runner_attempts_per_case": 1,
        "transport_internal_retry_observable": False,
        "model_contracts": {
            "local": {
                "provider": "ollama",
                "execution_mode": "contest_local_or_self_hosted",
                "model": "gemma4:26b",
                "temperature": 0,
                "seed": 42,
                "num_ctx": 16384,
            },
            "cloud": {
                "provider": "openai_codex",
                "execution_mode": "codex_account_integration",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "medium",
                "tools_allowed": False,
                "sdk": _installed_sdk_distribution(),
            },
        },
        "files": files,
    }
    return {
        **payload,
        "freeze_payload_sha256": _sha256_text(canonical_json(payload)),
    }


def verify_freeze_publication(freeze: Mapping[str, Any]) -> None:
    """Require the committed, clean repository state used for publication runs.

    This proves that the checked-out freeze and every sealed local dependency
    are byte-identical to the current commit.  It deliberately does not claim
    to identify the first commit that introduced ``FREEZE.json``.
    """

    if not isinstance(freeze, Mapping):
        raise TypeError("freeze must be a mapping")
    if freeze.get("freeze_payload_sha256") != _freeze_payload_sha256(freeze):
        raise RuntimeError("FREEZE.json payload hash does not match")
    if _git("status", "--porcelain"):
        raise RuntimeError("the Git worktree must be clean for a publication run")
    if not FREEZE_PATH.is_file():
        raise FileNotFoundError("FREEZE.json is missing")

    try:
        committed_freeze = _git_bytes(
            "show",
            f"HEAD:{FREEZE_PATH.relative_to(WORKSPACE_ROOT).as_posix()}",
        )
    except (subprocess.CalledProcessError, ValueError):
        raise RuntimeError("FREEZE.json is not tracked in current HEAD") from None
    if FREEZE_PATH.read_bytes() != committed_freeze:
        raise RuntimeError("FREEZE.json bytes differ from current HEAD")

    source_commit = freeze.get("source_commit")
    _validate_source_commit(source_commit)
    if not _git_commit_is_ancestor(source_commit, "HEAD"):
        raise RuntimeError("source_commit is not an ancestor of current HEAD")

    files = freeze.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("freeze files must be an object")
    if set(files) != set(FROZEN_RELATIVE_PATHS) or len(files) != len(
        FROZEN_RELATIVE_PATHS
    ):
        raise RuntimeError("freeze files are not the exact dependency closure")

    for relative_path in FROZEN_RELATIVE_PATHS:
        expected_sha256 = files[relative_path]
        if not isinstance(expected_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_sha256
        ):
            raise RuntimeError(f"invalid frozen hash: {relative_path}")
        path = WORKSPACE_ROOT / relative_path
        if not path.is_file():
            raise RuntimeError(f"frozen file is missing: {relative_path}")
        if _sha256_bytes(path.read_bytes()) != expected_sha256:
            raise RuntimeError(f"frozen file changed: {relative_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit")
    args = parser.parse_args(argv)
    source_commit = args.source_commit or _git("rev-parse", "HEAD")
    freeze = build_freeze(source_commit)
    _atomic_write(FREEZE_PATH, freeze)
    print(FREEZE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
