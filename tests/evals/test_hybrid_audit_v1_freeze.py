from __future__ import annotations

from pathlib import Path

import pytest

from evals.hybrid_audit_v1 import freeze as freeze_module
from evals.hybrid_audit_v1.schemas import (
    canonical_json,
    select_escalation_case_ids,
)


SOURCE_COMMIT = "1" * 40


def _clean_git(*arguments: str) -> str:
    if arguments == ("rev-parse", "HEAD"):
        return SOURCE_COMMIT
    if arguments == ("status", "--porcelain"):
        return ""
    raise AssertionError(f"unexpected git call: {arguments}")


def _signed(document: dict) -> dict:
    payload = dict(document)
    return {
        **payload,
        "freeze_payload_sha256": freeze_module._sha256_text(
            canonical_json(payload)
        ),
    }


def _publication_fixture(tmp_path: Path, monkeypatch) -> tuple[dict, Path]:
    root = tmp_path / "repository"
    freeze_path = root / "evals/hybrid_audit_v1/FREEZE.json"
    frozen_paths = ("package/__init__.py", "runner.py")
    contents = {
        "package/__init__.py": b"# package\n",
        "runner.py": b"RUNNER_ATTEMPTS = 1\n",
    }
    for relative_path, content in contents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    document = _signed(
        {
            "source_commit": SOURCE_COMMIT,
            "files": {
                relative_path: freeze_module._sha256_bytes(content)
                for relative_path, content in contents.items()
            },
        }
    )
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_path.write_bytes((canonical_json(document) + "\n").encode("utf-8"))

    monkeypatch.setattr(freeze_module, "WORKSPACE_ROOT", root)
    monkeypatch.setattr(freeze_module, "FREEZE_PATH", freeze_path)
    monkeypatch.setattr(freeze_module, "FROZEN_RELATIVE_PATHS", frozen_paths)
    monkeypatch.setattr(freeze_module, "_git", lambda *arguments: "")
    monkeypatch.setattr(
        freeze_module,
        "_git_bytes",
        lambda *arguments: freeze_path.read_bytes(),
    )
    monkeypatch.setattr(
        freeze_module,
        "_git_commit_is_ancestor",
        lambda ancestor, descendant="HEAD": True,
    )
    return document, freeze_path


def test_frozen_paths_cover_freezer_and_imported_package_initializers():
    paths = freeze_module.FROZEN_RELATIVE_PATHS

    assert len(paths) == len(set(paths))
    assert "evals/hybrid_audit_v1/__init__.py" in paths
    assert "evals/hybrid_audit_v1/freeze.py" in paths
    assert "llm/__init__.py" in paths
    # llm.__init__ imports this module even though the audit runner does not
    # instantiate its client.
    assert "llm/openai_compatible.py" in paths


def test_build_freeze_seals_ordered_selective_ids_and_observable_retry_contract(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(freeze_module, "FREEZE_PATH", tmp_path / "FREEZE.json")
    monkeypatch.setattr(freeze_module, "_git", _clean_git)
    monkeypatch.setattr(freeze_module, "_git_bytes", lambda *arguments: b"")
    monkeypatch.setattr(
        freeze_module.metadata,
        "version",
        lambda distribution: "test-sdk-version",
    )

    result = freeze_module.build_freeze(SOURCE_COMMIT)
    source = freeze_module.json.loads(
        freeze_module.SOURCE_PATH.read_text(encoding="utf-8")
    )
    expected_ids = select_escalation_case_ids(source["cases"], count=8)

    assert result["selective_escalation_case_ids"] == expected_ids
    assert result["selective_escalation_order_sha256"] == (
        freeze_module._sha256_text(canonical_json(expected_ids))
    )
    assert result["runner_attempts_per_case"] == 1
    assert result["transport_internal_retry_observable"] is False
    assert all(
        "attempts_per_case" not in contract
        for contract in result["model_contracts"].values()
    )
    assert result["model_contracts"]["cloud"]["sdk"] == {
        "distribution": "openai-codex",
        "version": "test-sdk-version",
        "metadata_available": True,
    }
    assert set(result["files"]) == set(freeze_module.FROZEN_RELATIVE_PATHS)
    assert result["freeze_payload_sha256"] == freeze_module._freeze_payload_sha256(
        result
    )


def test_sdk_metadata_absence_is_recorded_without_importing_sdk(monkeypatch):
    def missing(_distribution):
        raise freeze_module.metadata.PackageNotFoundError

    monkeypatch.setattr(freeze_module.metadata, "version", missing)

    assert freeze_module._installed_sdk_distribution() == {
        "distribution": "openai-codex",
        "version": None,
        "metadata_available": False,
    }


def test_build_freeze_refuses_a_dirty_worktree(tmp_path, monkeypatch):
    monkeypatch.setattr(freeze_module, "FREEZE_PATH", tmp_path / "FREEZE.json")

    def dirty_git(*arguments):
        if arguments == ("rev-parse", "HEAD"):
            return SOURCE_COMMIT
        if arguments == ("status", "--porcelain"):
            return " M evals/hybrid_audit_v1/run.py"
        raise AssertionError(f"unexpected git call: {arguments}")

    monkeypatch.setattr(freeze_module, "_git", dirty_git)

    with pytest.raises(RuntimeError, match="worktree must be clean"):
        freeze_module.build_freeze(SOURCE_COMMIT)


def test_verify_publication_accepts_clean_committed_exact_state(
    tmp_path,
    monkeypatch,
):
    document, _ = _publication_fixture(tmp_path, monkeypatch)

    assert freeze_module.verify_freeze_publication(document) is None


def test_verify_publication_requires_freeze_bytes_from_head(tmp_path, monkeypatch):
    document, _ = _publication_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(freeze_module, "_git_bytes", lambda *arguments: b"changed")

    with pytest.raises(RuntimeError, match="bytes differ"):
        freeze_module.verify_freeze_publication(document)


def test_verify_publication_requires_source_commit_ancestor(tmp_path, monkeypatch):
    document, _ = _publication_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        freeze_module,
        "_git_commit_is_ancestor",
        lambda ancestor, descendant="HEAD": False,
    )

    with pytest.raises(RuntimeError, match="not an ancestor"):
        freeze_module.verify_freeze_publication(document)


def test_verify_publication_requires_exact_dependency_keys(tmp_path, monkeypatch):
    document, freeze_path = _publication_fixture(tmp_path, monkeypatch)
    changed = dict(document)
    changed["files"] = dict(document["files"])
    changed["files"]["unexpected.py"] = "0" * 64
    changed = _signed(
        {
            key: value
            for key, value in changed.items()
            if key != "freeze_payload_sha256"
        }
    )
    freeze_path.write_bytes((canonical_json(changed) + "\n").encode("utf-8"))

    with pytest.raises(RuntimeError, match="exact dependency closure"):
        freeze_module.verify_freeze_publication(changed)


def test_verify_publication_requires_current_frozen_hashes(tmp_path, monkeypatch):
    document, freeze_path = _publication_fixture(tmp_path, monkeypatch)
    (freeze_module.WORKSPACE_ROOT / "runner.py").write_bytes(b"changed\n")
    monkeypatch.setattr(
        freeze_module,
        "_git_bytes",
        lambda *arguments: freeze_path.read_bytes(),
    )

    with pytest.raises(RuntimeError, match="frozen file changed"):
        freeze_module.verify_freeze_publication(document)


def test_verify_publication_requires_clean_worktree(tmp_path, monkeypatch):
    document, _ = _publication_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        freeze_module,
        "_git",
        lambda *arguments: "?? untracked.txt",
    )

    with pytest.raises(RuntimeError, match="worktree must be clean"):
        freeze_module.verify_freeze_publication(document)
