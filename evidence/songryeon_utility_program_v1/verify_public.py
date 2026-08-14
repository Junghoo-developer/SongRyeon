#!/usr/bin/env python3
"""Fail-closed verifier for the public-safe RC6 evidence derivative."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SEAL_FILES = {"MANIFEST.json", "SHA256SUMS.txt"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify_tree(errors: list[str]) -> dict[str, Any] | None:
    try:
        manifest = load_json(ROOT / "MANIFEST.json")
    except Exception as exc:  # fail closed at the public boundary
        errors.append(f"manifest_read_error:{type(exc).__name__}")
        return None

    entries = manifest.get("declared_files", [])
    declared = {entry.get("path") for entry in entries}
    if None in declared or len(declared) != len(entries):
        errors.append("manifest_paths_invalid_or_duplicated")
        return manifest

    actual = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
    }
    expected = declared | SEAL_FILES
    if actual != expected:
        errors.append(
            "recursive_file_set_mismatch:missing="
            + repr(sorted(expected - actual))
            + ":extra="
            + repr(sorted(actual - expected))
        )

    for entry in entries:
        rel = entry["path"]
        path = ROOT / rel
        if not path.is_file():
            continue
        if path.stat().st_size != entry.get("bytes"):
            errors.append(f"size_mismatch:{rel}")
        if sha256_file(path) != entry.get("sha256"):
            errors.append(f"sha256_mismatch:{rel}")

    recomputed_tree = sha256_bytes(canonical_bytes(entries))
    if recomputed_tree != manifest.get("content_tree_sha256"):
        errors.append("content_tree_sha256_mismatch")

    expected_sums = {
        entry["path"]: entry["sha256"] for entry in entries
    }
    expected_sums["MANIFEST.json"] = sha256_file(ROOT / "MANIFEST.json")
    expected_text = "".join(
        f"{digest}  {rel}\n" for rel, digest in sorted(expected_sums.items())
    )
    try:
        observed_text = (ROOT / "SHA256SUMS.txt").read_text(encoding="ascii")
    except Exception as exc:
        errors.append(f"sha256sums_read_error:{type(exc).__name__}")
    else:
        if observed_text != expected_text:
            errors.append("sha256sums_content_mismatch")
    return manifest


def recompute_metrics(errors: list[str]) -> dict[str, Any]:
    try:
        receipt = load_jsonl(ROOT / "data" / "receipt_reconstruction_rows.jsonl")
        mechanism = load_jsonl(ROOT / "data" / "mechanism_boundary_rows.jsonl")
        summary = load_json(ROOT / "DERIVATIVE_SUMMARY.json")
    except Exception as exc:
        errors.append(f"metric_input_read_error:{type(exc).__name__}")
        return {}

    receipt_ids = [row.get("row_id") for row in receipt]
    if len(receipt) != 24 or len(set(receipt_ids)) != 24:
        errors.append("receipt_row_count_or_identity_invalid")
    for row in receipt:
        for arm in ("plain_log", "linked_receipt"):
            correct = row.get(arm, {}).get("reconstruction_correct_fields")
            total = row.get(arm, {}).get("reconstruction_total_fields")
            if not isinstance(correct, int) or not isinstance(total, int) or not (0 <= correct <= total == 5):
                errors.append(f"receipt_field_count_invalid:{row.get('row_id')}:{arm}")

    plain_correct = sum(bool(row["plain_log"]["audit_correct"]) for row in receipt)
    linked_correct = sum(bool(row["linked_receipt"]["audit_correct"]) for row in receipt)
    plain_field_correct = sum(row["plain_log"]["reconstruction_correct_fields"] for row in receipt)
    plain_field_total = sum(row["plain_log"]["reconstruction_total_fields"] for row in receipt)
    linked_field_correct = sum(row["linked_receipt"]["reconstruction_correct_fields"] for row in receipt)
    linked_field_total = sum(row["linked_receipt"]["reconstruction_total_fields"] for row in receipt)

    mechanism_ids = [row.get("row_id") for row in mechanism]
    if len(mechanism) != 64 or len(set(mechanism_ids)) != 64:
        errors.append("mechanism_row_count_or_identity_invalid")
    output_identity = sum(
        row["plain_trace"]["output"] == row["label_only"]["output"]
        for row in mechanism
    )
    consumption_identity = sum(
        row["plain_trace"]["actual_origin_r_consumed"]
        == row["label_only"]["actual_origin_r_consumed"]
        for row in mechanism
    )
    clean = [row for row in mechanism if row["clean_labels"] is True]

    def correct_count(arm: str) -> int:
        return sum(row[arm]["output"] == row["authored_target"] for row in clean)

    def r_count(arm: str) -> int:
        return sum(row[arm]["actual_origin_r_consumed"] is True for row in clean)

    computed = {
        "receipt_reconstruction": {
            "authored_case_count": len(receipt),
            "plain_log_audit_correct": f"{plain_correct}/{len(receipt)}",
            "linked_receipt_audit_correct": f"{linked_correct}/{len(receipt)}",
            "plain_log_mean_reconstruction_completeness": f"{plain_field_correct / plain_field_total:.3f}",
            "linked_receipt_mean_reconstruction_completeness": f"{linked_field_correct / linked_field_total:.3f}",
        },
        "mechanism_boundaries": {
            "authored_case_count": len(mechanism),
            "plain_vs_label_only_output_identity": f"{output_identity}/{len(mechanism)}",
            "plain_vs_label_only_actual_origin_r_consumption_identity": f"{consumption_identity}/{len(mechanism)}",
            "clean_label_case_count": len(clean),
            "clean_label_label_only_actual_origin_r_consumed": f"{r_count('label_only')}/{len(clean)}",
            "clean_label_enforced_a_only_actual_origin_r_consumed": f"{r_count('enforced_a_only')}/{len(clean)}",
            "clean_label_label_only_correct": f"{correct_count('label_only')}/{len(clean)}",
            "clean_label_enforced_a_only_correct": f"{correct_count('enforced_a_only')}/{len(clean)}",
        },
    }
    for section, expected in computed.items():
        if summary.get(section) != expected:
            errors.append(f"published_summary_mismatch:{section}")

    expected_exact = {
        "plain_log_audit_correct": "17/24",
        "linked_receipt_audit_correct": "24/24",
        "plain_log_mean_reconstruction_completeness": "0.925",
        "linked_receipt_mean_reconstruction_completeness": "1.000",
    }
    for key, value in expected_exact.items():
        if computed["receipt_reconstruction"].get(key) != value:
            errors.append(f"receipt_claim_gate_failed:{key}")
    expected_mechanism = {
        "plain_vs_label_only_output_identity": "64/64",
        "plain_vs_label_only_actual_origin_r_consumption_identity": "64/64",
        "clean_label_label_only_actual_origin_r_consumed": "16/32",
        "clean_label_enforced_a_only_actual_origin_r_consumed": "0/32",
        "clean_label_label_only_correct": "16/32",
        "clean_label_enforced_a_only_correct": "16/32",
    }
    for key, value in expected_mechanism.items():
        if computed["mechanism_boundaries"].get(key) != value:
            errors.append(f"mechanism_claim_gate_failed:{key}")
    return computed


def privacy_scan(errors: list[str]) -> dict[str, int]:
    windows_users = "\\" + "Users" + "\\"
    cloud_folder = "One" + "Drive"
    reasoning_field = "reasoning" + "_content"
    provider_field = "provider" + "_trace"
    concealed_scorer_marker = "private" + "_scorer"
    patterns = {
        "windows_absolute_path": re.compile(r"(?i)(?:^|[\s\"'])\b[A-Z]:[\\/]"),
        "user_profile_path": re.compile(
            r"(?i)(?:/" + "Users" + r"/|/" + "home" + r"/|"
            + re.escape(windows_users)
            + "|"
            + cloud_folder
            + ")"
        ),
        "email_address": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        "korean_mobile": re.compile(r"\b01[016789][ -]?\d{3,4}[ -]?\d{4}\b"),
        "resident_registration_like": re.compile(r"\b\d{6}-[1-4]\d{6}\b"),
        "sensitive_trace_field": re.compile(
            r"(?i)(chain_" + "of_thought|" + reasoning_field + "|" + provider_field
            + "|" + concealed_scorer_marker + r"|api[_-]?key|secret[_-]?key)"
        ),
    }
    counts = {name: 0 for name in patterns}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {
            ".json",
            ".jsonl",
            ".md",
            ".py",
            ".txt",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"non_utf8_text_artifact:{path.relative_to(ROOT).as_posix()}")
            continue
        for name, pattern in patterns.items():
            matches = pattern.findall(text)
            counts[name] += len(matches)
    for name, count in counts.items():
        if count:
            errors.append(f"privacy_scan_match:{name}:{count}")
    return counts


def verify_claim_boundaries(errors: list[str]) -> None:
    try:
        summary = load_json(ROOT / "DERIVATIVE_SUMMARY.json")
        boundaries = load_json(ROOT / "AUDIT_BOUNDARIES.json")
        provenance = load_json(ROOT / "TRANSFORMATION_PROVENANCE.json")
    except Exception as exc:
        errors.append(f"boundary_read_error:{type(exc).__name__}")
        return
    ceiling = summary.get("claim_ceiling", {})
    required_false = [
        "broad_utility_proven",
        "model_accuracy_improvement_proven",
        "human_workflow_utility_tested",
        "field_or_cross_domain_generalization_tested",
    ]
    for key in required_false:
        if ceiling.get(key) is not False:
            errors.append(f"claim_ceiling_not_false:{key}")
    receipt = boundaries.get("receipt_independent_audit", {})
    if receipt.get("source_packet_safe_for_external_blind_review") is not False:
        errors.append("blind_review_limitation_missing")
    if receipt.get("source_manifest_whole_tree_sealed") is not False:
        errors.append("source_seal_limitation_missing")
    if receipt.get("claim_ceiling") != "L1_auditability_within_authored_fixture_contract":
        errors.append("receipt_l1_ceiling_missing")
    mechanism = boundaries.get("mechanism_independent_audit", {})
    if mechanism.get("verdict") != "revise":
        errors.append("mechanism_revise_verdict_missing")
    if provenance.get("public_derivative_has_independent_seal") is not True:
        errors.append("derivative_seal_provenance_missing")


def main() -> int:
    errors: list[str] = []
    manifest = verify_tree(errors)
    metrics = recompute_metrics(errors)
    verify_claim_boundaries(errors)
    privacy_counts = privacy_scan(errors)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "declared_file_count": None if manifest is None else manifest.get("declared_file_count"),
        "content_tree_sha256": None if manifest is None else manifest.get("content_tree_sha256"),
        "recomputed_metrics": metrics,
        "privacy_scan_match_counts": privacy_counts,
        "execution": {"cpu_only": True, "gpu_calls": 0, "model_calls": 0, "network_calls": 0},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
