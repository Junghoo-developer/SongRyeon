"""Integrity tests for blind ARM-consumption score validation and locking."""

from __future__ import annotations

import hashlib
import json

import pytest

import evals.mechanism_score_verify as score_verify
from evals.mechanism_blind import BUNDLE_ID
from evals.mechanism_packets import canonical_json_sha256


def _json_bytes(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path, value):
    path.write_bytes(_json_bytes(value))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _score_row(blind_id, polarity):
    return {
        "blind_id": blind_id,
        "direct_answer": 1,
        "answer_complete": 1,
        "unsupported_atomic_claim_count": 0,
        "no_unsupported_claims": 1,
        "evidence_laundering": 0 if polarity == "negative" else None,
        "negative_correction": 1 if polarity == "negative" else None,
        "positive_recognized": 1 if polarity == "positive" else None,
        "semantic_grounded_success": 1,
        "notes": "blind rubric score",
    }


def _make_bundle(tmp_path):
    root = tmp_path / "blind-bundle"
    root.mkdir(parents=True)
    rubric_sha256 = "a" * 64
    packet_artifacts = []
    rows_by_chunk = []

    for chunk_index in range(1, 4):
        items = []
        rows = []
        for offset in range(180):
            sequence = (chunk_index - 1) * 180 + offset + 1
            blind_id = f"blind-{sequence:064x}"
            polarity = "negative" if sequence % 2 else "positive"
            items.append(
                {
                    "blind_id": blind_id,
                    "question": f"blind question {sequence}",
                    "answer": f"blind answer {sequence}",
                    "error": None,
                    "completed": True,
                    "family": "declaration_enforcement",
                    "polarity": polarity,
                    "expected_a_facts": [],
                    "supported_claims": [],
                }
            )
            rows.append(_score_row(blind_id, polarity))
        core = {
            "schema_version": 1,
            "bundle_id": BUNDLE_ID,
            "packet_status": "unscored_condition_metadata_masked",
            "publishable": False,
            "chunk_index": chunk_index,
            "chunk_count": 3,
            "item_count": 180,
            "scoring_rubric_sha256": rubric_sha256,
            "items": items,
        }
        packet = {**core, "packet_sha256": canonical_json_sha256(core)}
        packet_path = root / f"blind_packet_{chunk_index:03d}.json"
        _write_json(packet_path, packet)
        packet_artifacts.append(
            {
                "path": packet_path.name,
                "byte_count": packet_path.stat().st_size,
                "file_sha256": _sha256(packet_path),
                "packet_sha256": packet["packet_sha256"],
            }
        )
        rows_by_chunk.append(rows)

    provenance_core = {
        "schema_version": 1,
        "bundle_id": BUNDLE_ID,
        "study_status": "unscored_condition_metadata_masked",
        "publishable": False,
        "warning": "keep the private key sealed until scores are locked",
        "capture": {},
        "evidence_packets": {},
        "run_plan": {},
        "derivation_source": {},
        "manifest": {},
        "scoring_rubric": {"file_sha256": rubric_sha256},
        "blinding": {},
        "chunk_count": 3,
        "chunk_size": 180,
        "item_count": 540,
        "completed_item_count": 540,
        "incomplete_item_count": 0,
        "blind_packet_files": packet_artifacts,
        "blind_key_file": {"sealed": True},
    }
    provenance = {
        **provenance_core,
        "provenance_sha256": canonical_json_sha256(provenance_core),
    }
    _write_json(root / "provenance.json", provenance)

    for chunk_index, rows in enumerate(rows_by_chunk, start=1):
        _write_json(
            root / f"scores-chunk-{chunk_index}.json",
            {
                "schema_version": 1,
                "bundle_id": BUNDLE_ID,
                "chunk_number": chunk_index,
                "scorer_type": "blind_ai_preliminary",
                "item_count": 180,
                "items": rows,
            },
        )

    # Deliberately invalid JSON: successful validation demonstrates that the
    # public score verifier never opens or parses the private blind key.
    (root / "blind_key.json").write_bytes(b"this must remain sealed")
    return root


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_validates_540_scores_and_exclusively_locks_all_file_hashes(
    tmp_path,
    monkeypatch,
):
    root = _make_bundle(tmp_path)
    summary = score_verify.validate_mechanism_score_bundle(root)
    assert summary["validated_item_count"] == 540
    assert summary["validated_unique_blind_id_count"] == 540
    assert summary["semantic_grounded_success_count_before_unblinding"] == 540

    original_validate = score_verify.validate_mechanism_score_bundle
    validation_calls = []

    def counted_validate(bundle_dir):
        validation_calls.append(bundle_dir)
        return original_validate(bundle_dir)

    monkeypatch.setattr(
        score_verify,
        "validate_mechanism_score_bundle",
        counted_validate,
    )
    lock_path, locked = score_verify.write_mechanism_score_lock(root)
    assert len(validation_calls) == 3  # initial, immediately before, and after write
    assert locked["scoring_status"] == "locked_before_unblinding"
    assert not list(root.glob(".score_lock.json.*.tmp"))

    lock = _read_json(lock_path)
    assert set(lock) == score_verify._LOCK_KEYS
    assert lock["packet_id"] == BUNDLE_ID
    assert lock["scorer_type"] == "blind_ai_preliminary"
    assert lock["scoring_status"] == "locked_before_unblinding"
    assert lock["blind_packet_sha256"] == {
        filename: _sha256(root / filename)
        for filename in score_verify.PACKET_FILENAMES
    }
    assert lock["provenance_sha256"] == _sha256(root / "provenance.json")
    assert lock["score_file_sha256"] == {
        filename: _sha256(root / filename)
        for filename in score_verify.SCORE_FILENAMES
    }


def test_rejects_semantic_success_that_disagrees_with_components(tmp_path):
    root = _make_bundle(tmp_path)
    path = root / "scores-chunk-1.json"
    scores = _read_json(path)
    scores["items"][0]["semantic_grounded_success"] = 0
    _write_json(path, scores)

    with pytest.raises(ValueError, match="component scores"):
        score_verify.validate_mechanism_score_bundle(root)


def test_rejects_wrong_polarity_nulls_and_non_integer_binary(tmp_path):
    root = _make_bundle(tmp_path)
    path = root / "scores-chunk-1.json"
    scores = _read_json(path)
    scores["items"][0]["evidence_laundering"] = None
    _write_json(path, scores)
    with pytest.raises(ValueError, match="negative-polarity scores"):
        score_verify.validate_mechanism_score_bundle(root)

    root = _make_bundle(tmp_path / "second")
    path = root / "scores-chunk-1.json"
    scores = _read_json(path)
    scores["items"][0]["direct_answer"] = True
    _write_json(path, scores)
    with pytest.raises(ValueError, match="must be 0 or 1"):
        score_verify.validate_mechanism_score_bundle(root)


def test_rejects_recursive_condition_seed_or_key_metadata(tmp_path):
    root = _make_bundle(tmp_path)
    path = root / "scores-chunk-1.json"
    scores = _read_json(path)
    scores["items"][0]["notes"] = {
        "audit": {
            "seed": 42,
            "case_id": "must-not-leak",
            "blindKey": "must-not-leak",
        }
    }
    _write_json(path, scores)

    with pytest.raises(ValueError, match="condition/seed/key metadata"):
        score_verify.validate_mechanism_score_bundle(root)


def test_rejects_score_schema_drift_and_count_flag_inconsistency(tmp_path):
    root = _make_bundle(tmp_path)
    path = root / "scores-chunk-1.json"
    scores = _read_json(path)
    scores["reviewer"] = "unexpected"
    _write_json(path, scores)
    with pytest.raises(ValueError, match="wrong fields"):
        score_verify.validate_mechanism_score_bundle(root)

    root = _make_bundle(tmp_path / "second")
    path = root / "scores-chunk-1.json"
    scores = _read_json(path)
    scores["items"][0]["unsupported_atomic_claim_count"] = 2
    _write_json(path, scores)
    with pytest.raises(ValueError, match="disagrees with unsupported_atomic_claim_count"):
        score_verify.validate_mechanism_score_bundle(root)


def test_rejects_cross_chunk_id_reordering_or_duplicate(tmp_path):
    root = _make_bundle(tmp_path)
    first_scores = _read_json(root / "scores-chunk-1.json")
    second_path = root / "scores-chunk-2.json"
    second_scores = _read_json(second_path)
    second_scores["items"][0]["blind_id"] = first_scores["items"][0]["blind_id"]
    _write_json(second_path, second_scores)

    with pytest.raises(ValueError, match="chunk reconstruction"):
        score_verify.validate_mechanism_score_bundle(root)


def test_rejects_packet_or_provenance_tampering(tmp_path):
    root = _make_bundle(tmp_path)
    packet_path = root / "blind_packet_001.json"
    packet = _read_json(packet_path)
    packet["items"][0]["question"] = "tampered"
    _write_json(packet_path, packet)
    with pytest.raises(ValueError, match="packet_sha256"):
        score_verify.validate_mechanism_score_bundle(root)

    root = _make_bundle(tmp_path / "second")
    provenance_path = root / "provenance.json"
    provenance = _read_json(provenance_path)
    provenance["warning"] = "tampered"
    _write_json(provenance_path, provenance)
    with pytest.raises(ValueError, match="provenance_sha256"):
        score_verify.validate_mechanism_score_bundle(root)


def test_writer_refuses_to_overwrite_existing_lock(tmp_path):
    root = _make_bundle(tmp_path)
    lock_path = root / "score_lock.json"
    lock_path.write_bytes(b"preserve this lock")

    with pytest.raises(ValueError, match="refusing to overwrite"):
        score_verify.write_mechanism_score_lock(root)
    assert lock_path.read_bytes() == b"preserve this lock"


def test_cli_validates_and_locks_a_bundle_directory(tmp_path, capsys):
    root = _make_bundle(tmp_path)
    assert score_verify.main([str(root), "--validate-only"]) == 0
    assert not (root / "score_lock.json").exists()
    assert score_verify.main([str(root)]) == 0
    assert (root / "score_lock.json").is_file()
    output = capsys.readouterr().out
    assert "locked_before_unblinding" in output
