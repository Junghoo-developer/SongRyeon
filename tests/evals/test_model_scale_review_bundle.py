"""Tests for the derived blinded model-scale review bundle."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from evals.model_scale_capture import (
    ARTIFACT_MANIFEST_FILENAME,
    DEFAULT_MODEL_CEILING_MANIFEST,
    EXPERIMENT_KIND,
)
from evals.model_scale_review_bundle import (
    CASE_MATERIAL_DIRECTORY,
    NORMALIZER_SOURCE_FILENAME,
    REVIEW_PACKET_FILENAME,
    REVIEWER_PROTOCOL_FILENAME,
    _REQUIRED_EXPERIMENT_SOURCE_PATHS,
    _validate_retention_contract,
    build_model_scale_review_bundle,
    verify_model_scale_review_bundle,
)
from evals.runner import load_manifest


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _record(information_type, information, turn_id, information_id):
    return {
        "information": information,
        "information_class": "absolute",
        "code_verifiable": True,
        "information_type": information_type,
        "turn_id": turn_id,
        "information_id": information_id,
        "created_at": "2000-01-01T00:00:00+00:00",
    }


def _tool_records(sequence, *, mode, content, result_content=None):
    turn_id = f"turn-main-tool-{sequence}"
    name = "read_python_file" if sequence == 1 else "list_python_files"
    arguments = {"path": "declaration_only.py"} if sequence == 1 else {}
    source_id = f"raw-content-{sequence}"
    values = [
        _record("tool_raw_name", name, turn_id, f"name-{sequence}"),
        _record(
            "tool_raw_arguments",
            json.dumps(arguments, separators=(",", ":")),
            turn_id,
            f"arguments-{sequence}",
        ),
        _record("tool_raw_success", True, turn_id, f"success-{sequence}"),
        _record("tool_raw_content", content, turn_id, source_id),
        _record("tool_raw_error", "", turn_id, f"error-{sequence}"),
        _record(
            "tool_raw_selection_source_id",
            source_id,
            turn_id,
            f"source-{sequence}",
        ),
        _record(
            "tool_retention_applied",
            json.dumps(
                {
                    "arguments": arguments,
                    "end": None,
                    "mode": mode,
                    "start": None,
                    "tool_name": name,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            turn_id,
            f"retention-{sequence}",
        ),
    ]
    if mode != "omit":
        values.append(
            _record(
                "tool_result_content",
                content if result_content is None else result_content,
                turn_id,
                f"result-{sequence}",
            )
        )
    return values


def _make_parent_pack(
    root,
    *,
    malformed_result=False,
    raw_node2_limit=False,
    declared_node2_limit=None,
    unexpected_fixture_memory=False,
):
    root.mkdir(parents=True)
    manifest = load_manifest(DEFAULT_MODEL_CEILING_MANIFEST)
    case_id = "heldout-declaration-is-not-enforcement"
    system_name = "SECRET-system-gamma"
    raw_path = root / "raw" / "SECRET-provider-model.memory.jsonl"
    transcript_path = root / "transcripts" / "SECRET-transcript.txt"
    fixture = {
        "information": "이전 기억은 상대정보다.",
        "information_class": "relative",
        "code_verifiable": False,
        "information_type": "fixture_memory",
        "turn_id": "fixture-seed",
        "information_id": "fixture-relative-1",
        "created_at": "2000-01-01T00:00:00+00:00",
    }
    content = "MAX_PAYLOAD_CHARACTERS = 128\n"
    records = [
        *([fixture] if unexpected_fixture_memory else []),
        *_tool_records(
            1,
            mode="full",
            content=content,
            result_content=("altered\n" if malformed_result else None),
        ),
        *_tool_records(2, mode="omit", content="declaration_only.py\n"),
    ]
    if raw_node2_limit:
        gate_turn_id = "turn-main-node2-limit"
        records.extend(
            [
                _record("source", "node2", gate_turn_id, "gate-source"),
                _record(
                    "action",
                    json.dumps(
                        {
                            "next_node": "node3",
                            "outcome": "reject_ignored_limit",
                            "rejection_ignored": True,
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    gate_turn_id,
                    "gate-action",
                ),
            ]
        )
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text("SECRET-provider transcript\n", encoding="utf-8")

    project_root = Path(__file__).resolve().parents[2]
    source_files = [
        {
            "path": path,
            "sha256": _sha256(project_root / Path(path)),
        }
        for path in sorted(_REQUIRED_EXPERIMENT_SOURCE_PATHS)
    ]
    protocol = {
        "schema_version": 1,
        "experiment_kind": EXPERIMENT_KIND,
        "source_snapshot": {
            "algorithm": "sha256(raw-bytes)",
            "file_count": len(source_files),
            "files": source_files,
            "tree_sha256": "fixture-source-tree",
        },
    }
    protocol_path = root / "protocol.json"
    _write_json(protocol_path, protocol)
    blind_key = {
        "schema_version": 1,
        "system_aliases": {system_name: "System A"},
        "items": [
            {
                "review_id": "0123456789abcdef",
                "run_id": "run-secret-0001",
                "system_name": system_name,
                "blind_system_alias": "System A",
            }
        ],
    }
    blind_key_path = root / "blind_key.json"
    _write_json(blind_key_path, blind_key)
    type_counts = dict(
        sorted(Counter(record["information_type"] for record in records).items())
    )
    capture = {
        "schema_version": 1,
        "experiment_kind": EXPERIMENT_KIND,
        "protocol_sha256": _sha256(protocol_path),
        "blind_key_file_sha256": _sha256(blind_key_path),
        "manifest": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
        },
        "systems": [
            {
                "system_name": system_name,
                "model_name": "SECRET-model-omega",
                "provider": "SECRET-provider",
            }
        ],
        "schedule": [{"run_id": "run-secret-0001"}],
        "coverage": {"planned_run_count": 1, "captured_run_count": 1},
        "captures": [
            {
                "run_id": "run-secret-0001",
                "case_id": case_id,
                "system_name": system_name,
                "manifest_question": manifest.questions[case_id],
                "evaluated_question": manifest.questions[case_id],
                "evaluated_turn_index": 0,
                "conversation_turns": [
                    {
                        "role": "user",
                        "content": manifest.questions[case_id],
                        "evaluate": True,
                    }
                ],
                "answer": "선언만 있고 집행 로직은 보이지 않습니다.",
                "completed": True,
                "error": None,
                "turn_id": "turn-main",
                "tool_call_count": 2,
                "node2_limit_exhausted": (
                    raw_node2_limit
                    if declared_node2_limit is None
                    else declared_node2_limit
                ),
                "node4_limit_exhausted": False,
                "raw_memory_artifact": {
                    "path": raw_path.relative_to(root).as_posix(),
                    "sha256": _sha256(raw_path),
                    "byte_count": raw_path.stat().st_size,
                    "event_count": len(records),
                    "information_type_counts": type_counts,
                },
                "transcript_artifact": {
                    "path": transcript_path.relative_to(root).as_posix(),
                    "sha256": _sha256(transcript_path),
                    "byte_count": transcript_path.stat().st_size,
                },
            }
        ],
    }
    capture_path = root / "capture.json"
    _write_json(capture_path, capture)

    artifact_entries = []
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        if not path.is_file() or path.name == ARTIFACT_MANIFEST_FILENAME:
            continue
        artifact_entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                "byte_count": path.stat().st_size,
            }
        )
    _write_json(
        root / ARTIFACT_MANIFEST_FILENAME,
        {
            "schema_version": 1,
            "algorithm": "sha256(raw-bytes)",
            "artifact_count": len(artifact_entries),
            "artifacts": artifact_entries,
        },
    )
    return {
        "system_name": system_name,
        "model_name": "SECRET-model-omega",
        "provider": "SECRET-provider",
        "raw_relative_path": raw_path.relative_to(root).as_posix(),
        "raw_sha256": _sha256(raw_path),
        "content": content,
    }


def test_review_bundle_reconstructs_a_without_identity_or_raw_join_keys(tmp_path):
    pack = tmp_path / "parent-pack"
    output = tmp_path / "review-bundle"
    secrets = _make_parent_pack(pack)
    parent_before = {
        path.relative_to(pack).as_posix(): _sha256(path)
        for path in pack.rglob("*")
        if path.is_file()
    }

    result = build_model_scale_review_bundle(pack, output_dir=output)

    assert {path.name for path in output.iterdir()} == {
        REVIEW_PACKET_FILENAME,
        REVIEWER_PROTOCOL_FILENAME,
        ARTIFACT_MANIFEST_FILENAME,
        CASE_MATERIAL_DIRECTORY,
        NORMALIZER_SOURCE_FILENAME,
    }
    assert (output / CASE_MATERIAL_DIRECTORY / "manifest.json").is_file()
    assert (
        output
        / CASE_MATERIAL_DIRECTORY
        / "project"
        / "declaration_only.py"
    ).is_file()
    packet = result["packet"]
    assert packet["automatic_answer_grading"] is False
    assert packet["item_count"] == 1
    assert len(packet["items_sha256"]) == 64
    item = packet["items"][0]
    assert item["review_id"] == "0123456789abcdef"
    assert item["blind_system_alias"] == "System A"
    observed = item["observed_execution_a"]
    assert observed["tool_call_count"] == 2
    assert [call["sequence"] for call in observed["tool_calls"]] == [1, 2]
    assert observed["tool_calls"][0]["path"] == "declaration_only.py"
    assert observed["tool_calls"][1]["retentions"][0]["mode"] == "omit"
    assert observed["fixture_memory"] == []
    assert len(item["downstream_public_a"]) == 1
    public = item["downstream_public_a"][0]
    assert public["tool_sequence"] == 1
    assert public["selected_character_count"] == len(secrets["content"])
    assert public["content"] == secrets["content"]
    assert public["content_sha256"] == hashlib.sha256(
        secrets["content"].encode("utf-8")
    ).hexdigest()

    parent_manifest_sha = _sha256(pack / ARTIFACT_MANIFEST_FILENAME)
    assert packet["provenance"]["parent_artifact_manifest_sha256"] == (
        parent_manifest_sha
    )
    derived_manifest = json.loads(
        (output / ARTIFACT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert derived_manifest["provenance"][
        "parent_artifact_manifest_sha256"
    ] == parent_manifest_sha
    assert derived_manifest["provenance"][
        "normalizer_source_sha256"
    ] == _sha256(output / NORMALIZER_SOURCE_FILENAME)
    assert packet["provenance"]["normalizer_source_sha256"] == _sha256(
        output / NORMALIZER_SOURCE_FILENAME
    )

    derived_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.rglob("*")
        if path.is_file()
    )
    for secret in (
        secrets["system_name"],
        secrets["model_name"],
        secrets["provider"],
        secrets["raw_relative_path"],
        secrets["raw_sha256"],
    ):
        assert secret not in derived_text

    parent_after = {
        path.relative_to(pack).as_posix(): _sha256(path)
        for path in pack.rglob("*")
        if path.is_file()
    }
    assert parent_after == parent_before


def test_review_bundle_fails_closed_when_public_content_is_not_exact_slice(
    tmp_path,
):
    pack = tmp_path / "malformed-parent-pack"
    _make_parent_pack(pack, malformed_result=True)

    with pytest.raises(ValueError, match="exact slice"):
        build_model_scale_review_bundle(
            pack,
            output_dir=tmp_path / "unused-output",
        )


def test_review_bundle_recomputes_gate_limit_from_raw_a(tmp_path):
    pack = tmp_path / "gate-mismatch-parent-pack"
    _make_parent_pack(
        pack,
        raw_node2_limit=True,
        declared_node2_limit=False,
    )

    with pytest.raises(ValueError, match="raw gate A"):
        build_model_scale_review_bundle(
            pack,
            output_dir=tmp_path / "unused-gate-output",
        )


def test_review_bundle_rejects_fixture_memory_not_in_manifest(tmp_path):
    pack = tmp_path / "unexpected-memory-parent-pack"
    _make_parent_pack(pack, unexpected_fixture_memory=True)

    with pytest.raises(ValueError, match="frozen manifest"):
        build_model_scale_review_bundle(
            pack,
            output_dir=tmp_path / "unused-memory-output",
        )


def test_retention_contract_rejects_long_full_and_wrong_chunk_boundary():
    raw_text = "x" * 2_001
    full_payload = {
        "arguments": {},
        "end": None,
        "mode": "full",
        "start": None,
        "tool_name": "list_python_files",
    }
    with pytest.raises(ValueError, match="긴 원문"):
        _validate_retention_contract(
            full_payload,
            raw_text,
            "full",
            None,
            None,
            recovery=False,
            label="test",
        )

    chunk_payload = {
        "arguments": {"path": "long.py"},
        "chunk_id": "chunk-0001",
        "end": 1_999,
        "mode": "chunk",
        "start": 0,
        "tool_name": "read_python_file",
    }
    with pytest.raises(ValueError, match="결정론적 경계"):
        _validate_retention_contract(
            chunk_payload,
            raw_text,
            "chunk",
            0,
            1_999,
            recovery=False,
            label="test",
        )


def test_retention_contract_rejects_recovery_omit_and_wrong_key_set():
    recovery_omit = {
        "arguments": {},
        "candidate_number": 1,
        "end": None,
        "mode": "omit",
        "previous_mode": "omit",
        "start": None,
        "tool_name": "list_python_files",
    }
    with pytest.raises(ValueError, match="recovery 계약"):
        _validate_retention_contract(
            recovery_omit,
            "short",
            "omit",
            None,
            None,
            recovery=True,
            label="test",
        )

    missing_start = {
        "arguments": {},
        "end": None,
        "mode": "full",
        "tool_name": "list_python_files",
    }
    with pytest.raises(ValueError, match="key 집합"):
        _validate_retention_contract(
            missing_start,
            "short",
            "full",
            None,
            None,
            recovery=False,
            label="test",
        )


def test_review_bundle_rejects_wrong_external_parent_pin(tmp_path):
    pack = tmp_path / "parent-pin-pack"
    _make_parent_pack(pack)

    with pytest.raises(ValueError, match="외부에 고정"):
        build_model_scale_review_bundle(
            pack,
            output_dir=tmp_path / "unused-pin-output",
            expected_parent_manifest_sha256="0" * 64,
        )


def test_review_bundle_verifier_detects_tampering(tmp_path):
    pack = tmp_path / "verify-parent-pack"
    output = tmp_path / "verified-review-bundle"
    _make_parent_pack(pack)
    build_model_scale_review_bundle(pack, output_dir=output)

    verified = verify_model_scale_review_bundle(output)
    assert verified["item_count"] == 1
    assert verified["artifact_count"] >= 3

    protocol_path = output / REVIEWER_PROTOCOL_FILENAME
    protocol_path.write_text(
        protocol_path.read_text(encoding="utf-8") + "tampered\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hash/size"):
        verify_model_scale_review_bundle(output)
