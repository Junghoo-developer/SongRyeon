"""Isolated checks for the v4 freeze and exact-byte evidence seal."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
V4_ROOT = WORKSPACE_ROOT / "evals" / "semantic_ceiling_v4"
if str(V4_ROOT) not in sys.path:
    sys.path.insert(0, str(V4_ROOT))

freeze_v4 = importlib.import_module("freeze_v4")
seal_v4 = importlib.import_module("seal_v4")


def _write(path: Path, payload: bytes = b"x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_bytecode_guard_covers_experiment_and_llm(tmp_path: Path) -> None:
    experiment = tmp_path / "evals" / "semantic_ceiling_v4"
    llm = tmp_path / "llm"
    experiment.mkdir(parents=True)
    llm.mkdir()
    freeze_v4.reject_bytecode_caches(str(experiment), str(llm))

    _write(experiment / "__pycache__" / "runner.pyc")
    with pytest.raises(RuntimeError, match="bytecode caches"):
        freeze_v4.reject_bytecode_caches(str(experiment), str(llm))
    (experiment / "__pycache__" / "runner.pyc").unlink()
    (experiment / "__pycache__").rmdir()

    _write(llm / "client.pyo")
    with pytest.raises(RuntimeError, match="bytecode caches"):
        freeze_v4.reject_bytecode_caches(str(experiment), str(llm))
    (llm / "client.pyo").unlink()

    relevant_cache = (
        tmp_path
        / "tests"
        / "evals"
        / "__pycache__"
        / "test_semantic_ceiling_v4_runner.cpython-310.pyc"
    )
    _write(relevant_cache)
    with pytest.raises(RuntimeError, match="bytecode caches"):
        freeze_v4.reject_bytecode_caches(str(experiment), str(llm))
    relevant_cache.unlink()
    relevant_cache.parent.rmdir()

    pytest_cache = experiment / ".pytest_cache"
    pytest_cache.mkdir()
    with pytest.raises(RuntimeError, match="pytest caches"):
        freeze_v4.reject_bytecode_caches(str(experiment), str(llm))


def test_direct_tools_require_dash_b_before_importing_scored_code() -> None:
    environment = dict(os.environ)
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    environment.pop("PYTHONPYCACHEPREFIX", None)
    for script in (V4_ROOT / "freeze_v4.py", V4_ROOT / "seal_v4.py"):
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )
        assert completed.returncode != 0
        assert "must be executed with python -B" in completed.stderr


def test_frozen_paths_cover_v4_llm_tests_and_attributes_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "evals" / "semantic_ceiling_v4"
    source = _write(root / "runner.py", b"print('v4')\n")
    control = _write(root / "control" / "run_plan.json", b"{}\n")
    _write(root / "FREEZE.json", b"not an input\n")
    _write(root / "FREEZE.json.deadbeef.tmp", b"not an input\n")
    llm_source = _write(workspace / "llm" / "client.py", b"class Client: pass\n")
    _write(workspace / "llm" / "README.md", b"not Python\n")
    relevant = _write(
        workspace / "tests" / "evals" / "test_semantic_ceiling_v4_runner.py",
        b"def test_it(): pass\n",
    )
    _write(
        workspace / "tests" / "evals" / "test_unrelated.py",
        b"def test_it(): pass\n",
    )
    attributes = _write(workspace / ".gitattributes", b"* text=auto\n")

    actual = freeze_v4.frozen_paths(root, workspace)
    assert actual == sorted(
        {
            source.resolve(),
            control.resolve(),
            llm_source.resolve(),
            relevant.resolve(),
            attributes.resolve(),
        },
        key=lambda path: path.relative_to(workspace).as_posix(),
    )


def test_file_manifest_is_sorted_and_commits_size_and_hash(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    second = _write(workspace / "z.py", b"second\n")
    first = _write(workspace / "a.py", b"first\n")
    files = freeze_v4.build_file_manifest([second, first], workspace)
    assert list(files) == ["a.py", "z.py"]
    assert files["a.py"] == {
        "size": 6,
        "sha256": hashlib.sha256(b"first\n").hexdigest(),
    }
    assert freeze_v4.file_tree_sha256(files) == hashlib.sha256(
        freeze_v4.canonical_json_bytes(files)
    ).hexdigest()
    changed = json.loads(json.dumps(files))
    changed["a.py"]["size"] += 1
    assert freeze_v4.file_tree_sha256(changed) != freeze_v4.file_tree_sha256(files)


def test_freeze_write_is_atomic_create_once(tmp_path: Path) -> None:
    destination = tmp_path / "FREEZE.json"
    freeze_v4.write_bytes_once(destination, b"first\n")
    assert destination.read_bytes() == b"first\n"
    with pytest.raises(FileExistsError, match="already exists"):
        freeze_v4.write_bytes_once(destination, b"replacement\n")
    assert destination.read_bytes() == b"first\n"
    assert list(tmp_path.glob("FREEZE.json.*.tmp")) == []


def test_strict_json_rejects_duplicate_keys_and_non_object(tmp_path: Path) -> None:
    duplicate = _write(tmp_path / "duplicate.json", b'{"a":1,"a":2}\n')
    scalar = _write(tmp_path / "scalar.json", b"[]\n")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        freeze_v4.load_strict_json(duplicate)
    with pytest.raises(ValueError, match="root must be an object"):
        freeze_v4.load_strict_json(scalar)


def test_fresh_build_requires_two_identical_builds_and_stored_controls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan = {
        "schema_version": 1,
        "experiment_id": "sol-medium-semantic-ceiling-v4",
        "units": [{}] * 8,
    }
    oracle = {
        "schema_version": 1,
        "python_version": "3.10.11 test",
        "manifest_sha256": "a" * 64,
        "results": [{}] * 8,
    }
    plan_path = tmp_path / "run_plan.json"
    oracle_path = tmp_path / "oracle_results.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    oracle_path.write_text(json.dumps(oracle), encoding="utf-8")
    calls = []

    def build_documents():
        calls.append(True)
        return json.loads(json.dumps(plan)), json.loads(json.dumps(oracle))

    fake = SimpleNamespace(
        __file__=str(freeze_v4.ROOT / "build_v4.py"),
        build_documents=build_documents,
    )
    monkeypatch.setattr(freeze_v4, "PLAN_PATH", plan_path)
    monkeypatch.setattr(freeze_v4, "ORACLE_PATH", oracle_path)
    monkeypatch.setattr(freeze_v4.importlib, "import_module", lambda name: fake)
    assert freeze_v4._fresh_builds() == (plan, oracle)
    assert len(calls) == 2

    calls.clear()

    def nondeterministic():
        calls.append(True)
        value = json.loads(json.dumps(plan))
        value["nonce"] = len(calls)
        return value, oracle

    fake.build_documents = nondeterministic
    with pytest.raises(ValueError, match="not byte-deterministic"):
        freeze_v4._fresh_builds()


def test_sdk_witness_requires_exactly_one_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = SimpleNamespace(version=freeze_v4.SDK_VERSION, files=())
    monkeypatch.setattr(
        freeze_v4.importlib.metadata,
        "distribution",
        lambda name: missing,
    )
    with pytest.raises(RuntimeError, match="exactly one"):
        freeze_v4.sdk_distribution_witness()


def test_actual_sdk_witness_rehashes_recorded_installation() -> None:
    witness = freeze_v4.sdk_distribution_witness()
    assert witness["name"] == "openai-codex"
    assert witness["version"] == freeze_v4.SDK_VERSION
    assert witness["verified_file_count"] >= 20
    assert freeze_v4.SHA256_RE.fullmatch(
        witness["verified_files_tree_sha256"]
    )


def test_manifest_bytes_must_equal_recorded_source_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "freeze-test@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Freeze Test"],
        cwd=repository,
        check=True,
    )
    source = _write(repository / "source.py", b"value = 1\n")
    subprocess.run(["git", "add", "source.py"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=repository, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    files = freeze_v4.build_file_manifest([source], repository)
    freeze_v4.require_manifest_at_commit(files, commit, repository)

    source.write_bytes(b"value = 2\n")
    changed = freeze_v4.build_file_manifest([source], repository)
    with pytest.raises(RuntimeError, match="differ from source commit"):
        freeze_v4.require_manifest_at_commit(changed, commit, repository)


def test_focused_tests_ignore_hostile_pytest_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="one passed", stderr="")

    monkeypatch.setenv("PYTEST_ADDOPTS", "--collect-only")
    monkeypatch.setenv("PYTEST_PLUGINS", "hostile_plugin")
    monkeypatch.setenv("PYTHONPATH", "hostile-path")
    monkeypatch.setattr(
        freeze_v4,
        "_focused_test_paths",
        lambda: [Path(__file__).resolve()],
    )
    monkeypatch.setattr(freeze_v4.subprocess, "run", fake_run)
    freeze_v4.run_focused_tests()
    assert captured["env"]["PYTEST_ADDOPTS"] == ""
    assert captured["env"]["PYTEST_PLUGINS"] == ""
    assert captured["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert "PYTHONPATH" not in captured["env"]
    assert "--noconftest" in captured["command"]
    assert "addopts=" in captured["command"]


def test_freeze_publication_rejects_a_second_touch(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "freeze-test@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Freeze Test"],
        cwd=repository,
        check=True,
    )
    freeze = _write(repository / "FREEZE.json", b"first\n")
    subprocess.run(["git", "add", "FREEZE.json"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "publish"], cwd=repository, check=True)
    first = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    assert freeze_v4._verify_freeze_publication(
        freeze,
        {"live_commit": first},
        repository,
    ) == first

    freeze.write_bytes(b"second\n")
    subprocess.run(["git", "add", "FREEZE.json"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "rewrite"], cwd=repository, check=True)
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    with pytest.raises(RuntimeError, match="exactly one immutable"):
        freeze_v4._verify_freeze_publication(
            freeze,
            {"live_commit": second},
            repository,
        )


def test_file_entry_schema_fails_closed() -> None:
    valid = {"a.py": {"size": 1, "sha256": "a" * 64}}
    assert freeze_v4._validate_file_entries(valid) == valid
    with pytest.raises(ValueError, match="path-sorted"):
        freeze_v4._validate_file_entries(
            {
                "z.py": {"size": 1, "sha256": "a" * 64},
                "a.py": {"size": 1, "sha256": "b" * 64},
            }
        )
    with pytest.raises(ValueError, match="invalid freeze file entry"):
        freeze_v4._validate_file_entries(
            {"a.py": {"size": True, "sha256": "a" * 64}}
        )


def test_seal_paths_are_freeze_scoped_and_outside_suite() -> None:
    digest = "a" * 64
    canonical = seal_v4.canonical_artifact_path(digest)
    evidence = seal_v4.public_evidence_path(digest)
    assert digest in canonical.parts
    assert digest in evidence.parts
    assert canonical.name == evidence.name == "run.json"
    assert V4_ROOT not in evidence.parents


def test_seal_is_exact_byte_atomic_and_never_overwrites(tmp_path: Path) -> None:
    destination = tmp_path / "evidence" / "run.json"
    payload = b'{"answer":"\xed\x95\x9c\xea\xb8\x80"}\r\n'
    seal_v4.write_bytes_once(destination, payload)
    assert destination.read_bytes() == payload
    with pytest.raises(FileExistsError, match="already exists"):
        seal_v4.write_bytes_once(destination, b"different\n")
    assert destination.read_bytes() == payload
    assert list(destination.parent.glob("run.json.*.tmp")) == []


def test_seal_identity_rejects_incomplete_or_wrong_freeze() -> None:
    freeze = {
        "tree_sha256": "1" * 64,
        "source_commit": "2" * 40,
        "model_contract": {"model_name": "gpt-5.6-sol"},
        "study_sha256": "3" * 64,
        "manifest_sha256": "4" * 64,
        "plan_sha256": "5" * 64,
        "oracle_sha256": "6" * 64,
        "protocol_sha256": "7" * 64,
    }
    document = {
        "run_state": "complete",
        "freeze_sha256": "8" * 64,
        "freeze_tree_sha256": freeze["tree_sha256"],
        "freeze_source_commit": freeze["source_commit"],
        "freeze_publication_commit": "9" * 40,
        "model_contract": freeze["model_contract"],
        "study_sha256": freeze["study_sha256"],
        "manifest_sha256": freeze["manifest_sha256"],
        "plan_sha256": freeze["plan_sha256"],
        "oracle_sha256": freeze["oracle_sha256"],
        "protocol_sha256": freeze["protocol_sha256"],
    }
    seal_v4._validate_identity(
        document,
        freeze=freeze,
        freeze_sha="8" * 64,
        freeze_publication_commit="9" * 40,
    )
    incomplete = dict(document, run_state="running")
    with pytest.raises(ValueError, match="identity differs"):
        seal_v4._validate_identity(
            incomplete,
            freeze=freeze,
            freeze_sha="8" * 64,
            freeze_publication_commit="9" * 40,
        )
    wrong = dict(document, freeze_sha256="a" * 64)
    with pytest.raises(ValueError, match="identity differs"):
        seal_v4._validate_identity(
            wrong,
            freeze=freeze,
            freeze_sha="8" * 64,
            freeze_publication_commit="9" * 40,
        )


def test_pairs_parser_rejects_duplicate_artifact_keys() -> None:
    with pytest.raises(ValueError, match="duplicate JSON key"):
        seal_v4._pairs_to_unique_object([("run_state", "complete"), ("run_state", "x")])
