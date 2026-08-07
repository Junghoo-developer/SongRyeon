"""Create or verify the one immutable Semantic Ceiling v4 freeze.

This program is deliberately a direct-file, ``python -I -B`` tool. Its import
boundary refuses bytecode for both the experiment and the Codex client before
either can be imported by the reproducibility checks.
"""

from __future__ import annotations

import os
import sys


def reject_bytecode_caches(
    experiment_root: str | None = None,
    llm_root: str | None = None,
    relevant_tests_root: str | None = None,
) -> None:
    """Fail if cached Python could bypass a hash of the corresponding source."""

    sys.pycache_prefix = None
    if experiment_root is None:
        experiment_root = os.path.dirname(os.path.abspath(__file__))
    if llm_root is None:
        workspace = os.path.dirname(os.path.dirname(experiment_root))
        llm_root = os.path.join(workspace, "llm")
    else:
        workspace = os.path.dirname(llm_root)
    if relevant_tests_root is None:
        relevant_tests_root = os.path.join(workspace, "tests", "evals")
    offenders: list[str] = []
    for root in (experiment_root, llm_root):
        for current, directories, files in os.walk(root):
            offenders.extend(
                os.path.join(current, name)
                for name in directories
                if name in {"__pycache__", ".pytest_cache"}
            )
            offenders.extend(
                os.path.join(current, name)
                for name in files
                if name.lower().endswith((".pyc", ".pyo"))
            )
    if os.path.isdir(relevant_tests_root):
        for current, _directories, files in os.walk(relevant_tests_root):
            offenders.extend(
                os.path.join(current, name)
                for name in files
                if "semantic_ceiling_v4" in name
                and name.lower().endswith((".pyc", ".pyo"))
            )
    if offenders:
        raise RuntimeError(
            "Semantic Ceiling v4 freeze refuses Python bytecode caches "
            "or pytest caches: "
            + repr(sorted(set(offenders)))
        )


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("freeze_v4.py must be executed by direct file path, not -m")
if __name__ == "__main__":
    if not sys.dont_write_bytecode:
        raise RuntimeError("freeze_v4.py must be executed with python -B")
    if not sys.flags.isolated:
        raise RuntimeError("freeze_v4.py must be executed with python -I -B")
    reject_bytecode_caches()
sys.pycache_prefix = None
sys.dont_write_bytecode = True

import argparse
import base64
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import string
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
FREEZE_PATH = ROOT / "FREEZE.json"
CONTROL_ROOT = ROOT / "control"
PLAN_PATH = CONTROL_ROOT / "run_plan.json"
ORACLE_PATH = CONTROL_ROOT / "oracle_results.json"
STUDY_PATH = ROOT / "study.json"
MANIFEST_PATH = ROOT / "manifest.json"
PROTOCOL_PATH = ROOT / "PROTOCOL.md"
EXPECTED_PYTHON = "3.10.11"
SDK_DISTRIBUTION = "openai-codex"
SDK_VERSION = "0.144.4"
MODEL_CONTRACT = {
    "provider": "openai_codex",
    "execution_mode": "codex_account_integration",
    "model_name": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "sdk_version": SDK_VERSION,
    "api_key_environment_forbidden": [
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
        "CODEX_ACCESS_TOKEN",
    ],
    "fresh_thread_per_cluster": True,
    "agent_tools_allowed": False,
    "runner_request_retry_count": 0,
    "transport_internal_retry_claim": False,
}
FREEZE_KEYS = {
    "schema_version",
    "status",
    "experiment_id",
    "python_contract",
    "sdk_distribution",
    "source_commit",
    "source_publication",
    "model_contract",
    "files",
    "tree_sha256",
    "study_sha256",
    "manifest_sha256",
    "plan_sha256",
    "oracle_sha256",
    "protocol_sha256",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> dict:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {token}")
            ),
        )
    except UnicodeDecodeError as error:
        raise ValueError(f"JSON is not UTF-8: {path}") from error
    if type(value) is not dict:
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def require_python_contract() -> dict[str, str]:
    witness = {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
    }
    if witness != {"implementation": "CPython", "version": EXPECTED_PYTHON}:
        raise RuntimeError(
            "Semantic Ceiling v4 requires exactly CPython 3.10.11; got "
            + repr(witness)
        )
    return witness


def sdk_distribution_witness() -> dict[str, str | int]:
    """Verify every hashed SDK RECORD entry and return a compact witness."""

    try:
        distribution = importlib.metadata.distribution(SDK_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError(f"required distribution is missing: {SDK_DISTRIBUTION}") from error
    if distribution.version != SDK_VERSION:
        raise RuntimeError(
            f"{SDK_DISTRIBUTION} must be {SDK_VERSION}, got {distribution.version}"
        )
    files = list(distribution.files or ())
    records = [
        item
        for item in files
        if item.name == "RECORD" and item.parent.name.endswith(".dist-info")
    ]
    if len(records) != 1:
        raise RuntimeError("openai-codex must expose exactly one dist-info RECORD")
    record = records[0]
    record_relative = record.as_posix()
    record_path = Path(distribution.locate_file(record)).resolve()
    if not record_path.is_file():
        raise RuntimeError("openai-codex RECORD entry does not resolve to a file")
    record_sha = sha256(record_path)
    if SHA256_RE.fullmatch(record_sha) is None:
        raise RuntimeError("openai-codex RECORD SHA-256 is invalid")
    verified: dict[str, dict[str, int | str]] = {}
    allowed_unhashed_present = {record_relative}
    for item in files:
        relative = item.as_posix()
        located = Path(distribution.locate_file(item)).resolve()
        declared_hash = item.hash
        declared_size = item.size
        if declared_hash is None or declared_size is None:
            if located.exists() and relative not in allowed_unhashed_present:
                raise RuntimeError(
                    "openai-codex exposes an unhashed installed file: " + relative
                )
            continue
        if declared_hash.mode != "sha256" or type(declared_size) is not int:
            raise RuntimeError("openai-codex RECORD uses an unsupported digest")
        if not located.is_file():
            raise RuntimeError("openai-codex RECORD file is missing: " + relative)
        payload = located.read_bytes()
        expected_digest = base64.urlsafe_b64decode(
            declared_hash.value + "=" * (-len(declared_hash.value) % 4)
        )
        actual_digest = hashlib.sha256(payload).digest()
        if len(payload) != declared_size or actual_digest != expected_digest:
            raise RuntimeError(
                "openai-codex installed file differs from RECORD: " + relative
            )
        verified[relative] = {
            "size": len(payload),
            "sha256": actual_digest.hex(),
        }

    package_root = Path(distribution.locate_file("openai_codex")).resolve()
    dist_info_root = record_path.parent
    recorded_paths = set(verified) | allowed_unhashed_present
    for scan_root in (package_root, dist_info_root):
        if not scan_root.is_dir():
            raise RuntimeError("openai-codex package root is missing")
        for actual in scan_root.rglob("*"):
            if not actual.is_file():
                continue
            relative = actual.resolve().relative_to(record_path.parents[1]).as_posix()
            if relative not in recorded_paths:
                raise RuntimeError(
                    "openai-codex contains a file outside its RECORD: " + relative
                )
    return {
        "name": SDK_DISTRIBUTION,
        "version": distribution.version,
        "record_path": record_relative,
        "record_sha256": record_sha,
        "verified_file_count": len(verified),
        "verified_files_tree_sha256": hashlib.sha256(
            canonical_json_bytes(dict(sorted(verified.items())))
        ).hexdigest(),
    }


def _is_freeze_generated(path: Path) -> bool:
    name = path.name
    return name == "FREEZE.json" or (
        name.startswith("FREEZE.json.") and name.endswith(".tmp")
    )


def relevant_test_paths(workspace_root: Path = WORKSPACE_ROOT) -> list[Path]:
    tests_root = workspace_root / "tests" / "evals"
    if not tests_root.is_dir():
        return []
    selected = {
        path.resolve()
        for path in tests_root.rglob("*.py")
        if "semantic_ceiling_v4" in path.as_posix()
    }
    return sorted(selected, key=lambda item: item.as_posix())


def frozen_paths(
    experiment_root: Path = ROOT,
    workspace_root: Path = WORKSPACE_ROOT,
) -> list[Path]:
    paths: set[Path] = set()
    for item in experiment_root.rglob("*"):
        if not item.is_file():
            continue
        parts = item.relative_to(experiment_root).parts
        if "__pycache__" in parts or ".pytest_cache" in parts:
            continue
        if item.suffix.lower() in {".pyc", ".pyo"} or _is_freeze_generated(item):
            continue
        paths.add(item.resolve())
    llm_root = workspace_root / "llm"
    paths.update(path.resolve() for path in llm_root.rglob("*.py") if path.is_file())
    paths.update(relevant_test_paths(workspace_root))
    paths.add((workspace_root / ".gitattributes").resolve())
    return sorted(paths, key=lambda item: item.relative_to(workspace_root).as_posix())


def build_file_manifest(
    paths: list[Path],
    workspace_root: Path = WORKSPACE_ROOT,
) -> dict[str, dict[str, int | str]]:
    manifest: dict[str, dict[str, int | str]] = {}
    for path in paths:
        resolved = path.resolve()
        relative = resolved.relative_to(workspace_root.resolve()).as_posix()
        if relative in manifest:
            raise ValueError(f"duplicate frozen path: {relative}")
        stat = resolved.stat()
        manifest[relative] = {"size": stat.st_size, "sha256": sha256(resolved)}
    return dict(sorted(manifest.items()))


def file_tree_sha256(files: dict[str, dict[str, int | str]]) -> str:
    return hashlib.sha256(canonical_json_bytes(files)).hexdigest()


def _git_text(*arguments: str, workspace_root: Path = WORKSPACE_ROOT) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=workspace_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _split_upstream(upstream: str) -> tuple[str, str]:
    if not isinstance(upstream, str) or "/" not in upstream:
        raise RuntimeError("current branch needs a remote-tracking upstream")
    remote, branch = upstream.split("/", 1)
    if not remote or not branch:
        raise RuntimeError("current branch needs a remote-tracking upstream")
    return remote, branch


def _parse_live_head(output: str, branch: str) -> str:
    expected_ref = f"refs/heads/{branch}"
    matches = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == expected_ref:
            matches.append(parts[0].lower())
    if (
        len(matches) != 1
        or len(matches[0]) != 40
        or any(character not in string.hexdigits for character in matches[0])
    ):
        raise RuntimeError("live upstream branch could not be verified exactly")
    return matches[0]


def validate_published_clean_head(
    workspace_root: Path = WORKSPACE_ROOT,
) -> dict[str, str]:
    if _git_text(
        "status", "--porcelain", "--untracked-files=all", workspace_root=workspace_root
    ):
        raise RuntimeError("freeze requires a completely clean Git worktree")
    head = _git_text("rev-parse", "HEAD", workspace_root=workspace_root).lower()
    upstream_commit = _git_text(
        "rev-parse", "@{u}", workspace_root=workspace_root
    ).lower()
    upstream = _git_text(
        "rev-parse", "--abbrev-ref", "@{u}", workspace_root=workspace_root
    )
    remote, branch = _split_upstream(upstream)
    if head != upstream_commit:
        raise RuntimeError("HEAD differs from its pushed tracking branch")
    live_output = _git_text(
        "ls-remote",
        "--heads",
        remote,
        f"refs/heads/{branch}",
        workspace_root=workspace_root,
    )
    live_commit = _parse_live_head(live_output, branch)
    if head != live_commit:
        raise RuntimeError("HEAD differs from the live remote branch")
    return {
        "commit": head,
        "branch": _git_text("branch", "--show-current", workspace_root=workspace_root),
        "upstream": upstream,
        "remote_url": _git_text(
            "remote", "get-url", remote, workspace_root=workspace_root
        ),
        "live_commit": live_commit,
    }


def require_tracked(paths: list[Path], workspace_root: Path = WORKSPACE_ROOT) -> None:
    for path in paths:
        relative = path.resolve().relative_to(workspace_root.resolve()).as_posix()
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"freeze input is not Git-tracked: {relative}")


def require_manifest_at_commit(
    files: dict[str, dict[str, int | str]],
    commit: str,
    workspace_root: Path = WORKSPACE_ROOT,
) -> None:
    """Bind every frozen worktree byte to the recorded source Git commit."""

    if (
        type(commit) is not str
        or len(commit) != 40
        or any(character not in string.hexdigits for character in commit)
    ):
        raise ValueError("source commit is not a full Git object ID")
    for relative, expected in files.items():
        completed = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=workspace_root,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"frozen input does not exist at source commit: {relative}"
            )
        blob = completed.stdout
        actual = {
            "size": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }
        if actual != expected:
            raise RuntimeError(
                f"frozen worktree bytes differ from source commit: {relative}"
            )


def _fresh_builds() -> tuple[dict, dict]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    build_module = importlib.import_module("build_v4")
    if Path(build_module.__file__).resolve() != (ROOT / "build_v4.py").resolve():
        raise RuntimeError("build_v4 import provenance differs from the frozen source")
    first_plan, first_oracle = build_module.build_documents()
    second_plan, second_oracle = build_module.build_documents()
    for label, value in (
        ("first plan", first_plan),
        ("first oracle", first_oracle),
        ("second plan", second_plan),
        ("second oracle", second_oracle),
    ):
        if type(value) is not dict:
            raise ValueError(f"{label} must be a JSON object")
    if canonical_json_bytes(first_plan) != canonical_json_bytes(second_plan):
        raise ValueError("build_v4 plan is not byte-deterministic")
    if canonical_json_bytes(first_oracle) != canonical_json_bytes(second_oracle):
        raise ValueError("build_v4 oracle is not byte-deterministic")
    stored_plan = load_strict_json(PLAN_PATH)
    stored_oracle = load_strict_json(ORACLE_PATH)
    if canonical_json_bytes(first_plan) != canonical_json_bytes(stored_plan):
        raise ValueError("stored run_plan.json differs from a pure build_v4 build")
    if canonical_json_bytes(first_oracle) != canonical_json_bytes(stored_oracle):
        raise ValueError("stored oracle_results.json differs from a pure build_v4 build")
    return stored_plan, stored_oracle


def _focused_test_paths() -> list[Path]:
    paths = relevant_test_paths()
    internal = ROOT / "tests"
    if internal.is_dir():
        paths.extend(path.resolve() for path in internal.rglob("test_*.py"))
    paths = sorted(set(paths), key=lambda path: path.as_posix())
    if not paths:
        raise RuntimeError("no focused Semantic Ceiling v4 tests were found")
    return paths


def run_focused_tests() -> None:
    paths = _focused_test_paths()
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTEST_ADDOPTS"] = ""
    environment["PYTEST_PLUGINS"] = ""
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment.pop("PYTHONPYCACHEPREFIX", None)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONSTARTUP", None)
    with tempfile.TemporaryDirectory(prefix="songryeon-v4-pytest-") as temporary:
        temporary_root = Path(temporary)
        config = temporary_root / "pytest.ini"
        config.write_text("[pytest]\naddopts =\n", encoding="utf-8", newline="\n")
        base_temp = temporary_root / "run"
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "-c",
                str(config),
                "--noconftest",
                "-p",
                "no:cacheprovider",
                "-o",
                "addopts=",
                "--basetemp",
                str(base_temp),
                "-q",
                *[str(path) for path in paths],
            ],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=240,
            env=environment,
        )
    if completed.returncode != 0:
        raise RuntimeError(
            "focused Semantic Ceiling v4 tests failed:\n"
            + completed.stdout
            + completed.stderr
        )


def _validate_control_documents(plan: dict, oracle: dict) -> None:
    if plan.get("schema_version") != 1 or plan.get("experiment_id") != (
        "sol-medium-semantic-ceiling-v4"
    ):
        raise ValueError("run plan identity differs from the v4 protocol")
    units = plan.get("units")
    if type(units) is not list or len(units) != 8:
        raise ValueError("run plan must contain exactly eight units")
    if (
        oracle.get("schema_version") != 1
        or type(oracle.get("python_version")) is not str
        or not oracle["python_version"].startswith("3.10.11 ")
        or type(oracle.get("results")) is not list
        or len(oracle["results"]) != 8
    ):
        raise ValueError("oracle identity differs from the v4 protocol")


def _source_hashes(files: dict[str, dict[str, int | str]]) -> dict[str, str]:
    special = {
        "study_sha256": sha256(STUDY_PATH),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "plan_sha256": sha256(PLAN_PATH),
        "oracle_sha256": sha256(ORACLE_PATH),
        "protocol_sha256": sha256(PROTOCOL_PATH),
    }
    labels = {
        "study_sha256": STUDY_PATH,
        "manifest_sha256": MANIFEST_PATH,
        "plan_sha256": PLAN_PATH,
        "oracle_sha256": ORACLE_PATH,
        "protocol_sha256": PROTOCOL_PATH,
    }
    for key, path in labels.items():
        relative = path.relative_to(WORKSPACE_ROOT).as_posix()
        if files.get(relative, {}).get("sha256") != special[key]:
            raise RuntimeError(f"special hash is absent from frozen tree: {relative}")
    return special


def _serialize_freeze(document: dict) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")


def write_bytes_once(destination: Path, payload: bytes) -> None:
    """Atomically create complete bytes without a replace/overwrite race."""

    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(
            "FREEZE.json already exists; a meaningful change needs a new suite version"
        )
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


def _preflight_sources() -> tuple[dict, dict, dict, dict[str, str]]:
    reject_bytecode_caches()
    require_python_contract()
    paths = frozen_paths()
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"freeze inputs are missing: {missing}")
    if not relevant_test_paths():
        raise RuntimeError("at least one external v4 freeze/runner test is required")
    publication = validate_published_clean_head()
    require_tracked(paths)
    plan, oracle = _fresh_builds()
    _validate_control_documents(plan, oracle)
    before = build_file_manifest(paths)
    require_manifest_at_commit(before, publication["commit"])
    run_focused_tests()
    reject_bytecode_caches()
    publication_after = validate_published_clean_head()
    if publication_after != publication:
        raise RuntimeError("published Git identity changed during freeze preflight")
    paths_after = frozen_paths()
    after = build_file_manifest(paths_after)
    if before != after:
        raise RuntimeError("frozen source tree changed during focused tests")
    require_manifest_at_commit(after, publication["commit"])
    return after, plan, oracle, publication


def create_freeze(path: Path = FREEZE_PATH) -> dict:
    path = Path(path).resolve()
    if path.exists():
        raise FileExistsError(
            "FREEZE.json already exists; a meaningful change needs a new suite version"
        )
    files, _plan, _oracle, publication = _preflight_sources()
    study = load_strict_json(STUDY_PATH)
    if study.get("model_contract") != MODEL_CONTRACT:
        raise ValueError("study model contract differs from freeze_v4.py")
    special = _source_hashes(files)
    document = {
        "schema_version": 1,
        "status": "preregistered_before_target_model_output",
        "experiment_id": "sol-medium-semantic-ceiling-v4",
        "python_contract": require_python_contract(),
        "sdk_distribution": sdk_distribution_witness(),
        "source_commit": publication["commit"],
        "source_publication": publication,
        "model_contract": MODEL_CONTRACT,
        "files": files,
        "tree_sha256": file_tree_sha256(files),
        **special,
    }
    final_publication = validate_published_clean_head()
    if final_publication != publication:
        raise RuntimeError("published Git identity changed before freeze creation")
    if build_file_manifest(frozen_paths()) != files:
        raise RuntimeError("frozen source tree changed before freeze creation")
    require_manifest_at_commit(files, publication["commit"])
    write_bytes_once(path, _serialize_freeze(document))
    return document


def _validate_file_entries(files: object) -> dict[str, dict[str, int | str]]:
    if type(files) is not dict or list(files) != sorted(files):
        raise ValueError("freeze files must be a path-sorted object")
    for label, entry in files.items():
        if (
            type(label) is not str
            or not label
            or type(entry) is not dict
            or set(entry) != {"size", "sha256"}
            or type(entry["size"]) is not int
            or entry["size"] < 0
            or type(entry["sha256"]) is not str
            or SHA256_RE.fullmatch(entry["sha256"]) is None
        ):
            raise ValueError(f"invalid freeze file entry: {label!r}")
    return files


def _verify_freeze_publication(
    path: Path,
    current: dict[str, str],
    workspace_root: Path = WORKSPACE_ROOT,
) -> str:
    workspace_root = Path(workspace_root).resolve()
    relative = path.resolve().relative_to(workspace_root).as_posix()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if tracked.returncode != 0:
        raise RuntimeError("FREEZE.json must be committed before verification")
    history = _git_text(
        "log", "--format=%H", "--", relative, workspace_root=workspace_root
    ).splitlines()
    if len(history) != 1:
        raise RuntimeError(
            "FREEZE.json must have exactly one immutable publication commit"
        )
    commit = history[0].lower()
    added = _git_text(
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-status",
        "-r",
        commit,
        "--",
        relative,
        workspace_root=workspace_root,
    ).splitlines()
    if len(added) != 1 or added[0].split("\t", 1) != ["A", relative]:
        raise RuntimeError("FREEZE.json publication commit must add it exactly once")
    blob = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=workspace_root,
        capture_output=True,
    )
    if blob.returncode != 0 or blob.stdout != path.read_bytes():
        raise RuntimeError("FREEZE.json differs from its initial publication blob")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, current["live_commit"]],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if ancestor.returncode != 0:
        raise RuntimeError("FREEZE.json publication commit is not on the live branch")
    return commit


def verify_freeze(path: Path = FREEZE_PATH) -> dict:
    reject_bytecode_caches()
    python_contract = require_python_contract()
    path = Path(path).resolve()
    document = load_strict_json(path)
    if set(document) != FREEZE_KEYS:
        raise ValueError("FREEZE.json fields differ from the fail-closed schema")
    if (
        document["schema_version"] != 1
        or document["status"] != "preregistered_before_target_model_output"
        or document["experiment_id"] != "sol-medium-semantic-ceiling-v4"
    ):
        raise ValueError("FREEZE.json identity is invalid")
    if document["python_contract"] != python_contract:
        raise ValueError("frozen Python contract differs from this interpreter")
    if document["sdk_distribution"] != sdk_distribution_witness():
        raise ValueError("frozen openai-codex installation witness changed")
    if document["model_contract"] != MODEL_CONTRACT:
        raise ValueError("frozen model contract changed")
    study = load_strict_json(STUDY_PATH)
    if study.get("model_contract") != MODEL_CONTRACT:
        raise ValueError("study model contract differs from the freeze")

    current = validate_published_clean_head()
    source_commit = document["source_commit"]
    if (
        type(source_commit) is not str
        or len(source_commit) != 40
        or any(character not in string.hexdigits for character in source_commit)
    ):
        raise ValueError("frozen source commit is invalid")
    source_publication = document["source_publication"]
    if (
        type(source_publication) is not dict
        or set(source_publication) != {
            "commit",
            "branch",
            "upstream",
            "remote_url",
            "live_commit",
        }
        or source_publication.get("commit") != source_commit
        or source_publication.get("live_commit") != source_commit
        or source_publication.get("branch") != current["branch"]
        or source_publication.get("upstream") != current["upstream"]
        or source_publication.get("remote_url") != current["remote_url"]
    ):
        raise ValueError("frozen source publication witness is invalid")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, current["commit"]],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if ancestor.returncode != 0:
        raise RuntimeError("frozen source commit is not an ancestor of current HEAD")
    publication_commit = _verify_freeze_publication(path, current)
    source_precedes_publication = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, publication_commit],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if source_precedes_publication.returncode != 0:
        raise RuntimeError("frozen source commit does not precede freeze publication")

    paths = frozen_paths()
    require_tracked(paths)
    actual_files = build_file_manifest(paths)
    expected_files = _validate_file_entries(document["files"])
    if actual_files != expected_files:
        raise ValueError("frozen path, size, or SHA-256 tree changed")
    require_manifest_at_commit(actual_files, source_commit)
    if document["tree_sha256"] != file_tree_sha256(actual_files):
        raise ValueError("frozen tree SHA-256 is invalid")
    special = _source_hashes(actual_files)
    if any(document[key] != value for key, value in special.items()):
        raise ValueError("one or more frozen control/document hashes changed")
    plan, oracle = _fresh_builds()
    _validate_control_documents(plan, oracle)

    before = actual_files
    run_focused_tests()
    reject_bytecode_caches()
    current_after = validate_published_clean_head()
    if current_after != current:
        raise RuntimeError("published Git identity changed during freeze verification")
    after = build_file_manifest(frozen_paths())
    if after != before:
        raise RuntimeError("frozen source tree changed during verification tests")
    if not publication_commit:
        raise RuntimeError("FREEZE.json has no verified publication commit")
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    document = create_freeze() if args.create else verify_freeze()
    output = {
        "freeze": str(FREEZE_PATH),
        "tree_sha256": document["tree_sha256"],
        "file_count": len(document["files"]),
        "source_commit": document["source_commit"],
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
