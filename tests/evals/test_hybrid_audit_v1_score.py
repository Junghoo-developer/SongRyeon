from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from evals.hybrid_audit_v1.prompts import build_audit_prompts, canonical_json
from evals.hybrid_audit_v1.run import (
    CLOUD_CONDITION,
    EXPERIMENT_ID,
    LOCAL_CONDITION,
    sha256_bytes,
    sha256_text,
)
from evals.hybrid_audit_v1.schemas import (
    add_snapshot_id,
    select_escalation_case_ids,
)
from evals.hybrid_audit_v1.score import (
    ScoringIntegrityError,
    score_documents,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "evals/hybrid_audit_v1/source_snapshot.json"


def _source() -> tuple[dict, str]:
    raw = SOURCE_PATH.read_bytes()
    return json.loads(raw.decode("utf-8")), sha256_bytes(raw)


def _freeze(source: dict, source_sha: str) -> dict:
    case_ids = [case["case_id"] for case in source["cases"]]
    escalation_ids = select_escalation_case_ids(source["cases"], count=8)
    body = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "study_status": "retrospective_paired_feasibility_pilot",
        "source_commit": "1" * 40,
        "created_at_utc": "2026-08-07T00:00:00+00:00",
        "source_snapshot_id": source["snapshot_id"],
        "source_seed": 42,
        "case_count": 30,
        "expected_audit_verdict_counts": {
            verdict: sum(
                case["expected_audit_verdict"] == verdict
                for case in source["cases"]
            )
            for verdict in ("permit", "reject")
        },
        "planned_case_ids": case_ids,
        "planned_case_order_sha256": sha256_text(canonical_json(case_ids)),
        "selective_escalation_count": 8,
        "selective_escalation_case_ids": escalation_ids,
        "selective_escalation_order_sha256": sha256_text(
            canonical_json(escalation_ids)
        ),
        "conditions": [
            "no-audit",
            LOCAL_CONDITION,
            CLOUD_CONDITION,
            "selective-hybrid-8-of-30",
        ],
        "runner_attempts_per_case": 1,
        "transport_internal_retry_observable": False,
        "model_contracts": {
            "local": {
                "provider": "ollama",
                "execution_mode": "contest_local_or_self_hosted",
                "model": "gemma4:26b",
                "temperature": 0,
                "seed": 42,
                "num_ctx": 16384,
            },
            "cloud": {
                "provider": "openai_codex",
                "execution_mode": "codex_account_integration",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "medium",
                "tools_allowed": False,
                "sdk": {
                    "distribution": "openai-codex",
                    "version": "test-sdk",
                    "metadata_available": True,
                },
            },
        },
        "files": {
            "evals/hybrid_audit_v1/source_snapshot.json": source_sha,
            "evals/hybrid_audit_v1/score.py": "2" * 64,
        },
    }
    return {
        **body,
        "freeze_payload_sha256": sha256_text(canonical_json(body)),
    }


def _runner_summary(rows: list[dict]) -> dict:
    state_counts = {}
    metric_totals = {}
    for row in rows:
        state_counts[row["state"]] = state_counts.get(row["state"], 0) + 1
        for key, value in row["metrics"].items():
            metric_totals[key] = metric_totals.get(key, 0) + value
    return {
        "planned_rows": len(rows),
        "state_counts": state_counts,
        "latency_ms_sum": round(sum(row["latency_ms"] for row in rows), 3),
        "metric_totals": metric_totals,
    }


def _artifact(
    source: dict,
    source_sha: str,
    freeze: dict,
    condition: str,
    decisions: dict[str, str],
    *,
    failed: set[str] | None = None,
) -> dict:
    failed = failed or set()
    is_local = condition == LOCAL_CONDITION
    model = "gemma4:26b" if is_local else "gpt-5.6-sol"
    readiness = {
        "provider": "ollama" if is_local else "openai_codex",
        "execution_mode": (
            "contest_local_or_self_hosted"
            if is_local
            else "codex_account_integration"
        ),
        "model_name": model,
    }
    if is_local:
        readiness.update({"temperature": 0, "seed": 42, "num_ctx": 16384})
    else:
        readiness.update(
            {
                "reasoning_effort": "medium",
                "tools_allowed": False,
                "sdk_version": "test-sdk",
            }
        )
    rows = []
    for index, case in enumerate(source["cases"]):
        system_prompt, user_prompt = build_audit_prompts(
            a_records=case["audit_input"]["a_records"],
            candidate_draft=case["local_draft"],
        )
        case_id = case["case_id"]
        failure = case_id in failed
        parsed = None if failure else {
            "verdict": decisions[case_id],
            "reason": "The decision follows only the displayed A.",
        }
        raw = "" if failure else canonical_json(parsed)
        metrics = (
            {"prompt_eval_count": 100 + index, "eval_count": 10}
            if is_local
            else {
                "cached_input_tokens": 5,
                "input_tokens": 100 + index,
                "output_tokens": 10,
                "reasoning_output_tokens": 3,
                "total_tokens": 110 + index,
            }
        )
        if failure:
            metrics = {}
        rows.append(
            {
                "case_id": case_id,
                "runner_attempt": index + 1,
                "state": "failed" if failure else "valid",
                "started_at_unix": float(index),
                "finished_at_unix": float(index) + 0.1,
                "latency_ms": 100.0,
                "a_records_sha256": sha256_text(
                    canonical_json(case["audit_input"]["a_records"])
                ),
                "draft_sha256": sha256_text(case["local_draft"]),
                "system_prompt_sha256": sha256_text(system_prompt),
                "user_prompt_sha256": sha256_text(user_prompt),
                "raw_response": raw,
                "raw_response_sha256": sha256_text(raw) if raw else None,
                "thinking": "",
                "parsed_output": parsed,
                "requested_model": model,
                "client_reported_model": None if failure else model,
                "client_done_reason": None if is_local else "stop",
                "metrics": metrics,
                "error": (
                    {"type": "ModelCallError", "message": "planned failure"}
                    if failure
                    else None
                ),
            }
        )
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "run_state": "complete",
        "source_snapshot_id": source["snapshot_id"],
        "source_snapshot_sha256": source_sha,
        "freeze_payload_sha256": freeze["freeze_payload_sha256"],
        "model_readiness": readiness,
        "planned_case_ids": [case["case_id"] for case in source["cases"]],
        "started_at_unix": 0.0,
        "finished_at_unix": 30.0,
        "rows": rows,
        "summary": _runner_summary(rows),
    }


def _pilot_decisions(source: dict):
    expected = {
        case["case_id"]: case["expected_audit_verdict"]
        for case in source["cases"]
    }
    selected = select_escalation_case_ids(source["cases"])
    selected_permits = [case_id for case_id in selected if expected[case_id] == "permit"]
    nonselected_rejects = [
        case_id
        for case_id in expected
        if case_id not in selected and expected[case_id] == "reject"
    ]
    nonselected_permits = [
        case_id
        for case_id in expected
        if case_id not in selected and expected[case_id] == "permit"
    ]
    assert len(selected_permits) >= 2
    assert len(nonselected_rejects) >= 2
    assert nonselected_permits

    local = dict(expected)
    cloud = dict(expected)
    for case_id in selected_permits[:2]:
        local[case_id] = "reject"
    for case_id in nonselected_rejects[:2]:
        local[case_id] = "permit"
    cloud[nonselected_permits[0]] = "reject"
    return expected, local, cloud


def _score(source, source_sha, freeze, local, cloud, **kwargs):
    local_artifact = _artifact(
        source, source_sha, freeze, LOCAL_CONDITION, local,
        failed=kwargs.get("local_failed"),
    )
    cloud_artifact = _artifact(
        source, source_sha, freeze, CLOUD_CONDITION, cloud,
        failed=kwargs.get("cloud_failed"),
    )
    return score_documents(
        source=source,
        source_file_sha256=source_sha,
        freeze=freeze,
        local_artifact=local_artifact,
        cloud_artifact=cloud_artifact,
        local_artifact_sha256="a" * 64,
        cloud_artifact_sha256="b" * 64,
    ), local_artifact, cloud_artifact


def test_scores_all_four_conditions_and_exact_protocol_thresholds():
    source, source_sha = _source()
    freeze = _freeze(source, source_sha)
    expected, local, cloud = _pilot_decisions(source)

    (report, packet, key), _, _ = _score(
        source, source_sha, freeze, local, cloud
    )

    assert report["conditions"][LOCAL_CONDITION]["false_permits"] == 2
    assert report["conditions"][LOCAL_CONDITION]["false_rejects"] == 2
    assert report["conditions"][CLOUD_CONDITION]["false_permits"] == 0
    assert report["conditions"][CLOUD_CONDITION]["false_rejects"] == 1
    assert report["paired_comparisons"]["c2_vs_c1"]["corrected_count"] == 4
    assert report["paired_comparisons"]["c2_vs_c1"]["regressed_count"] == 1
    assert report["paired_comparisons"]["c2_vs_c1"]["net_correction"] == 3
    assert report["paired_comparisons"]["c3_vs_c1"]["net_correction"] == 2
    assert report["threshold_assessment"]["status"] == "pass"
    assert report["efficiency"][CLOUD_CONDITION]["token_totals"]["total_tokens"]["complete_reporting"] is True
    assert (
        report["efficiency"]["selective-hybrid-8-of-30"][
            "c3_cloud_runner_attempts"
        ]
        == 8
    )
    assert report["publishable"] is False
    assert packet["item_count"] == key["item_count"] == 5


def test_failed_row_stays_invalid_and_is_not_guessed_or_dropped():
    source, source_sha = _source()
    freeze = _freeze(source, source_sha)
    expected, local, cloud = _pilot_decisions(source)
    failed_case = next(iter(expected))

    (report, _, _), _, _ = _score(
        source,
        source_sha,
        freeze,
        local,
        cloud,
        cloud_failed={failed_case},
    )

    c2 = report["conditions"][CLOUD_CONDITION]
    assert c2["technical_failures"] == 1
    assert c2["technical_failure_case_ids"] == [failed_case]
    assert c2["valid_decisions"] == 29
    assert c2["planned_accuracy"]["denominator"] == 30
    assert report["paired_comparisons"]["c2_vs_c1"]["invalid_pair_count"] == 1


def test_blind_packet_omits_expected_labels_case_ids_and_auditor_identity():
    source, source_sha = _source()
    freeze = _freeze(source, source_sha)
    _, local, cloud = _pilot_decisions(source)

    (report, packet, key), _, _ = _score(
        source, source_sha, freeze, local, cloud
    )

    assert packet["item_count"] > 0
    for item in packet["items"]:
        assert set(item) == {
            "item_number",
            "blind_id",
            "a_records",
            "candidate_draft",
            "masked_decisions",
        }
        assert all(
            decision["auditor"] in {"auditor-alpha", "auditor-beta"}
            for decision in item["masked_decisions"]
        )
    rendered_packet = canonical_json(packet)
    assert "expected_audit_verdict" not in rendered_packet
    assert LOCAL_CONDITION not in rendered_packet
    assert CLOUD_CONDITION not in rendered_packet
    assert "selection_reasons" not in rendered_packet
    assert all("case_id" in item for item in key["items"])
    assert report["human_audit"]["packet_payload_sha256"] == packet["packet_payload_sha256"]


def test_rejects_missing_coverage_and_source_hash_tampering():
    source, source_sha = _source()
    freeze = _freeze(source, source_sha)
    _, local, cloud = _pilot_decisions(source)
    (_, _, _), local_artifact, cloud_artifact = _score(
        source, source_sha, freeze, local, cloud
    )

    missing = deepcopy(local_artifact)
    missing["rows"].pop()
    with pytest.raises(ScoringIntegrityError, match="coverage"):
        score_documents(
            source=source,
            source_file_sha256=source_sha,
            freeze=freeze,
            local_artifact=missing,
            cloud_artifact=cloud_artifact,
            local_artifact_sha256="a" * 64,
            cloud_artifact_sha256="b" * 64,
        )

    tampered = deepcopy(local_artifact)
    tampered["rows"][0]["draft_sha256"] = "0" * 64
    with pytest.raises(ScoringIntegrityError, match="draft hash"):
        score_documents(
            source=source,
            source_file_sha256=source_sha,
            freeze=freeze,
            local_artifact=tampered,
            cloud_artifact=cloud_artifact,
            local_artifact_sha256="a" * 64,
            cloud_artifact_sha256="b" * 64,
        )


def test_class_below_five_is_explicitly_inconclusive():
    source, _ = _source()
    changed = deepcopy(source)
    reject_cases = [
        case for case in changed["cases"]
        if case["expected_audit_verdict"] == "reject"
    ]
    for case in reject_cases[3:]:
        case["expected_audit_verdict"] = "permit"
        case["historical_reference"]["blind_preliminary_score"]["item"][
            "no_unsupported_claims"
        ] = 1
    body = {key: value for key, value in changed.items() if key != "snapshot_id"}
    source = add_snapshot_id(body)
    source_sha = sha256_text(canonical_json(source) + "\n")
    freeze = _freeze(source, source_sha)
    decisions = {
        case["case_id"]: case["expected_audit_verdict"]
        for case in source["cases"]
    }

    (report, _, _), _, _ = _score(
        source, source_sha, freeze, decisions, decisions
    )

    c2 = report["conditions"][CLOUD_CONDITION]
    assert c2["error_detection_rate"]["denominator"] == 3
    assert c2["error_detection_rate"]["status"] == "inconclusive"
    assert c2["balanced_accuracy"]["status"] == "inconclusive"
    assert report["threshold_assessment"]["status"] == "inconclusive"
