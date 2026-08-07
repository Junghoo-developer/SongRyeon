from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from evals.semantic_ceiling_v4 import build_v4
from evals.semantic_ceiling_v4.schemas_v4 import (
    canonical_json,
    decode_wire_observation,
    load_strict_json,
    parse_response,
    response_schema,
)


ROOT = Path(build_v4.__file__).resolve().parent
UNIT_KEYS = {
    "plan_id",
    "case_id",
    "expected_ids",
    "internal_claim_ids",
    "system_prompt",
    "user_prompt",
    "response_schema",
    "num_predict",
    "effective_request_sha256",
}


@pytest.fixture(scope="module")
def documents():
    return build_v4.build_documents_verified()


def test_final_suite_builds_twice_with_dynamic_matrix_and_exact_balance(documents):
    plan, oracle = documents
    assert set(plan) == {"schema_version", "experiment_id", "units"}
    assert set(oracle) == {
        "schema_version",
        "python_version",
        "manifest_sha256",
        "results",
    }
    assert plan["schema_version"] == oracle["schema_version"] == 1
    assert plan["experiment_id"] == "sol-medium-semantic-ceiling-v4"
    assert oracle["python_version"].startswith("3.10.11 ")
    assert len(plan["units"]) == len(oracle["results"]) == 8

    claims = [claim for case in oracle["results"] for claim in case["claims"]]
    assert len(claims) == 24
    assert Counter(claim["verdict"] for claim in claims) == {
        "SUPPORTED": 12,
        "UNSUPPORTED": 12,
    }
    for position in range(3):
        assert Counter(
            case["claims"][position]["verdict"] for case in oracle["results"]
        ) == {"SUPPORTED": 4, "UNSUPPORTED": 4}

    manifest_bytes = (ROOT / "manifest.json").read_bytes()
    assert oracle["manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()


def test_plan_is_one_opaque_three_claim_batch_per_case(documents):
    plan, _ = documents
    manifest = load_strict_json(ROOT / "manifest.json")
    assert len(plan["units"]) == len(manifest["cases"])

    public_ids = []
    for unit, case in zip(plan["units"], manifest["cases"]):
        assert set(unit) == UNIT_KEYS
        assert unit["case_id"] == case["case_id"]
        assert len(unit["expected_ids"]) == 3
        assert len(unit["internal_claim_ids"]) == 3
        assert unit["internal_claim_ids"] == [claim["id"] for claim in case["claims"]]
        assert unit["num_predict"] == 2_400
        assert all(re.fullmatch(r"Q-[0-9a-f]{16}", item) for item in unit["expected_ids"])
        assert case["case_id"] not in unit["plan_id"]
        assert case["case_id"] not in unit["user_prompt"]
        assert case["source"] not in unit["user_prompt"]
        assert all(
            internal not in unit["user_prompt"]
            for internal in unit["internal_claim_ids"]
        )
        assert unit["user_prompt"].count('"expression"') == 3
        assert unit["effective_request_sha256"] == (
            build_v4.effective_request_sha256(unit)
        )
        public_ids.extend(unit["expected_ids"])
    assert len(public_ids) == len(set(public_ids)) == 24


def _walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_sol_schema_has_object_root_nested_anyof_and_closed_required_objects():
    schema = response_schema(["Q-a", "Q-b", "Q-c"])
    assert schema["type"] == "object"
    assert "anyOf" not in schema
    assert all("oneOf" not in item and "const" not in item for item in _walk(schema) if isinstance(item, dict))

    objects = [item for item in _walk(schema) if isinstance(item, dict) and item.get("type") == "object"]
    assert objects
    for item in objects:
        assert item["additionalProperties"] is False
        assert set(item["required"]) == set(item["properties"])

    observation = schema["properties"]["claims"]["items"]["properties"]["observation"]
    assert set(observation) == {"anyOf"}
    assert [
        variant["properties"]["kind"] for variant in observation["anyOf"]
    ] == [
        {"type": "string", "enum": ["return"]},
        {"type": "string", "enum": ["raise"]},
    ]
    assert observation["anyOf"][1]["properties"]["value_json"] == {
        "type": "string",
        "enum": ["null"],
    }


@pytest.mark.parametrize(
    "text",
    [
        '{"a":1,"a":2}',
        "NaN",
        "Infinity",
        "-Infinity",
        "1e999",
        '"\\ud800"',
    ],
)
def test_strict_json_rejects_duplicates_nonfinite_and_invalid_unicode(text):
    with pytest.raises((ValueError, UnicodeError)):
        build_v4.strict_json_loads(text)


def test_value_json_is_decoded_exactly_once_and_wrong_raise_payload_is_rejected():
    wire = {"kind": "return", "value_json": '"null"', "exception": None}
    decoded, error = decode_wire_observation(wire)
    assert error is None
    assert decoded == {"kind": "return", "value": "null", "exception": None}

    nested_duplicate = {
        "kind": "return",
        "value_json": '{"x":1,"x":2}',
        "exception": None,
    }
    assert decode_wire_observation(nested_duplicate)[1] == "value_json_not_strict_json"
    bad_raise = {"kind": "raise", "value_json": " null ", "exception": "TypeError"}
    assert decode_wire_observation(bad_raise)[1] == "raise_value_json_must_be_null"


def test_response_parser_rejects_outer_duplicates_and_returns_typed_values():
    answer = canonical_json(
        {
            "claims": [
                {
                    "id": "Q-a",
                    "verdict": "UNSUPPORTED",
                    "observation": {
                        "kind": "return",
                        "value_json": "[true,1,1.0]",
                        "exception": None,
                    },
                    "reason": "predicted actual value",
                }
            ]
        }
    )
    parsed, error = parse_response(answer, ["Q-a"])
    assert error is None
    assert [type(value) for value in parsed["Q-a"]["observation"]["value"]] == [
        bool,
        int,
        float,
    ]
    duplicate = answer.replace('"id":"Q-a"', '"id":"Q-a","id":"Q-a"')
    assert parse_response(duplicate, ["Q-a"])[1] == "answer_is_not_strict_json"


def test_request_identity_hashes_all_four_effective_fields(documents):
    unit = documents[0]["units"][0]
    baseline = build_v4.effective_request_sha256(unit)
    mutations = {
        "system_prompt": unit["system_prompt"] + "!",
        "user_prompt": unit["user_prompt"] + "!",
        "response_schema": {**unit["response_schema"], "title": "changed"},
        "num_predict": unit["num_predict"] + 1,
    }
    for field, value in mutations.items():
        changed = deepcopy(unit)
        changed[field] = value
        assert build_v4.effective_request_sha256(changed) != baseline


def test_duplicate_ids_odd_case_count_and_bad_balance_fail_closed():
    manifest = load_strict_json(ROOT / "manifest.json")
    duplicate = deepcopy(manifest)
    duplicate["cases"][1]["claims"][0]["id"] = duplicate["cases"][0]["claims"][0]["id"]
    with pytest.raises(build_v4.BuildValidationError, match="duplicate claim id"):
        build_v4._validate_manifest(duplicate)

    odd = deepcopy(manifest)
    odd["cases"].pop()
    with pytest.raises(build_v4.BuildValidationError, match="case count must be even"):
        build_v4._validate_manifest(odd)

    results = [
        {"claims": [{"verdict": "SUPPORTED"} for _ in range(3)]},
        {"claims": [{"verdict": "UNSUPPORTED"} for _ in range(3)]},
    ]
    build_v4.validate_oracle_balance(results)
    results[1]["claims"][0]["verdict"] = "SUPPORTED"
    with pytest.raises(build_v4.BuildValidationError, match="overall 50/50"):
        build_v4.validate_oracle_balance(results)


def _source_snapshot(path: Path, content: str) -> build_v4.SourceSnapshot:
    data = content.encode("utf-8")
    path.write_bytes(data)
    return build_v4.SourceSnapshot(
        declared_path="fixtures/test.py",
        resolved_path=path.resolve(),
        content_bytes=data,
        content_text=content,
        sha256=hashlib.sha256(data).hexdigest(),
    )


@pytest.mark.parametrize(
    ("content", "match"),
    [
        ("print('noise')\ndef observe():\n    return 1\n", "unexpected stdout"),
        (
            "import sys\nsys.stderr.write('noise')\ndef observe():\n    return 1\n",
            "unexpected stderr",
        ),
    ],
)
def test_oracle_rejects_stdout_and_stderr_anomalies(tmp_path, content, match):
    source = _source_snapshot(tmp_path / "test.py", content)
    with pytest.raises(build_v4.OracleExecutionError, match=match):
        build_v4._execute_claim(
            source,
            "observe",
            python_executable=sys.executable,
            timeout_seconds=5,
        )


def test_oracle_is_fresh_uses_isolation_flags_and_rejects_timeout(tmp_path):
    source = _source_snapshot(
        tmp_path / "fresh.py",
        "counter = 0\ndef observe():\n    global counter\n    counter += 1\n    return counter\n",
    )
    first = build_v4._execute_claim(
        source, "observe", python_executable=sys.executable, timeout_seconds=5
    )[1]
    second = build_v4._execute_claim(
        source, "observe", python_executable=sys.executable, timeout_seconds=5
    )[1]
    assert first == second == {"kind": "return", "value": 1, "exception": None}

    slow = _source_snapshot(
        tmp_path / "slow.py",
        "import time\ndef observe():\n    time.sleep(1)\n    return 1\n",
    )
    with pytest.raises(build_v4.OracleExecutionError, match="timeout"):
        build_v4._execute_claim(
            slow,
            "observe",
            python_executable=sys.executable,
            timeout_seconds=0.01,
        )
    assert '"-B"' not in build_v4.ORACLE_RUNNER  # flags belong to the process command


def test_source_path_and_symlink_escape_are_rejected(tmp_path):
    suite = tmp_path / "suite"
    fixtures = suite / "fixtures"
    fixtures.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("def observe():\n    return 1\n", encoding="utf-8")

    with pytest.raises(build_v4.BuildValidationError, match="normalized relative"):
        build_v4._resolve_source(suite.resolve(), "fixtures/../../outside.py")

    link = fixtures / "link.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable on this Windows host")
    with pytest.raises(build_v4.BuildValidationError, match="escapes suite root"):
        build_v4._resolve_source(suite.resolve(), "fixtures/link.py")


def test_verified_builder_detects_nondeterminism(monkeypatch):
    calls = iter([({"x": 1}, {"y": 1}), ({"x": 2}, {"y": 1})])
    monkeypatch.setattr(build_v4, "build_documents", lambda **_kwargs: next(calls))
    with pytest.raises(build_v4.BuildValidationError, match="not deterministic"):
        build_v4.build_documents_verified()


@pytest.mark.parametrize("hash_seed", ["0", "1", "42", "8849", "123456"])
def test_control_bytes_are_invariant_across_hash_seeds(tmp_path, hash_seed):
    """Five seeds times 24 fresh oracle calls cover the frozen 120-call matrix."""

    plan_path = tmp_path / f"plan-{hash_seed}.json"
    oracle_path = tmp_path / f"oracle-{hash_seed}.json"
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = hash_seed
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONPYCACHEPREFIX", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "build_v4.py"),
            "--plan-output",
            str(plan_path),
            "--oracle-output",
            str(oracle_path),
        ],
        cwd=ROOT.parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert plan_path.read_bytes() == (ROOT / "control" / "run_plan.json").read_bytes()
    assert oracle_path.read_bytes() == (
        ROOT / "control" / "oracle_results.json"
    ).read_bytes()
