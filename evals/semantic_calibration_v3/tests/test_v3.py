from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_oracle import build_oracle
from build_plan import build_plan
from schemas import encode_wire_observation, parse_response, response_schema
from score_v3 import score_contract_document, score_semantic_document
from artifacts import SYSTEM_NAME


READINESS = {"ollama_version": "test", "model": "gemma4:26b"}
HASH = "0" * 64
PUBLICATION = {"commit": "1" * 40, "remote_ref": "origin/test"}


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def answer(claims):
    return json.dumps(
        {
            "claims": [
                {
                    "id": claim["id"],
                    "verdict": claim["verdict"],
                    "observation": encode_wire_observation(
                        claim["observation"],
                        allow_unknown=True,
                    ),
                    "reason": "fixture-derived test answer",
                }
                for claim in claims
            ]
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def execution_fields():
    return {
        "schema_version": 1,
        "completed": True,
        "error": None,
        "latency_ms": 1,
        "model_call_count": 1,
        "agent_tool_calls": [],
        "model_metrics": {},
        "model_reply": {"model": "gemma4:26b", "done_reason": "stop", "thinking": ""},
        "state": "finished",
    }


def completed_document(run_id, rows, *, contract_preflight=None):
    return {
        "schema_version": 1,
        "stage": rows[0]["stage"],
        "system_name": SYSTEM_NAME,
        "freeze_sha256": HASH,
        "freeze_publication": PUBLICATION,
        "run_plan_sha256": HASH,
        "run_id": run_id,
        "run_state": "complete",
        "model_readiness": READINESS,
        "final_readiness": READINESS,
        "model_contract": {"model_name": "gemma4:26b"},
        "contract_preflight": contract_preflight,
        "rows": rows,
    }


def test_manifest_shape_and_oracle_balance():
    manifest = load("manifest.json")
    oracle = load("control/oracle_results.json")
    assert len(manifest["cases"]) == 12
    assert all(len(case["claims"]) == 3 for case in manifest["cases"])
    assert Counter(case["difficulty"] for case in manifest["cases"]) == {
        "anchor": 4,
        "medium": 4,
        "hard": 4,
    }
    by_tier = {}
    for case in oracle["results"]:
        by_tier.setdefault(case["difficulty"], Counter()).update(
            claim["verdict"] for claim in case["claims"]
        )
    assert by_tier == {
        "anchor": Counter(SUPPORTED=6, UNSUPPORTED=6),
        "medium": Counter(SUPPORTED=6, UNSUPPORTED=6),
        "hard": Counter(SUPPORTED=6, UNSUPPORTED=6),
    }
    for difficulty in ("anchor", "medium", "hard"):
        cases = [case for case in oracle["results"] if case["difficulty"] == difficulty]
        for position in range(3):
            assert Counter(case["claims"][position]["verdict"] for case in cases) == {
                "SUPPORTED": 2,
                "UNSUPPORTED": 2,
            }


def test_oracle_reproduces_in_fresh_processes():
    assert build_oracle() == load("control/oracle_results.json")


def test_plan_matrix_and_frozen_order():
    plan = load("control/run_plan.json")
    rebuilt = build_plan()
    assert plan == rebuilt
    assert len(plan["contract_units"]) == 4
    assert len(plan["semantic_units"]) == 48
    assert sum(unit["mode"] == "single" for unit in plan["semantic_units"]) == 36
    assert sum(unit["mode"] == "batch" for unit in plan["semantic_units"]) == 12
    by_case = {}
    for unit in plan["semantic_units"]:
        by_case.setdefault(unit["case_id"], []).append(unit["mode"])
        assert "expected_verdict" not in unit["user_prompt"]
        assert "oracle_results" not in unit["user_prompt"]
        assert unit["difficulty"] not in unit["user_prompt"].lower()
        assert "cal_a" not in unit["user_prompt"]
        assert "cal_m" not in unit["user_prompt"]
        assert "cal_h" not in unit["user_prompt"]
        assert all(value not in unit["user_prompt"] for value in unit["internal_claim_ids"])
        manifest_case = next(
            case for case in load("manifest.json")["cases"]
            if case["case_id"] == unit["case_id"]
        )
        assert manifest_case["source"] not in unit["user_prompt"]
    for index, modes in enumerate(by_case.values(), 1):
        assert modes == (
            ["batch", "single", "single", "single"]
            if index % 2
            else ["single", "single", "single", "batch"]
        )


def test_contract_prompt_uses_wire_but_semantic_proposition_stays_typed():
    plan = load("control/run_plan.json")
    for unit in plan["contract_units"]:
        supplied = json.loads(unit["user_prompt"].split("\n", 1)[1])
        assert all(
            set(claim["observation"]) == {"kind", "value_json", "exception"}
            for claim in supplied
        )
    for unit in plan["semantic_units"]:
        assert '"proposition_observation"' in unit["user_prompt"]
        assert '"value_json"' not in unit["user_prompt"]
        variants = unit["response_schema"]["properties"]["claims"]["items"][
            "properties"
        ]["observation"]["oneOf"]
        assert all("value_json" in variant["properties"] for variant in variants)
        assert all("value" not in variant["properties"] for variant in variants)


def test_typed_parser_rejects_wrong_shapes():
    valid = answer(
        [
            {
                "id": "X",
                "verdict": "SUPPORTED",
                "observation": {"kind": "return", "value": True, "exception": None},
            }
        ]
    )
    parsed, error = parse_response(valid, ["X"], allow_unknown=False)
    assert error is None
    assert parsed["X"]["observation"]["value"] is True
    invalid = json.dumps(
        {
            "claims": [
                {
                    "id": "X",
                    "verdict": "SUPPORTED",
                    "observation": {
                        "kind": "raise",
                        "value_json": "1",
                        "exception": "ValueError",
                    },
                    "reason": "bad",
                }
            ]
        }
    )
    assert (
        parse_response(invalid, ["X"], allow_unknown=False)[1]
        == "raise_value_json_must_be_null"
    )
    duplicate = valid.replace('"id":"X"', '"id":"X","id":"X"')
    assert parse_response(duplicate, ["X"], allow_unknown=False)[1] == "answer_is_not_strict_json"
    non_json_number = valid.replace('"value_json":"true"', '"value_json":NaN')
    assert parse_response(non_json_number, ["X"], allow_unknown=False)[1] == "answer_is_not_strict_json"
    unhashable_id = json.dumps(
        {
            "claims": [
                {
                    "id": [],
                    "verdict": "SUPPORTED",
                    "observation": {"kind": "return", "value": True, "exception": None},
                    "reason": "malformed identity",
                }
            ]
        }
    )
    assert parse_response(unhashable_id, ["X"], allow_unknown=False)[1] == "claim_identity_mismatch"
    assert response_schema(["X"], allow_unknown=False)["properties"]["claims"]["minItems"] == 1


def test_provider_schema_uses_only_anchored_patterns_while_parser_rejects_blank_reason():
    schema = response_schema(["X"], allow_unknown=False)
    patterns = []

    def collect(value):
        if isinstance(value, dict):
            if "pattern" in value:
                patterns.append(value["pattern"])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(schema)
    assert patterns
    assert all(pattern.startswith("^") and pattern.endswith("$") for pattern in patterns)
    reason_schema = schema["properties"]["claims"]["items"]["properties"]["reason"]
    assert reason_schema == {"type": "string", "minLength": 1}

    whitespace_reason = json.dumps(
        {
            "claims": [
                {
                    "id": "X",
                    "verdict": "SUPPORTED",
                    "observation": {
                        "kind": "return",
                        "value": True,
                        "exception": None,
                    },
                    "reason": "   ",
                }
            ]
        }
    )
    assert parse_response(whitespace_reason, ["X"], allow_unknown=False)[1] == "reason_invalid"


def test_perfect_contract_document_passes():
    cases = load("contract_cases.json")["cases"]
    units = load("control/run_plan.json")["contract_units"]
    run_id = "contract-test-run"
    rows = [
        {
            "plan_id": unit["plan_id"],
            "stage": unit["stage"],
            "case_id": case["case_id"],
            "mode": unit["mode"],
            "difficulty": unit["difficulty"],
            "expected_ids": unit["expected_ids"],
            "internal_claim_ids": unit["internal_claim_ids"],
            "effective_request_sha256": unit["effective_request_sha256"],
            "attempt_id": f"{run_id}:{index}:{unit['plan_id']}",
            "answer": answer(case["claims"]),
            **execution_fields(),
        }
        for index, (case, unit) in enumerate(zip(cases, units), 1)
    ]
    score = score_contract_document(completed_document(run_id, rows))
    assert score["passed"] is True
    assert score["exact_tasks"] == 4
    assert score["exact_claims"] == 6


def test_perfect_semantic_document_is_detected_as_ceiling():
    plan = load("control/run_plan.json")["semantic_units"]
    oracle = {
        claim["id"]: claim
        for case in load("control/oracle_results.json")["results"]
        for claim in case["claims"]
    }
    rows = []
    run_id = "semantic-test-run"
    for index, unit in enumerate(plan, 1):
        claims = [
            {**oracle[internal_id], "id": visible_id}
            for visible_id, internal_id in zip(
                unit["expected_ids"], unit["internal_claim_ids"]
            )
        ]
        rows.append(
            {
                "plan_id": unit["plan_id"],
                "stage": unit["stage"],
                "case_id": unit["case_id"],
                "mode": unit["mode"],
                "difficulty": unit["difficulty"],
                "expected_ids": unit["expected_ids"],
                "internal_claim_ids": unit["internal_claim_ids"],
                "effective_request_sha256": unit["effective_request_sha256"],
                "attempt_id": f"{run_id}:{index}:{unit['plan_id']}",
                "answer": answer(claims),
                **execution_fields(),
                "latency_ms": 1,
                "model_metrics": {"eval_count": 1},
            }
        )
    score = score_semantic_document(
        completed_document(
            run_id,
            rows,
            contract_preflight={"sha256": HASH, "run_id": "contract-test-run"},
        )
    )
    assert score["matrix_ok"] is True
    assert score["summaries"]["single"]["joint_correct"] == 36
    assert score["summaries"]["batch"]["joint_correct"] == 36
    assert score["paired"] == {"both_correct": 36}
    assert score["status"] == "semantic_ceiling"


def test_fixtures_compile_and_remain_small():
    paths = sorted((ROOT / "fixtures").glob("*.py"))
    assert len(paths) == 12
    for path in paths:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        assert len(source) <= 2_500
