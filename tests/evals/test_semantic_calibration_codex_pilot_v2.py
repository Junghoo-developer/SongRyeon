import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import evals.semantic_calibration_codex_pilot_v2 as pilot_v2
from evals.semantic_calibration_codex_pilot import EXPECTED_PLAN_IDS
from evals.semantic_calibration_codex_pilot_v2 import (
    EXPECTED_V2_DEPENDENCY_HASHES,
    EXPECTED_V2_REQUEST_HASHES,
    EXPECTED_V2_SCHEMA_HASHES,
    OUTPUT_PATH,
    PRIOR_V1_EVIDENCE_PATH,
    V3_ROOT,
    _contains_forbidden_schema_key,
    build_transport_schema,
    hash_json,
    transport_request_sha256,
)
from evals.semantic_calibration_v3.schemas import canonical_json, parse_response
from llm import ModelCallError


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def selected_units():
    plan = load_json(V3_ROOT / "control" / "run_plan.json")
    by_id = {unit["plan_id"]: unit for unit in plan["semantic_units"]}
    return [by_id[plan_id] for plan_id in EXPECTED_PLAN_IDS]


def assert_all_objects_are_closed_and_required(value):
    if isinstance(value, dict):
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False
            assert set(value.get("required", [])) == set(value.get("properties", {}))
        for child in value.values():
            assert_all_objects_are_closed_and_required(child)
    elif isinstance(value, list):
        for child in value:
            assert_all_objects_are_closed_and_required(child)


def test_transport_repair_changes_only_the_nested_observation_shape():
    for unit in selected_units():
        source = unit["response_schema"]
        source_before = canonical_json(source)
        transport = build_transport_schema(source)

        assert canonical_json(source) == source_before
        assert not _contains_forbidden_schema_key(transport)
        assert_all_objects_are_closed_and_required(transport)

        source_copy = json.loads(canonical_json(source))
        transport_copy = json.loads(canonical_json(transport))
        source_observation = source_copy["properties"]["claims"]["items"][
            "properties"
        ].pop("observation")
        transport_observation = transport_copy["properties"]["claims"]["items"][
            "properties"
        ].pop("observation")
        assert set(source_observation) == {"oneOf"}
        assert source_copy == transport_copy
        assert set(transport_observation) == {"anyOf"}
        assert len(transport_observation["anyOf"]) == 2
        expected_variants = source_observation["oneOf"]
        for variant in expected_variants:
            properties = variant["properties"]
            kind_value = properties["kind"].pop("const")
            properties["kind"] = {
                "type": "string",
                "enum": [kind_value],
            }
            if "const" in properties["value_json"]:
                value = properties["value_json"].pop("const")
                properties["value_json"] = {
                    "type": "string",
                    "enum": [value],
                }
        assert transport_observation["anyOf"] == expected_variants
        return_variant, raise_variant = transport_observation["anyOf"]
        assert return_variant["properties"]["kind"] == {
            "type": "string",
            "enum": ["return"],
        }
        assert raise_variant["properties"]["kind"] == {
            "type": "string",
            "enum": ["raise"],
        }
        assert raise_variant["properties"]["value_json"] == {
            "type": "string",
            "enum": ["null"],
        }


def test_unchanged_posthoc_parser_enforces_removed_cross_field_rule():
    unit = selected_units()[0]
    claims = []
    for claim_id in unit["expected_ids"]:
        claims.append(
            {
                "id": claim_id,
                "verdict": "SUPPORTED",
                "observation": {
                    "kind": "return",
                    "value_json": "1",
                    "exception": None,
                },
                "reason": "test",
            }
        )
    claims[0]["observation"]["exception"] = "ValueError"
    parsed, error = parse_response(
        canonical_json({"claims": claims}),
        unit["expected_ids"],
        allowed_verdicts=("SUPPORTED", "UNSUPPORTED"),
        allow_unknown=False,
    )
    assert parsed is None
    assert error == "return_exception_must_be_null"


def test_v2_transport_request_hashes_are_frozen():
    actual = {}
    schema_hashes = {}
    for unit in selected_units():
        transport = build_transport_schema(unit["response_schema"])
        actual[unit["plan_id"]] = transport_request_sha256(unit, transport)
        schema_hashes[unit["plan_id"]] = hash_json(transport)
    assert actual == EXPECTED_V2_REQUEST_HASHES
    assert schema_hashes == EXPECTED_V2_SCHEMA_HASHES


def test_v2_dependency_hashes_match():
    workspace = V3_ROOT.parents[1]
    actual = {
        relative: hashlib.sha256((workspace / relative).read_bytes()).hexdigest()
        for relative in EXPECTED_V2_DEPENDENCY_HASHES
    }
    assert actual == EXPECTED_V2_DEPENDENCY_HASHES


def test_v1_evidence_and_v2_output_are_separate():
    assert OUTPUT_PATH.name == "sol-medium-hard-batches-v2.json"
    assert PRIOR_V1_EVIDENCE_PATH.name == "pilot.json"
    assert hashlib.sha256(PRIOR_V1_EVIDENCE_PATH.read_bytes()).hexdigest() == (
        "6e944771338e7e1887a448673e723508173b7173e3627895eda9443e00a418a9"
    )


def test_direct_runner_bypasses_evals_package_initializer():
    runner = Path(pilot_v2.__file__).resolve()
    script = f"""
import importlib.util
import json
import pathlib
import sys

runner = pathlib.Path({str(runner)!r})
spec = importlib.util.spec_from_file_location("pilot_v2_probe", runner)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name in tuple(sys.modules):
    if name == "evals" or name.startswith("evals."):
        del sys.modules[name]
module._install_minimal_evals_package()
import evals.semantic_calibration_codex_pilot
print(json.dumps({{
    "has_evaluator_export": hasattr(sys.modules["evals"], "evaluate_run"),
    "loaded_evaluator": "evals.evaluator" in sys.modules,
    "loaded_runner": "evals.runner" in sys.modules,
    "loaded_base": "evals.semantic_calibration_codex_pilot" in sys.modules,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=runner.parents[1],
    )
    result = json.loads(completed.stdout)
    assert result == {
        "has_evaluator_export": False,
        "loaded_evaluator": False,
        "loaded_runner": False,
        "loaded_base": True,
    }


def test_hash_json_is_canonical():
    assert hash_json({"b": 1, "a": 2}) == hash_json({"a": 2, "b": 1})


class FakePilotClient:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = 0
        self.last_item_types = ()

    def check_configuration(self):
        return {
            "provider": "openai_codex",
            "execution_mode": "codex_account_integration",
            "model_name": "gpt-5.6-sol",
            "reasoning_effort": "medium",
            "sdk_version": "0.144.4",
        }

    def complete(self, *, response_schema, **_kwargs):
        self.calls += 1
        if self.fail:
            raise ModelCallError("synthetic transport failure")
        ids = response_schema["properties"]["claims"]["items"]["properties"][
            "id"
        ]["enum"]
        content = canonical_json(
            {
                "claims": [
                    {
                        "id": claim_id,
                        "verdict": "SUPPORTED",
                        "observation": {
                            "kind": "return",
                            "value_json": "null",
                            "exception": None,
                        },
                        "reason": "synthetic valid answer",
                    }
                    for claim_id in ids
                ]
            }
        )
        return SimpleNamespace(
            content=content,
            thinking="",
            model="gpt-5.6-sol",
            done_reason="stop",
            metrics={"output_tokens": 1, "total_tokens": 1},
        )

    def close(self):
        return None


def test_v2_success_path_calls_exactly_four_units(monkeypatch, tmp_path):
    fake = FakePilotClient()
    monkeypatch.setattr(
        pilot_v2.base,
        "StrictPilotCodexClient",
        lambda **_kwargs: fake,
    )

    result = pilot_v2._run_locked_pilot(tmp_path / "success.json", {"test": "git"})

    assert fake.calls == 4
    assert result["summary"]["attempted_units"] == 4
    assert result["summary"]["parsed_units"] == 4
    assert result["summary"]["stopped_early"] is False


def test_v2_runtime_failure_stops_after_first_call(monkeypatch, tmp_path):
    fake = FakePilotClient(fail=True)
    monkeypatch.setattr(
        pilot_v2.base,
        "StrictPilotCodexClient",
        lambda **_kwargs: fake,
    )

    result = pilot_v2._run_locked_pilot(tmp_path / "failure.json", {"test": "git"})

    assert fake.calls == 1
    assert result["summary"]["attempted_units"] == 1
    assert result["summary"]["parsed_units"] == 0
    assert result["summary"]["stopped_early"] is True
    assert result["summary"]["classification"] == "output_or_runtime_failure"
