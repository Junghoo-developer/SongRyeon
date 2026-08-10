"""Mechanism capture의 condition-metadata-masked 파생 계약을 검사한다."""

from collections import Counter
import hashlib
import json

import pytest

import evals.mechanism_blind as mechanism_blind
from evals.mechanism_blind import (
    BLIND_SOURCE_CONDITIONS,
    EVIDENCE_ENFORCED,
    STYLE_PLACEBO_ENFORCED,
    validate_mechanism_blind_bundle,
    write_mechanism_blind_bundle,
)
from evals.mechanism_capture import (
    ANSWER_CONDITIONS,
    AR_CONSUMER_RULE,
    EVIDENCE_REVIEWER,
    MECHANISM_SEEDS,
    STYLE_PLACEBO_REVIEWER,
)
from evals.runner import load_manifest


def _json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _make_verified_capture(tmp_path, monkeypatch):
    manifest = load_manifest(mechanism_blind.DEFAULT_SOURCE_MANIFEST_PATH)
    root = tmp_path / "capture"
    artifacts = []

    for seed in MECHANISM_SEEDS:
        for packet_index, case in enumerate(manifest.cases):
            answer_calls = {
                condition: {
                    "status": "valid",
                    "output": {
                        "answer": (
                            f"{case.case_id}에 대한 합성 답변 "
                            f"{packet_index + 1}-{ANSWER_CONDITIONS.index(condition) + 1}"
                        )
                    },
                }
                for condition in ANSWER_CONDITIONS
            }
            consumer_answer = answer_calls[AR_CONSUMER_RULE]["output"]["answer"]
            style_failed = seed == MECHANISM_SEEDS[0] and packet_index == 0
            reviewer_calls = {
                STYLE_PLACEBO_REVIEWER: (
                    {"status": "invalid_exhausted", "output": None}
                    if style_failed
                    else {
                        "status": "valid",
                        "output": {
                            "verdict": "permit",
                            "reason": "합성",
                            "revised_answer": consumer_answer,
                        },
                    }
                ),
                EVIDENCE_REVIEWER: {
                    "status": "valid",
                    "output": {
                        "verdict": "permit",
                        "reason": "합성",
                        "revised_answer": consumer_answer,
                    },
                },
            }
            unit = {
                "case_id": case.case_id,
                "packet_index": packet_index,
                "seed": seed,
                "answer_calls": answer_calls,
                "reviewer_calls": reviewer_calls,
                "derived_outputs": {
                    "shadow": consumer_answer,
                    STYLE_PLACEBO_ENFORCED: (
                        None if style_failed else consumer_answer
                    ),
                    EVIDENCE_ENFORCED: consumer_answer,
                },
            }
            relative = (
                f"raw/seed-{seed}/{packet_index + 1:03d}-{case.case_id}.json"
            )
            raw_path = root / relative
            raw = _json_bytes(unit)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            artifacts.append(
                {
                    "case_id": case.case_id,
                    "packet_index": packet_index,
                    "seed": seed,
                    "path": relative,
                    "byte_count": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )

    capture_path = root / "capture.json"
    _write_json(
        capture_path,
        {
            "capture_status": "complete",
            "planned_unit_count": 90,
            "completed_unit_count": 90,
            "raw_artifacts": artifacts,
        },
    )
    packet_path = tmp_path / "evidence_packets.json"
    _write_json(packet_path, {"synthetic": True})

    verification_calls = []

    def fake_verify(capture, packets, **kwargs):
        verification_calls.append((capture, packets, kwargs))
        return {
            "unit_count": 90,
            "packet_set_sha256": "a" * 64,
        }

    monkeypatch.setattr(mechanism_blind, "verify_capture", fake_verify)
    return capture_path, packet_path, verification_calls


def _read_bundle_packets(output_dir):
    return [
        json.loads(
            (output_dir / f"blind_packet_{index:03d}.json").read_text(
                encoding="utf-8"
            )
        )
        for index in range(1, 4)
    ]


def test_blind_bundle_is_540_item_bijection_with_one_generic_itt_failure(
    tmp_path,
    monkeypatch,
):
    capture_path, packet_path, verification_calls = _make_verified_capture(
        tmp_path,
        monkeypatch,
    )
    output_dir = tmp_path / "blind"

    saved_dir, summary = write_mechanism_blind_bundle(
        capture_path=capture_path,
        packet_path=packet_path,
        output_dir=output_dir,
        blinding_secret=b"fixed blind test secret".ljust(32, b"!"),
    )

    assert saved_dir == output_dir.resolve()
    assert summary["item_count"] == 540
    assert summary["completed_item_count"] == 539
    assert summary["incomplete_item_count"] == 1
    assert summary["chunk_count"] == 3
    assert summary["chunk_size"] == 180
    assert len(verification_calls) == 2  # 생성 전 + 저장 뒤 TOCTOU 재검증

    packets = _read_bundle_packets(output_dir)
    assert [packet["item_count"] for packet in packets] == [180, 180, 180]
    items = [item for packet in packets for item in packet["items"]]
    assert len({item["blind_id"] for item in items}) == 540
    assert Counter(item["polarity"] for item in items) == {
        "negative": 270,
        "positive": 270,
    }
    assert Counter(item["family"] for item in items) == {
        "declaration_enforcement": 108,
        "import_invocation": 108,
        "documentation_runtime": 108,
        "action_report": 108,
        "attribution_provenance": 108,
    }
    incomplete = [item for item in items if not item["completed"]]
    assert len(incomplete) == 1
    assert incomplete[0]["answer"] is None
    assert incomplete[0]["error"] == "output_unavailable"
    public_text = json.dumps(packets, ensure_ascii=False, sort_keys=True)
    assert "invalid_exhausted" not in public_text
    for forbidden_key in (
        '"condition"',
        '"seed"',
        '"order"',
        '"system"',
        '"case_id"',
        '"raw_artifact_sha256"',
    ):
        assert forbidden_key not in public_text

    key = json.loads((output_dir / "blind_key.json").read_text(encoding="utf-8"))
    assert len(key["items"]) == 540
    assert Counter(item["condition"] for item in key["items"]) == {
        condition: 90 for condition in BLIND_SOURCE_CONDITIONS
    }
    assert "shadow" not in {item["condition"] for item in key["items"]}
    assert {item["blind_id"] for item in key["items"]} == {
        item["blind_id"] for item in items
    }
    assert (output_dir / "SCORING_RUBRIC.md").read_bytes() == (
        mechanism_blind.DEFAULT_SCORING_RUBRIC_PATH.read_bytes()
    )


def test_validator_rejects_blind_packet_tampering(tmp_path, monkeypatch):
    capture_path, packet_path, _calls = _make_verified_capture(
        tmp_path,
        monkeypatch,
    )
    output_dir = tmp_path / "blind"
    write_mechanism_blind_bundle(
        capture_path=capture_path,
        packet_path=packet_path,
        output_dir=output_dir,
        blinding_secret=b"second fixed secret".ljust(32, b"!"),
    )
    packet_path_to_tamper = output_dir / "blind_packet_001.json"
    packet = json.loads(packet_path_to_tamper.read_text(encoding="utf-8"))
    packet["items"][0]["answer"] += " 변조"
    _write_json(packet_path_to_tamper, packet)

    with pytest.raises(ValueError, match="self-hash"):
        validate_mechanism_blind_bundle(
            output_dir,
            capture_path=capture_path,
            packet_path=packet_path,
        )


def test_writer_refuses_nonempty_output_directory(tmp_path, monkeypatch):
    capture_path, packet_path, _calls = _make_verified_capture(
        tmp_path,
        monkeypatch,
    )
    output_dir = tmp_path / "blind"
    output_dir.mkdir()
    (output_dir / "keep.txt").write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(ValueError, match="덮어쓰지"):
        write_mechanism_blind_bundle(
            capture_path=capture_path,
            packet_path=packet_path,
            output_dir=output_dir,
            blinding_secret=b"third fixed secret".ljust(32, b"!"),
        )
    assert (output_dir / "keep.txt").read_text(encoding="utf-8") == "do not overwrite"
