#!/usr/bin/env python3
"""Build the public-safe RC6 evidence derivative from adjacent frozen studies.

This maintainer tool reads only five selected source artifacts, emits neutralized
row-level data, and seals the public directory.  It never writes outside ROOT.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROGRAM_ROOT = ROOT.parent

SOURCE_PATHS = {
    "receipt_results": PROGRAM_ROOT / "receipt_benchmark" / "RESULTS.json",
    "receipt_audit": PROGRAM_ROOT / "receipt_benchmark_audit" / "INDEPENDENT_AUDIT.json",
    "mechanism_rows": PROGRAM_ROOT
    / "imported_threads"
    / "role_a_fixed_input_causal_v1"
    / "evidence"
    / "SCORED_ROWS.jsonl",
    "mechanism_scores": PROGRAM_ROOT
    / "imported_threads"
    / "role_a_fixed_input_causal_v1"
    / "evidence"
    / "SCORES.json",
    "mechanism_audit": PROGRAM_ROOT
    / "imported_threads"
    / "role_a_fixed_input_causal_v1_audit"
    / "INDEPENDENT_AUDIT.json",
}

LOGICAL_SOURCE_PATHS = {
    "receipt_results": "receipt_benchmark/RESULTS.json",
    "receipt_audit": "receipt_benchmark_audit/INDEPENDENT_AUDIT.json",
    "mechanism_rows": "imported_threads/role_a_fixed_input_causal_v1/evidence/SCORED_ROWS.jsonl",
    "mechanism_scores": "imported_threads/role_a_fixed_input_causal_v1/evidence/SCORES.json",
    "mechanism_audit": "imported_threads/role_a_fixed_input_causal_v1_audit/INDEPENDENT_AUDIT.json",
}

DECLARED_CONTENT = {
    "AUDIT_BOUNDARIES.json",
    "CLAIM_LIMITS.md",
    "DERIVATIVE_SUMMARY.json",
    "README.md",
    "REPORT_KO.md",
    "TRANSFORMATION_PROVENANCE.json",
    "build_public_derivative.py",
    "data/mechanism_boundary_rows.jsonl",
    "data/receipt_reconstruction_rows.jsonl",
    "tests/test_verify_public.py",
    "verify_public.py",
}


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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(payload, encoding="utf-8", newline="\n")


def source_record(key: str) -> dict[str, Any]:
    path = SOURCE_PATHS[key]
    return {
        "logical_path": LOGICAL_SOURCE_PATHS[key],
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_receipt_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in results["rows"]:
        grouped[row["case_id"]][row["treatment"]] = row

    if len(grouped) != 24:
        raise ValueError(f"expected 24 receipt cases, found {len(grouped)}")

    public_rows: list[dict[str, Any]] = []
    for index, original_id in enumerate(sorted(grouped), start=1):
        pair = grouped[original_id]
        if set(pair) != {"plain_log", "linked_receipt"}:
            raise ValueError(f"incomplete receipt pair at source row {index}")
        plain = pair["plain_log"]
        linked = pair["linked_receipt"]
        public_rows.append(
            {
                "row_id": f"receipt-{index:03d}",
                "plain_log": {
                    "audit_correct": bool(plain["audit_correct"]),
                    "reconstruction_correct_fields": int(
                        plain["reconstruction_correct_fields"]
                    ),
                    "reconstruction_total_fields": int(
                        plain["reconstruction_total_fields"]
                    ),
                },
                "linked_receipt": {
                    "audit_correct": bool(linked["audit_correct"]),
                    "reconstruction_correct_fields": int(
                        linked["reconstruction_correct_fields"]
                    ),
                    "reconstruction_total_fields": int(
                        linked["reconstruction_total_fields"]
                    ),
                },
            }
        )
    return public_rows


def build_mechanism_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[row["case_id"]][row["condition"]] = row

    required = {"plain_trace", "ar_label_only", "enforced_a_only"}
    if len(grouped) != 64:
        raise ValueError(f"expected 64 mechanism cases, found {len(grouped)}")

    public_rows: list[dict[str, Any]] = []
    for index, original_id in enumerate(sorted(grouped), start=1):
        by_condition = grouped[original_id]
        if not required.issubset(by_condition):
            raise ValueError(f"incomplete mechanism conditions at source row {index}")
        plain = by_condition["plain_trace"]
        label = by_condition["ar_label_only"]
        enforced = by_condition["enforced_a_only"]
        clean_values = {bool(plain["clean_labels"]), bool(label["clean_labels"]), bool(enforced["clean_labels"])}
        target_values = {
            plain["gold_disposition"],
            label["gold_disposition"],
            enforced["gold_disposition"],
        }
        if len(clean_values) != 1 or len(target_values) != 1:
            raise ValueError(f"condition identity mismatch at source row {index}")

        def arm(row: dict[str, Any]) -> dict[str, Any]:
            return {
                "output": row["output"],
                "actual_origin_r_consumed": bool(
                    row["actual_origin_r_consumed"]
                ),
            }

        public_rows.append(
            {
                "row_id": f"mechanism-{index:03d}",
                "clean_labels": clean_values.pop(),
                "authored_target": target_values.pop(),
                "plain_trace": arm(plain),
                "label_only": arm(label),
                "enforced_a_only": arm(enforced),
            }
        )
    return public_rows


def derive_summary(
    receipt_rows: list[dict[str, Any]], mechanism_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    plain_correct = sum(row["plain_log"]["audit_correct"] for row in receipt_rows)
    linked_correct = sum(
        row["linked_receipt"]["audit_correct"] for row in receipt_rows
    )
    plain_field_correct = sum(
        row["plain_log"]["reconstruction_correct_fields"] for row in receipt_rows
    )
    plain_field_total = sum(
        row["plain_log"]["reconstruction_total_fields"] for row in receipt_rows
    )
    linked_field_correct = sum(
        row["linked_receipt"]["reconstruction_correct_fields"]
        for row in receipt_rows
    )
    linked_field_total = sum(
        row["linked_receipt"]["reconstruction_total_fields"]
        for row in receipt_rows
    )

    identity_output = sum(
        row["plain_trace"]["output"] == row["label_only"]["output"]
        for row in mechanism_rows
    )
    identity_consumption = sum(
        row["plain_trace"]["actual_origin_r_consumed"]
        == row["label_only"]["actual_origin_r_consumed"]
        for row in mechanism_rows
    )
    clean = [row for row in mechanism_rows if row["clean_labels"]]

    def correct_count(arm_name: str) -> int:
        return sum(row[arm_name]["output"] == row["authored_target"] for row in clean)

    def r_count(arm_name: str) -> int:
        return sum(row[arm_name]["actual_origin_r_consumed"] for row in clean)

    return {
        "schema": "songryeon.public-evidence-derivative.summary.v1",
        "receipt_reconstruction": {
            "authored_case_count": len(receipt_rows),
            "plain_log_audit_correct": f"{plain_correct}/{len(receipt_rows)}",
            "linked_receipt_audit_correct": f"{linked_correct}/{len(receipt_rows)}",
            "plain_log_mean_reconstruction_completeness": f"{plain_field_correct / plain_field_total:.3f}",
            "linked_receipt_mean_reconstruction_completeness": f"{linked_field_correct / linked_field_total:.3f}",
        },
        "mechanism_boundaries": {
            "authored_case_count": len(mechanism_rows),
            "plain_vs_label_only_output_identity": f"{identity_output}/{len(mechanism_rows)}",
            "plain_vs_label_only_actual_origin_r_consumption_identity": f"{identity_consumption}/{len(mechanism_rows)}",
            "clean_label_case_count": len(clean),
            "clean_label_label_only_actual_origin_r_consumed": f"{r_count('label_only')}/{len(clean)}",
            "clean_label_enforced_a_only_actual_origin_r_consumed": f"{r_count('enforced_a_only')}/{len(clean)}",
            "clean_label_label_only_correct": f"{correct_count('label_only')}/{len(clean)}",
            "clean_label_enforced_a_only_correct": f"{correct_count('enforced_a_only')}/{len(clean)}",
        },
        "claim_ceiling": {
            "receipt": "L1_auditability_within_authored_fixture_contract",
            "mechanism": "L0_deterministic_mechanism_conformance",
            "broad_utility_proven": False,
            "model_accuracy_improvement_proven": False,
            "human_workflow_utility_tested": False,
            "field_or_cross_domain_generalization_tested": False,
        },
        "public_recomputation": {
            "cpu_only": True,
            "gpu_calls": 0,
            "model_calls": 0,
            "network_calls": 0,
        },
    }


def build_audit_boundaries(
    receipt_audit: dict[str, Any], mechanism_audit: dict[str, Any]
) -> dict[str, Any]:
    blind = receipt_audit["pairing_and_leakage"]["blind_packet"]
    projection = receipt_audit["pairing_and_leakage"]["semantic_projection"]
    fairness = receipt_audit["auditor_results"]["contract_fairness"]
    receipt_manifest = receipt_audit["integrity"]["manifest"]
    return {
        "schema": "songryeon.public-evidence-derivative.audit-boundaries.v1",
        "receipt_independent_audit": {
            "result": receipt_audit["overall"]["fixed_fixture_result"],
            "claim_ceiling": receipt_audit["overall"]["claim_ceiling"],
            "auditors_and_fixtures_share_authored_contract": fairness[
                "auditors_and_fixtures_share_one_authored_contract"
            ],
            "independent_heldout_oracle": fairness["independent_heldout_oracle"],
            "full_artifact_information_equal": projection[
                "full_artifact_information_equal"
            ],
            "equal_after_removing_receipt_only_metadata": projection[
                "all_equal_after_removing_receipt_only_ids_links_digest_authority_and_index_metadata"
            ],
            "source_packet_safe_for_external_blind_review": blind[
                "safe_for_external_blind_review_as_is"
            ],
            "source_packet_family_prefix_occurrences": blind[
                "case_family_prefix_target_occurrences"
            ],
            "source_packet_changed_marker_occurrences": blind[
                "changed_after_projection_marker_occurrences"
            ],
            "source_reveal_was_adjacent": blind["reveal_file_adjacent_in_same_package"],
            "source_manifest_whole_tree_sealed": receipt_manifest[
                "whole_tree_sealed"
            ],
            "source_unsealed_import_cache_count": len(
                receipt_manifest["current_unsealed_pyc_files"]
            ),
            "source_finding_ids": [item["id"] for item in receipt_audit["findings"]],
        },
        "mechanism_independent_audit": {
            "verdict": mechanism_audit["verdict"],
            "claim_ceiling": mechanism_audit["claim_ceiling"]["maximum_level"],
            "plain_equals_label_decision_count": mechanism_audit[
                "matrix_and_isolation"
            ]["plain_equals_label_output_consumption_budget_route"],
            "semantic_target_blinding": mechanism_audit["gold_leakage"][
                "outcome_blinding"
            ],
            "current_runtime_post_state_receipt_supported": mechanism_audit[
                "runtime_failpoint"
            ]["applied_receipt_claim_supported"],
            "source_verifier_rejects_undeclared_recursive_addition": mechanism_audit[
                "manifest_behavior"
            ]["undeclared_recursive_addition_rejected"],
            "l2_operational_interception": mechanism_audit["claim_ceiling"][
                "l2_operational_interception"
            ],
            "l3_human_operational_utility": mechanism_audit["claim_ceiling"][
                "l3_human_operational_utility"
            ],
            "l4_generalization": mechanism_audit["claim_ceiling"][
                "l4_generalization"
            ],
            "source_finding_ids": [
                item["id"]
                for severity in ("P0", "P1", "P2")
                for item in mechanism_audit["findings"][severity]
            ],
        },
    }


def seal_public_tree() -> None:
    actual_content = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name not in {"MANIFEST.json", "SHA256SUMS.txt"}
    }
    if actual_content != DECLARED_CONTENT:
        missing = sorted(DECLARED_CONTENT - actual_content)
        extra = sorted(actual_content - DECLARED_CONTENT)
        raise ValueError(f"public content set mismatch; missing={missing}, extra={extra}")

    entries = []
    for rel in sorted(DECLARED_CONTENT):
        path = ROOT / rel
        entries.append(
            {"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    content_tree_sha256 = sha256_bytes(canonical_bytes(entries))
    manifest = {
        "schema": "songryeon.public-evidence-derivative.manifest.v1",
        "declared_file_count": len(entries),
        "declared_files": entries,
        "content_tree_sha256": content_tree_sha256,
        "content_tree_algorithm": "sha256(canonical-json(sorted declared_files[path,bytes,sha256]))",
        "exact_recursive_set_enforced_by": "verify_public.py",
        "seal_file_exclusions": ["MANIFEST.json", "SHA256SUMS.txt"],
        "signature_or_attestation": False,
    }
    write_json(ROOT / "MANIFEST.json", manifest)

    sums_entries = [
        (sha256_file(ROOT / rel), rel) for rel in sorted(DECLARED_CONTENT)
    ]
    sums_entries.append((sha256_file(ROOT / "MANIFEST.json"), "MANIFEST.json"))
    sums_text = "".join(f"{digest}  {rel}\n" for digest, rel in sorted(sums_entries, key=lambda item: item[1]))
    (ROOT / "SHA256SUMS.txt").write_text(sums_text, encoding="ascii", newline="\n")


def main() -> None:
    missing = [str(path) for path in SOURCE_PATHS.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen source artifacts: {missing}")

    receipt_results = load_json(SOURCE_PATHS["receipt_results"])
    receipt_audit = load_json(SOURCE_PATHS["receipt_audit"])
    mechanism_source_rows = load_jsonl(SOURCE_PATHS["mechanism_rows"])
    mechanism_scores = load_json(SOURCE_PATHS["mechanism_scores"])
    mechanism_audit = load_json(SOURCE_PATHS["mechanism_audit"])

    receipt_rows = build_receipt_rows(receipt_results)
    mechanism_rows = build_mechanism_rows(mechanism_source_rows)
    summary = derive_summary(receipt_rows, mechanism_rows)

    expected_receipt = receipt_results["aggregates"]
    if summary["receipt_reconstruction"]["plain_log_audit_correct"] != "17/24":
        raise ValueError("receipt source no longer reproduces 17/24")
    if expected_receipt["plain_log"]["mean_reconstruction_completeness"] < 0.924999999:
        raise ValueError("receipt source completeness no longer matches")
    clean_scores = mechanism_scores["aggregates"]["clean_labels"]
    if clean_scores["ar_label_only"]["correct"] != 16 or clean_scores["enforced_a_only"]["correct"] != 16:
        raise ValueError("mechanism clean-label accuracy source no longer matches")

    write_jsonl(ROOT / "data" / "receipt_reconstruction_rows.jsonl", receipt_rows)
    write_jsonl(ROOT / "data" / "mechanism_boundary_rows.jsonl", mechanism_rows)
    write_json(ROOT / "DERIVATIVE_SUMMARY.json", summary)
    write_json(
        ROOT / "AUDIT_BOUNDARIES.json",
        build_audit_boundaries(receipt_audit, mechanism_audit),
    )

    provenance = {
        "schema": "songryeon.public-evidence-derivative.transformation-provenance.v1",
        "derivative_id": "songryeon_utility_program_public_submission_v1",
        "derivation_date_kst": "2026-08-14",
        "source_artifacts": [source_record(key) for key in SOURCE_PATHS],
        "transformations": [
            "Pair receipt result rows by source case identity and replace source identities with neutral sequential row IDs.",
            "Retain only audit correctness and five-field reconstruction counts for the receipt comparison.",
            "Pair three mechanism conditions by source case identity and replace source identities with neutral sequential row IDs.",
            "Retain only clean-label status, authored target, output, and actual-origin R-consumption booleans.",
            "Recompute every published aggregate from the retained neutralized rows.",
            "Copy only bounded independent-audit conclusions needed to interpret the published aggregates.",
        ],
        "excluded_material": [
            {
                "category": "receipt source packets, reveal material, original fixture bodies, and family-coded identifiers",
                "reason": "not needed for aggregate recomputation; source independent audit found the packet unsuitable for external blind review",
            },
            {
                "category": "mechanism raw traces, candidate identifiers, receipts, and file-separated target artifacts",
                "reason": "not needed for the two published null and boundary checks",
            },
            {
                "category": "provider traces, model reasoning, credentials, concealed answer-key bytes, personal paths, and contact data",
                "reason": "privacy and minimum-necessary public disclosure",
            },
            {
                "category": "ARM exploratory artifacts",
                "reason": "not used as primary RC6 evidence",
            },
            {
                "category": "internal omnibus synthesis artifacts",
                "reason": "internal-only synthesis is not a public byte source and its hashes are not reused for this derivative",
            },
        ],
        "identity_and_information_warning": "The receipt comparison is not an equal-information formatting comparison: the linked artifact adds identifiers, links, index, authority, and digest metadata.",
        "public_derivative_has_independent_seal": True,
    }
    write_json(ROOT / "TRANSFORMATION_PROVENANCE.json", provenance)
    seal_public_tree()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
