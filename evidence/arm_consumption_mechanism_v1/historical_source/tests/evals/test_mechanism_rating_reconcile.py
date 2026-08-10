"""Tests for deterministic two-rater blind score reconciliation."""

from __future__ import annotations

import hashlib
import json

import pytest

import evals.mechanism_rating_reconcile as reconcile
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


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _score_row(blind_id, polarity, notes):
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
        "notes": notes,
    }


def _make_bundle(tmp_path, disagreement_sequences=(1, 181, 540)):
    root = tmp_path / "rating-bundle"
    root.mkdir(parents=True)
    disagreement_sequences = set(disagreement_sequences)
    rating_a_chunks = []
    rating_b_chunks = []

    for chunk_index in range(1, 4):
        public_items = []
        rating_a_rows = []
        rating_b_rows = []
        for offset in range(180):
            sequence = (chunk_index - 1) * 180 + offset + 1
            blind_id = f"blind-{sequence:064x}"
            polarity = "negative" if sequence % 2 else "positive"
            public_items.append(
                {
                    "blind_id": blind_id,
                    "question": f"public question {sequence}",
                    "answer": f"public answer {sequence}",
                    "error": None,
                    "completed": True,
                    "family": "declaration_enforcement",
                    "polarity": polarity,
                    "expected_a_facts": [],
                    "supported_claims": [],
                }
            )
            rating_a = _score_row(blind_id, polarity, f"rater A {sequence}")
            rating_b = _score_row(blind_id, polarity, f"rater B {sequence}")
            if sequence in disagreement_sequences:
                rating_b["direct_answer"] = 0
                rating_b["semantic_grounded_success"] = 0
            rating_a_rows.append(rating_a)
            rating_b_rows.append(rating_b)

        packet_core = {
            "schema_version": 1,
            "bundle_id": BUNDLE_ID,
            "packet_status": "unscored_condition_metadata_masked",
            "publishable": False,
            "chunk_index": chunk_index,
            "chunk_count": 3,
            "item_count": 180,
            "scoring_rubric_sha256": "a" * 64,
            "items": public_items,
        }
        _write_json(
            root / f"blind_packet_{chunk_index:03d}.json",
            {
                **packet_core,
                "packet_sha256": canonical_json_sha256(packet_core),
            },
        )
        rating_a_chunks.append(rating_a_rows)
        rating_b_chunks.append(rating_b_rows)

    for rater, chunks in (("a", rating_a_chunks), ("b", rating_b_chunks)):
        for chunk_index, rows in enumerate(chunks, start=1):
            _write_json(
                root / f"ratings-{rater}-chunk-{chunk_index}.json",
                {
                    "schema_version": 1,
                    "bundle_id": BUNDLE_ID,
                    "chunk_number": chunk_index,
                    "scorer_type": (
                        "blind_ai_preliminary"
                        if rater == "a"
                        else "blind_ai_preliminary_b"
                    ),
                    "item_count": 180,
                    "items": rows,
                },
            )

    # This file is intentionally not JSON.  Reconciliation must never open it.
    (root / "blind_key.json").write_bytes(b"sealed private mapping")
    return root


def _write_adjudications(root, *, drop_last=False):
    packet = _read_json(root / "adjudication_packet.json")
    rows = [item["rating_b"] for item in packet["items"]]
    if drop_last:
        rows = rows[:-1]
    document = {
        "schema_version": 1,
        "bundle_id": BUNDLE_ID,
        "adjudication_packet_sha256": packet["adjudication_packet_sha256"],
        "item_count": len(rows),
        "items": rows,
    }
    _write_json(root / "adjudications.json", document)
    return document


def test_validates_two_540_sets_and_ignores_notes_only_differences(tmp_path):
    root = _make_bundle(tmp_path)
    summary = reconcile.validate_mechanism_ratings(root)

    assert summary["validated_item_count_per_rater"] == 540
    assert summary["validated_unique_blind_id_count_per_rater"] == 540
    assert summary["agreement_count"] == 537
    assert summary["disagreement_count"] == 3
    assert summary["rater_a_semantic_grounded_success_count"] == 540
    assert summary["rater_b_semantic_grounded_success_count"] == 537


def test_atomically_emits_disagreement_packet_with_rows_items_and_hashes(tmp_path):
    root = _make_bundle(tmp_path)
    path, summary = reconcile.write_mechanism_adjudication_packet(root)
    packet = _read_json(path)

    assert summary["disagreement_count"] == 3
    assert packet["status"] == "awaiting_blind_adjudication"
    assert packet["item_count"] == 3
    assert [item["blind_id"] for item in packet["items"]] == [
        f"blind-{sequence:064x}" for sequence in (1, 181, 540)
    ]
    for item in packet["items"]:
        assert item["blind_item"]["blind_id"] == item["blind_id"]
        assert item["rating_a"]["blind_id"] == item["blind_id"]
        assert item["rating_b"]["blind_id"] == item["blind_id"]
        assert item["blind_item_sha256"] == canonical_json_sha256(
            item["blind_item"]
        )
        assert item["rating_a_sha256"] == canonical_json_sha256(item["rating_a"])
        assert item["rating_b_sha256"] == canonical_json_sha256(item["rating_b"])
        assert item["differing_fields"] == [
            "direct_answer",
            "semantic_grounded_success",
        ]
    assert packet["blind_packet_sha256"] == {
        filename: _sha256(root / filename)
        for filename in score_verify.PACKET_FILENAMES
    }
    assert not reconcile._private_metadata_paths(packet)
    assert not list(root.glob(".adjudication_packet.json.*.tmp"))


def test_rejects_recursive_private_metadata_and_wrong_bundle_envelope(tmp_path):
    root = _make_bundle(tmp_path)
    path = root / "ratings-a-chunk-1.json"
    ratings = _read_json(path)
    ratings["items"][0]["notes"] = {
        "audit": {"condition": "hidden", "modelName": "hidden"}
    }
    _write_json(path, ratings)
    with pytest.raises(ValueError, match="condition/seed/model/key metadata"):
        reconcile.validate_mechanism_ratings(root)

    root = _make_bundle(tmp_path / "second")
    path = root / "ratings-b-chunk-2.json"
    ratings = _read_json(path)
    ratings["bundle_id"] = "wrong"
    _write_json(path, ratings)
    with pytest.raises(ValueError, match="bundle_id"):
        reconcile.validate_mechanism_ratings(root)


@pytest.mark.parametrize(
    ("rater", "wrong_scorer_type", "required_scorer_type"),
    (
        ("a", "blind_ai_preliminary_b", "blind_ai_preliminary"),
        ("b", "blind_ai_preliminary", "blind_ai_preliminary_b"),
    ),
)
def test_requires_exact_rater_specific_scorer_type(
    tmp_path,
    rater,
    wrong_scorer_type,
    required_scorer_type,
):
    root = _make_bundle(tmp_path)
    path = root / f"ratings-{rater}-chunk-1.json"
    ratings = _read_json(path)
    ratings["scorer_type"] = wrong_scorer_type
    _write_json(path, ratings)

    with pytest.raises(ValueError, match=f"must be {required_scorer_type}"):
        reconcile.validate_mechanism_ratings(root)


def test_requires_adjudications_to_exactly_cover_disagreements(tmp_path):
    root = _make_bundle(tmp_path)
    reconcile.write_mechanism_adjudication_packet(root)
    _write_adjudications(root, drop_last=True)

    with pytest.raises(ValueError, match="disagreement count"):
        reconcile.finalize_mechanism_ratings(root)
    assert not any((root / name).exists() for name in reconcile.FINAL_SCORE_FILENAMES)


def test_rejects_private_metadata_in_adjudications(tmp_path):
    root = _make_bundle(tmp_path)
    reconcile.write_mechanism_adjudication_packet(root)
    adjudications = _write_adjudications(root)
    adjudications["items"][0]["notes"] = {
        "blindKey": "hidden",
        "seed": 42,
    }
    _write_json(root / "adjudications.json", adjudications)

    with pytest.raises(ValueError, match="condition/seed/model/key metadata"):
        reconcile.finalize_mechanism_ratings(root)


def test_finalizes_packet_order_with_a_agreements_and_adjudicated_disagreements(
    tmp_path,
):
    root = _make_bundle(tmp_path)
    reconcile.write_mechanism_adjudication_packet(root)
    _write_adjudications(root)

    provenance_path, summary = reconcile.finalize_mechanism_ratings(root)
    assert summary["status"] == "finalized_before_unblinding"
    assert summary["agreement_count"] == 537
    assert summary["adjudicated_item_count"] == 3
    assert summary["semantic_grounded_success_count"] == 537

    final_chunk_1 = _read_json(root / "scores-chunk-1.json")
    rating_a_chunk_1 = _read_json(root / "ratings-a-chunk-1.json")
    rating_b_chunk_1 = _read_json(root / "ratings-b-chunk-1.json")
    assert final_chunk_1["bundle_id"] == BUNDLE_ID
    assert final_chunk_1["items"][0] == rating_b_chunk_1["items"][0]
    assert final_chunk_1["items"][1] == rating_a_chunk_1["items"][1]

    provenance = _read_json(provenance_path)
    assert provenance["status"] == "finalized_before_unblinding"
    assert provenance["adjudication_packet_file_sha256"] == _sha256(
        root / "adjudication_packet.json"
    )
    assert provenance["adjudications_file_sha256"] == _sha256(
        root / "adjudications.json"
    )
    assert provenance["final_score_file_sha256"] == {
        filename: _sha256(root / filename)
        for filename in reconcile.FINAL_SCORE_FILENAMES
    }
    assert reconcile.validate_mechanism_rating_finalization(root)["status"] == (
        "finalized_before_unblinding"
    )


def test_refuses_to_overwrite_adjudication_or_final_outputs(tmp_path):
    root = _make_bundle(tmp_path)
    adjudication_path = root / "adjudication_packet.json"
    adjudication_path.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        reconcile.write_mechanism_adjudication_packet(root)
    assert adjudication_path.read_bytes() == b"preserve"

    root = _make_bundle(tmp_path / "second")
    reconcile.write_mechanism_adjudication_packet(root)
    _write_adjudications(root)
    final_path = root / "scores-chunk-2.json"
    final_path.write_bytes(b"preserve final")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        reconcile.finalize_mechanism_ratings(root)
    assert final_path.read_bytes() == b"preserve final"
    assert not (root / "rating_provenance.json").exists()


def test_detects_adjudication_packet_tampering(tmp_path):
    root = _make_bundle(tmp_path)
    path, _summary = reconcile.write_mechanism_adjudication_packet(root)
    packet = _read_json(path)
    packet["items"][0]["rating_a"]["notes"] = "tampered"
    _write_json(path, packet)

    with pytest.raises(ValueError, match="does not match current"):
        reconcile.validate_mechanism_adjudication_packet(root)


def test_cli_prepare_and_finalize(tmp_path, capsys):
    root = _make_bundle(tmp_path)
    assert reconcile.main(["prepare", str(root)]) == 0
    _write_adjudications(root)
    assert reconcile.main(["finalize", str(root)]) == 0
    assert (root / "rating_provenance.json").is_file()
    assert "finalized_before_unblinding" in capsys.readouterr().out
