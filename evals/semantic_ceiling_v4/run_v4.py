"""Execute and validate the one Semantic Ceiling v4 target-model attempt.

The canonical command is a direct-file ``python -I -B`` invocation. The startup
guard runs before any experiment or model-client module is imported so cached
bytecode cannot bypass the frozen source tree.
"""

from __future__ import annotations

import os
import sys


def reject_startup_caches(
    experiment_root: str | None = None,
    llm_root: str | None = None,
) -> None:
    """Reject bytecode and pytest caches inside either frozen code root."""

    sys.pycache_prefix = None
    if experiment_root is None:
        experiment_root = os.path.dirname(os.path.abspath(__file__))
    if llm_root is None:
        workspace_root = os.path.dirname(os.path.dirname(experiment_root))
        llm_root = os.path.join(workspace_root, "llm")
    offenders: list[str] = []
    for root in (experiment_root, llm_root):
        for current, directories, files in os.walk(root):
            offenders.extend(
                os.path.join(current, name)
                for name in directories
                if name in {"__pycache__", ".pytest_cache"}
            )
            offenders.extend(
                os.path.join(current, name)
                for name in files
                if name.lower().endswith((".pyc", ".pyo"))
            )
    if offenders:
        raise RuntimeError(
            "Semantic Ceiling v4 runner refuses Python bytecode or pytest "
            "caches: " + repr(sorted(set(offenders)))
        )


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("run_v4.py must be executed by direct file path, not -m")
if __name__ == "__main__":
    if not sys.dont_write_bytecode:
        raise RuntimeError("run_v4.py must be executed with python -B")
    if not sys.flags.isolated:
        raise RuntimeError("run_v4.py must be executed with python -I -B")
    reject_startup_caches()
sys.pycache_prefix = None
sys.dont_write_bytecode = True

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import math
from pathlib import Path
import re
import tempfile
import time
import uuid


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __package__:
    from .build_v4 import effective_request_sha256
    from .freeze_v4 import (
        FREEZE_PATH,
        ORACLE_PATH,
        PLAN_PATH,
        _verify_freeze_publication,
        load_strict_json,
        sha256,
        validate_published_clean_head,
        verify_freeze,
    )
    from .schemas_v4 import (
        canonical_json,
        parse_response,
        response_schema,
        validate_observation,
    )
else:
    from build_v4 import effective_request_sha256
    from freeze_v4 import (  # type: ignore[no-redef]
        FREEZE_PATH,
        ORACLE_PATH,
        PLAN_PATH,
        _verify_freeze_publication,
        load_strict_json,
        sha256,
        validate_published_clean_head,
        verify_freeze,
    )
    from schemas_v4 import (  # type: ignore[no-redef]
        canonical_json,
        parse_response,
        response_schema,
        validate_observation,
    )

from llm.codex_account import CodexAccountIntegrationClient, _read_usage_metrics
from llm.client import ModelResponseError


EXPERIMENT_ID = "sol-medium-semantic-ceiling-v4"
OUTPUT_ROOT = WORKSPACE_ROOT / ".tmp" / "evals" / "semantic_ceiling_v4"
MAX_REQUESTS = 8
CLAIMS_PER_UNIT = 3
CLAIM_COUNT = MAX_REQUESTS * CLAIMS_PER_UNIT
MAX_OUTPUT_TOKENS = 2_400
FORBIDDEN_AUTH_ENV = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CODEX_ACCESS_TOKEN",
)
PASSIVE_ITEM_TYPES = frozenset(
    {
        "AgentMessageThreadItem",
        "ReasoningThreadItem",
        "UserMessageThreadItem",
    }
)
USAGE_KEYS = (
    "cached_input_tokens",
    "input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
EXPECTED_READINESS = {
    "provider": "openai_codex",
    "execution_mode": "codex_account_integration",
    "model_name": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "sdk_version": "0.144.4",
}
ERROR_KEYS = {"type", "message"}
READINESS_KEYS = {"ok", "value", "error"}
ROW_KEYS = {
    "plan_id",
    "case_id",
    "expected_ids",
    "effective_request_sha256",
    "response_schema_sha256",
    "attempt_id",
    "state",
    "model_call_count",
    "started_at_unix",
    "finished_at_unix",
    "latency_ms",
    "observed_item_types",
    "answer",
    "model_metrics",
    "parse_error",
    "claims",
    "error",
}
CLAIM_SCORE_KEYS = {
    "id",
    "expected_verdict",
    "verdict_correct",
    "observation_correct",
    "joint_correct",
}
SUMMARY_KEYS = {
    "planned_units",
    "attempted_units",
    "parsed_units",
    "claim_count",
    "joint_correct",
    "supported_joint_correct",
    "unsupported_joint_correct",
    "copy_supported_baseline_joint_correct",
    "cluster_scores",
    "nonperfect_clusters",
    "zero_score_clusters",
    "stopped_early",
    "readiness_match",
    "classification",
    "usage",
    "latency_ms",
}
COMPLETE_DOCUMENT_KEYS = {
    "schema_version",
    "experiment_id",
    "run_id",
    "run_state",
    "freeze_sha256",
    "freeze_tree_sha256",
    "freeze_source_commit",
    "freeze_publication_commit",
    "model_contract",
    "study_sha256",
    "manifest_sha256",
    "plan_sha256",
    "oracle_sha256",
    "protocol_sha256",
    "initial_readiness",
    "final_readiness",
    "started_at_unix",
    "finished_at_unix",
    "rows",
    "summary",
}
HEX_32 = re.compile(r"^[0-9a-f]{32}$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class AuditedCodexClient(CodexAccountIntegrationClient):
    """Capture SDK item types before enforcing the no-tool boundary."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.last_item_types: tuple[str, ...] = ()
        self.last_model_metrics: dict[str, int] = {}

    def _parse_result(self, result, *, num_predict: int):
        candidate_metrics = _read_usage_metrics(getattr(result, "usage", None))
        try:
            self.last_model_metrics = _validate_usage(
                candidate_metrics,
                enforce_budget=False,
            )
        except ValueError:
            self.last_model_metrics = {}
        items = getattr(result, "items", None)
        if not isinstance(items, (list, tuple)) or not items:
            self.last_item_types = ()
            raise ModelResponseError("Codex SDK thread items are missing or invalid")
        item_types = tuple(
            type(getattr(item, "root", None)).__name__ for item in items
        )
        self.last_item_types = item_types
        if "AgentMessageThreadItem" not in item_types:
            raise ModelResponseError("Codex SDK result has no final agent message")
        if any(item_type not in PASSIVE_ITEM_TYPES for item_type in item_types):
            raise ModelResponseError("Codex SDK result contains forbidden activity")
        return super()._parse_result(result, num_predict=num_predict)


def canonical_artifact_path(freeze_sha: str) -> Path:
    if type(freeze_sha) is not str or SHA256_HEX.fullmatch(freeze_sha) is None:
        raise ValueError("freeze SHA-256 must be 64 lowercase hexadecimal characters")
    return OUTPUT_ROOT / freeze_sha / "run.json"


def attempt_lock_path(artifact_path: Path) -> Path:
    return Path(artifact_path).with_name("attempt.lock")


def _canonical_bytes(value: object) -> bytes:
    return canonical_json(value).encode("utf-8") + b"\n"


def _atomic_write(path: Path, value: dict) -> None:
    """Replace one checkpoint atomically after syncing its complete bytes."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(_canonical_bytes(value))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def reserve_attempt(artifact_path: Path, freeze_sha: str) -> Path:
    """Persistently reserve the sole attempt without overwriting any artifact."""

    artifact_path = Path(artifact_path)
    lock_path = attempt_lock_path(artifact_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        raise FileExistsError("the canonical v4 artifact already exists")
    payload = _canonical_bytes(
        {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "freeze_sha256": freeze_sha,
            "status": "canonical_attempt_reserved",
        }
    )
    try:
        descriptor = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError:
        raise FileExistsError(
            "a canonical v4 attempt is already reserved for this freeze"
        ) from None
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if artifact_path.exists():
        raise FileExistsError("the canonical v4 artifact appeared during reservation")
    return lock_path


def validate_no_api_auth(environment=os.environ) -> None:
    present = [name for name in FORBIDDEN_AUTH_ENV if name in environment]
    if present:
        raise RuntimeError(
            "v4 runner refuses API/access-token environment keys: "
            + ", ".join(present)
        )


def validate_source_import_provenance() -> None:
    expected = (
        (effective_request_sha256, ROOT / "build_v4.py"),
        (verify_freeze, ROOT / "freeze_v4.py"),
        (parse_response, ROOT / "schemas_v4.py"),
        (
            CodexAccountIntegrationClient,
            WORKSPACE_ROOT / "llm" / "codex_account.py",
        ),
    )
    for value, expected_path in expected:
        module = inspect.getmodule(value)
        actual_file = getattr(module, "__file__", None)
        if actual_file is None or Path(actual_file).resolve() != expected_path.resolve():
            raise RuntimeError(
                "v4 import provenance differs from frozen source: "
                + repr(getattr(value, "__name__", value))
            )


def validate_sdk_import_provenance() -> None:
    module = sys.modules.get("openai_codex")
    actual_file = getattr(module, "__file__", None)
    distribution = importlib.metadata.distribution("openai-codex")
    expected_file = Path(
        distribution.locate_file("openai_codex/__init__.py")
    ).resolve()
    if actual_file is None or Path(actual_file).resolve() != expected_file:
        raise RuntimeError("loaded openai_codex provenance differs from its RECORD")


def _hash_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _error_record(error: Exception) -> dict[str, str]:
    return {"type": type(error).__name__, "message": str(error)}


def _capture_readiness(client) -> dict:
    try:
        value = client.check_configuration()
    except Exception as error:
        return {"ok": False, "value": None, "error": _error_record(error)}
    return {
        "ok": value == EXPECTED_READINESS,
        "value": value,
        "error": None,
    }


def _validate_error_record(value, label: str) -> None:
    if (
        type(value) is not dict
        or set(value) != ERROR_KEYS
        or type(value["type"]) is not str
        or not value["type"]
        or type(value["message"]) is not str
    ):
        raise ValueError(f"{label} is not a structured error record")


def _validate_readiness_witness(value, label: str) -> None:
    if type(value) is not dict or set(value) != READINESS_KEYS:
        raise ValueError(f"{label} readiness witness fields differ")
    if type(value["ok"]) is not bool:
        raise ValueError(f"{label} readiness ok flag is invalid")
    if value["error"] is None:
        readiness = value["value"]
        if (
            type(readiness) is not dict
            or set(readiness) != set(EXPECTED_READINESS)
            or any(type(item) is not str for item in readiness.values())
            or value["ok"] != (readiness == EXPECTED_READINESS)
        ):
            raise ValueError(f"{label} readiness value is invalid")
    else:
        if value["ok"] or value["value"] is not None:
            raise ValueError(f"{label} readiness error combination is invalid")
        _validate_error_record(value["error"], f"{label} readiness")


def _readiness_matches(initial: dict, final: dict) -> bool:
    return bool(
        initial["ok"]
        and final["ok"]
        and initial["value"] == final["value"] == EXPECTED_READINESS
    )


def _validate_usage(metrics, *, enforce_budget: bool) -> dict[str, int]:
    if type(metrics) is not dict or set(metrics) != set(USAGE_KEYS):
        raise ValueError("model usage fields differ from the v4 contract")
    if any(type(metrics[key]) is not int or metrics[key] < 0 for key in USAGE_KEYS):
        raise ValueError("model usage values must be nonnegative integers")
    if metrics["total_tokens"] != metrics["input_tokens"] + metrics["output_tokens"]:
        raise ValueError("model total_tokens is inconsistent")
    if metrics["cached_input_tokens"] > metrics["input_tokens"]:
        raise ValueError("cached input tokens exceed input tokens")
    if metrics["reasoning_output_tokens"] > metrics["output_tokens"]:
        raise ValueError("reasoning output tokens exceed output tokens")
    if enforce_budget and metrics["output_tokens"] > MAX_OUTPUT_TOKENS:
        raise ValueError("model output exceeded the frozen batch budget")
    return {key: metrics[key] for key in USAGE_KEYS}


def _sum_usage(rows: list[dict]) -> dict[str, int]:
    total = {key: 0 for key in USAGE_KEYS}
    for row in rows:
        try:
            metrics = _validate_usage(
                row["model_metrics"],
                enforce_budget=False,
            )
        except ValueError:
            continue
        for key in USAGE_KEYS:
            total[key] += metrics[key]
    return total


def build_expected_claims(plan: dict, oracle: dict) -> dict[str, dict[str, dict]]:
    """Validate both controls and map opaque public IDs to oracle claims."""

    if (
        type(plan) is not dict
        or set(plan) != {"schema_version", "experiment_id", "units"}
        or plan["schema_version"] != 1
        or plan["experiment_id"] != EXPERIMENT_ID
        or type(plan["units"]) is not list
        or len(plan["units"]) != MAX_REQUESTS
    ):
        raise ValueError("run plan identity or cardinality differs")
    if (
        type(oracle) is not dict
        or set(oracle)
        != {"schema_version", "python_version", "manifest_sha256", "results"}
        or oracle["schema_version"] != 1
        or type(oracle["results"]) is not list
        or len(oracle["results"]) != MAX_REQUESTS
    ):
        raise ValueError("oracle identity or cardinality differs")

    cases: dict[str, dict] = {}
    for case in oracle["results"]:
        if type(case) is not dict or type(case.get("case_id")) is not str:
            raise ValueError("oracle case is invalid")
        if case["case_id"] in cases:
            raise ValueError("oracle case ID is duplicated")
        cases[case["case_id"]] = case

    expected: dict[str, dict[str, dict]] = {}
    public_ids: set[str] = set()
    plan_ids: set[str] = set()
    case_ids: set[str] = set()
    for unit in plan["units"]:
        if type(unit) is not dict:
            raise ValueError("run plan unit is invalid")
        plan_id = unit.get("plan_id")
        case_id = unit.get("case_id")
        expected_ids = unit.get("expected_ids")
        internal_ids = unit.get("internal_claim_ids")
        if (
            type(plan_id) is not str
            or not plan_id
            or plan_id in plan_ids
            or type(case_id) is not str
            or not case_id
            or case_id in case_ids
            or type(expected_ids) is not list
            or len(expected_ids) != CLAIMS_PER_UNIT
            or any(type(item) is not str or not item for item in expected_ids)
            or len(set(expected_ids)) != CLAIMS_PER_UNIT
            or public_ids.intersection(expected_ids)
            or type(internal_ids) is not list
            or len(internal_ids) != CLAIMS_PER_UNIT
            or any(type(item) is not str or not item for item in internal_ids)
            or len(set(internal_ids)) != CLAIMS_PER_UNIT
            or unit.get("num_predict") != MAX_OUTPUT_TOKENS
        ):
            raise ValueError("run plan unit identity differs")
        if unit.get("response_schema") != response_schema(expected_ids):
            raise ValueError("run plan response schema differs")
        if unit.get("effective_request_sha256") != effective_request_sha256(unit):
            raise ValueError("run plan effective request hash differs")
        case = cases.get(case_id)
        if case is None:
            raise ValueError("run plan case is absent from oracle")
        claims = case.get("claims")
        if type(claims) is not list or len(claims) != CLAIMS_PER_UNIT:
            raise ValueError("oracle case claim cardinality differs")
        internal = {}
        for claim in claims:
            if (
                type(claim) is not dict
                or set(claim) != {"id", "verdict", "observation"}
                or type(claim["id"]) is not str
                or claim["id"] in internal
                or claim["verdict"] not in {"SUPPORTED", "UNSUPPORTED"}
                or validate_observation(claim["observation"], allow_unknown=False)
                is not None
            ):
                raise ValueError("oracle claim is invalid")
            internal[claim["id"]] = claim
        if set(internal_ids) != set(internal):
            raise ValueError("run plan internal claim IDs differ from oracle")
        expected[plan_id] = {
            public_id: internal[internal_id]
            for internal_id, public_id in zip(
                internal_ids,
                expected_ids,
                strict=True,
            )
        }
        plan_ids.add(plan_id)
        case_ids.add(case_id)
        public_ids.update(expected_ids)
    if len(expected) != MAX_REQUESTS or len(public_ids) != CLAIM_COUNT:
        raise ValueError("public claim map cardinality differs")
    return expected


def score_claims(parsed: dict, expected: dict, ids: list[str]) -> list[dict]:
    details = []
    for claim_id in ids:
        answer = parsed[claim_id]
        truth = expected[claim_id]
        verdict_correct = answer["verdict"] == truth["verdict"]
        observation_correct = (
            canonical_json(answer["observation"])
            == canonical_json(truth["observation"])
        )
        details.append(
            {
                "id": claim_id,
                "expected_verdict": truth["verdict"],
                "verdict_correct": verdict_correct,
                "observation_correct": observation_correct,
                "joint_correct": verdict_correct and observation_correct,
            }
        )
    return details


def classify_result(
    *,
    parsed_units: int,
    cluster_scores: list[int | None],
    readiness_match: bool,
    unsupported_joint_correct: int,
) -> str:
    if (
        type(parsed_units) is not int
        or not 0 <= parsed_units <= MAX_REQUESTS
        or type(cluster_scores) is not list
        or len(cluster_scores) > MAX_REQUESTS
        or any(
            item is not None and (type(item) is not int or not 0 <= item <= 3)
            for item in cluster_scores
        )
        or sum(item is not None for item in cluster_scores) != parsed_units
        or type(readiness_match) is not bool
        or type(unsupported_joint_correct) is not int
        or not 0 <= unsupported_joint_correct <= 12
    ):
        raise ValueError("classification inputs are invalid")
    if parsed_units != MAX_REQUESTS or not readiness_match:
        return "output_or_runtime_failure"
    if len(cluster_scores) != MAX_REQUESTS or any(
        item is None for item in cluster_scores
    ):
        raise ValueError("fully parsed classification needs eight cluster scores")
    scores = [item for item in cluster_scores if item is not None]
    total = sum(scores)
    nonperfect = sum(score < CLAIMS_PER_UNIT for score in scores)
    zero_scores = sum(score == 0 for score in scores)
    if total == CLAIM_COUNT:
        return "ceiling_persists"
    if 21 <= total <= 23:
        return "near_ceiling"
    if (
        14 <= total <= 20
        and nonperfect >= 4
        and zero_scores <= 1
        and unsupported_joint_correct >= 4
    ):
        return "anti_ceiling_pass"
    if total <= 13 or zero_scores >= 2:
        return "semantic_floor_or_topic_cliff"
    return "shape_inconclusive"


def _finite_nonnegative_number(value, label: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite nonnegative number")
    return float(value)


def _build_summary(rows: list[dict], initial: dict, final: dict) -> dict:
    cluster_scores: list[int | None] = []
    for row in rows:
        if row["error"] is None and row["parse_error"] is None:
            cluster_scores.append(sum(item["joint_correct"] for item in row["claims"]))
        else:
            cluster_scores.append(None)
    parsed_units = sum(score is not None for score in cluster_scores)
    concrete_scores = [score for score in cluster_scores if score is not None]
    scored_claims = [
        claim
        for row in rows
        if row["error"] is None and row["parse_error"] is None
        for claim in row["claims"]
    ]
    supported_joint_correct = sum(
        claim["joint_correct"] and claim["expected_verdict"] == "SUPPORTED"
        for claim in scored_claims
    )
    unsupported_joint_correct = sum(
        claim["joint_correct"] and claim["expected_verdict"] == "UNSUPPORTED"
        for claim in scored_claims
    )
    readiness_match = _readiness_matches(initial, final)
    return {
        "planned_units": MAX_REQUESTS,
        "attempted_units": len(rows),
        "parsed_units": parsed_units,
        "claim_count": CLAIM_COUNT,
        "joint_correct": sum(concrete_scores),
        "supported_joint_correct": supported_joint_correct,
        "unsupported_joint_correct": unsupported_joint_correct,
        "copy_supported_baseline_joint_correct": 12,
        "cluster_scores": cluster_scores,
        "nonperfect_clusters": sum(
            score < CLAIMS_PER_UNIT for score in concrete_scores
        ),
        "zero_score_clusters": sum(score == 0 for score in concrete_scores),
        "stopped_early": len(rows) < MAX_REQUESTS,
        "readiness_match": readiness_match,
        "classification": classify_result(
            parsed_units=parsed_units,
            cluster_scores=cluster_scores,
            readiness_match=readiness_match,
            unsupported_joint_correct=unsupported_joint_correct,
        ),
        "usage": _sum_usage(rows),
        "latency_ms": round(sum(row["latency_ms"] for row in rows), 4),
    }


def _validate_row_shape(row: dict, unit: dict, seen_attempts: set[str]) -> None:
    if type(row) is not dict or set(row) != ROW_KEYS:
        raise ValueError("artifact row fields differ")
    if (
        row["plan_id"] != unit["plan_id"]
        or row["case_id"] != unit["case_id"]
        or row["expected_ids"] != unit["expected_ids"]
        or row["effective_request_sha256"] != unit["effective_request_sha256"]
        or row["effective_request_sha256"] != effective_request_sha256(unit)
        or row["response_schema_sha256"] != _hash_json(unit["response_schema"])
        or row["state"] != "finished"
        or row["model_call_count"] != 1
    ):
        raise ValueError("artifact row request identity differs")
    attempt_id = row["attempt_id"]
    if (
        type(attempt_id) is not str
        or HEX_32.fullmatch(attempt_id) is None
        or attempt_id in seen_attempts
    ):
        raise ValueError("artifact row attempt ID is invalid or duplicated")
    seen_attempts.add(attempt_id)
    started = _finite_nonnegative_number(row["started_at_unix"], "row start")
    finished = _finite_nonnegative_number(row["finished_at_unix"], "row finish")
    if finished < started:
        raise ValueError("artifact row finishes before it starts")
    _finite_nonnegative_number(row["latency_ms"], "row latency")
    if (
        type(row["observed_item_types"]) is not list
        or any(type(item) is not str or not item for item in row["observed_item_types"])
        or type(row["model_metrics"]) is not dict
        or type(row["claims"]) is not list
        or (row["answer"] is not None and type(row["answer"]) is not str)
        or (row["parse_error"] is not None and type(row["parse_error"]) is not str)
    ):
        raise ValueError("artifact row observation fields are invalid")
    if row["error"] is not None:
        _validate_error_record(row["error"], "row")
        if row["parse_error"] is not None or row["claims"]:
            raise ValueError("runtime-error row contains semantic scores")


def validate_artifact_document(
    document: dict,
    *,
    freeze: dict,
    freeze_sha: str,
    plan: dict,
    oracle: dict,
) -> bool:
    """Reparse raw answers and recompute every score and summary field."""

    if type(document) is not dict or set(document) != COMPLETE_DOCUMENT_KEYS:
        raise ValueError("complete artifact fields differ from the v4 schema")
    required_identity = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "run_state": "complete",
        "freeze_sha256": freeze_sha,
        "freeze_tree_sha256": freeze["tree_sha256"],
        "freeze_source_commit": freeze["source_commit"],
        "model_contract": freeze["model_contract"],
        "study_sha256": freeze["study_sha256"],
        "manifest_sha256": freeze["manifest_sha256"],
        "plan_sha256": freeze["plan_sha256"],
        "oracle_sha256": freeze["oracle_sha256"],
        "protocol_sha256": freeze["protocol_sha256"],
    }
    for key, expected_value in required_identity.items():
        if document[key] != expected_value:
            raise ValueError(f"artifact {key} differs from the freeze")
    publication_commit = document["freeze_publication_commit"]
    if (
        type(publication_commit) is not str
        or len(publication_commit) != 40
        or any(character not in "0123456789abcdef" for character in publication_commit)
    ):
        raise ValueError("artifact freeze publication commit is invalid")
    if type(document["run_id"]) is not str or HEX_32.fullmatch(document["run_id"]) is None:
        raise ValueError("artifact run ID is invalid")
    started = _finite_nonnegative_number(document["started_at_unix"], "run start")
    finished = _finite_nonnegative_number(document["finished_at_unix"], "run finish")
    if finished < started:
        raise ValueError("artifact run finishes before it starts")
    _validate_readiness_witness(document["initial_readiness"], "initial")
    _validate_readiness_witness(document["final_readiness"], "final")
    if document["initial_readiness"] != {
        "ok": True,
        "value": EXPECTED_READINESS,
        "error": None,
    }:
        raise ValueError("canonical attempt did not begin from expected readiness")

    expected = build_expected_claims(plan, oracle)
    units = plan["units"]
    rows = document["rows"]
    if (
        type(rows) is not list
        or not rows
        or len(rows) > MAX_REQUESTS
        or [row.get("plan_id") for row in rows]
        != [unit["plan_id"] for unit in units[: len(rows)]]
    ):
        raise ValueError("artifact rows are not an ordered plan prefix")
    seen_attempts: set[str] = set()
    saw_runtime_error = False
    for index, (row, unit) in enumerate(zip(rows, units, strict=False)):
        _validate_row_shape(row, unit, seen_attempts)
        if saw_runtime_error:
            raise ValueError("artifact continues after a runtime/client error")
        if row["error"] is not None:
            saw_runtime_error = True
            if index != len(rows) - 1:
                raise ValueError("runtime/client error row is not the final row")
            continue

        _validate_usage(row["model_metrics"], enforce_budget=True)
        item_types = row["observed_item_types"]
        if (
            "AgentMessageThreadItem" not in item_types
            or any(item not in PASSIVE_ITEM_TYPES for item in item_types)
        ):
            raise ValueError("successful row contains forbidden or missing SDK items")
        if type(row["answer"]) is not str or not row["answer"].strip():
            raise ValueError("successful row has no raw model answer")
        parsed, parse_error = parse_response(row["answer"], unit["expected_ids"])
        if row["parse_error"] != parse_error:
            raise ValueError("stored parse error differs from the raw answer")
        if parse_error is not None:
            if row["claims"]:
                raise ValueError("strict-parse failure row contains scores")
            continue
        recalculated = score_claims(
            parsed,
            expected[unit["plan_id"]],
            unit["expected_ids"],
        )
        if row["claims"] != recalculated:
            raise ValueError("stored claim scores differ from the raw answer")
        for claim in row["claims"]:
            if type(claim) is not dict or set(claim) != CLAIM_SCORE_KEYS:
                raise ValueError("claim score fields differ")
            if any(
                type(claim[key]) is not bool
                for key in (
                    "verdict_correct",
                    "observation_correct",
                    "joint_correct",
                )
            ):
                raise ValueError("claim correctness flags are invalid")
            if claim["expected_verdict"] not in {"SUPPORTED", "UNSUPPORTED"}:
                raise ValueError("claim expected verdict is invalid")

    if not saw_runtime_error and len(rows) != MAX_REQUESTS:
        raise ValueError("artifact stopped without a runtime/client error")
    recalculated_summary = _build_summary(
        rows,
        document["initial_readiness"],
        document["final_readiness"],
    )
    if type(document["summary"]) is not dict or set(document["summary"]) != SUMMARY_KEYS:
        raise ValueError("artifact summary fields differ")
    if document["summary"] != recalculated_summary:
        raise ValueError("artifact summary differs from raw-answer recomputation")
    return True


def _new_document(
    *,
    freeze: dict,
    freeze_sha: str,
    freeze_publication_commit: str,
    initial_readiness: dict,
) -> dict:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "run_id": uuid.uuid4().hex,
        "run_state": "running",
        "freeze_sha256": freeze_sha,
        "freeze_tree_sha256": freeze["tree_sha256"],
        "freeze_source_commit": freeze["source_commit"],
        "freeze_publication_commit": freeze_publication_commit,
        "model_contract": freeze["model_contract"],
        "study_sha256": freeze["study_sha256"],
        "manifest_sha256": freeze["manifest_sha256"],
        "plan_sha256": freeze["plan_sha256"],
        "oracle_sha256": freeze["oracle_sha256"],
        "protocol_sha256": freeze["protocol_sha256"],
        "initial_readiness": initial_readiness,
        "final_readiness": None,
        "started_at_unix": time.time(),
        "finished_at_unix": None,
        "rows": [],
        "summary": None,
    }


def _new_started_row(unit: dict) -> dict:
    return {
        "plan_id": unit["plan_id"],
        "case_id": unit["case_id"],
        "expected_ids": unit["expected_ids"],
        "effective_request_sha256": unit["effective_request_sha256"],
        "response_schema_sha256": _hash_json(unit["response_schema"]),
        "attempt_id": uuid.uuid4().hex,
        "state": "started",
        # Reserved before entering client.complete: interruption is indeterminate
        # and the persistent lock forbids retrying the same frozen attempt.
        "model_call_count": 1,
        "started_at_unix": time.time(),
        "finished_at_unix": None,
        "latency_ms": None,
        "observed_item_types": [],
        "answer": None,
        "model_metrics": {},
        "parse_error": None,
        "claims": [],
        "error": None,
    }


def _finish_runtime_error(row: dict, error: Exception, client, started_perf: float) -> None:
    row["observed_item_types"] = list(getattr(client, "last_item_types", ()))
    if not row["model_metrics"]:
        captured_metrics = getattr(client, "last_model_metrics", {})
        if type(captured_metrics) is dict:
            row["model_metrics"] = dict(captured_metrics)
    row["error"] = _error_record(error)
    row["state"] = "finished"
    row["finished_at_unix"] = time.time()
    row["latency_ms"] = round((time.perf_counter() - started_perf) * 1000, 4)


def _write_invalid_artifact(output: Path, document: dict, error: Exception) -> None:
    invalid = dict(document)
    invalid["run_state"] = "invalid"
    invalid["finished_at_unix"] = time.time()
    invalid["internal_error"] = _error_record(error)
    try:
        _atomic_write(output, invalid)
    except Exception:
        # The persistent attempt lock is the final fail-closed witness if even
        # the invalid checkpoint cannot be written.
        pass


def run_v4(
    output_path: Path | None = None,
    *,
    client_factory=AuditedCodexClient,
) -> dict:
    """Run the one canonical attempt after all no-inference preflights pass."""

    validate_no_api_auth()
    validate_source_import_provenance()
    freeze = verify_freeze()
    freeze_sha = sha256(FREEZE_PATH)
    output = canonical_artifact_path(freeze_sha)
    if output_path is not None and Path(output_path).resolve() != output.resolve():
        raise ValueError("v4 output must use the canonical freeze-scoped path")

    plan = load_strict_json(PLAN_PATH)
    oracle = load_strict_json(ORACLE_PATH)
    expected = build_expected_claims(plan, oracle)
    current_publication = validate_published_clean_head()
    freeze_publication_commit = _verify_freeze_publication(
        FREEZE_PATH,
        current_publication,
    )

    client = client_factory(
        model_name=EXPECTED_READINESS["model_name"],
        reasoning_effort=EXPECTED_READINESS["reasoning_effort"],
    )
    attempt_reserved = False
    document: dict | None = None
    try:
        initial_readiness = _capture_readiness(client)
        _validate_readiness_witness(initial_readiness, "initial")
        if initial_readiness != {
            "ok": True,
            "value": EXPECTED_READINESS,
            "error": None,
        }:
            raise RuntimeError("initial Codex account/model readiness differs")
        validate_sdk_import_provenance()

        reserve_attempt(output, freeze_sha)
        attempt_reserved = True
        document = _new_document(
            freeze=freeze,
            freeze_sha=freeze_sha,
            freeze_publication_commit=freeze_publication_commit,
            initial_readiness=initial_readiness,
        )
        _atomic_write(output, document)

        for unit in plan["units"]:
            row = _new_started_row(unit)
            document["rows"].append(row)
            _atomic_write(output, document)
            started_perf = time.perf_counter()
            if hasattr(client, "last_item_types"):
                client.last_item_types = ()
            if hasattr(client, "last_model_metrics"):
                client.last_model_metrics = {}
            try:
                reply = client.complete(
                    system_prompt=unit["system_prompt"],
                    user_prompt=unit["user_prompt"],
                    response_schema=unit["response_schema"],
                    num_predict=unit["num_predict"],
                )
            except Exception as error:
                _finish_runtime_error(row, error, client, started_perf)
                _atomic_write(output, document)
                break

            row["answer"] = reply.content
            row["model_metrics"] = (
                dict(reply.metrics) if type(reply.metrics) is dict else {}
            )
            row["observed_item_types"] = list(
                getattr(client, "last_item_types", ())
            )
            try:
                if type(row["answer"]) is not str or not row["answer"].strip():
                    raise ModelResponseError(
                        "Codex SDK returned no nonempty raw answer"
                    )
                _validate_usage(row["model_metrics"], enforce_budget=True)
                item_types = row["observed_item_types"]
                if (
                    "AgentMessageThreadItem" not in item_types
                    or any(item not in PASSIVE_ITEM_TYPES for item in item_types)
                ):
                    raise ModelResponseError(
                        "Codex SDK item audit differs from the no-tool contract"
                    )
            except Exception as error:
                _finish_runtime_error(row, error, client, started_perf)
                _atomic_write(output, document)
                break

            parsed, parse_error = parse_response(
                reply.content,
                unit["expected_ids"],
            )
            row["parse_error"] = parse_error
            if parse_error is None:
                row["claims"] = score_claims(
                    parsed,
                    expected[unit["plan_id"]],
                    unit["expected_ids"],
                )
            row["state"] = "finished"
            row["finished_at_unix"] = time.time()
            row["latency_ms"] = round(
                (time.perf_counter() - started_perf) * 1000,
                4,
            )
            _atomic_write(output, document)

        final_readiness = _capture_readiness(client)
        _validate_readiness_witness(final_readiness, "final")
        document["final_readiness"] = final_readiness
        document["finished_at_unix"] = time.time()
        document["run_state"] = "complete"
        document["summary"] = _build_summary(
            document["rows"],
            document["initial_readiness"],
            document["final_readiness"],
        )
        validate_artifact_document(
            document,
            freeze=freeze,
            freeze_sha=freeze_sha,
            plan=plan,
            oracle=oracle,
        )
        _atomic_write(output, document)
        return document
    except Exception as error:
        if attempt_reserved and document is not None and output.exists():
            _write_invalid_artifact(output, document, error)
        raise
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_v4(args.output)
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
