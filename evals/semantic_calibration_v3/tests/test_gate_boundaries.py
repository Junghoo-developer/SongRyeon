from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artifacts import SYSTEM_NAME
from schemas import encode_wire_observation
from score_v3 import score_semantic_document


READINESS = {"ollama_version": "test", "model": "gemma4:26b"}
HASH = "0" * 64
PUBLICATION = {"commit": "1" * 40, "remote_ref": "origin/test"}


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def oracle_by_id():
    return {
        claim["id"]: {**claim, "difficulty": case["difficulty"]}
        for case in load("control/oracle_results.json")["results"]
        for claim in case["claims"]
    }


def selected_ids(counts):
    oracle = oracle_by_id()
    result = set()
    for difficulty, count in counts.items():
        ids = [
            claim_id
            for claim_id, claim in oracle.items()
            if claim["difficulty"] == difficulty
        ]
        result.update(ids[:count])
    return result


def response_for_unit(unit, correct_ids):
    oracle = oracle_by_id()
    claims = []
    for visible_id, internal_id in zip(
        unit["expected_ids"],
        unit["internal_claim_ids"],
    ):
        expected = oracle[internal_id]
        verdict = expected["verdict"]
        if internal_id not in correct_ids:
            verdict = "UNSUPPORTED" if verdict == "SUPPORTED" else "SUPPORTED"
        claims.append(
            {
                "id": visible_id,
                "verdict": verdict,
                "observation": encode_wire_observation(
                    expected["observation"],
                    allow_unknown=False,
                ),
                "reason": "synthetic boundary answer",
            }
        )
    return json.dumps({"claims": claims}, ensure_ascii=False, separators=(",", ":"))


def semantic_document(
    single_counts,
    batch_counts,
    *,
    invalid_single=0,
    invalid_batch=0,
):
    units = load("control/run_plan.json")["semantic_units"]
    selected = {
        "single": selected_ids(single_counts),
        "batch": selected_ids(batch_counts),
    }
    invalid_remaining = {"single": invalid_single, "batch": invalid_batch}
    run_id = "synthetic-semantic-run"
    rows = []
    for index, unit in enumerate(units, 1):
        answer = response_for_unit(unit, selected[unit["mode"]])
        if invalid_remaining[unit["mode"]]:
            answer = "not strict json"
            invalid_remaining[unit["mode"]] -= 1
        rows.append(
            {
                "schema_version": 1,
                "plan_id": unit["plan_id"],
                "stage": unit["stage"],
                "case_id": unit["case_id"],
                "mode": unit["mode"],
                "difficulty": unit["difficulty"],
                "expected_ids": unit["expected_ids"],
                "internal_claim_ids": unit["internal_claim_ids"],
                "effective_request_sha256": unit["effective_request_sha256"],
                "attempt_id": f"{run_id}:{index}:{unit['plan_id']}",
                "completed": True,
                "answer": answer,
                "error": None,
                "model_call_count": 1,
                "agent_tool_calls": [],
                "model_reply": {
                    "model": "gemma4:26b",
                    "done_reason": "stop",
                    "thinking": "",
                },
                "state": "finished",
                "latency_ms": 1,
                "model_metrics": {"eval_count": 1},
            }
        )
    return {
        "schema_version": 1,
        "stage": "semantic",
        "system_name": SYSTEM_NAME,
        "freeze_sha256": HASH,
        "freeze_publication": PUBLICATION,
        "run_plan_sha256": HASH,
        "run_id": run_id,
        "run_state": "complete",
        "model_readiness": READINESS,
        "final_readiness": READINESS,
        "model_contract": {"model_name": "gemma4:26b"},
        "contract_preflight": {"sha256": HASH, "run_id": "contract"},
        "rows": rows,
    }


def test_parse_failures_are_reported_by_boundary_stage():
    counts = {"anchor": 12, "medium": 12, "hard": 12}
    document = semantic_document(counts, counts)
    batch_row = next(row for row in document["rows"] if row["mode"] == "batch")
    batch_answer = json.loads(batch_row["answer"])
    batch_answer["claims"][0]["observation"]["value_json"] = "NaN"
    batch_row["answer"] = json.dumps(batch_answer)

    single_rows = [row for row in document["rows"] if row["mode"] == "single"]
    single_rows[0]["answer"] = "not strict json"
    normalized_answer = json.loads(single_rows[1]["answer"])
    normalized_answer["claims"][0]["observation"]["exception"] = "ValueError"
    single_rows[1]["answer"] = json.dumps(normalized_answer)

    score = score_semantic_document(document)
    assert score["parse_error_stages"]["batch"] == {"inner_json_decode": 1}
    assert score["parse_error_stages"]["single"] == {
        "outer_json_or_schema": 1,
        "normalized_observation": 1,
    }
    assert score["parse_pipeline"]["batch"] == {
        "total_units": 12,
        "execution_success": 12,
        "outer_json_or_schema_success": 12,
        "inner_json_decode_success": 11,
        "normalized_observation_success": 11,
        "fully_parsed_units": 11,
    }
    assert score["parse_pipeline"]["single"] == {
        "total_units": 36,
        "execution_success": 36,
        "outer_json_or_schema_success": 35,
        "inner_json_decode_success": 35,
        "normalized_observation_success": 34,
        "fully_parsed_units": 34,
    }


def test_preregistered_bare_gate_pass_boundary():
    score = score_semantic_document(
        semantic_document(
            {"anchor": 8, "medium": 7, "hard": 5},
            {"anchor": 7, "medium": 6, "hard": 5},
        )
    )
    assert score["status"] == "bare_gate_passed"
    assert all(score["gate_conditions"].values())
    assert score["summaries"]["single"]["joint_correct"] == 20
    assert score["summaries"]["batch"]["joint_correct"] == 18
    assert score["difficulty"]["single"]["anchor"]["joint_correct"] == 8
    assert (
        score["difficulty"]["single"]["anchor"]["joint_correct"]
        - score["difficulty"]["single"]["hard"]["joint_correct"]
        == 3
    )


def test_remaining_inclusive_pass_boundaries():
    hard_floor = score_semantic_document(
        semantic_document(
            {"anchor": 9, "medium": 9, "hard": 2},
            {"anchor": 7, "medium": 6, "hard": 5},
        )
    )
    assert hard_floor["status"] == "bare_gate_passed"
    assert hard_floor["difficulty"]["single"]["hard"]["joint_correct"] == 2

    loss_five = score_semantic_document(
        semantic_document(
            {"anchor": 10, "medium": 8, "hard": 5},
            {"anchor": 7, "medium": 6, "hard": 5},
        )
    )
    assert loss_five["status"] == "bare_gate_passed"
    assert (
        loss_five["summaries"]["single"]["joint_correct"]
        - loss_five["summaries"]["batch"]["joint_correct"]
        == 5
    )

    upper = score_semantic_document(
        semantic_document(
            {"anchor": 11, "medium": 11, "hard": 8},
            {"anchor": 10, "medium": 10, "hard": 10},
        )
    )
    assert upper["status"] == "bare_gate_passed"
    assert upper["summaries"]["single"]["joint_correct"] == 30
    assert upper["summaries"]["batch"]["joint_correct"] == 30


def test_preregistered_floor_boundary():
    score = score_semantic_document(
        semantic_document(
            {"anchor": 8, "medium": 6, "hard": 5},
            {"anchor": 8, "medium": 6, "hard": 4},
        )
    )
    assert score["summaries"]["single"]["joint_correct"] == 19
    assert score["status"] == "semantic_floor"

    hard_floor = score_semantic_document(
        semantic_document(
            {"anchor": 10, "medium": 10, "hard": 1},
            {"anchor": 7, "medium": 6, "hard": 5},
        )
    )
    assert hard_floor["summaries"]["single"]["joint_correct"] == 21
    assert hard_floor["status"] == "semantic_floor"


def test_preregistered_batch_confound_boundary():
    score = score_semantic_document(
        semantic_document(
            {"anchor": 8, "medium": 7, "hard": 5},
            {"anchor": 6, "medium": 6, "hard": 5},
        )
    )
    assert score["summaries"]["batch"]["joint_correct"] == 17
    assert (
        score["summaries"]["single"]["joint_correct"]
        - score["summaries"]["batch"]["joint_correct"]
        == 3
    )
    assert score["status"] == "batch_assembly_confound"

    loss_six = score_semantic_document(
        semantic_document(
            {"anchor": 10, "medium": 8, "hard": 6},
            {"anchor": 7, "medium": 6, "hard": 5},
        )
    )
    assert loss_six["summaries"]["batch"]["joint_correct"] == 18
    assert (
        loss_six["summaries"]["single"]["joint_correct"]
        - loss_six["summaries"]["batch"]["joint_correct"]
        == 6
    )
    assert loss_six["status"] == "batch_assembly_confound"


def test_preregistered_shape_rejection_boundary():
    score = score_semantic_document(
        semantic_document(
            {"anchor": 8, "medium": 8, "hard": 8},
            {"anchor": 8, "medium": 8, "hard": 6},
        )
    )
    assert score["status"] == "calibration_shape_rejected"
    assert score["gate_conditions"]["anchor_hard_gap"] is False


def test_gradient_hard_upper_and_range_overflow_shape_rejections():
    gradient = score_semantic_document(
        semantic_document(
            {"anchor": 8, "medium": 9, "hard": 5},
            {"anchor": 7, "medium": 6, "hard": 5},
        )
    )
    assert gradient["gate_conditions"]["gradient"] is False
    assert gradient["status"] == "calibration_shape_rejected"

    hard_nine = score_semantic_document(
        semantic_document(
            {"anchor": 12, "medium": 9, "hard": 9},
            {"anchor": 10, "medium": 10, "hard": 10},
        )
    )
    assert hard_nine["gate_conditions"]["hard_range"] is False
    assert hard_nine["status"] == "calibration_shape_rejected"

    single_31 = score_semantic_document(
        semantic_document(
            {"anchor": 12, "medium": 11, "hard": 8},
            {"anchor": 10, "medium": 10, "hard": 10},
        )
    )
    assert single_31["summaries"]["single"]["joint_correct"] == 31
    assert single_31["summaries"]["batch"]["joint_correct"] == 30
    assert single_31["status"] == "calibration_shape_rejected"

    batch_31 = score_semantic_document(
        semantic_document(
            {"anchor": 11, "medium": 11, "hard": 8},
            {"anchor": 11, "medium": 10, "hard": 10},
        )
    )
    assert batch_31["summaries"]["single"]["joint_correct"] == 30
    assert batch_31["summaries"]["batch"]["joint_correct"] == 31
    assert batch_31["status"] == "calibration_shape_rejected"


def test_exact_ceiling_and_status_priority():
    ceiling = score_semantic_document(
        semantic_document(
            {"anchor": 12, "medium": 11, "hard": 8},
            {"anchor": 11, "medium": 10, "hard": 10},
        )
    )
    assert ceiling["summaries"]["single"]["joint_correct"] == 31
    assert ceiling["summaries"]["batch"]["joint_correct"] == 31
    assert ceiling["status"] == "semantic_ceiling"

    floor_and_confound = score_semantic_document(
        semantic_document(
            {"anchor": 8, "medium": 6, "hard": 5},
            {"anchor": 4, "medium": 3, "hard": 3},
        )
    )
    assert floor_and_confound["summaries"]["single"]["joint_correct"] == 19
    assert floor_and_confound["summaries"]["batch"]["joint_correct"] == 10
    assert floor_and_confound["status"] == "semantic_floor"


def test_parse_thresholds_accept_exactly_35_single_and_11_batch_units():
    score = score_semantic_document(
        semantic_document(
            {"anchor": 12, "medium": 12, "hard": 12},
            {"anchor": 12, "medium": 12, "hard": 12},
            invalid_single=1,
            invalid_batch=1,
        )
    )
    assert score["summaries"]["single"]["parsed_units"] == 35
    assert score["summaries"]["batch"]["parsed_units"] == 11
    assert score["gate_conditions"]["single_parse"] is True
    assert score["gate_conditions"]["batch_parse"] is True


def test_parse_thresholds_reject_34_single_or_10_batch_units():
    single_failure = score_semantic_document(
        semantic_document(
            {"anchor": 12, "medium": 12, "hard": 12},
            {"anchor": 12, "medium": 12, "hard": 12},
            invalid_single=2,
        )
    )
    assert single_failure["summaries"]["single"]["parsed_units"] == 34
    assert single_failure["status"] == "output_contract_or_matrix_failure"

    batch_failure = score_semantic_document(
        semantic_document(
            {"anchor": 12, "medium": 12, "hard": 12},
            {"anchor": 12, "medium": 12, "hard": 12},
            invalid_batch=2,
        )
    )
    assert batch_failure["summaries"]["batch"]["parsed_units"] == 10
    assert batch_failure["status"] == "output_contract_or_matrix_failure"
