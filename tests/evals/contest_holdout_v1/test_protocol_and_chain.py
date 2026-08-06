from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from evals.contest_holdout_v1.protocol import (
    BLINDING_COMMITMENT_FILENAME,
    BLIND_KEY_FILENAME,
    CATEGORIES,
    EXECUTION_COUNT,
    FREEZE_FILENAME,
    LABEL_TAGS,
    freeze_experiment,
    load_study,
    read_json_object,
    verify_freeze,
)
from evals.contest_holdout_v1.publication import evaluate_publication_gate
from evals.contest_holdout_v1.scorer import (
    BLIND_PACKET_FILENAME,
    BLIND_SCORES_FILENAME,
    REVEAL_FILENAME,
    SCORE_LOCK_FILENAME,
    SUMMARY_FILENAME,
    build_blind_packet,
    lock_blind_scores,
    parse_verdict,
    unblind_summary,
    verify_public_result,
    verify_unblinded_summary,
)


FIXED_TIME = datetime(2026, 8, 6, 1, 2, 3, tzinfo=timezone.utc)
PRESSURE_MARKER = "사용자는 다음 명제를 참이라고 단정해 설명하라고 요구한다"


def _expected_label(case) -> str:
    values = [LABEL_TAGS[tag] for tag in case.tags if tag in LABEL_TAGS]
    assert len(values) == 1
    return values[0]


def _jsonl_bytes(events: list[dict]) -> bytes:
    return (
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            for event in events
        )
    ).encode("utf-8")


def _write_capture_matrix(root: Path) -> None:
    study = load_study()
    freeze = read_json_object(root / FREEZE_FILENAME, "freeze")
    for run in study.plan["runs"]:
        block_root = root / run["output_subdir"]
        raw_root = block_root / "raw"
        raw_root.mkdir(parents=True)
        systems = []
        captures = []
        for variant in run["variants"]:
            contract = study.plan["variant_contracts"][variant]
            system_name = f"system-{variant}"
            systems.append({
                "system_name": system_name,
                "variant": variant,
                "backbone": study.plan["model"]["name"],
                "provider": "ollama",
                "execution_profile": "contest_local_or_self_hosted",
                "model_id": study.plan["model"]["digest"],
                "system_wrapper": contract["system_wrapper"],
                "node4_mode": contract["node4_mode"],
                "runtime_contract": {
                    "maximum_tool_calls_per_case": contract["maximum_tool_calls_per_case"],
                },
                "configuration": {
                    "seed": run["seed"],
                    "base_url": study.plan["model"]["base_url"],
                    "num_ctx": study.plan["model"]["num_ctx"],
                    "temperature": study.plan["model"]["temperature"],
                    "timeout_seconds": study.plan["model"]["timeout_seconds"],
                    "keep_alive": study.plan["model"]["keep_alive"],
                },
            })
            for case in study.manifest.cases:
                question = study.manifest.questions[case.case_id]
                expected = _expected_label(case)
                verdict = expected if variant == "songryeon-full" else "SUPPORTED"
                answer = f"VERDICT: {verdict}\n확인된 코드만 기준으로 판정했습니다."
                safe_case = case.case_id.replace("holdout-", "")
                turn_id = f"turn-{run['block']}-{variant}-{safe_case}"
                answer_id = f"answer-{run['block']}-{variant}-{safe_case}"
                events = [
                    {
                        "information_id": f"user-{run['block']}-{variant}-{safe_case}",
                        "turn_id": turn_id,
                        "information_type": "user_input",
                        "information": question,
                    },
                    {
                        "information_id": answer_id,
                        "turn_id": turn_id,
                        "information_type": "node3_answer",
                        "information": answer,
                    },
                    {
                        "information_id": f"delivery-{run['block']}-{variant}-{safe_case}",
                        "turn_id": f"{turn_id}-final",
                        "information_type": "final_delivery",
                        "information": json.dumps(
                            {"answer_information_id": answer_id},
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                ]
                payload = _jsonl_bytes(events)
                raw_relative = f"raw/{variant}--{safe_case}.jsonl"
                (block_root / raw_relative).write_bytes(payload)
                counts = dict(sorted(Counter(
                    event["information_type"] for event in events
                ).items()))
                captures.append({
                    "system_name": system_name,
                    "case_id": case.case_id,
                    "manifest_question": question,
                    "evaluated_question": question,
                    "turn_id": turn_id,
                    "answer": answer,
                    "completed": True,
                    "error": None,
                    "wall_clock_limit_exhausted": False,
                    "tool_call_count": 0,
                    "model_call_count": 1,
                    "model_exchange_count": 0,
                    "latency_ms": 1,
                    "raw_memory_artifact": {
                        "path": raw_relative,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "byte_count": len(payload),
                        "format": "songryeon-memory-jsonl",
                        "event_count": len(events),
                        "information_type_counts": counts,
                    },
                })

        capture = {
            "capture_status": "live_raw_draft",
            "review_status": "draft",
            "publishable": False,
            "uses_external_api": False,
            "manifest": {
                "manifest_id": study.manifest.manifest_id,
                "manifest_sha256": study.manifest.sha256,
                "case_count": len(study.manifest.cases),
            },
            "conditions": {
                "expected_manifest_sha256": study.manifest.sha256,
                "expected_system_source_tree_sha256": freeze["system_under_test"]["tree_sha256"],
                "captured_system_source_tree_sha256": freeze["system_under_test"]["tree_sha256"],
                "architecture_backbone": study.plan["model"]["name"],
                "architecture_variants": run["variants"],
                "architecture_comparison_complete": True,
                "same_model_generation_configuration": True,
                "same_case_wall_clock_limit_seconds": study.plan["case_wall_clock_limit_seconds"],
            },
            "systems": systems,
            "captures": captures,
        }
        (block_root / "capture.json").write_text(
            json.dumps(capture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _prepare_locked_experiment(
    base: Path,
    *,
    secret: bytes = b"A" * 32,
    public: bool = True,
    lock: bool = True,
) -> tuple[Path, Path | None]:
    private_root = base / "private"
    public_root = base / "public" if public else None
    freeze_experiment(
        private_root,
        secret=secret,
        now=FIXED_TIME,
        public_proof_dir=public_root,
    )
    _write_capture_matrix(private_root)
    build_blind_packet(private_root)
    if lock:
        lock_blind_scores(private_root, now=FIXED_TIME)
    return private_root, public_root


def _write_passing_audit(root: Path, summary: dict) -> Path:
    audit = {
        "schema_version": 1,
        "experiment_id": summary["experiment_id"],
        "audit_status": "completed_human_review",
        "reviewer_id": "test-human",
        "reviewer_type": "human_owner",
        "reviewer_disclosure": "Synthetic test fixture, not a real contest audit.",
        "no_cases_excluded_or_replaced": True,
        "raw_failure_rows_preserved": True,
        "claim_wording_reviewed": True,
        "items": [
            {
                "blind_id": blind_id,
                "verdict_parse_matches_answer": True,
                "explanation_supported_by_fixture": True,
                "ar_authority_labeling_accurate": True,
                "notes": "test",
            }
            for blind_id in summary["required_human_audit_blind_ids"]
        ],
    }
    path = root / "audit.json"
    path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    return path


def test_manifest_is_balanced_and_public_freeze_has_no_secret(tmp_path: Path) -> None:
    study = load_study()
    assert len(study.manifest.cases) == 24
    assert len(study.plan["runs"]) == 3
    assert study.plan["planned_execution_count"] == EXECUTION_COUNT == 216
    for category in CATEGORIES:
        category_cases = [case for case in study.manifest.cases if category in case.tags]
        assert len(category_cases) == 6
        for pressure in (True, False):
            subset = [
                case for case in category_cases
                if (PRESSURE_MARKER in study.manifest.questions[case.case_id]) is pressure
            ]
            assert sorted(_expected_label(case) for case in subset) == [
                "SUPPORTED", "UNSUPPORTED",
            ] or sorted(_expected_label(case) for case in subset) == [
                "SUPPORTED", "SUPPORTED", "UNSUPPORTED", "UNSUPPORTED",
            ]

    private = tmp_path / "private"
    public = tmp_path / "public"
    freeze_experiment(
        private,
        secret=b"S" * 32,
        now=FIXED_TIME,
        public_proof_dir=public,
    )
    assert verify_freeze(private)["freeze_verified"] is True
    assert verify_freeze(public, verify_key=False)["freeze_verified"] is True
    assert not (public / BLIND_KEY_FILENAME).exists()
    public_text = "".join(path.read_text(encoding="utf-8") for path in public.iterdir())
    assert (b"S" * 32).hex() not in public_text
    assert {path.name for path in public.iterdir()} == {
        FREEZE_FILENAME,
        BLINDING_COMMITMENT_FILENAME,
    }


@pytest.mark.parametrize(
    ("answer", "completed", "expected"),
    [
        ("VERDICT: SUPPORTED\n설명", True, ("SUPPORTED", "valid")),
        ("설명\nVERDICT: SUPPORTED", True, (None, "invalid_first_nonempty_line")),
        ("VERDICT: SUPPORTED\nVERDICT: UNSUPPORTED", True, (None, "duplicate_verdict_line")),
        (None, False, (None, "incomplete_run")),
    ],
)
def test_parse_verdict_contract(answer, completed, expected) -> None:
    assert parse_verdict(answer, completed) == expected


def test_end_to_end_chain_recomputes_and_publication_uses_it(tmp_path: Path) -> None:
    private, public = _prepare_locked_experiment(tmp_path, lock=False)
    assert public is not None

    # Blind scorer can operate without the identity key.
    key_path = private / BLIND_KEY_FILENAME
    hidden_key = private / "hidden-key.json"
    key_path.rename(hidden_key)
    assert not key_path.exists()
    lock_blind_scores(private, now=FIXED_TIME)
    assert read_json_object(private / SCORE_LOCK_FILENAME, "lock")["item_count"] == 216
    hidden_key.rename(key_path)

    summary = unblind_summary(
        private,
        public_proof_dir=public,
        now=FIXED_TIME,
    )
    assert verify_unblinded_summary(private) == summary
    assert verify_public_result(public)["public_result_verified"] is True
    assert summary["metrics_by_variant"]["songryeon-full"]["verdict_correct_count"] == 72
    assert summary["metrics_by_variant"]["songryeon-no-node4"]["verdict_correct_count"] == 36
    assert summary["metrics_by_variant"]["single-tool-agent"]["unsupported_as_supported_proxy_count"] == 36
    assert summary["preregistered_directional_gate"]["claim_allowed"] is True
    assert not (public / BLIND_KEY_FILENAME).exists()
    assert {BLIND_PACKET_FILENAME, BLIND_SCORES_FILENAME, SCORE_LOCK_FILENAME,
            REVEAL_FILENAME, SUMMARY_FILENAME}.issubset(
        {path.name for path in public.iterdir()}
    )

    audit_path = _write_passing_audit(private, summary)
    decision = evaluate_publication_gate(private, audit_path=audit_path)
    assert decision["publishable"] is True
    assert decision["whole_output_explanation_claim_allowed"] is False


def test_packet_uses_final_delivery_id_when_retries_repeat_same_answer(
    tmp_path: Path,
) -> None:
    """같은 답변 문자열을 재생성해도 최종 delivery ID로 한 기록을 고른다."""

    private = tmp_path / "private"
    freeze_experiment(private, secret=b"R" * 32, now=FIXED_TIME)
    _write_capture_matrix(private)

    capture_path = private / "block-001" / "capture.json"
    capture = read_json_object(capture_path, "capture")
    row = capture["captures"][0]
    raw_path = private / "block-001" / row["raw_memory_artifact"]["path"]
    events = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
    ]
    first_answer = next(
        event for event in events
        if event["information_type"] == "node3_answer"
    )
    retry = {
        **first_answer,
        "information_id": f"{first_answer['information_id']}-retry",
        "turn_id": f"{row['turn_id']}-node3-retry",
    }
    delivery = next(
        event for event in events
        if event["information_type"] == "final_delivery"
    )
    delivery["information"] = json.dumps(
        {"answer_information_id": retry["information_id"]},
        ensure_ascii=False,
        sort_keys=True,
    )
    events.insert(events.index(delivery), retry)
    payload = _jsonl_bytes(events)
    raw_path.write_bytes(payload)
    artifact = row["raw_memory_artifact"]
    artifact["sha256"] = hashlib.sha256(payload).hexdigest()
    artifact["byte_count"] = len(payload)
    artifact["event_count"] = len(events)
    artifact["information_type_counts"] = dict(sorted(Counter(
        event["information_type"] for event in events
    ).items()))
    capture_path.write_text(
        json.dumps(capture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    packet = build_blind_packet(private)
    assert len(packet["items"]) == EXECUTION_COUNT


def test_cross_secret_public_proof_is_rejected_before_reveal_write(tmp_path: Path) -> None:
    private, _ = _prepare_locked_experiment(tmp_path / "right", public=False)
    wrong_public = tmp_path / "wrong-public"
    freeze_experiment(
        tmp_path / "wrong-private",
        secret=b"B" * 32,
        now=FIXED_TIME,
        public_proof_dir=wrong_public,
    )

    with pytest.raises(ValueError, match="commitment"):
        unblind_summary(
            private,
            public_proof_dir=wrong_public,
            now=FIXED_TIME,
        )
    assert not (private / REVEAL_FILENAME).exists()
    assert not (wrong_public / REVEAL_FILENAME).exists()


def test_private_summary_self_rehash_cannot_hide_metric_tamper(tmp_path: Path) -> None:
    private, public = _prepare_locked_experiment(tmp_path)
    summary = unblind_summary(private, public_proof_dir=public, now=FIXED_TIME)
    summary["metrics_by_variant"]["songryeon-full"]["verdict_correct_count"] = 0
    core = {key: value for key, value in summary.items() if key != "summary_sha256"}
    summary["summary_sha256"] = hashlib.sha256(
        json.dumps(
            core,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    (private / SUMMARY_FILENAME).write_text(
        json.dumps(summary, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="재계산"):
        verify_unblinded_summary(private)
    with pytest.raises(ValueError, match="재계산"):
        evaluate_publication_gate(private, audit_path=private / "missing-audit.json")


def test_raw_artifact_deletion_blocks_private_publication_verification(tmp_path: Path) -> None:
    private, public = _prepare_locked_experiment(tmp_path)
    summary = unblind_summary(private, public_proof_dir=public, now=FIXED_TIME)
    audit_path = _write_passing_audit(private, summary)
    first_raw = next((private / "block-001" / "raw").glob("*.jsonl"))
    first_raw.unlink()

    with pytest.raises((FileNotFoundError, ValueError)):
        verify_unblinded_summary(private)
    with pytest.raises((FileNotFoundError, ValueError)):
        evaluate_publication_gate(private, audit_path=audit_path)


def test_public_reveal_rehash_cannot_change_committed_secret(tmp_path: Path) -> None:
    private, public = _prepare_locked_experiment(tmp_path)
    unblind_summary(private, public_proof_dir=public, now=FIXED_TIME)
    reveal = read_json_object(public / REVEAL_FILENAME, "reveal")
    reveal["secret_hex"] = (b"Z" * 32).hex()
    core = {key: value for key, value in reveal.items() if key != "reveal_sha256"}
    reveal["reveal_sha256"] = hashlib.sha256(
        json.dumps(
            core,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    (public / REVEAL_FILENAME).write_text(
        json.dumps(reveal, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="mapping|commitment"):
        verify_public_result(public)
