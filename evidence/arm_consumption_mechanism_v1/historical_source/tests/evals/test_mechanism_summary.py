"""Mechanism summary가 lock, 맹검 해제, case-cluster 분석을 지키는지 검사한다."""

import hashlib
import json
from pathlib import Path

import pytest

from evals.mechanism_capture import ANSWER_CONDITIONS, REVIEWERS
from evals.mechanism_summary import (
    EVIDENCE_ENFORCED,
    SCORE_CONDITIONS,
    STYLE_PLACEBO_ENFORCED,
    main,
    summarize_mechanism,
)


SEEDS = (42, 43, 44)
CASES = ("case-negative", "case-positive")
SECRET = "MODEL-ANSWER-MUST-NOT-APPEAR-IN-SUMMARY"


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _call(*, reviewer=False, verdict="permit", duration=1_000_000):
    output = (
        {
            "verdict": verdict,
            "reason": SECRET,
            "revised_answer": SECRET,
        }
        if reviewer
        else {"answer": SECRET}
    )
    return {
        "status": "valid",
        "base_prompt_sha256": "a" * 64,
        "masked_prompt_sha256": "b" * 64,
        "attempts": [
            {
                "attempt": 1,
                "status": "valid",
                "system_prompt": SECRET,
                "user_prompt": SECRET,
                "raw_response": SECRET,
                "thinking": SECRET,
                "metrics": {
                    "total_duration": duration,
                    "prompt_eval_count": 10,
                    "eval_count": 5,
                },
            }
        ],
        "output": output,
    }


def _build_capture(tmp_path: Path):
    root = tmp_path / "capture"
    artifacts = []
    packet_index = 0
    for case_id in CASES:
        for seed in SEEDS:
            answer_calls = {condition: _call() for condition in ANSWER_CONDITIONS}
            reviewer_calls = {
                REVIEWERS[0]: _call(reviewer=True, verdict="permit", duration=2_000_000),
                REVIEWERS[1]: _call(reviewer=True, verdict="reject", duration=2_000_000),
            }
            unit = {
                "schema_version": 1,
                "experiment_id": "songryeon-arm-consumption-mechanism-exploratory-v1",
                "case_id": case_id,
                "packet_sha256": "c" * 64,
                "packet_index": packet_index,
                "seed": seed,
                "answer_condition_order": list(ANSWER_CONDITIONS),
                "reviewer_order": list(REVIEWERS),
                "answer_calls": answer_calls,
                "reviewer_calls": reviewer_calls,
                "derived_outputs": {
                    "shadow": SECRET,
                    "style_placebo_enforced": SECRET,
                    "evidence_enforced": SECRET,
                },
            }
            raw_path = root / "raw" / f"{packet_index:03d}.json"
            _write_json(raw_path, unit)
            payload = raw_path.read_bytes()
            artifacts.append(
                {
                    "case_id": case_id,
                    "packet_index": packet_index,
                    "seed": seed,
                    "path": raw_path.relative_to(root).as_posix(),
                    "byte_count": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
            packet_index += 1

    capture = {
        "schema_version": 1,
        "capture_status": "complete",
        "review_status": "unreviewed",
        "publishable": False,
        "configuration": {
            "experiment_id": "songryeon-arm-consumption-mechanism-exploratory-v1",
            "answer_conditions": list(ANSWER_CONDITIONS),
            "reviewers": list(REVIEWERS),
        },
        "raw_artifacts": artifacts,
    }
    return _write_json(root / "capture.json", capture)


def _build_manifest(tmp_path: Path):
    return _write_json(
        tmp_path / "manifest.json",
        {
            "schema_version": 1,
            "cases": [
                {
                    "case_id": "case-negative",
                    "tags": [
                        "evidence_laundering",
                        "declaration_enforcement",
                        "negative_control",
                    ],
                },
                {
                    "case_id": "case-positive",
                    "tags": [
                        "evidence_laundering",
                        "declaration_enforcement",
                        "positive_control",
                    ],
                },
            ],
        },
    )


def _success(case_id: str, seed: int, condition: str) -> int:
    if case_id == "case-negative":
        return int(condition in {"ar-label-only", EVIDENCE_ENFORCED})
    if condition == EVIDENCE_ENFORCED and seed == 44:
        return 0
    return 1


def _score_row(blind_id: str, polarity: str, success: int):
    common = {
        "blind_id": blind_id,
        "direct_answer": 1,
        "answer_complete": 1,
        "unsupported_atomic_claim_count": 0,
        "no_unsupported_claims": 1,
        "semantic_grounded_success": success,
        "notes": "locked score",
    }
    if polarity == "negative":
        common.update(
            {
                "evidence_laundering": 0 if success else 1,
                "negative_correction": 1 if success else 0,
                "positive_recognized": None,
            }
        )
    else:
        common.update(
            {
                "evidence_laundering": None,
                "negative_correction": None,
                "positive_recognized": success,
            }
        )
    return common


def _build_locked_scores(tmp_path: Path):
    blind_items = []
    rows = []
    counter = 1
    for case_id in CASES:
        polarity = "negative" if case_id == "case-negative" else "positive"
        for seed in SEEDS:
            for condition in SCORE_CONDITIONS:
                blind_id = f"BLIND-{counter:04d}"
                blind_items.append(
                    {
                        "blind_id": blind_id,
                        "case_id": case_id,
                        "seed": seed,
                        # 실제 mechanism blind bundle도 enforced 이름에 underscore를 쓴다.
                        "condition": (
                            condition.replace("-", "_")
                            if condition in {STYLE_PLACEBO_ENFORCED, EVIDENCE_ENFORCED}
                            else condition
                        ),
                    }
                )
                rows.append(_score_row(blind_id, polarity, _success(case_id, seed, condition)))
                counter += 1

    blind_key_path = _write_json(
        tmp_path / "blind_key.json",
        {"schema_version": 1, "items": blind_items},
    )
    score_path = _write_json(
        tmp_path / "scores.json",
        {
            "schema_version": 1,
            "item_count": len(rows),
            "items": rows,
        },
    )
    score_digest = hashlib.sha256(score_path.read_bytes()).hexdigest()
    lock_path = _write_json(
        tmp_path / "score_lock.json",
        {
            "schema_version": 1,
            "scoring_status": "locked_before_unblinding",
            "blind_key_sha256": hashlib.sha256(blind_key_path.read_bytes()).hexdigest(),
            "score_file_sha256": {score_path.name: score_digest},
            "validated_item_count": len(rows),
            "validated_unique_blind_id_count": len(rows),
            "semantic_grounded_success_count_before_unblinding": sum(
                row["semantic_grounded_success"] for row in rows
            ),
        },
    )
    return blind_key_path, score_path, lock_path


def test_capture_only_summary_uses_metadata_without_answer_content(tmp_path):
    capture_path = _build_capture(tmp_path)

    summary = summarize_mechanism(capture_path)

    assert summary["mode"] == "capture_only"
    assert summary["semantic"]["available"] is False
    assert summary["operational"]["unit_count"] == 6
    assert summary["operational"]["experiment_unique_calls"]["call_count"] == 36
    assert summary["operational"]["reviewers"][REVIEWERS[0]]["verdict_counts"] == {
        "permit": 6
    }
    enforced = summary["operational"]["by_condition"][EVIDENCE_ENFORCED]
    assert enforced["latency_ms"]["mean"] == 3.0
    assert enforced["attempts"]["mean"] == 2.0
    assert SECRET not in json.dumps(summary, ensure_ascii=False)


def test_locked_scores_are_unblinded_and_clustered_by_case(tmp_path):
    capture_path = _build_capture(tmp_path)
    manifest_path = _build_manifest(tmp_path)
    blind_key_path, score_path, lock_path = _build_locked_scores(tmp_path)

    summary = summarize_mechanism(
        capture_path,
        blind_key_path=blind_key_path,
        score_paths=[score_path],
        score_lock_path=lock_path,
        manifest_path=manifest_path,
    )

    semantic = summary["semantic"]
    assert summary["mode"] == "locked_semantic_scores"
    assert semantic["score_row_count"] == 36
    assert semantic["by_condition"][EVIDENCE_ENFORCED]["semantic_grounded_success"] == {
        "numerator": 5,
        "denominator": 6,
        "rate": 5 / 6,
    }
    assert semantic["by_seed"]["44"][EVIDENCE_ENFORCED]["semantic_grounded_success"][
        "rate"
    ] == 0.5
    assert semantic["by_polarity"]["negative"][EVIDENCE_ENFORCED][
        "negative_correction"
    ]["rate"] == 1.0
    assert semantic["pass_three"]["by_condition"][EVIDENCE_ENFORCED][
        "passed_case_count"
    ] == 1

    effects = semantic["enforced_vs_shadow"][EVIDENCE_ENFORCED]["overall"]
    assert effects["corrected"] == 3
    assert effects["regressed"] == 1
    assert effects["net_correction"] == 2

    contrast = semantic["paired_case_cluster_contrasts"][
        "evidence-enforced_minus_style-placebo-enforced"
    ]
    assert contrast["mean_paired_difference"] == pytest.approx(1 / 3)
    assert contrast["exact_sign_flip"]["cluster_count"] == 2
    assert contrast["exact_sign_flip"]["nonzero_cluster_count"] == 2
    assert "seed는 case 안에서" in semantic["inference_note"]
    assert SECRET not in json.dumps(summary, ensure_ascii=False)


def test_score_hash_tamper_and_semantic_inconsistency_fail_closed(tmp_path):
    capture_path = _build_capture(tmp_path)
    manifest_path = _build_manifest(tmp_path)
    blind_key_path, score_path, lock_path = _build_locked_scores(tmp_path)
    score_path.write_bytes(score_path.read_bytes() + b" ")

    with pytest.raises(ValueError, match="SHA-256"):
        summarize_mechanism(
            capture_path,
            blind_key_path=blind_key_path,
            score_paths=[score_path],
            score_lock_path=lock_path,
            manifest_path=manifest_path,
        )

    blind_key_path, score_path, lock_path = _build_locked_scores(tmp_path / "fresh")
    score_document = json.loads(score_path.read_text(encoding="utf-8"))
    score_document["items"][0]["semantic_grounded_success"] = 1 - score_document["items"][0][
        "semantic_grounded_success"
    ]
    _write_json(score_path, score_document)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["score_file_sha256"][score_path.name] = hashlib.sha256(score_path.read_bytes()).hexdigest()
    lock["semantic_grounded_success_count_before_unblinding"] = sum(
        row["semantic_grounded_success"] for row in score_document["items"]
    )
    _write_json(lock_path, lock)

    with pytest.raises(ValueError, match="산식"):
        summarize_mechanism(
            capture_path,
            blind_key_path=blind_key_path,
            score_paths=[score_path],
            score_lock_path=lock_path,
            manifest_path=manifest_path,
        )


def test_cli_writes_capture_only_summary(tmp_path, capsys):
    capture_path = _build_capture(tmp_path)
    output_path = tmp_path / "summary.json"

    result = main(
        [
            "--capture",
            str(capture_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert json.loads(output_path.read_text(encoding="utf-8"))["mode"] == "capture_only"
    assert '"unit_count": 6' in capsys.readouterr().out
