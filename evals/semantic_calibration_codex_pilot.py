"""Run the preregistered four-call Codex-account Sol ceiling pilot."""

from __future__ import annotations

import os
import sys


def _prepare_imports() -> None:
    """Refuse cached experiment/client bytecode before importing scored code."""

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
    if bytecode:
        raise RuntimeError(f"pilot refuses Python bytecode caches: {bytecode}")


if __name__ == "__main__" and __spec__ is not None:
    raise RuntimeError("pilot must be executed by direct file path, not -m")
if __name__ == "__main__":
    _prepare_imports()
else:
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import string
import subprocess
import time
import uuid


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
V3_ROOT = WORKSPACE_ROOT / "evals" / "semantic_calibration_v3"
PROTOCOL_PATH = WORKSPACE_ROOT / "evals" / "semantic_calibration_codex_pilot_PROTOCOL.md"
OUTPUT_PATH = (
    WORKSPACE_ROOT
    / ".tmp"
    / "evals"
    / "semantic_calibration_codex_pilot"
    / "sol-medium-hard-batches-v1.json"
)

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from evals.semantic_calibration_v3.schemas import (  # noqa: E402
    canonical_json,
    load_strict_json,
    parse_response,
)
from llm import ModelResponseError  # noqa: E402
from llm.codex_account import CodexAccountIntegrationClient  # noqa: E402


MODEL_NAME = "gpt-5.6-sol"
REASONING_EFFORT = "medium"
SDK_VERSION = "0.144.4"
EXPERIMENT_ID = "sol-medium-hard-batches-v1"
EXPECTED_DEPENDENCY_HASHES = {
    "evals/semantic_calibration_v3/FREEZE.json": (
        "fb9f26c1cba78eafa7f8b1422b2a19757eaa748bf205b3dc918a6ebe9ed872a0"
    ),
    "evals/semantic_calibration_v3/control/run_plan.json": (
        "5f54b9b6dd972b6ad01fe2e1db5bc8d8f2edbfb9bffbd6846361798517c19522"
    ),
    "evals/semantic_calibration_v3/control/oracle_results.json": (
        "4358ae9a4e583591263885b674636a8f07598adc5e7189ed4a41c08305ffd5f2"
    ),
    "evals/semantic_calibration_v3/manifest.json": (
        "98b29c0c50440723f34afcc8f3e66054862aca754aed6fb5bcec24bd57d3dc6b"
    ),
    "evals/semantic_calibration_v3/schemas.py": (
        "5d187d5117d7fe63fb2b31685133e877e72d5b781e2ead2c55976d6be08362b4"
    ),
    "llm/codex_account.py": (
        "20e465fff8aa6ac656609103bb879b8106be7da7cb4082a01dd195a7d04d6cdc"
    ),
}
EXPECTED_PLAN_IDS = (
    "semantic-33-batch-cal-h01-reflected-operator-Q-59fd981294_Q-fb72e27640_Q-c1f4f9aa46",
    "semantic-40-batch-cal-h02-metaclass-order-Q-8ea116cd1b_Q-2dff061d7b_Q-2932ec0e9c",
    "semantic-41-batch-cal-h03-new-return-type-Q-37bd519fff_Q-d0109ae755_Q-0de4b040cb",
    "semantic-48-batch-cal-h04-exec-namespaces-Q-c9f97f02a0_Q-2ca0af488a_Q-885d3c76eb",
)
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_document(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    ) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)


def acquire_attempt_lock(output_path: Path) -> Path:
    """Atomically reserve the one allowed pilot attempt."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_path.with_name(output_path.name + ".lock")
    descriptor = os.open(
        str(lock_path),
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
    )
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
    finally:
        os.close(descriptor)
    return lock_path


def git_text(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=WORKSPACE_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def validate_no_api_auth(environment=os.environ) -> None:
    present = [name for name in FORBIDDEN_AUTH_ENV if environment.get(name)]
    if present:
        raise RuntimeError(
            "pilot refuses API/access-token environment variables: "
            + ", ".join(present)
        )


def validate_dependencies() -> None:
    for relative, expected in EXPECTED_DEPENDENCY_HASHES.items():
        actual = sha256(WORKSPACE_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen dependency changed: {relative}")


def validate_published_clean_head() -> dict[str, str]:
    if git_text("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("pilot requires a clean Git worktree")
    head = git_text("rev-parse", "HEAD")
    upstream_sha = git_text("rev-parse", "@{u}")
    upstream_ref = git_text("rev-parse", "--abbrev-ref", "@{u}")
    remote, remote_branch = split_upstream_ref(upstream_ref)
    if head != upstream_sha:
        raise RuntimeError("pilot requires HEAD to equal its pushed upstream")
    remote_output = git_text(
        "ls-remote",
        "--heads",
        remote,
        f"refs/heads/{remote_branch}",
    )
    remote_sha = parse_remote_head(remote_output, remote_branch)
    if head != remote_sha:
        raise RuntimeError("pilot requires HEAD to equal the live remote branch")
    return {
        "commit": head,
        "branch": git_text("branch", "--show-current"),
        "upstream": upstream_ref,
        "remote_url": git_text("remote", "get-url", remote),
        "remote_commit": remote_sha,
    }


def split_upstream_ref(upstream_ref: str) -> tuple[str, str]:
    if not isinstance(upstream_ref, str) or "/" not in upstream_ref:
        raise RuntimeError("pilot requires a remote-tracking upstream")
    remote, branch = upstream_ref.split("/", 1)
    if not remote or not branch:
        raise RuntimeError("pilot requires a remote-tracking upstream")
    return remote, branch


def parse_remote_head(output: str, branch: str) -> str:
    expected_ref = f"refs/heads/{branch}"
    matches = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == expected_ref:
            matches.append(parts[0])
    if (
        len(matches) != 1
        or len(matches[0]) != 40
        or any(character not in string.hexdigits for character in matches[0])
    ):
        raise RuntimeError("live upstream branch could not be verified")
    return matches[0]


def select_pilot_units(plan: dict) -> list[dict]:
    units = [
        unit
        for unit in plan.get("semantic_units", [])
        if unit.get("mode") == "batch" and unit.get("difficulty") == "hard"
    ]
    if tuple(unit.get("plan_id") for unit in units) != EXPECTED_PLAN_IDS:
        raise RuntimeError("hard-batch plan identity or order changed")
    if any(len(unit.get("expected_ids", [])) != 3 for unit in units):
        raise RuntimeError("each pilot batch must contain exactly three claims")
    return units


def build_expected_claims(units: list[dict], oracle_document: dict) -> dict:
    cases = {
        case["case_id"]: case
        for case in oracle_document.get("results", [])
        if case.get("difficulty") == "hard"
    }
    expected = {}
    for unit in units:
        case = cases.get(unit["case_id"])
        if case is None:
            raise RuntimeError("pilot case missing from oracle")
        internal = {claim["id"]: claim for claim in case["claims"]}
        for internal_id, public_id in zip(
            unit["internal_claim_ids"], unit["expected_ids"], strict=True
        ):
            oracle_claim = internal[internal_id]
            expected[public_id] = {
                "verdict": oracle_claim["verdict"],
                "observation": oracle_claim["observation"],
            }
    if len(expected) != 12:
        raise RuntimeError("pilot oracle must contain exactly 12 claims")
    return expected


def score_parsed_claims(parsed: dict, expected: dict, ids: list[str]) -> list[dict]:
    details = []
    for claim_id in ids:
        actual = parsed.get(claim_id)
        oracle = expected[claim_id]
        verdict_correct = bool(actual and actual["verdict"] == oracle["verdict"])
        observation_correct = bool(
            actual
            and canonical_json(actual["observation"])
            == canonical_json(oracle["observation"])
        )
        details.append(
            {
                "id": claim_id,
                "verdict_correct": verdict_correct,
                "observation_correct": observation_correct,
                "joint_correct": verdict_correct and observation_correct,
            }
        )
    return details


def classify_result(*, parsed_units: int, joint_correct: int) -> str:
    if parsed_units != 4:
        return "output_or_runtime_failure"
    if joint_correct >= 10:
        return "harder_v4_triggered"
    return "screen_threshold_not_met"


def validate_output_budget(metrics: dict, budget: int) -> int:
    output_tokens = metrics.get("output_tokens") if isinstance(metrics, dict) else None
    if type(output_tokens) is not int or output_tokens < 0:
        raise ModelResponseError("Codex SDK output token usage is missing or invalid")
    if output_tokens > budget:
        raise ModelResponseError("Codex SDK output exceeded the frozen pilot budget")
    return output_tokens


def validate_passive_items(result) -> tuple[str, ...]:
    items = getattr(result, "items", None)
    if not isinstance(items, (list, tuple)) or not items:
        raise ModelResponseError("Codex SDK thread items are missing or invalid")
    item_types = tuple(type(getattr(item, "root", None)).__name__ for item in items)
    if "AgentMessageThreadItem" not in item_types:
        raise ModelResponseError("Codex SDK result has no final agent message item")
    if any(item_type not in PASSIVE_ITEM_TYPES for item_type in item_types):
        raise ModelResponseError("Codex SDK result contains forbidden activity")
    return item_types


class StrictPilotCodexClient(CodexAccountIntegrationClient):
    """Add fail-closed SDK item auditing without changing the frozen client."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_item_types: tuple[str, ...] = ()

    def _parse_result(self, result, *, num_predict: int):
        self.last_item_types = validate_passive_items(result)
        return super()._parse_result(result, num_predict=num_predict)


def sum_metrics(rows: list[dict]) -> dict[str, int]:
    fields = (
        "cached_input_tokens",
        "input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "total_tokens",
    )
    return {
        field: sum(
            row.get("model_metrics", {}).get(field, 0)
            for row in rows
            if isinstance(row.get("model_metrics"), dict)
        )
        for field in fields
    }


def run_pilot(output_path: Path = OUTPUT_PATH) -> dict:
    if output_path.resolve() != OUTPUT_PATH.resolve():
        raise ValueError(f"pilot output must use canonical path: {OUTPUT_PATH}")
    validate_no_api_auth()
    validate_dependencies()
    git_state = validate_published_clean_head()
    attempt_lock = acquire_attempt_lock(output_path)
    try:
        if output_path.exists():
            raise FileExistsError("the primary pilot attempt already exists")
        return _run_locked_pilot(output_path, git_state)
    finally:
        attempt_lock.unlink(missing_ok=True)


def _run_locked_pilot(output_path: Path, git_state: dict[str, str]) -> dict:
    plan_path = V3_ROOT / "control" / "run_plan.json"
    oracle_path = V3_ROOT / "control" / "oracle_results.json"
    plan = load_strict_json(plan_path)
    units = select_pilot_units(plan)
    expected = build_expected_claims(units, load_strict_json(oracle_path))

    client = StrictPilotCodexClient(
        model_name=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
    )
    started_at = time.time()
    document = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "run_id": uuid.uuid4().hex,
        "run_state": "running",
        "publishable": False,
        "official_score": False,
        "diagnostic_score": True,
        "agent_runtime": True,
        "purpose": "ceiling diagnostic only",
        "protocol_sha256": sha256(PROTOCOL_PATH),
        "dependency_hashes": dict(EXPECTED_DEPENDENCY_HASHES),
        "git": git_state,
        "model_contract": {
            "model_name": MODEL_NAME,
            "reasoning_effort": REASONING_EFFORT,
            "sdk_version": SDK_VERSION,
            "request_count": 4,
            "claim_count": 12,
            "num_predict_semantics": "post-hoc SDK usage check, not server cap",
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
            raise RuntimeError("Codex account/model readiness differs from protocol")
        document["model_readiness"] = readiness
        write_document(output_path, document)

        for unit in units:
            row = {
                "plan_id": unit["plan_id"],
                "case_id": unit["case_id"],
                "expected_ids": unit["expected_ids"],
                "effective_request_sha256": unit["effective_request_sha256"],
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
            write_document(output_path, document)
            call_started = time.perf_counter()
            try:
                client.last_item_types = ()
                reply = client.complete(
                    system_prompt=unit["system_prompt"],
                    user_prompt=unit["user_prompt"],
                    response_schema=unit["response_schema"],
                    num_predict=unit["num_predict"],
                )
                validate_output_budget(reply.metrics, unit["num_predict"])
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
                    row["claims"] = score_parsed_claims(
                        parsed,
                        expected,
                        unit["expected_ids"],
                    )
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
            row["observed_item_types"] = list(client.last_item_types)
            row["model_call_count"] = 1
            row["latency_ms"] = round(
                (time.perf_counter() - call_started) * 1000,
                4,
            )
            row["state"] = "finished"
            write_document(output_path, document)

        final_readiness = client.check_configuration()
        if final_readiness != document["model_readiness"]:
            raise RuntimeError("Codex account/model readiness changed during pilot")
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
            "attempted_units": 4,
            "parsed_units": parsed_units,
            "claim_count": 12,
            "joint_correct": joint_correct,
            "classification": classify_result(
                parsed_units=parsed_units,
                joint_correct=joint_correct,
            ),
            "usage": sum_metrics(document["rows"]),
            "latency_ms": round(
                sum(row["latency_ms"] for row in document["rows"]),
                4,
            ),
        }
        document["final_readiness"] = final_readiness
        document["finished_at_unix"] = time.time()
        document["run_state"] = "complete"
        write_document(output_path, document)
        return document
    except Exception:
        if output_path.exists():
            document["run_state"] = "invalid"
            document["finished_at_unix"] = time.time()
            write_document(output_path, document)
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
