"""Run the preregistered Sol pilot with an API-compatible transport schema."""

from __future__ import annotations

import importlib.machinery
import os
import sys
import types


def _prepare_imports() -> None:
    """Refuse bytecode that could bypass the hashed source dependencies."""

    sys.pycache_prefix = None
    sys.dont_write_bytecode = True
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = (
        os.path.join(workspace, "evals", "semantic_calibration_v3"),
        os.path.join(workspace, "llm"),
    )
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

    eval_cache = os.path.join(workspace, "evals", "__pycache__")
    if os.path.isdir(eval_cache):
        bytecode.extend(
            os.path.join(eval_cache, name)
            for name in os.listdir(eval_cache)
            if name.startswith("semantic_calibration_codex_pilot.")
            and name.lower().endswith((".pyc", ".pyo"))
        )
    if bytecode:
        raise RuntimeError(f"pilot v2 refuses Python bytecode caches: {bytecode}")


def _install_minimal_evals_package() -> None:
    """Expose only the hashed eval modules without executing evals/__init__.py."""

    if "evals" in sys.modules:
        raise RuntimeError("pilot v2 imported evals before the integrity boundary")
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_path = os.path.join(workspace, "evals")
    package = types.ModuleType("evals")
    package.__file__ = os.path.join(package_path, "__init__.py")
    package.__package__ = "evals"
    package.__path__ = [package_path]
    package_spec = importlib.machinery.ModuleSpec(
        "evals",
        loader=None,
        is_package=True,
    )
    package_spec.submodule_search_locations = [package_path]
    package.__spec__ = package_spec
    sys.modules["evals"] = package


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("pilot v2 must be executed by direct file path, not -m")
if __name__ == "__main__":
    _prepare_imports()
    _install_minimal_evals_package()
else:
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import uuid


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
V3_ROOT = WORKSPACE_ROOT / "evals" / "semantic_calibration_v3"
PROTOCOL_PATH = (
    WORKSPACE_ROOT / "evals" / "semantic_calibration_codex_pilot_v2_PROTOCOL.md"
)
OUTPUT_PATH = (
    WORKSPACE_ROOT
    / ".tmp"
    / "evals"
    / "semantic_calibration_codex_pilot"
    / "sol-medium-hard-batches-v2.json"
)
PRIOR_V1_EVIDENCE_PATH = (
    WORKSPACE_ROOT
    / "evidence"
    / "semantic_calibration_codex_pilot"
    / "6e944771338e7e1887a448673e723508173b7173e3627895eda9443e00a418a9"
    / "pilot.json"
)

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from evals import semantic_calibration_codex_pilot as base  # noqa: E402
from evals.semantic_calibration_v3.schemas import (  # noqa: E402
    canonical_json,
    load_strict_json,
    parse_response,
)
from llm import ModelCallError  # noqa: E402


MODEL_NAME = "gpt-5.6-sol"
REASONING_EFFORT = "medium"
SDK_VERSION = "0.144.4"
EXPERIMENT_ID = "sol-medium-hard-batches-v2"
EXPECTED_V2_DEPENDENCY_HASHES = {
    "evals/semantic_calibration_codex_pilot.py": (
        "7e54c909f1f35ed4bf4b23f14bc14b0cd4832da29b1466862a0f8c2ef7b7863a"
    ),
    (
        "evidence/semantic_calibration_codex_pilot/"
        "6e944771338e7e1887a448673e723508173b7173e3627895eda9443e00a418a9/"
        "pilot.json"
    ): "6e944771338e7e1887a448673e723508173b7173e3627895eda9443e00a418a9",
}
EXPECTED_V2_REQUEST_HASHES = {
    base.EXPECTED_PLAN_IDS[0]: (
        "d66959ca140a32320de290f73ddc59b532d123330a98dbdf1a666ea032205d40"
    ),
    base.EXPECTED_PLAN_IDS[1]: (
        "6eb760df933994abeb7bc1553165ed7cc5668c0346837e0827a2ffce85f276b2"
    ),
    base.EXPECTED_PLAN_IDS[2]: (
        "648a2759bdf3f1078c3b9cf14ef06eb675cb6e5d8965a4100e255a2e5c7a08d6"
    ),
    base.EXPECTED_PLAN_IDS[3]: (
        "61549c5a10001defd77f0ad83d882721c04fca09eb898a709e0c482ce412d636"
    ),
}
EXPECTED_V2_SCHEMA_HASHES = {
    base.EXPECTED_PLAN_IDS[0]: (
        "1ae878c19778f43413890f65ecc6009985763f6c0eb74fa1cdac98725d6a3d80"
    ),
    base.EXPECTED_PLAN_IDS[1]: (
        "dcdfedbb3dafbdf81a6830f4aec30997821d6cc9688c8a4a04df1c31ad417ae0"
    ),
    base.EXPECTED_PLAN_IDS[2]: (
        "0f245b222558341b109b21f40f72cc02a8030eab0317bd01031d8bd66d19a709"
    ),
    base.EXPECTED_PLAN_IDS[3]: (
        "68440783f7328394197480b7d6ffcc5699634b72658d9abc8c72c179f8347c88"
    ),
}
FORBIDDEN_SCHEMA_KEYS = frozenset(
    {
        "oneOf",
        "allOf",
        "not",
        "dependentRequired",
        "dependentSchemas",
        "if",
        "then",
        "else",
        "const",
    }
)


def hash_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_v2_dependencies() -> None:
    base.validate_dependencies()
    for relative, expected in EXPECTED_V2_DEPENDENCY_HASHES.items():
        actual = base.sha256(WORKSPACE_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"pilot v2 dependency changed: {relative}")


def _contains_forbidden_schema_key(value) -> bool:
    if isinstance(value, dict):
        return bool(FORBIDDEN_SCHEMA_KEYS.intersection(value)) or any(
            _contains_forbidden_schema_key(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_schema_key(item) for item in value)
    return False


def build_transport_schema(source_schema: dict) -> dict:
    """Translate oneOf/const to the supported, logically equivalent dialect."""

    schema = deepcopy(source_schema)
    observation = schema["properties"]["claims"]["items"]["properties"][
        "observation"
    ]
    if set(observation) != {"oneOf"}:
        raise RuntimeError("source observation schema shape changed")
    variants = observation["oneOf"]
    if not isinstance(variants, list) or len(variants) != 2:
        raise RuntimeError("source observation variants changed")
    kinds = [
        variant.get("properties", {}).get("kind", {}).get("const")
        for variant in variants
    ]
    if kinds != ["return", "raise"]:
        raise RuntimeError("source observation kind order changed")

    translated_variants = deepcopy(variants)
    for variant in translated_variants:
        properties = variant["properties"]
        kind_value = properties["kind"].pop("const")
        properties["kind"].update(
            {
                "type": "string",
                "enum": [kind_value],
            }
        )
        value_json = properties["value_json"]
        if "const" in value_json:
            value = value_json.pop("const")
            value_json.update(
                {
                    "type": "string",
                    "enum": [value],
                }
            )

    observation.clear()
    observation["anyOf"] = translated_variants
    if _contains_forbidden_schema_key(schema):
        raise RuntimeError("transport schema contains an unsupported composition key")
    return schema


def transport_request_sha256(unit: dict, transport_schema: dict) -> str:
    return hash_json(
        {
            "system_prompt": unit["system_prompt"],
            "user_prompt": unit["user_prompt"],
            "response_schema": transport_schema,
        }
    )


def prepare_units(plan: dict) -> list[dict]:
    prepared = []
    for unit in base.select_pilot_units(plan):
        transport_schema = build_transport_schema(unit["response_schema"])
        schema_hash = hash_json(transport_schema)
        if schema_hash != EXPECTED_V2_SCHEMA_HASHES.get(unit["plan_id"]):
            raise RuntimeError(f"pilot v2 transport schema changed: {unit['plan_id']}")
        transport_hash = transport_request_sha256(unit, transport_schema)
        expected_hash = EXPECTED_V2_REQUEST_HASHES.get(unit["plan_id"])
        if transport_hash != expected_hash:
            raise RuntimeError(f"pilot v2 request changed: {unit['plan_id']}")
        prepared.append(
            {
                "source": unit,
                "transport_schema": transport_schema,
                "source_schema_sha256": hash_json(unit["response_schema"]),
                "transport_schema_sha256": schema_hash,
                "transport_request_sha256": transport_hash,
            }
        )
    return prepared


def run_pilot(output_path: Path = OUTPUT_PATH) -> dict:
    if output_path.resolve() != OUTPUT_PATH.resolve():
        raise ValueError(f"pilot v2 output must use canonical path: {OUTPUT_PATH}")
    base.validate_no_api_auth()
    validate_v2_dependencies()
    git_state = base.validate_published_clean_head()
    attempt_lock = base.acquire_attempt_lock(output_path)
    try:
        if output_path.exists():
            raise FileExistsError("the primary pilot v2 attempt already exists")
        return _run_locked_pilot(output_path, git_state)
    finally:
        attempt_lock.unlink(missing_ok=True)


def _run_locked_pilot(output_path: Path, git_state: dict[str, str]) -> dict:
    plan = load_strict_json(V3_ROOT / "control" / "run_plan.json")
    prepared_units = prepare_units(plan)
    source_units = [item["source"] for item in prepared_units]
    expected = base.build_expected_claims(
        source_units,
        load_strict_json(V3_ROOT / "control" / "oracle_results.json"),
    )

    client = base.StrictPilotCodexClient(
        model_name=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
    )
    started_at = time.time()
    document = {
        "schema_version": 2,
        "experiment_id": EXPERIMENT_ID,
        "run_id": uuid.uuid4().hex,
        "run_state": "running",
        "publishable": False,
        "official_score": False,
        "diagnostic_score": True,
        "agent_runtime": True,
        "purpose": "ceiling diagnostic after transport-schema repair",
        "prior_invalid_artifact_sha256": base.sha256(PRIOR_V1_EVIDENCE_PATH),
        "protocol_sha256": base.sha256(PROTOCOL_PATH),
        "base_dependency_hashes": dict(base.EXPECTED_DEPENDENCY_HASHES),
        "v2_dependency_hashes": dict(EXPECTED_V2_DEPENDENCY_HASHES),
        "git": git_state,
        "model_contract": {
            "model_name": MODEL_NAME,
            "reasoning_effort": REASONING_EFFORT,
            "sdk_version": SDK_VERSION,
            "maximum_request_count": 4,
            "claim_count": 12,
            "num_predict_semantics": "post-hoc SDK usage check, not server cap",
        },
        "transport_schema_policy": {
            "changed_path": "properties.claims.items.properties.observation",
            "source_union": "oneOf(return, raise)",
            "transport_shape": "anyOf(return, raise) with singleton enums",
            "logical_document_set_unchanged": True,
            "strict_posthoc_parser_unchanged": True,
        },
        "decision_rule": {
            "harder_v4_trigger_min_joint": 10,
            "required_parsed_units": 4,
        },
        "started_at_unix": started_at,
        "rows": [],
    }

    try:
        readiness = client.check_configuration()
        required_readiness = {
            "provider": "openai_codex",
            "execution_mode": "codex_account_integration",
            "model_name": MODEL_NAME,
            "reasoning_effort": REASONING_EFFORT,
            "sdk_version": SDK_VERSION,
        }
        if readiness != required_readiness:
            raise RuntimeError("Codex account/model readiness differs from v2 protocol")
        document["model_readiness"] = readiness
        base.write_document(output_path, document)

        for prepared in prepared_units:
            unit = prepared["source"]
            row = {
                "plan_id": unit["plan_id"],
                "case_id": unit["case_id"],
                "expected_ids": unit["expected_ids"],
                "source_effective_request_sha256": unit[
                    "effective_request_sha256"
                ],
                "source_response_schema_sha256": prepared[
                    "source_schema_sha256"
                ],
                "transport_response_schema_sha256": prepared[
                    "transport_schema_sha256"
                ],
                "transport_effective_request_sha256": prepared[
                    "transport_request_sha256"
                ],
                "attempt_id": uuid.uuid4().hex,
                "state": "started",
                "model_call_count": 0,
                "agent_tool_calls": [],
                "observed_item_types": [],
                "answer": None,
                "model_reply": None,
                "model_metrics": {},
                "parse_error": None,
                "claims": [],
                "error": None,
            }
            document["rows"].append(row)
            base.write_document(output_path, document)
            call_started = time.perf_counter()
            fatal_runtime_error = False
            try:
                client.last_item_types = ()
                reply = client.complete(
                    system_prompt=unit["system_prompt"],
                    user_prompt=unit["user_prompt"],
                    response_schema=prepared["transport_schema"],
                    num_predict=unit["num_predict"],
                )
                base.validate_output_budget(reply.metrics, unit["num_predict"])
                parsed, parse_error = parse_response(
                    reply.content,
                    unit["expected_ids"],
                    allowed_verdicts=("SUPPORTED", "UNSUPPORTED"),
                    allow_unknown=False,
                )
                row["answer"] = reply.content
                row["model_reply"] = {
                    "model": reply.model,
                    "done_reason": reply.done_reason,
                    "thinking": reply.thinking,
                }
                row["model_metrics"] = reply.metrics
                row["parse_error"] = parse_error
                if parse_error is None:
                    row["claims"] = base.score_parsed_claims(
                        parsed,
                        expected,
                        unit["expected_ids"],
                    )
            except ModelCallError as error:
                row["error"] = f"{type(error).__name__}: {error}"
                fatal_runtime_error = True
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
                fatal_runtime_error = True
            row["observed_item_types"] = list(client.last_item_types)
            row["model_call_count"] = 1
            row["latency_ms"] = round(
                (time.perf_counter() - call_started) * 1000,
                4,
            )
            row["state"] = "finished"
            base.write_document(output_path, document)
            if fatal_runtime_error:
                break

        final_readiness = client.check_configuration()
        if final_readiness != document["model_readiness"]:
            raise RuntimeError("Codex account/model readiness changed during pilot v2")
        parsed_units = sum(
            row["error"] is None and row["parse_error"] is None
            for row in document["rows"]
        )
        joint_correct = sum(
            claim["joint_correct"]
            for row in document["rows"]
            for claim in row["claims"]
        )
        document["summary"] = {
            "planned_units": 4,
            "attempted_units": len(document["rows"]),
            "parsed_units": parsed_units,
            "claim_count": 12,
            "joint_correct": joint_correct,
            "stopped_early": len(document["rows"]) < 4,
            "classification": base.classify_result(
                parsed_units=parsed_units,
                joint_correct=joint_correct,
            ),
            "usage": base.sum_metrics(document["rows"]),
            "latency_ms": round(
                sum(row["latency_ms"] for row in document["rows"]),
                4,
            ),
        }
        document["final_readiness"] = final_readiness
        document["finished_at_unix"] = time.time()
        document["run_state"] = "complete"
        base.write_document(output_path, document)
        return document
    except Exception:
        if output_path.exists():
            document["run_state"] = "invalid"
            document["finished_at_unix"] = time.time()
            base.write_document(output_path, document)
        raise
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    result = run_pilot(args.output)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
