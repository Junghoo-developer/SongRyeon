"""Score the frozen local/cloud A-only audit pilot without model calls."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import math
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from .prompts import build_audit_prompts, canonical_json, parse_audit_output
from .run import (
    CLOUD_CONDITION,
    EXPERIMENT_ID,
    FREEZE_PATH,
    LOCAL_CONDITION,
    OUTPUT_ROOT,
    SOURCE_PATH,
    WORKSPACE_ROOT,
    _atomic_write_json,
    _verify_freeze,
    load_strict_json,
    sha256_bytes,
    sha256_text,
)
from .schemas import (
    select_escalation_case_ids,
    validate_audit_output,
    validate_source_snapshot,
)


NO_AUDIT_CONDITION = "no-audit"
SELECTIVE_CONDITION = "selective-hybrid-8-of-30"
SUMMARY_NAME = "summary.json"
HUMAN_PACKET_NAME = "human-audit-packet.json"
HUMAN_KEY_NAME = "human-audit-key.json"
RATE_MINIMUM_CLASS_SIZE = 5
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)

ARTIFACT_KEYS = {
    "schema_version",
    "experiment_id",
    "condition",
    "run_state",
    "source_snapshot_id",
    "source_snapshot_sha256",
    "freeze_payload_sha256",
    "model_readiness",
    "planned_case_ids",
    "started_at_unix",
    "finished_at_unix",
    "rows",
    "summary",
}
ROW_KEYS = {
    "case_id",
    "runner_attempt",
    "state",
    "started_at_unix",
    "finished_at_unix",
    "latency_ms",
    "a_records_sha256",
    "draft_sha256",
    "system_prompt_sha256",
    "user_prompt_sha256",
    "raw_response",
    "raw_response_sha256",
    "thinking",
    "parsed_output",
    "requested_model",
    "client_reported_model",
    "client_done_reason",
    "metrics",
    "error",
}


class ScoringIntegrityError(RuntimeError):
    """A frozen input or captured artifact cannot be scored safely."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScoringIntegrityError(message)


def _finite_number(value: Any, label: str) -> float:
    _require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value),
        f"{label} must be a finite number",
    )
    return float(value)


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    _require(type(numerator) is int and numerator >= 0, "rate numerator is invalid")
    _require(
        type(denominator) is int and denominator >= numerator,
        "rate denominator is invalid",
    )
    value = None if denominator == 0 else numerator / denominator
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "status": (
            "reported"
            if denominator >= RATE_MINIMUM_CLASS_SIZE
            else "inconclusive"
        ),
    }


def _hash_document_body(body: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(body))


def _with_content_hash(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {**deepcopy(dict(body)), field: _hash_document_body(body)}


def _recomputed_runner_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    state_counts: dict[str, int] = {}
    latency_sum = 0.0
    metric_totals: dict[str, int | float] = {}
    for row in rows:
        state = row["state"]
        state_counts[state] = state_counts.get(state, 0) + 1
        latency_sum += float(row["latency_ms"])
        for key, value in row["metrics"].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metric_totals[key] = metric_totals.get(key, 0) + value
    return {
        "planned_rows": len(rows),
        "state_counts": state_counts,
        "latency_ms_sum": round(latency_sum, 3),
        "metric_totals": metric_totals,
    }


def _validate_freeze_against_source(
    freeze: Mapping[str, Any],
    source: Mapping[str, Any],
    source_file_sha256: str,
) -> None:
    _require(freeze.get("schema_version") == 1, "freeze schema version mismatch")
    _require(freeze.get("experiment_id") == EXPERIMENT_ID, "freeze experiment mismatch")
    freeze_body = dict(freeze)
    freeze_hash = freeze_body.pop("freeze_payload_sha256", None)
    _require(
        freeze_hash == _hash_document_body(freeze_body),
        "freeze payload hash mismatch",
    )
    cases = source["cases"]
    case_ids = [case["case_id"] for case in cases]
    expected_counts = {
        verdict: sum(case["expected_audit_verdict"] == verdict for case in cases)
        for verdict in ("permit", "reject")
    }
    _require(freeze.get("source_snapshot_id") == source["snapshot_id"], "freeze source ID mismatch")
    _require(freeze.get("case_count") == len(cases) == 30, "freeze case count mismatch")
    _require(freeze.get("planned_case_ids") == case_ids, "freeze planned coverage mismatch")
    _require(
        freeze.get("planned_case_order_sha256") == sha256_text(canonical_json(case_ids)),
        "freeze planned order hash mismatch",
    )
    _require(
        freeze.get("expected_audit_verdict_counts") == expected_counts,
        "freeze reference counts mismatch",
    )
    _require(freeze.get("selective_escalation_count") == 8, "freeze escalation count mismatch")
    escalation_ids = select_escalation_case_ids(cases, count=8)
    _require(
        freeze.get("selective_escalation_case_ids") == escalation_ids,
        "freeze escalation IDs mismatch",
    )
    _require(
        freeze.get("selective_escalation_order_sha256")
        == sha256_text(canonical_json(escalation_ids)),
        "freeze escalation order hash mismatch",
    )
    _require(
        freeze.get("runner_attempts_per_case") == 1,
        "freeze runner attempt contract mismatch",
    )
    _require(
        freeze.get("transport_internal_retry_observable") is False,
        "freeze transport retry observability mismatch",
    )
    _require(
        freeze.get("conditions")
        == [
            NO_AUDIT_CONDITION,
            LOCAL_CONDITION,
            CLOUD_CONDITION,
            SELECTIVE_CONDITION,
        ],
        "freeze conditions mismatch",
    )
    files = freeze.get("files")
    _require(isinstance(files, dict), "freeze files must be an object")
    _require(
        files.get("evals/hybrid_audit_v1/source_snapshot.json")
        == source_file_sha256,
        "freeze source file hash mismatch",
    )


def _validate_row(
    row: Mapping[str, Any],
    case: Mapping[str, Any],
    expected_model: str,
    expected_runner_attempt: int,
) -> None:
    _require(isinstance(row, dict) and set(row) == ROW_KEYS, "audit row schema mismatch")
    _require(row["case_id"] == case["case_id"], "audit row case mismatch")
    _require(
        row["runner_attempt"] == expected_runner_attempt,
        "audit row runner attempt mismatch",
    )
    started = _finite_number(row["started_at_unix"], "row started_at_unix")
    finished = _finite_number(row["finished_at_unix"], "row finished_at_unix")
    latency = _finite_number(row["latency_ms"], "row latency_ms")
    _require(finished >= started and latency >= 0, "audit row timing is invalid")

    system_prompt, user_prompt = build_audit_prompts(
        a_records=case["audit_input"]["a_records"],
        candidate_draft=case["local_draft"],
    )
    _require(
        row["a_records_sha256"]
        == sha256_text(canonical_json(case["audit_input"]["a_records"])),
        "audit row A hash mismatch",
    )
    _require(row["draft_sha256"] == sha256_text(case["local_draft"]), "audit row draft hash mismatch")
    _require(row["system_prompt_sha256"] == sha256_text(system_prompt), "audit row system prompt hash mismatch")
    _require(row["user_prompt_sha256"] == sha256_text(user_prompt), "audit row user prompt hash mismatch")

    raw_response = row["raw_response"]
    _require(isinstance(raw_response, str), "raw_response must be text")
    if raw_response:
        _require(
            row["raw_response_sha256"] == sha256_text(raw_response),
            "raw response hash mismatch",
        )
    else:
        _require(row["raw_response_sha256"] is None, "empty response must not have a hash")
    _require(isinstance(row["thinking"], str), "thinking must be text")
    _require(
        row["client_done_reason"] is None
        or isinstance(row["client_done_reason"], str),
        "client_done_reason must be text or null",
    )
    _require(isinstance(row["metrics"], dict), "row metrics must be an object")
    for name, value in row["metrics"].items():
        _require(isinstance(name, str), "metric names must be strings")
        _finite_number(value, f"metric {name}")
        _require(value >= 0, f"metric {name} must be nonnegative")

    state = row["state"]
    _require(state in {"valid", "failed"}, "complete artifact contains an invalid row state")
    if state == "valid":
        _require(row["error"] is None, "valid row must not contain an error")
        _require(
            row["requested_model"] == expected_model,
            "valid row requested model mismatch",
        )
        _require(
            row["client_reported_model"] == expected_model,
            "valid row client-reported model mismatch",
        )
        validate_audit_output(row["parsed_output"])
        _require(raw_response != "", "valid row must preserve a response")
        try:
            parsed_again = parse_audit_output(raw_response)
        except Exception as error:
            raise ScoringIntegrityError("valid raw response no longer parses") from error
        _require(parsed_again == row["parsed_output"], "parsed output differs from raw response")
    else:
        _require(row["parsed_output"] is None, "failed row must not contain a guessed decision")
        error = row["error"]
        _require(
            isinstance(error, dict)
            and set(error) == {"type", "message"}
            and isinstance(error["type"], str)
            and bool(error["type"])
            and isinstance(error["message"], str),
            "failed row error schema mismatch",
        )
        _require(
            row["requested_model"] == expected_model,
            "failed row requested model mismatch",
        )
        _require(
            row["client_reported_model"] is None
            or row["client_reported_model"] == expected_model,
            "failed row client-reported model mismatch",
        )


def validate_audit_artifact(
    artifact: Mapping[str, Any],
    *,
    condition: str,
    source: Mapping[str, Any],
    source_file_sha256: str,
    freeze: Mapping[str, Any],
) -> None:
    """Validate exact planned coverage and every source/prompt/response hash."""

    _require(
        isinstance(artifact, dict) and set(artifact) == ARTIFACT_KEYS,
        "audit artifact schema mismatch",
    )
    _require(artifact["schema_version"] == 1, "artifact schema version mismatch")
    _require(artifact["experiment_id"] == EXPERIMENT_ID, "artifact experiment mismatch")
    _require(artifact["condition"] == condition, "artifact condition mismatch")
    _require(artifact["run_state"] == "complete", "artifact run is not complete")
    _require(artifact["source_snapshot_id"] == source["snapshot_id"], "artifact source ID mismatch")
    _require(artifact["source_snapshot_sha256"] == source_file_sha256, "artifact source hash mismatch")
    _require(
        artifact["freeze_payload_sha256"] == freeze["freeze_payload_sha256"],
        "artifact freeze hash mismatch",
    )
    case_ids = [case["case_id"] for case in source["cases"]]
    _require(artifact["planned_case_ids"] == case_ids, "artifact plan mismatch")
    rows = artifact["rows"]
    _require(isinstance(rows, list) and len(rows) == len(case_ids), "artifact row coverage mismatch")
    _require([row.get("case_id") for row in rows] == case_ids, "artifact row order mismatch")
    _require(len({row["case_id"] for row in rows}) == len(rows), "artifact contains duplicate cases")
    _require(isinstance(artifact["model_readiness"], dict), "model readiness must be an object")
    started = _finite_number(artifact["started_at_unix"], "artifact started_at_unix")
    finished = _finite_number(artifact["finished_at_unix"], "artifact finished_at_unix")
    _require(finished >= started, "artifact timing is invalid")

    model_contract = freeze["model_contracts"][
        "local" if condition == LOCAL_CONDITION else "cloud"
    ]
    expected_model = model_contract["model"]
    readiness = artifact["model_readiness"]
    _require(readiness.get("provider") == model_contract["provider"], "artifact provider mismatch")
    if "execution_mode" in model_contract:
        _require(
            readiness.get("execution_mode") == model_contract["execution_mode"],
            "artifact execution mode mismatch",
        )
    _require(readiness.get("model_name") == expected_model, "artifact readiness model mismatch")
    if condition == LOCAL_CONDITION:
        for field in ("temperature", "seed", "num_ctx"):
            _require(
                readiness.get(field) == model_contract[field],
                f"local readiness {field} mismatch",
            )
    else:
        _require(
            readiness.get("reasoning_effort")
            == model_contract["reasoning_effort"],
            "cloud readiness reasoning effort mismatch",
        )
        _require(
            readiness.get("tools_allowed") is False,
            "cloud readiness tools contract mismatch",
        )
        sdk = model_contract["sdk"]
        if sdk.get("metadata_available"):
            _require(
                readiness.get("sdk_version") == sdk.get("version"),
                "cloud readiness SDK version mismatch",
            )
    for runner_attempt, (row, case) in enumerate(
        zip(rows, source["cases"]),
        1,
    ):
        _validate_row(row, case, expected_model, runner_attempt)
    _require(
        artifact["summary"] == _recomputed_runner_summary(rows),
        "artifact runner summary mismatch",
    )


def _decisions_from_artifact(artifact: Mapping[str, Any]) -> dict[str, str | None]:
    decisions: dict[str, str | None] = {}
    for row in artifact["rows"]:
        decisions[row["case_id"]] = (
            row["parsed_output"]["verdict"] if row["state"] == "valid" else None
        )
    return decisions


def _condition_metrics(
    expected: Mapping[str, str],
    decisions: Mapping[str, str | None],
) -> dict[str, Any]:
    case_ids = list(expected)
    _require(set(decisions) == set(case_ids), "decision coverage mismatch")
    expected_permit = sum(expected[case_id] == "permit" for case_id in case_ids)
    expected_reject = len(case_ids) - expected_permit
    correct = 0
    false_permits = 0
    false_rejects = 0
    failures: list[str] = []
    for case_id in case_ids:
        decision = decisions[case_id]
        if decision is None:
            failures.append(case_id)
        elif decision == expected[case_id]:
            correct += 1
        elif decision == "permit":
            false_permits += 1
        else:
            false_rejects += 1
    detection = _rate(expected_reject - false_permits - sum(
        expected[case_id] == "reject" for case_id in failures
    ), expected_reject)
    preservation = _rate(expected_permit - false_rejects - sum(
        expected[case_id] == "permit" for case_id in failures
    ), expected_permit)
    balanced_status = (
        "reported"
        if detection["status"] == preservation["status"] == "reported"
        else "inconclusive"
    )
    balanced_value = (
        (detection["value"] + preservation["value"]) / 2
        if balanced_status == "reported"
        else None
    )
    return {
        "planned_cases": len(case_ids),
        "expected_permit": expected_permit,
        "expected_reject": expected_reject,
        "valid_decisions": len(case_ids) - len(failures),
        "technical_failures": len(failures),
        "technical_failure_case_ids": failures,
        "correct": correct,
        "incorrect_valid_decisions": false_permits + false_rejects,
        "planned_accuracy": _rate(correct, len(case_ids)),
        "error_detection_rate": detection,
        "supported_draft_preservation_rate": preservation,
        "false_permits": false_permits,
        "false_rejects": false_rejects,
        "balanced_accuracy": {
            "value": balanced_value,
            "status": balanced_status,
        },
    }


def _paired_comparison(
    *,
    baseline: Mapping[str, str | None],
    comparison: Mapping[str, str | None],
    expected: Mapping[str, str],
) -> dict[str, Any]:
    corrected: list[str] = []
    regressed: list[str] = []
    invalid: list[str] = []
    unchanged: list[str] = []
    for case_id in expected:
        baseline_decision = baseline[case_id]
        comparison_decision = comparison[case_id]
        if baseline_decision is None or comparison_decision is None:
            invalid.append(case_id)
            continue
        baseline_correct = baseline_decision == expected[case_id]
        comparison_correct = comparison_decision == expected[case_id]
        if not baseline_correct and comparison_correct:
            corrected.append(case_id)
        elif baseline_correct and not comparison_correct:
            regressed.append(case_id)
        else:
            unchanged.append(case_id)
    return {
        "both_valid_pairs": len(expected) - len(invalid),
        "invalid_pair_count": len(invalid),
        "invalid_case_ids": invalid,
        "corrected_count": len(corrected),
        "corrected_case_ids": corrected,
        "regressed_count": len(regressed),
        "regressed_case_ids": regressed,
        "unchanged_count": len(unchanged),
        "net_correction": len(corrected) - len(regressed),
    }


def _native_token_value(metrics: Mapping[str, Any], field: str) -> int | None:
    value = metrics.get(field)
    if type(value) is int and value >= 0:
        return value
    if field == "input_tokens":
        value = metrics.get("prompt_eval_count")
        return value if type(value) is int and value >= 0 else None
    if field == "output_tokens":
        value = metrics.get("eval_count")
        return value if type(value) is int and value >= 0 else None
    if field == "total_tokens":
        prompt = metrics.get("prompt_eval_count")
        output = metrics.get("eval_count")
        if type(prompt) is int and prompt >= 0 and type(output) is int and output >= 0:
            return prompt + output
    return None


def _efficiency(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    latencies = [float(row["latency_ms"]) for row in rows]
    token_totals: dict[str, dict[str, Any]] = {}
    for field in TOKEN_FIELDS:
        values = [
            value
            for row in rows
            if (value := _native_token_value(row["metrics"], field)) is not None
        ]
        token_totals[field] = {
            "reported_rows": len(values),
            "planned_rows": len(rows),
            "complete_reporting": len(values) == len(rows),
            "sum": sum(values) if values else None,
        }
    return {
        "planned_runner_attempts": len(rows),
        "valid_calls": sum(row["state"] == "valid" for row in rows),
        "failed_calls": sum(row["state"] == "failed" for row in rows),
        "latency_ms": {
            "sum": round(sum(latencies), 3),
            "mean": round(sum(latencies) / len(latencies), 3),
            "median": round(float(median(latencies)), 3),
            "minimum": round(min(latencies), 3),
            "maximum": round(max(latencies), 3),
        },
        "token_totals": token_totals,
        "provider_native_metric_totals": _recomputed_runner_summary(rows)[
            "metric_totals"
        ],
    }


def _selective_cloud_efficiency(
    cloud_rows: list[Mapping[str, Any]],
    selected_ids: list[str],
    cloud_net: int,
    selective_net: int,
) -> dict[str, Any]:
    selected = set(selected_ids)
    selected_rows = [row for row in cloud_rows if row["case_id"] in selected]
    all_tokens = [
        _native_token_value(row["metrics"], "total_tokens") for row in cloud_rows
    ]
    selected_tokens = [
        _native_token_value(row["metrics"], "total_tokens") for row in selected_rows
    ]
    complete_tokens = all(value is not None for value in all_tokens)
    selected_complete = all(value is not None for value in selected_tokens)
    all_sum = sum(all_tokens) if complete_tokens else None
    selected_sum = sum(selected_tokens) if selected_complete else None
    return {
        "c2_cloud_runner_attempts": len(cloud_rows),
        "c3_cloud_runner_attempts": len(selected_rows),
        "c3_local_runner_attempts": len(cloud_rows),
        "c3_total_runner_attempts": len(cloud_rows) + len(selected_rows),
        "cloud_runner_attempt_reduction": {
            "absolute": len(cloud_rows) - len(selected_rows),
            "fraction": 1 - len(selected_rows) / len(cloud_rows),
        },
        "cloud_total_tokens": all_sum,
        "selective_cloud_total_tokens": selected_sum,
        "selective_cloud_token_reduction": (
            {
                "absolute": all_sum - selected_sum,
                "fraction": 1 - selected_sum / all_sum if all_sum else None,
                "status": "reported",
            }
            if all_sum is not None and selected_sum is not None
            else {"absolute": None, "fraction": None, "status": "incomplete_telemetry"}
        ),
        "c2_cloud_runner_attempts_per_net_correction": (
            len(cloud_rows) / cloud_net if cloud_net > 0 else None
        ),
        "c2_cloud_tokens_per_net_correction": (
            all_sum / cloud_net if all_sum is not None and cloud_net > 0 else None
        ),
        "c3_cloud_runner_attempts_per_net_correction": (
            len(selected_rows) / selective_net if selective_net > 0 else None
        ),
        "c3_cloud_tokens_per_net_correction": (
            selected_sum / selective_net
            if selected_sum is not None and selective_net > 0
            else None
        ),
    }


def _threshold_assessment(
    *,
    c1: Mapping[str, Any],
    c2: Mapping[str, Any],
    c2_pair: Mapping[str, Any],
    c3_pair: Mapping[str, Any],
) -> dict[str, Any]:
    detection_reported = (
        c1["error_detection_rate"]["status"]
        == c2["error_detection_rate"]["status"]
        == "reported"
    )
    preservation_reported = (
        c1["supported_draft_preservation_rate"]["status"]
        == c2["supported_draft_preservation_rate"]["status"]
        == "reported"
    )
    detection_gain = (
        c2["error_detection_rate"]["value"]
        - c1["error_detection_rate"]["value"]
        if detection_reported
        else None
    )
    preservation_fall = (
        c1["supported_draft_preservation_rate"]["value"]
        - c2["supported_draft_preservation_rate"]["value"]
        if preservation_reported
        else None
    )
    c2_net = c2_pair["net_correction"]
    c3_net = c3_pair["net_correction"]
    retention_ratio = c3_net / c2_net if c2_net > 0 else None
    checks = {
        "c2_net_at_least_3": {
            "observed": c2_net,
            "threshold": 3,
            "passed": c2_net >= 3,
        },
        "detection_gain_at_least_20pp": {
            "observed": detection_gain,
            "threshold": 0.20,
            "passed": detection_gain is not None and detection_gain >= 0.20 - 1e-12,
        },
        "preservation_fall_at_most_5pp": {
            "observed": preservation_fall,
            "threshold": 0.05,
            "passed": preservation_fall is not None and preservation_fall <= 0.05 + 1e-12,
        },
        "c3_retains_at_least_half_c2_net": {
            "observed": retention_ratio,
            "threshold": 0.50,
            "passed": retention_ratio is not None and retention_ratio >= 0.50,
        },
        "c3_fixes_at_least_1": {
            "observed": c3_pair["corrected_count"],
            "threshold": 1,
            "passed": c3_pair["corrected_count"] >= 1,
        },
        "c3_harms_at_most_1": {
            "observed": c3_pair["regressed_count"],
            "threshold": 1,
            "passed": c3_pair["regressed_count"] <= 1,
        },
    }
    class_floor_ok = detection_reported and preservation_reported
    technical_complete = (
        c1["technical_failures"] == 0 and c2["technical_failures"] == 0
    )
    return {
        "status": (
            "inconclusive"
            if not class_floor_ok or not technical_complete
            else "pass" if all(check["passed"] for check in checks.values()) else "fail"
        ),
        "technical_complete": technical_complete,
        "checks": checks,
        "note": (
            "Engineering continuation thresholds for a reused synthetic pilot; not statistical proof."
        ),
    }


def _human_audit_documents(
    *,
    source: Mapping[str, Any],
    freeze_hash: str,
    local: Mapping[str, str | None],
    cloud: Mapping[str, str | None],
    expected: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected_case_ids = []
    selection_reasons: dict[str, list[str]] = {}
    for case in source["cases"]:
        case_id = case["case_id"]
        reasons = []
        if local[case_id] is not None and cloud[case_id] is not None and local[case_id] != cloud[case_id]:
            reasons.append("c1_c2_disagreement")
        if expected[case_id] == "reject" and (
            local[case_id] == "permit" or cloud[case_id] == "permit"
        ):
            reasons.append("false_permit_against_preliminary_reference")
        if reasons:
            selected_case_ids.append(case_id)
            selection_reasons[case_id] = reasons

    packet_items = []
    key_items = []
    cases_by_id = {case["case_id"]: case for case in source["cases"]}
    for ordinal, case_id in enumerate(selected_case_ids, 1):
        case = cases_by_id[case_id]
        blind_id = "hybrid-human-" + hashlib.sha256(
            f"hybrid-audit-v1|human|{freeze_hash}|{case_id}".encode("utf-8")
        ).hexdigest()
        swap = int(hashlib.sha256(
            f"hybrid-audit-v1|mask|{freeze_hash}|{case_id}".encode("utf-8")
        ).hexdigest(), 16) % 2 == 1
        condition_order = (
            [CLOUD_CONDITION, LOCAL_CONDITION]
            if swap
            else [LOCAL_CONDITION, CLOUD_CONDITION]
        )
        values = {LOCAL_CONDITION: local[case_id], CLOUD_CONDITION: cloud[case_id]}
        masked = []
        mask_key = {}
        for alias, condition in zip(("auditor-alpha", "auditor-beta"), condition_order):
            verdict = values[condition]
            masked.append(
                {
                    "auditor": alias,
                    "state": "valid" if verdict is not None else "technical_failure",
                    "verdict": verdict,
                }
            )
            mask_key[alias] = condition
        packet_items.append(
            {
                "item_number": ordinal,
                "blind_id": blind_id,
                "a_records": deepcopy(case["audit_input"]["a_records"]),
                "candidate_draft": case["local_draft"],
                "masked_decisions": masked,
            }
        )
        key_items.append(
            {
                "blind_id": blind_id,
                "case_id": case_id,
                "expected_audit_verdict": expected[case_id],
                "mask_to_condition": mask_key,
                "selection_reasons": selection_reasons[case_id],
            }
        )

    packet_body = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "freeze_payload_sha256": freeze_hash,
        "blinding": (
            "Expected labels, source case IDs, auditor identities, reasons, and selection reasons are omitted. "
            "Judge each candidate only against the displayed A records before opening the key."
        ),
        "item_count": len(packet_items),
        "items": packet_items,
    }
    key_body = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "freeze_payload_sha256": freeze_hash,
        "item_count": len(key_items),
        "items": key_items,
    }
    return (
        _with_content_hash(packet_body, "packet_payload_sha256"),
        _with_content_hash(key_body, "key_payload_sha256"),
    )


def score_documents(
    *,
    source: Mapping[str, Any],
    source_file_sha256: str,
    freeze: Mapping[str, Any],
    local_artifact: Mapping[str, Any],
    cloud_artifact: Mapping[str, Any],
    local_artifact_sha256: str,
    cloud_artifact_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return deterministic summary, blinded packet, and separate unblinding key."""

    validate_source_snapshot(source)
    _validate_freeze_against_source(freeze, source, source_file_sha256)
    validate_audit_artifact(
        local_artifact,
        condition=LOCAL_CONDITION,
        source=source,
        source_file_sha256=source_file_sha256,
        freeze=freeze,
    )
    validate_audit_artifact(
        cloud_artifact,
        condition=CLOUD_CONDITION,
        source=source,
        source_file_sha256=source_file_sha256,
        freeze=freeze,
    )
    expected = {
        case["case_id"]: case["expected_audit_verdict"] for case in source["cases"]
    }
    c0_decisions = {case_id: "permit" for case_id in expected}
    c1_decisions = _decisions_from_artifact(local_artifact)
    c2_decisions = _decisions_from_artifact(cloud_artifact)
    recomputed_selected_ids = select_escalation_case_ids(
        source["cases"], count=freeze["selective_escalation_count"]
    )
    selected_ids = freeze["selective_escalation_case_ids"]
    _require(
        selected_ids == recomputed_selected_ids,
        "sealed selective escalation IDs do not match the frozen source",
    )
    selected = set(selected_ids)
    c3_decisions = {
        case_id: c2_decisions[case_id] if case_id in selected else c1_decisions[case_id]
        for case_id in expected
    }
    condition_metrics = {
        NO_AUDIT_CONDITION: _condition_metrics(expected, c0_decisions),
        LOCAL_CONDITION: _condition_metrics(expected, c1_decisions),
        CLOUD_CONDITION: _condition_metrics(expected, c2_decisions),
        SELECTIVE_CONDITION: _condition_metrics(expected, c3_decisions),
    }
    c2_pair = _paired_comparison(
        baseline=c1_decisions, comparison=c2_decisions, expected=expected
    )
    c3_pair = _paired_comparison(
        baseline=c1_decisions, comparison=c3_decisions, expected=expected
    )
    local_efficiency = _efficiency(local_artifact["rows"])
    cloud_efficiency = _efficiency(cloud_artifact["rows"])
    hybrid_efficiency = _selective_cloud_efficiency(
        cloud_artifact["rows"],
        selected_ids,
        c2_pair["net_correction"],
        c3_pair["net_correction"],
    )
    packet, key = _human_audit_documents(
        source=source,
        freeze_hash=freeze["freeze_payload_sha256"],
        local=c1_decisions,
        cloud=c2_decisions,
        expected=expected,
    )
    report_body = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "study_status": "retrospective_paired_feasibility_pilot",
        "publishable": False,
        "reference_label_status": "blind_ai_preliminary_not_human_ground_truth",
        "freeze_payload_sha256": freeze["freeze_payload_sha256"],
        "source_snapshot_id": source["snapshot_id"],
        "source_snapshot_sha256": source_file_sha256,
        "artifact_provenance": {
            LOCAL_CONDITION: local_artifact_sha256,
            CLOUD_CONDITION: cloud_artifact_sha256,
        },
        "selective_escalation_case_ids": selected_ids,
        "conditions": condition_metrics,
        "paired_comparisons": {
            "c2_vs_c1": c2_pair,
            "c3_vs_c1": c3_pair,
        },
        "efficiency": {
            NO_AUDIT_CONDITION: {"planned_runner_attempts": 0},
            LOCAL_CONDITION: local_efficiency,
            CLOUD_CONDITION: cloud_efficiency,
            SELECTIVE_CONDITION: hybrid_efficiency,
        },
        "threshold_assessment": _threshold_assessment(
            c1=condition_metrics[LOCAL_CONDITION],
            c2=condition_metrics[CLOUD_CONDITION],
            c2_pair=c2_pair,
            c3_pair=c3_pair,
        ),
        "human_audit": {
            "required_before_contest_performance_claim": True,
            "packet_file": HUMAN_PACKET_NAME,
            "packet_payload_sha256": packet["packet_payload_sha256"],
            "key_file": HUMAN_KEY_NAME,
            "key_payload_sha256": key["key_payload_sha256"],
            "item_count": packet["item_count"],
        },
        "allowed_conclusion": (
            "On 30 reused frozen Gemma drafts, under one fixed A-only audit interface, "
            "the observed local/cloud/selective audit decisions differed by the reported amounts."
        ),
    }
    report = _with_content_hash(report_body, "summary_payload_sha256")
    return report, packet, key


def _write_once_or_identical(path: Path, document: Mapping[str, Any]) -> None:
    if path.exists():
        existing = load_strict_json(path)
        if canonical_json(existing) != canonical_json(document):
            raise FileExistsError(f"existing score artifact differs: {path}")
        return
    _atomic_write_json(path, document)


def score_frozen_experiment() -> Path:
    freeze, source, source_sha = _verify_freeze()
    output_directory = OUTPUT_ROOT / freeze["freeze_payload_sha256"]
    local_path = output_directory / f"{LOCAL_CONDITION}.json"
    cloud_path = output_directory / f"{CLOUD_CONDITION}.json"
    _require(local_path.is_file(), f"missing local artifact: {local_path}")
    _require(cloud_path.is_file(), f"missing cloud artifact: {cloud_path}")
    local_bytes = local_path.read_bytes()
    cloud_bytes = cloud_path.read_bytes()
    report, packet, key = score_documents(
        source=source,
        source_file_sha256=source_sha,
        freeze=freeze,
        local_artifact=load_strict_json(local_path),
        cloud_artifact=load_strict_json(cloud_path),
        local_artifact_sha256=sha256_bytes(local_bytes),
        cloud_artifact_sha256=sha256_bytes(cloud_bytes),
    )
    _write_once_or_identical(output_directory / HUMAN_PACKET_NAME, packet)
    _write_once_or_identical(output_directory / HUMAN_KEY_NAME, key)
    summary_path = output_directory / SUMMARY_NAME
    _write_once_or_identical(summary_path, report)
    return summary_path


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: list[str] | None = None) -> int:
    _build_parser().parse_args(argv)
    print(score_frozen_experiment())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
