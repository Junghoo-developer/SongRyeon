"""Strictly score contract and paired single/batch semantic calibration."""

from __future__ import annotations

import os
import sys


def _prepare_scored_imports():
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True
    experiment_root = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(os.path.dirname(experiment_root))
    roots = (experiment_root, os.path.join(workspace_root, "llm"))
    bytecode = []
    for root in roots:
        for current, directories, files in os.walk(root):
            bytecode.extend(
                os.path.join(current, name)
                for name in directories
                if name == "__pycache__"
            )
            bytecode.extend(
                os.path.join(current, name)
                for name in files
                if name.lower().endswith((".pyc", ".pyo"))
            )
    if bytecode:
        raise RuntimeError(f"scored imports refuse Python bytecode caches: {bytecode}")


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("scorer must be executed by direct file path, not -m")
if __name__ == "__main__":
    _prepare_scored_imports()
else:
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True

import argparse
from collections import Counter
import json
from pathlib import Path

from artifacts import SYSTEM_NAME, scoring_matrix_valid, validate_artifact_document
from freeze_v3 import sha256, verify_freeze, verify_freeze_publication
from schemas import canonical_json, load_strict_json, parse_response
from seal_v3 import verify_public_evidence


ROOT = Path(__file__).resolve().parent


def load_json(path):
    return load_strict_json(path)


def ensure_output_path_is_safe(output, protected_paths):
    resolved = output.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("score output must be outside the tracked calibration suite")
    protected = {Path(path).resolve() for path in protected_paths if path is not None}
    if resolved in protected:
        raise ValueError("score output collides with an input or freeze artifact")


def observation_equal(left, right):
    return canonical_json(left) == canonical_json(right)


def row_execution_valid(row, *, expected_model=None):
    reply = row.get("model_reply")
    return bool(
        row.get("completed") is True
        and row.get("state") == "finished"
        and isinstance(row.get("attempt_id"), str)
        and bool(row["attempt_id"])
        and row.get("error") is None
        and row.get("model_call_count") == 1
        and row.get("agent_tool_calls") == []
        and isinstance(row.get("answer"), str)
        and row["answer"].strip()
        and isinstance(reply, dict)
        and set(reply) == {"model", "done_reason", "thinking"}
        and isinstance(reply["model"], str)
        and bool(reply["model"])
        and (expected_model is None or reply["model"] == expected_model)
        and reply["done_reason"] == "stop"
        and reply["thinking"] == ""
    )


def run_completed_cleanly(document):
    return bool(
        isinstance(document, dict)
        and document.get("run_state") == "complete"
        and document.get("final_readiness") == document.get("model_readiness")
    )


def require_completed_run(document, label):
    if not run_completed_cleanly(document):
        raise ValueError(f"{label} did not complete cleanly")


def validate_contract_preflight_binding(
    semantic_document,
    contract_document,
    contract_sha256,
):
    if not isinstance(semantic_document, dict) or not isinstance(contract_document, dict):
        raise ValueError("contract preflight binding documents must be objects")
    expected = {
        "sha256": contract_sha256,
        "run_id": contract_document.get("run_id"),
    }
    if semantic_document.get("contract_preflight") != expected:
        raise ValueError("semantic result contract preflight binding mismatch")


def require_valid_matrix(score, label):
    if not score.get("matrix_ok"):
        raise ValueError(f"{label} row matrix is invalid")


def score_contract_document(document):
    if not isinstance(document, dict):
        document = {}
    units = load_json(ROOT / "control" / "run_plan.json")["contract_units"]
    expected_cases = {
        case["case_id"]: case
        for case in load_json(ROOT / "contract_cases.json")["cases"]
    }
    raw_rows = document.get("rows")
    rows = raw_rows if isinstance(raw_rows, list) else []
    matrix_ok = scoring_matrix_valid(document, units, expected_stage="contract")
    details = []
    exact_tasks = 0
    exact_claims = 0
    total_claims = sum(len(case["claims"]) for case in expected_cases.values())
    model_contract = document.get("model_contract")
    expected_model = (
        model_contract.get("model_name") if isinstance(model_contract, dict) else None
    )
    for raw_row in rows:
        row = raw_row if isinstance(raw_row, dict) else {}
        case = expected_cases.get(row.get("case_id"))
        if case is None:
            continue
        ids = [claim["id"] for claim in case["claims"]]
        execution_valid = row_execution_valid(row, expected_model=expected_model)
        if execution_valid:
            parsed, parse_error = parse_response(
                row.get("answer", ""),
                ids,
                allowed_verdicts=("SUPPORTED", "UNSUPPORTED", "INSUFFICIENT"),
                allow_unknown=True,
            )
        else:
            parsed, parse_error = None, "execution_invalid"
        claim_results = []
        for expected in case["claims"]:
            actual = parsed.get(expected["id"]) if parsed else None
            exact = bool(
                actual
                and actual["verdict"] == expected["verdict"]
                and observation_equal(actual["observation"], expected["observation"])
            )
            exact_claims += int(exact)
            claim_results.append({"id": expected["id"], "exact": exact})
        task_exact = (
            execution_valid
            and parse_error is None
            and all(item["exact"] for item in claim_results)
        )
        exact_tasks += int(task_exact)
        details.append(
            {
                "case_id": case["case_id"],
                "execution_valid": execution_valid,
                "parse_error": parse_error,
                "exact": task_exact,
                "claims": claim_results,
            }
        )
    passed = matrix_ok and exact_tasks == 4 and exact_claims == total_claims
    return {
        "passed": passed,
        "matrix_ok": matrix_ok,
        "exact_tasks": exact_tasks,
        "task_count": 4,
        "exact_claims": exact_claims,
        "claim_count": total_claims,
        "details": details,
    }


def oracle_map():
    document = load_json(ROOT / "control" / "oracle_results.json")
    return {
        claim["id"]: {
            "case_id": case["case_id"],
            "difficulty": case["difficulty"],
            **claim,
        }
        for case in document["results"]
        for claim in case["claims"]
    }


def expected_semantic_matrix():
    plan = load_json(ROOT / "control" / "run_plan.json")
    return plan["semantic_units"]


def score_semantic_document(document):
    if not isinstance(document, dict):
        document = {}
    units = expected_semantic_matrix()
    raw_rows = document.get("rows")
    rows = raw_rows if isinstance(raw_rows, list) else []
    matrix_ok = scoring_matrix_valid(document, units, expected_stage="semantic")
    oracle = oracle_map()
    model_contract = document.get("model_contract")
    expected_model = (
        model_contract.get("model_name") if isinstance(model_contract, dict) else None
    )
    summaries = {
        "single": Counter(units=36, claims=36),
        "batch": Counter(units=12, claims=36),
    }
    tier = {
        mode: {name: Counter(claims=12) for name in ("anchor", "medium", "hard")}
        for mode in ("single", "batch")
    }
    claim_results = {"single": {}, "batch": {}}
    unit_details = []

    for unit, raw_row in zip(units, rows):
        row = raw_row if isinstance(raw_row, dict) else {}
        mode = unit["mode"]
        ids = unit["expected_ids"]
        internal_ids = unit["internal_claim_ids"]
        execution_valid = row_execution_valid(row, expected_model=expected_model)
        if execution_valid:
            parsed, parse_error = parse_response(
                row.get("answer", ""),
                ids,
                allowed_verdicts=("SUPPORTED", "UNSUPPORTED"),
                allow_unknown=False,
            )
        else:
            parsed, parse_error = None, "execution_invalid"
        if execution_valid:
            summaries[mode]["completed_units"] += 1
        if parse_error is None:
            summaries[mode]["parsed_units"] += 1
            summaries[mode]["claims_in_parsed_units"] += len(ids)
        details = []
        for visible_id, claim_id in zip(ids, internal_ids):
            expected = oracle[claim_id]
            actual = parsed.get(visible_id) if parsed else None
            verdict_correct = bool(
                actual and actual["verdict"] == expected["verdict"]
            )
            observation_correct = bool(
                actual
                and observation_equal(
                    actual["observation"], expected["observation"]
                )
            )
            joint = verdict_correct and observation_correct
            summaries[mode]["verdict_correct"] += int(verdict_correct)
            summaries[mode]["observation_correct"] += int(observation_correct)
            summaries[mode]["joint_correct"] += int(joint)
            tier[mode][expected["difficulty"]]["joint_correct"] += int(joint)
            claim_results[mode][claim_id] = joint
            details.append(
                {
                    "id": claim_id,
                    "visible_id": visible_id,
                    "expected_verdict": expected["verdict"],
                    "expected_observation": expected["observation"],
                    "actual": actual,
                    "verdict_correct": verdict_correct,
                    "observation_correct": observation_correct,
                    "joint_correct": joint,
                }
            )
        if mode == "batch" and all(item["joint_correct"] for item in details):
            summaries[mode]["exact_three_claim_units"] += 1
        model_calls = row.get("model_call_count", 0)
        latency_ms = row.get("latency_ms", 0)
        summaries[mode]["model_calls"] += (
            model_calls if isinstance(model_calls, int) else 0
        )
        summaries[mode]["latency_ms"] += (
            latency_ms if isinstance(latency_ms, (int, float)) else 0
        )
        metrics = row.get("model_metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        summaries[mode]["generated_tokens"] += metrics.get("eval_count", 0) or 0
        unit_details.append(
            {
                "plan_id": unit["plan_id"],
                "mode": mode,
                "case_id": unit["case_id"],
                "execution_valid": execution_valid,
                "parse_error": parse_error,
                "claims": details,
            }
        )

    paired = Counter()
    paired_details = []
    for claim_id in oracle:
        single = claim_results["single"].get(claim_id, False)
        batch = claim_results["batch"].get(claim_id, False)
        label = (
            "both_correct"
            if single and batch
            else "single_only"
            if single
            else "batch_only"
            if batch
            else "neither"
        )
        paired[label] += 1
        paired_details.append(
            {"id": claim_id, "single_correct": single, "batch_correct": batch, "pair": label}
        )

    summary_document = {}
    for mode, counts in summaries.items():
        value = dict(counts)
        parsed_claims = value.get("claims_in_parsed_units", 0)
        value["strict_end_to_end_accuracy"] = value.get("joint_correct", 0) / 36
        value["semantic_given_parse"] = (
            value.get("joint_correct", 0) / parsed_claims if parsed_claims else 0.0
        )
        summary_document[mode] = value
    tier_document = {
        mode: {name: dict(counts) for name, counts in values.items()}
        for mode, values in tier.items()
    }

    single = summary_document["single"]
    batch = summary_document["batch"]
    single_joint = single.get("joint_correct", 0)
    batch_joint = batch.get("joint_correct", 0)
    anchor = tier_document["single"]["anchor"].get("joint_correct", 0)
    medium = tier_document["single"]["medium"].get("joint_correct", 0)
    hard = tier_document["single"]["hard"].get("joint_correct", 0)
    conditions = {
        "matrix_ok": matrix_ok and len(rows) == 48,
        "single_parse": single.get("parsed_units", 0) >= 35,
        "batch_parse": batch.get("parsed_units", 0) >= 11,
        "single_range": 20 <= single_joint <= 30,
        "batch_range": 18 <= batch_joint <= 30,
        "batch_net_loss": single_joint - batch_joint <= 5,
        "gradient": anchor >= medium >= hard,
        "anchor_hard_gap": anchor - hard >= 3,
        "anchor_floor": anchor >= 8,
        "hard_range": 2 <= hard <= 8,
    }
    if not conditions["matrix_ok"] or not conditions["single_parse"] or not conditions["batch_parse"]:
        status = "output_contract_or_matrix_failure"
    elif single_joint < 20 or hard <= 1:
        status = "semantic_floor"
    elif single_joint > 30 and batch_joint > 30:
        status = "semantic_ceiling"
    elif batch_joint < 18 or single_joint - batch_joint >= 6:
        status = "batch_assembly_confound"
    elif all(conditions.values()):
        status = "bare_gate_passed"
    else:
        status = "calibration_shape_rejected"
    return {
        "status": status,
        "matrix_ok": matrix_ok,
        "summaries": summary_document,
        "difficulty": tier_document,
        "paired": dict(paired),
        "gate_conditions": conditions,
        "paired_details": paired_details,
        "unit_details": unit_details,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--semantic", type=Path)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("score output already exists")
    ensure_output_path_is_safe(
        args.output,
        [
            args.contract,
            args.semantic,
            args.freeze,
            ROOT / "control" / "run_plan.json",
            ROOT / "control" / "oracle_results.json",
            ROOT / "manifest.json",
            ROOT / "contract_cases.json",
        ],
    )
    freeze = verify_freeze(args.freeze)
    freeze_sha = sha256(args.freeze)
    contract_sha = sha256(args.contract)
    contract_document = load_json(args.contract)
    if not isinstance(contract_document, dict):
        raise ValueError("contract result must be a JSON object")
    publication = contract_document.get("freeze_publication")
    verify_freeze_publication(publication, args.freeze)
    verify_public_evidence(
        args.contract,
        freeze_sha,
        "contract",
        publication["remote_ref"],
    )
    if sha256(args.contract) != contract_sha:
        raise RuntimeError("contract result changed while reading")
    run_plan_sha = sha256(ROOT / "control" / "run_plan.json")
    if contract_document.get("freeze_sha256") != freeze_sha:
        raise ValueError("contract result freeze identity mismatch")
    if contract_document.get("freeze_publication") != publication:
        raise ValueError("contract result freeze publication mismatch")
    if contract_document.get("run_plan_sha256") != run_plan_sha:
        raise ValueError("contract result plan identity mismatch")
    if contract_document.get("stage") != "contract":
        raise ValueError("contract result stage mismatch")
    if contract_document.get("system_name") != SYSTEM_NAME:
        raise ValueError("contract result system identity mismatch")
    if contract_document.get("model_contract") != freeze["model_contract"]:
        raise ValueError("contract result model contract mismatch")
    if contract_document.get("model_readiness") != freeze["model_readiness"]:
        raise ValueError("contract result model readiness mismatch")
    if contract_document.get("contract_preflight") is not None:
        raise ValueError("contract result must not reference another preflight")
    validate_artifact_document(
        contract_document,
        units=load_json(ROOT / "control" / "run_plan.json")["contract_units"],
        expected_stage="contract",
        expected_freeze_sha=freeze_sha,
        expected_freeze_publication=publication,
        expected_plan_sha=run_plan_sha,
        expected_model_contract=freeze["model_contract"],
        expected_readiness=freeze["model_readiness"],
        expected_contract_preflight=None,
        require_exact_rows=True,
        allow_started=False,
        allowed_run_states={"complete"},
    )
    require_completed_run(contract_document, "contract result")
    contract_score = score_contract_document(contract_document)
    require_valid_matrix(contract_score, "contract result")
    result = {
        "schema_version": 1,
        "freeze_sha256": freeze_sha,
        "run_plan_sha256": run_plan_sha,
        "input_artifacts": {
            "contract": {"path": str(args.contract.resolve()), "sha256": contract_sha}
        },
        "contract": contract_score,
    }
    if args.semantic:
        semantic_sha = sha256(args.semantic)
        semantic_document = load_json(args.semantic)
        if not isinstance(semantic_document, dict):
            raise ValueError("semantic result must be a JSON object")
        if sha256(args.semantic) != semantic_sha:
            raise RuntimeError("semantic result changed while reading")
        verify_public_evidence(
            args.semantic,
            freeze_sha,
            "semantic",
            publication["remote_ref"],
        )
        if semantic_document.get("freeze_sha256") != freeze_sha:
            raise ValueError("semantic result freeze identity mismatch")
        if semantic_document.get("freeze_publication") != publication:
            raise ValueError("semantic result freeze publication mismatch")
        if semantic_document.get("run_plan_sha256") != run_plan_sha:
            raise ValueError("semantic result plan identity mismatch")
        if semantic_document.get("stage") != "semantic":
            raise ValueError("semantic result stage mismatch")
        if semantic_document.get("system_name") != SYSTEM_NAME:
            raise ValueError("semantic result system identity mismatch")
        if semantic_document.get("model_contract") != freeze["model_contract"]:
            raise ValueError("semantic result model contract mismatch")
        if semantic_document.get("model_readiness") != freeze["model_readiness"]:
            raise ValueError("semantic result model readiness mismatch")
        validate_contract_preflight_binding(
            semantic_document,
            contract_document,
            contract_sha,
        )
        validate_artifact_document(
            semantic_document,
            units=load_json(ROOT / "control" / "run_plan.json")["semantic_units"],
            expected_stage="semantic",
            expected_freeze_sha=freeze_sha,
            expected_freeze_publication=publication,
            expected_plan_sha=run_plan_sha,
            expected_model_contract=freeze["model_contract"],
            expected_readiness=freeze["model_readiness"],
            expected_contract_preflight=semantic_document["contract_preflight"],
            require_exact_rows=True,
            allow_started=False,
            allowed_run_states={"complete"},
        )
        require_completed_run(semantic_document, "semantic result")
        result["input_artifacts"]["semantic"] = {
            "path": str(args.semantic.resolve()),
            "sha256": semantic_sha,
        }
        semantic_score = score_semantic_document(semantic_document)
        require_valid_matrix(semantic_score, "semantic result")
        result["semantic"] = semantic_score
        if not result["contract"]["passed"]:
            result["semantic"]["status"] = "contract_preflight_failed"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
