"""사람 감사 뒤 대회용 결과 공개 가능 범위를 결정한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .protocol import (
    EXPERIMENT_ID,
    canonical_json_sha256,
    read_json_object,
    _write_new_json,
)
from .scorer import verify_unblinded_summary


AUDIT_FILENAME = "HUMAN_AUDIT.json"
DECISION_FILENAME = "PUBLICATION_DECISION.json"
_AUDIT_KEYS = {
    "schema_version",
    "experiment_id",
    "audit_status",
    "reviewer_id",
    "reviewer_type",
    "reviewer_disclosure",
    "no_cases_excluded_or_replaced",
    "raw_failure_rows_preserved",
    "claim_wording_reviewed",
    "items",
}
_ITEM_KEYS = {
    "blind_id",
    "verdict_parse_matches_answer",
    "explanation_supported_by_fixture",
    "ar_authority_labeling_accurate",
    "notes",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    _require(isinstance(value, dict), f"{label}은 객체여야 합니다.")
    actual = set(value)
    _require(
        actual == expected,
        f"{label} 필드가 다릅니다. missing={sorted(expected-actual)}, "
        f"unknown={sorted(actual-expected)}",
    )


def evaluate_publication_gate(
    experiment_root: Path,
    *,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """동결·기계 점수·사람 감사를 대조해 허용 가능한 공개 주장만 만든다."""

    root = Path(experiment_root).resolve(strict=True)
    summary = verify_unblinded_summary(root)
    freeze = {
        key: summary["provenance"][key]
        for key in (
            "experiment_id", "freeze_verified", "manifest_sha256",
            "system_source_tree_sha256", "protocol_tree_sha256",
            "planned_execution_count",
        )
    }
    audit = read_json_object(
        root / AUDIT_FILENAME if audit_path is None else Path(audit_path),
        "human audit",
    )
    _exact_keys(audit, _AUDIT_KEYS, "human audit")
    _require(audit["schema_version"] == 1, "audit schema version이 다릅니다.")
    _require(audit["experiment_id"] == EXPERIMENT_ID, "audit experiment ID가 다릅니다.")
    _require(audit["audit_status"] == "completed_human_review", "사람 감사 완료 상태가 아닙니다.")
    _require(isinstance(audit["reviewer_id"], str) and audit["reviewer_id"].strip(), "reviewer ID가 필요합니다.")
    _require(audit["reviewer_type"] in {"human_owner", "human_independent"}, "reviewer type이 사람이어야 합니다.")
    _require(isinstance(audit["reviewer_disclosure"], str) and audit["reviewer_disclosure"].strip(), "reviewer disclosure가 필요합니다.")
    for field in (
        "no_cases_excluded_or_replaced",
        "raw_failure_rows_preserved",
        "claim_wording_reviewed",
    ):
        _require(audit[field] is True, f"{field} 확인이 필요합니다.")

    items = audit["items"]
    _require(isinstance(items, list), "audit items는 배열이어야 합니다.")
    item_by_id = {}
    for index, item in enumerate(items):
        _exact_keys(item, _ITEM_KEYS, f"audit item {index}")
        blind_id = item["blind_id"]
        _require(isinstance(blind_id, str) and blind_id, "audit blind ID가 필요합니다.")
        _require(blind_id not in item_by_id, "audit blind ID가 중복됐습니다.")
        for field in (
            "verdict_parse_matches_answer",
            "explanation_supported_by_fixture",
            "ar_authority_labeling_accurate",
        ):
            _require(isinstance(item[field], bool), f"audit item {field}는 bool이어야 합니다.")
        _require(isinstance(item["notes"], str), "audit notes는 문자열이어야 합니다.")
        item_by_id[blind_id] = item

    required = set(summary["required_human_audit_blind_ids"])
    known_ids = {row["blind_id"] for row in summary["rows"]}
    unknown = sorted(set(item_by_id) - known_ids)
    _require(not unknown, f"summary에 없는 audit blind ID가 있습니다: {unknown[:5]}")
    missing = sorted(required - set(item_by_id))
    _require(not missing, f"필수 사람 감사 item이 빠졌습니다: {missing[:5]}")
    _require(
        all(item_by_id[blind_id]["verdict_parse_matches_answer"] for blind_id in required),
        "기계 verdict parse와 실제 답변이 다른 필수 item이 있습니다.",
    )
    sampled_explanations_supported = all(
        item_by_id[blind_id]["explanation_supported_by_fixture"]
        for blind_id in required
    )
    sampled_authority_accurate = all(
        item_by_id[blind_id]["ar_authority_labeling_accurate"]
        for blind_id in required
    )
    directional = summary["preregistered_directional_gate"]
    claim_allowed = directional["claim_allowed"] is True

    decision = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "decision_status": "publication_integrity_gate_passed",
        "publishable": True,
        "mechanical_performance_claim_allowed": claim_allowed,
        "sampled_explanation_grounding_passed": sampled_explanations_supported,
        "sampled_ar_authority_labeling_passed": sampled_authority_accurate,
        "whole_output_explanation_claim_allowed": False,
        "permitted_claim": (
            "동결된 24개 합성 Python holdout과 3개 seed에서 full 송련은 "
            "두 비교군보다 기계 verdict 정답 수가 많고 unsupported 명제를 "
            "SUPPORTED로 판정한 proxy 오류 수가 적었으며 positive guardrail을 지켰다."
            if claim_allowed
            else None
        ),
        "required_disclosures": [
            "첫 verdict만 기계 채점했고 설명 전체는 별도 사람 감사다.",
            "설명 감사는 사전 blind 표본 18개와 모든 기계 오답·실패의 합집합이며 216개 전체 설명 검증이 아니다.",
            "seed 반복은 독립 case가 아니다.",
            "full/no-Node4는 독립 end-to-end 실행이며 Node4 단독 인과효과가 아니다.",
            "합성 Python fixture 결과를 실제 업무 전체나 환각 제거로 일반화하지 않는다.",
            f"사람 감사자는 {audit['reviewer_type']}이며 disclosure를 함께 공개한다.",
        ],
        "forbidden_claims": [
            "환각을 완전히 제거했다.",
            "Node4 하나의 순수한 인과효과를 증명했다.",
            "통계적 유의성이나 실제 업무 일반화를 입증했다.",
            "216개 전체 답변 설명의 근거성과 A/R 표기가 검증됐다.",
        ],
        "human_audit": {
            "reviewer_id": audit["reviewer_id"],
            "reviewer_type": audit["reviewer_type"],
            "reviewer_disclosure": audit["reviewer_disclosure"],
            "required_item_count": len(required),
            "submitted_known_item_count": len(item_by_id),
            "selection_policy": "precommitted 18 blind IDs plus every mechanically incorrect or invalid row",
            "sampled_explanation_supported_for_all_required": sampled_explanations_supported,
            "sampled_ar_authority_accurate_for_all_required": sampled_authority_accurate,
        },
        "provenance": {
            **freeze,
            "summary_sha256": summary["summary_sha256"],
            "audit_sha256": canonical_json_sha256(audit),
        },
    }
    decision["decision_sha256"] = canonical_json_sha256(decision)
    _write_new_json(root / DECISION_FILENAME, decision)
    return decision


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="사람 감사와 동결 결과로 공개 가능성을 판정합니다.")
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = evaluate_publication_gate(
            args.experiment_root,
            audit_path=args.audit,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"contest holdout publication gate 실패: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
