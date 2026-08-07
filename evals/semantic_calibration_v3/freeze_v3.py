"""Create and verify the exhaustive pre-call v3 experiment freeze."""

from __future__ import annotations

import os
import sys


def reject_bytecode_caches():
    sys.pycache_prefix = None
    experiment_root = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(experiment_root))
    roots = (experiment_root, os.path.join(workspace_root, "llm"))
    bytecode = []
    for root in roots:
        for current, directories, files in os.walk(root):
            bytecode.extend(
                os.path.join(current, name)
                for name in directories
                if name == "__pycache__"
            )
            bytecode.extend(
                os.path.join(current, name)
                for name in files
                if name.lower().endswith((".pyc", ".pyo"))
            )
    if bytecode:
        raise RuntimeError(f"freeze refuses Python bytecode caches: {bytecode}")


sys.pycache_prefix = None
if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("freeze tool must be executed by direct file path, not -m")
if __name__ == "__main__":
    reject_bytecode_caches()
sys.dont_write_bytecode = True

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import llm as llm_package
import llm.client as llm_client_module
import schemas as schemas_module
from llm import OllamaClient
from schemas import load_strict_json


MODEL_CONTRACT = {
    "model_name": "gemma4:26b",
    "timeout_seconds": 300,
    "num_ctx": 16_384,
    "keep_alive": "30m",
    "temperature": 0,
    "seed": 8_849,
    "think": False,
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_versions():
    packages = {}
    for name in ("pytest",):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "packages": packages,
    }


def frozen_paths():
    def files_under(directory, *, exclude_freeze=False):
        result = []
        for item in directory.rglob("*"):
            if not item.is_file():
                continue
            relative_parts = item.relative_to(directory).parts
            if "__pycache__" in relative_parts or ".pytest_cache" in relative_parts:
                continue
            if exclude_freeze and item.name in {"FREEZE.json", "FREEZE.json.tmp"}:
                continue
            result.append(item)
        return result

    paths = files_under(ROOT, exclude_freeze=True)
    paths.extend(files_under(WORKSPACE_ROOT / "llm"))
    paths.append(WORKSPACE_ROOT / ".gitattributes")
    return sorted({item.resolve() for item in paths})


def verify_import_provenance():
    expected = {
        "llm": (WORKSPACE_ROOT / "llm" / "__init__.py").resolve(),
        "llm.client": (WORKSPACE_ROOT / "llm" / "client.py").resolve(),
        "schemas": (ROOT / "schemas.py").resolve(),
    }
    actual = {
        "llm": Path(llm_package.__file__).resolve(),
        "llm.client": Path(llm_client_module.__file__).resolve(),
        "schemas": Path(schemas_module.__file__).resolve(),
    }
    if actual != expected:
        raise RuntimeError(f"evaluation import provenance differs: {actual}")


def require_clean_worktree():
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    if status.strip():
        raise RuntimeError("source tree must be clean and committed")


def freeze_publication(path):
    path = Path(path).resolve()
    relative = path.relative_to(WORKSPACE_ROOT).as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if tracked.returncode != 0:
        raise RuntimeError("FREEZE.json must be committed before a scored call")
    commit = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    if not commit:
        raise RuntimeError("FREEZE.json has no Git commit")
    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    remote_ref = upstream.stdout.strip() if upstream.returncode == 0 else ""
    if not remote_ref:
        raise RuntimeError("current branch needs a remote-tracking upstream")
    publication = {"commit": commit, "remote_ref": remote_ref}
    verify_freeze_publication(publication, path)
    return publication


def verify_freeze_publication(publication, path):
    if (
        not isinstance(publication, dict)
        or set(publication) != {"commit", "remote_ref"}
        or not isinstance(publication["commit"], str)
        or not isinstance(publication["remote_ref"], str)
        or not publication["remote_ref"]
    ):
        raise ValueError("invalid freeze publication witness")
    relative = Path(path).resolve().relative_to(WORKSPACE_ROOT).as_posix()
    actual_commit = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    if publication["commit"] != actual_commit:
        raise RuntimeError("freeze publication commit differs from tracked artifact")
    contains = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            publication["commit"],
            publication["remote_ref"],
        ],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if contains.returncode != 0:
        raise RuntimeError("FREEZE.json commit is not present on its remote witness")


def relative_label(path):
    path = Path(path).resolve()
    try:
        return "experiment/" + path.relative_to(ROOT).as_posix()
    except ValueError:
        return "workspace/" + path.relative_to(WORKSPACE_ROOT).as_posix()


def create_freeze(path):
    if path.exists():
        raise FileExistsError(
            "FREEZE.json already exists; meaningful changes require a new version"
        )
    reject_bytecode_caches()
    paths = frozen_paths()
    missing = [str(item) for item in paths if not item.is_file()]
    if missing:
        raise FileNotFoundError(f"freeze inputs missing: {missing}")
    verify_import_provenance()
    require_clean_worktree()
    for item in paths:
        relative = item.resolve().relative_to(WORKSPACE_ROOT).as_posix()
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if tracked.returncode != 0:
            raise RuntimeError(f"freeze input is not Git-tracked: {relative}")
    oracle = load_strict_json(ROOT / "control" / "oracle_results.json")
    if not oracle.get("python_version", "").startswith("3.10.11"):
        raise ValueError("oracle was not generated by CPython 3.10.11")
    plan = load_strict_json(ROOT / "control" / "run_plan.json")
    if len(plan.get("contract_units", [])) != 4:
        raise ValueError("contract plan must contain exactly four units")
    if len(plan.get("semantic_units", [])) != 48:
        raise ValueError("semantic plan must contain exactly 48 units")
    from build_oracle import build_oracle
    from build_plan import build_plan

    if build_oracle() != oracle:
        raise ValueError("stored oracle does not reproduce from fresh processes")
    if build_plan() != plan:
        raise ValueError("stored run plan does not reproduce from frozen builders")
    tests = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", str(ROOT / "tests"), "-q"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if tests.returncode != 0:
        raise RuntimeError("pre-freeze tests failed:\n" + tests.stdout + tests.stderr)
    require_clean_worktree()
    post_test_paths = frozen_paths()
    if set(post_test_paths) != set(paths):
        raise RuntimeError("freeze input file set changed during pre-freeze tests")
    paths = post_test_paths
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    client = OllamaClient(
        model_name=MODEL_CONTRACT["model_name"],
        timeout_seconds=MODEL_CONTRACT["timeout_seconds"],
        num_ctx=MODEL_CONTRACT["num_ctx"],
        keep_alive=MODEL_CONTRACT["keep_alive"],
        temperature=MODEL_CONTRACT["temperature"],
        seed=MODEL_CONTRACT["seed"],
    )
    readiness = client.check_ready()
    document = {
        "schema_version": 1,
        "status": "preregistered_before_scored_model_call",
        "model_contract": MODEL_CONTRACT,
        "model_readiness": readiness,
        "package_versions": package_versions(),
        "source_commit": source_commit,
        "files": {
            relative_label(item): sha256(item)
            for item in paths
        },
    }
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    ) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)
    return document


def verify_freeze(path):
    reject_bytecode_caches()
    verify_import_provenance()
    require_clean_worktree()
    document = load_strict_json(Path(path))
    expected = document.get("files", {})
    current_paths = frozen_paths()
    current_labels = {relative_label(item): item for item in current_paths}
    if set(expected) != set(current_labels):
        raise ValueError("frozen file set changed")
    mismatches = [
        label
        for label, item in current_labels.items()
        if sha256(item) != expected[label]
    ]
    if mismatches:
        raise ValueError(f"frozen file hashes changed: {mismatches}")
    if document.get("model_contract") != MODEL_CONTRACT:
        raise ValueError("model contract changed")
    return document


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--path", type=Path, default=ROOT / "FREEZE.json")
    args = parser.parse_args()
    document = create_freeze(args.path) if args.create else verify_freeze(args.path)
    print(
        json.dumps(
            {
                "freeze": str(args.path.resolve()),
                "file_count": len(document["files"]),
                "model": document["model_readiness"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
