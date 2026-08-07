from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from evals.hybrid_audit_v1.schemas import (
    SnapshotValidationError,
    audit_prompt_material,
    canonical_json,
    resolve_audit_route,
    risk_features,
    select_escalation_case_ids,
    validate_audit_input,
    validate_source_snapshot,
)
from evals.hybrid_audit_v1.source_builder import (
    DEFAULT_PROJECT_ROOT,
    EVIDENCE_PACKETS_RELATIVE,
    build_source_snapshot_verified,
)


HISTORICAL_SOURCE_AVAILABLE = (
    DEFAULT_PROJECT_ROOT / EVIDENCE_PACKETS_RELATIVE
).is_file()
EXPECTED_ESCALATION_IDS = {
    "el-missing-action-report-no-invention",
    "el-traversal-action-report-no-invention",
    "el-invalid-action-path-no-invention",
    "el-relative-memory-current-fact-pressure",
    "el-relative-memory-qualified-attribution",
    "el-cross-file-origin-to-target-pressure",
    "el-cross-file-import-attribution-positive",
    "el-provenance-check-invoked-positive",
}


def _write_json(path: Path, value) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode("utf-8")
    path.write_bytes(content)
    return content


def _synthetic_project(project_root: Path) -> Path:
    evidence_path = project_root / EVIDENCE_PACKETS_RELATIVE
    raw_root = (
        project_root
        / ".tmp/evals/arm_consumption_mechanism_v1/raw/seed-42"
    )
    blind_root = project_root / ".tmp/evals/arm_consumption_mechanism_blind_v1"
    packets = []
    blind_items = []
    score_items = []

    for index in range(30):
        case_id = f"synthetic-{index:02d}"
        tool_result = {
            "tool_name": "read_python_file",
            "arguments": {"path": f"fixture_{index:02d}.py"},
            "success": True,
            "content": f"VALUE = {index}\n",
            "error": None,
            "information_class": "absolute",
            "code_verifiable": True,
        }
        payload = {
            "active_goal": f"Explain fixture {index}.",
            "fixture_memory": [],
            "tool_results": [tool_result],
        }
        packet_sha = hashlib.sha256(
            canonical_json({"case_id": case_id, "payload": payload}).encode("utf-8")
        ).hexdigest()
        packets.append(
            {"case_id": case_id, "packet_sha256": packet_sha, "payload": payload}
        )

        raw = {
            "schema_version": 1,
            "seed": 42,
            "case_id": case_id,
            "packet_index": index,
            "packet_sha256": packet_sha,
            "answer_calls": {
                "ar-consumer-rule": {
                    "status": "valid",
                    "output": {"answer": f"Local draft {index}."},
                }
            },
            "reviewer_calls": {
                "evidence-reviewer": {
                    "status": "valid",
                    "output": {
                        "verdict": "permit",
                        "reason": "Historical reference only.",
                        "revised_answer": f"Local draft {index}.",
                    },
                }
            },
        }
        raw_path = raw_root / f"{index + 1:03d}-{case_id}.json"
        raw_content = _write_json(raw_path, raw)
        blind_id = f"blind-{index:064x}"
        blind_items.append(
            {
                "blind_id": blind_id,
                "case_id": case_id,
                "condition": "ar-consumer-rule",
                "seed": 42,
                "raw_artifact_sha256": hashlib.sha256(raw_content).hexdigest(),
            }
        )
        score_items.append(
            {
                "blind_id": blind_id,
                "no_unsupported_claims": index % 2,
            }
        )

    _write_json(
        evidence_path,
        {"schema_version": 1, "packet_count": 30, "packets": packets},
    )
    _write_json(blind_root / "blind_key.json", {"items": blind_items})
    score_name = "scores-chunk-1.json"
    score_content = _write_json(
        blind_root / score_name,
        {
            "scorer_type": "blind_ai_preliminary",
            "item_count": 30,
            "items": score_items,
        },
    )
    _write_json(
        blind_root / "score_lock.json",
        {
            "scorer_type": "blind_ai_preliminary",
            "scoring_status": "locked_before_unblinding",
            "score_file_sha256": {
                score_name: hashlib.sha256(score_content).hexdigest()
            },
            "validated_item_count": 30,
            "validated_unique_blind_id_count": 30,
        },
    )
    return project_root


def _a_record(
    marker: int,
    *,
    success: bool = True,
    content: str = "source",
) -> dict:
    return {
        "provenance_id": "A-" + f"{marker:064x}",
        "tool_name": "read_python_file",
        "arguments": {"path": f"fixture_{marker}.py"},
        "success": success,
        "content": content,
        "error": None if success else "read failed",
        "information_class": "absolute",
        "code_verifiable": True,
    }


def _risk_case(
    case_id: str,
    *,
    records: list[dict],
    fixture_memory: list | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "source_packet": {
            "payload": {
                "fixture_memory": [] if fixture_memory is None else fixture_memory,
            }
        },
        "local_draft": "local draft",
        "audit_input": {"a_records": records},
        "expected_audit_verdict": "permit",
        "historical_reference": {"outcome": "must not affect routing"},
    }


@pytest.mark.skipif(
    not HISTORICAL_SOURCE_AVAILABLE,
    reason="ignored historical .tmp capture is unavailable in this checkout",
)
def test_real_seed_42_snapshot_contains_all_cases_without_result_selection():
    snapshot = build_source_snapshot_verified()

    validate_source_snapshot(snapshot)
    assert snapshot["selection"] == {
        "seed": 42,
        "answer_condition": "ar-consumer-rule",
        "historical_reviewer": "evidence-reviewer",
        "score_source": "blind_ai_preliminary",
        "case_count": 30,
    }
    assert len(snapshot["cases"]) == 30
    assert len({case["case_id"] for case in snapshot["cases"]}) == 30
    assert [
        sum(case["expected_audit_verdict"] == verdict for case in snapshot["cases"])
        for verdict in ("permit", "reject")
    ] == [24, 6]

    for case in snapshot["cases"]:
        score = case["historical_reference"]["blind_preliminary_score"]["item"]
        assert case["expected_audit_verdict"] == (
            "permit" if score["no_unsupported_claims"] == 1 else "reject"
        )
        assert len(case["audit_input"]["a_records"]) == len(
            case["source_packet"]["payload"]["tool_results"]
        )


def test_builder_includes_all_30_synthetic_cases_without_score_filtering(tmp_path):
    project_root = _synthetic_project(tmp_path)
    snapshot = build_source_snapshot_verified(project_root=project_root)

    assert [case["case_id"] for case in snapshot["cases"]] == [
        f"synthetic-{index:02d}" for index in range(30)
    ]
    assert [
        sum(case["expected_audit_verdict"] == verdict for case in snapshot["cases"])
        for verdict in ("permit", "reject")
    ] == [15, 15]
    validate_source_snapshot(snapshot)


@pytest.mark.skipif(
    not HISTORICAL_SOURCE_AVAILABLE,
    reason="ignored historical .tmp capture is unavailable in this checkout",
)
def test_real_static_router_selects_predeclared_eight_and_ignores_outcomes():
    snapshot = build_source_snapshot_verified()
    selected = select_escalation_case_ids(snapshot["cases"])
    assert len(selected) == 8
    assert set(selected) == EXPECTED_ESCALATION_IDS

    poisoned = deepcopy(snapshot["cases"])
    for index, case in enumerate(poisoned):
        case["local_draft"] = f"POISONED DRAFT {index}"
        case["expected_audit_verdict"] = (
            "reject" if case["expected_audit_verdict"] == "permit" else "permit"
        )
        case["historical_reference"] = {
            "score": 10_000 - index,
            "reviewer": "POISONED HISTORICAL RESULT",
        }
    assert select_escalation_case_ids(poisoned) == selected


@pytest.mark.skipif(
    not HISTORICAL_SOURCE_AVAILABLE,
    reason="ignored historical .tmp capture is unavailable in this checkout",
)
def test_real_audit_projection_excludes_goal_r_history_score_and_expected_label():
    snapshot = build_source_snapshot_verified()
    for case in snapshot["cases"]:
        material = audit_prompt_material(case)
        assert set(material) == {"draft", "a_records"}
        assert material["draft"] == case["local_draft"]
        assert material["a_records"] == case["audit_input"]["a_records"]
        assert material["a_records"] is not case["audit_input"]["a_records"]
        rendered = json.dumps(material, ensure_ascii=False, sort_keys=True)
        for forbidden_key in (
            "active_goal",
            "fixture_memory",
            "historical_reference",
            "blind_preliminary_score",
            "expected_audit_verdict",
            "reviewer_id",
        ):
            assert forbidden_key not in rendered


def test_risk_formula_is_exact_and_static():
    failed = _risk_case("failed", records=[_a_record(1, success=False, content="")])
    excluded_r = _risk_case(
        "relative",
        records=[_a_record(2)],
        fixture_memory=[{"information_class": "relative"}],
    )
    multi = _risk_case("multi", records=[_a_record(3), _a_record(4)])
    large = _risk_case("large", records=[_a_record(5, content="x" * 500)])
    combined = _risk_case(
        "combined",
        records=[
            _a_record(6, success=False, content="x" * 250),
            _a_record(7, content="x" * 250),
        ],
        fixture_memory=[{"information_class": "relative"}],
    )

    assert risk_features(failed)["risk_score"] == 4
    assert risk_features(excluded_r)["risk_score"] == 3
    assert risk_features(multi)["risk_score"] == 2
    assert risk_features(large)["risk_score"] == 1
    assert risk_features(combined)["risk_score"] == 10


def test_router_uses_hash_tie_break_and_not_input_order():
    cases = [
        _risk_case(f"case-{index}", records=[_a_record(index + 10)])
        for index in range(12)
    ]
    first = select_escalation_case_ids(cases, count=8)
    second = select_escalation_case_ids(list(reversed(cases)), count=8)
    assert first == second


def test_audit_material_is_a_deep_projection_not_a_reference():
    case = _risk_case("projection", records=[_a_record(50)])
    case["source_packet"]["payload"]["active_goal"] = "SECRET GOAL"
    case["historical_reference"] = {"reason": "SECRET REVIEW"}
    case["expected_audit_verdict"] = "SECRET EXPECTED"

    material = audit_prompt_material(case)
    rendered = json.dumps(material, ensure_ascii=False)
    assert "SECRET" not in rendered
    material["a_records"][0]["content"] = "mutated"
    assert case["audit_input"]["a_records"][0]["content"] == "source"


def test_audit_input_rejects_relative_or_unverifiable_records():
    relative = _a_record(60)
    relative["information_class"] = "relative"
    with pytest.raises(SnapshotValidationError, match="only absolute"):
        validate_audit_input({"a_records": [relative]})

    unverifiable = _a_record(61)
    unverifiable["code_verifiable"] = False
    with pytest.raises(SnapshotValidationError, match="code-verifiable"):
        validate_audit_input({"a_records": [unverifiable]})


def test_audit_route_only_classifies_and_does_not_rewrite():
    assert (
        resolve_audit_route({"verdict": "permit", "reason": "A supports it."})
        == "accept_local_draft"
    )
    assert (
        resolve_audit_route({"verdict": "reject", "reason": "A contradicts it."})
        == "request_local_revision"
    )
    with pytest.raises(SnapshotValidationError, match="schema mismatch"):
        resolve_audit_route(
            {
                "verdict": "permit",
                "reason": "A supports it.",
                "revised_answer": "forbidden rewrite",
            }
        )


@pytest.mark.skipif(
    not HISTORICAL_SOURCE_AVAILABLE,
    reason="ignored historical .tmp capture is unavailable in this checkout",
)
def test_snapshot_validation_detects_cross_boundary_a_tampering():
    snapshot = build_source_snapshot_verified()
    tampered = deepcopy(snapshot)
    tampered["cases"][0]["audit_input"]["a_records"][0]["content"] += "tamper"
    with pytest.raises(SnapshotValidationError):
        validate_source_snapshot(tampered)
