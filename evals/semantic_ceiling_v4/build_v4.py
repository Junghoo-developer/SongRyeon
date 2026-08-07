"""Build the self-contained oracle and batch-only plan for semantic ceiling v4."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

if __package__:
    from .schemas_v4 import (
        canonical_json,
        response_schema,
        strict_json_loads,
        validate_observation,
    )
else:
    from schemas_v4 import (  # type: ignore[no-redef]
        canonical_json,
        response_schema,
        strict_json_loads,
        validate_observation,
    )


ROOT = Path(__file__).resolve().parent
EXPECTED_PYTHON_SCOPE = "CPython 3.10.11"
EXPECTED_VERSION = (3, 10, 11)
CLAIMS_PER_CASE = 3
DEFAULT_NUM_PREDICT = 2_400
DEFAULT_ORACLE_TIMEOUT_SECONDS = 20.0

MANIFEST_KEYS = {"schema_version", "suite_id", "python_scope", "cases"}
CASE_KEYS = {"case_id", "source", "claims"}
CLAIM_KEYS = {"id", "function", "description", "proposition"}


SEMANTIC_SYSTEM_PROMPT = """You predict CPython 3.10.11 behavior from complete source code.
Each claim gives a proposition about one zero-argument function call in a fresh
interpreter. SUPPORTED means the proposition observation exactly matches the
actual call. UNSUPPORTED means it does not. In both cases, observation must
contain your predicted actual result, not a copy of a false proposition. Do not
execute code. The input proposition_observation uses a typed JSON value. In your
output, encode the predicted actual value exactly once as JSON text in
value_json. For example, JSON true becomes the string "true", a list becomes
the string "[1,2]", and the actual string null becomes the string '"null"'.
For return observations exception must be null. For raise observations
value_json must be the four-character string "null". Every reason must be
nonempty. Return only the required JSON object. Every claim must appear exactly
once."""


# Source bytes are supplied on stdin. This prevents the child from reopening a
# pathname after the parent hashes it, while the canonical path remains the
# compile filename for useful diagnostics. The child itself verifies the exact
# interpreter before executing any fixture code.
ORACLE_RUNNER = r'''import inspect, json, sys
if sys.implementation.name != "cpython" or sys.version_info[:3] != (3, 10, 11):
    raise RuntimeError("oracle requires CPython 3.10.11")
filename, function_name = sys.argv[1], sys.argv[2]
source = sys.stdin.buffer.read().decode("utf-8", errors="strict")
namespace = {
    "__name__": "__semantic_ceiling_v4_oracle__",
    "__file__": filename,
    "__package__": None,
}
exec(compile(source, filename, "exec"), namespace, namespace)
target = namespace.get(function_name)
if (
    not inspect.isfunction(target)
    or target.__module__ != "__semantic_ceiling_v4_oracle__"
    or target.__name__ != function_name
    or target.__qualname__ != function_name
    or inspect.iscoroutinefunction(target)
    or inspect.isgeneratorfunction(target)
    or inspect.isasyncgenfunction(target)
    or len(inspect.signature(target).parameters) != 0
):
    raise TypeError("oracle target must be the named top-level synchronous zero-argument function")
try:
    value = target()
except Exception as failure:
    observation = {
        "kind": "raise",
        "value": None,
        "exception": type(failure).__name__,
    }
else:
    observation = {"kind": "return", "value": value, "exception": None}
document = {"python_version": sys.version, "observation": observation}
payload = json.dumps(
    document,
    ensure_ascii=False,
    allow_nan=False,
    separators=(",", ":"),
    sort_keys=True,
).encode("utf-8")
sys.stdout.buffer.write(payload + b"\n")
'''


class BuildValidationError(ValueError):
    """The immutable suite inputs do not satisfy the v4 contract."""


class OracleExecutionError(RuntimeError):
    """An isolated oracle process violated its execution contract."""


@dataclass(frozen=True)
class SourceSnapshot:
    declared_path: str
    resolved_path: Path
    content_bytes: bytes
    content_text: str
    sha256: str


@dataclass(frozen=True)
class SuiteSnapshot:
    root: Path
    manifest: dict
    manifest_sha256: str
    sources: tuple[SourceSnapshot, ...]


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _require_exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != expected:
        raise BuildValidationError(f"{label} schema mismatch")


def _require_nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise BuildValidationError(f"{label} must be a nonempty string")


def _validate_source_spelling(value: str) -> PurePosixPath:
    _require_nonempty_string(value, "source")
    if "\\" in value or ":" in value or "\x00" in value:
        raise BuildValidationError("source must be a normalized relative POSIX path")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or relative.as_posix() != value
        or any(part in {"", ".", ".."} for part in relative.parts)
        or not relative.parts
        or relative.parts[0] != "fixtures"
        or relative.suffix != ".py"
    ):
        raise BuildValidationError("source must be a normalized relative fixture path")
    return relative


def _validate_manifest(manifest):
    _require_exact_keys(manifest, MANIFEST_KEYS, "manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise BuildValidationError("manifest schema_version must be integer 1")
    _require_nonempty_string(manifest["suite_id"], "suite_id")
    if manifest["python_scope"] != EXPECTED_PYTHON_SCOPE:
        raise BuildValidationError(
            f"python_scope must be exactly {EXPECTED_PYTHON_SCOPE!r}"
        )

    cases = manifest["cases"]
    if not isinstance(cases, list) or not cases:
        raise BuildValidationError("manifest cases must be a nonempty list")
    if len(cases) % 2:
        raise BuildValidationError("case count must be even for exact position balance")

    case_ids = set()
    claim_ids = set()
    normalized_sources = set()
    for case_index, case in enumerate(cases, 1):
        _require_exact_keys(case, CASE_KEYS, f"case {case_index}")
        case_id = case["case_id"]
        _require_nonempty_string(case_id, f"case {case_index} id")
        if case_id in case_ids:
            raise BuildValidationError(f"duplicate case id: {case_id}")
        case_ids.add(case_id)

        source = case["source"]
        _validate_source_spelling(source)
        folded_source = source.casefold()
        if folded_source in normalized_sources:
            raise BuildValidationError(f"duplicate source path: {source}")
        normalized_sources.add(folded_source)

        claims = case["claims"]
        if not isinstance(claims, list) or len(claims) != CLAIMS_PER_CASE:
            raise BuildValidationError(
                f"case {case_id} must contain exactly {CLAIMS_PER_CASE} claims"
            )
        functions = set()
        for position, claim in enumerate(claims, 1):
            _require_exact_keys(
                claim,
                CLAIM_KEYS,
                f"claim {position} in case {case_id}",
            )
            claim_id = claim["id"]
            _require_nonempty_string(claim_id, "claim id")
            if claim_id in claim_ids:
                raise BuildValidationError(f"duplicate claim id: {claim_id}")
            claim_ids.add(claim_id)

            function = claim["function"]
            if not isinstance(function, str) or not function.isidentifier():
                raise BuildValidationError(
                    f"claim {claim_id} function must be one identifier"
                )
            if function in functions:
                raise BuildValidationError(
                    f"duplicate function in case {case_id}: {function}"
                )
            functions.add(function)
            _require_nonempty_string(claim["description"], "claim description")
            error = validate_observation(
                claim["proposition"],
                allow_unknown=False,
            )
            if error:
                raise BuildValidationError(
                    f"invalid proposition for {claim_id}: {error}"
                )


def _resolve_source(root: Path, declared: str) -> Path:
    relative = _validate_source_spelling(declared)
    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError) as failure:
        raise BuildValidationError(
            f"source path or symlink escapes suite root: {declared}"
        ) from failure
    if not resolved.is_file():
        raise BuildValidationError(f"source is not a regular file: {declared}")
    return resolved


def _load_suite_snapshot(root: Path | None = None) -> SuiteSnapshot:
    suite_root = (ROOT if root is None else Path(root)).resolve(strict=True)
    manifest_candidate = suite_root / "manifest.json"
    try:
        manifest_path = manifest_candidate.resolve(strict=True)
        manifest_path.relative_to(suite_root)
    except (FileNotFoundError, OSError, ValueError) as failure:
        raise BuildValidationError("manifest path or symlink escapes suite root") from failure

    manifest_bytes = manifest_path.read_bytes()
    if manifest_bytes.startswith(b"\xef\xbb\xbf"):
        raise BuildValidationError("manifest must be UTF-8 without a BOM")
    try:
        manifest = strict_json_loads(manifest_bytes.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError, RecursionError) as failure:
        raise BuildValidationError("manifest is not strict UTF-8 JSON") from failure
    _validate_manifest(manifest)

    sources = []
    resolved_identities = set()
    for case in manifest["cases"]:
        resolved = _resolve_source(suite_root, case["source"])
        identity = str(resolved).casefold()
        if identity in resolved_identities:
            raise BuildValidationError(
                f"multiple manifest paths resolve to one source: {case['source']}"
            )
        resolved_identities.add(identity)
        content_bytes = resolved.read_bytes()
        if content_bytes.startswith(b"\xef\xbb\xbf"):
            raise BuildValidationError(
                f"source must be UTF-8 without a BOM: {case['source']}"
            )
        try:
            content_text = content_bytes.decode("utf-8", errors="strict")
        except UnicodeError as failure:
            raise BuildValidationError(
                f"source is not strict UTF-8: {case['source']}"
            ) from failure
        sources.append(
            SourceSnapshot(
                declared_path=case["source"],
                resolved_path=resolved,
                content_bytes=content_bytes,
                content_text=content_text,
                sha256=_sha256_bytes(content_bytes),
            )
        )

    return SuiteSnapshot(
        root=suite_root,
        manifest=manifest,
        manifest_sha256=_sha256_bytes(manifest_bytes),
        sources=tuple(sources),
    )


def _execute_claim(
    source: SourceSnapshot,
    function: str,
    *,
    python_executable: str | Path,
    timeout_seconds: float,
):
    if not isinstance(timeout_seconds, (int, float)) or isinstance(
        timeout_seconds, bool
    ) or timeout_seconds <= 0:
        raise ValueError("oracle timeout must be positive")
    command = [
        str(python_executable),
        "-B",
        "-I",
        "-c",
        ORACLE_RUNNER,
        str(source.resolved_path),
        function,
    ]
    try:
        completed = subprocess.run(
            command,
            input=source.content_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=source.root if hasattr(source, "root") else source.resolved_path.parent,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as failure:
        raise OracleExecutionError(
            f"oracle timeout for {source.declared_path}:{function}"
        ) from failure
    except OSError as failure:
        raise OracleExecutionError(
            f"oracle could not start for {source.declared_path}:{function}"
        ) from failure

    if completed.stderr != b"":
        raise OracleExecutionError(
            f"oracle emitted unexpected stderr for {source.declared_path}:{function}"
        )
    if completed.returncode != 0:
        raise OracleExecutionError(
            f"oracle exited with status {completed.returncode} for "
            f"{source.declared_path}:{function}"
        )
    try:
        stdout = completed.stdout.decode("utf-8", errors="strict")
        document = strict_json_loads(stdout)
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RecursionError,
    ) as failure:
        raise OracleExecutionError(
            f"oracle emitted unexpected stdout for {source.declared_path}:{function}"
        ) from failure

    if not isinstance(document, dict) or set(document) != {
        "python_version",
        "observation",
    }:
        raise OracleExecutionError(
            f"oracle envelope mismatch for {source.declared_path}:{function}"
        )
    python_version = document["python_version"]
    if not isinstance(python_version, str) or not python_version.startswith("3.10.11 "):
        raise OracleExecutionError(
            f"oracle runtime mismatch for {source.declared_path}:{function}"
        )
    observation = document["observation"]
    error = validate_observation(observation, allow_unknown=False)
    if error:
        raise OracleExecutionError(
            f"invalid oracle observation for {source.declared_path}:{function}: {error}"
        )
    expected_stdout = (canonical_json(document) + "\n").encode("utf-8")
    if completed.stdout != expected_stdout:
        raise OracleExecutionError(
            f"oracle emitted unexpected stdout for {source.declared_path}:{function}"
        )
    return python_version, observation


def validate_oracle_balance(results):
    """Require exact overall and within-batch-position 50/50 truth balance."""

    if not isinstance(results, list) or not results or len(results) % 2:
        raise BuildValidationError("oracle result case count must be positive and even")
    expected_per_position = len(results) // 2
    expected_overall = len(results) * CLAIMS_PER_CASE // 2
    allowed = {"SUPPORTED", "UNSUPPORTED"}

    overall = Counter()
    positions = [Counter() for _ in range(CLAIMS_PER_CASE)]
    for result in results:
        claims = result.get("claims") if isinstance(result, dict) else None
        if not isinstance(claims, list) or len(claims) != CLAIMS_PER_CASE:
            raise BuildValidationError("oracle result must contain three claims per case")
        for position, claim in enumerate(claims):
            verdict = claim.get("verdict") if isinstance(claim, dict) else None
            if verdict not in allowed:
                raise BuildValidationError("oracle verdict is invalid")
            overall[verdict] += 1
            positions[position][verdict] += 1

    required_overall = Counter(
        {"SUPPORTED": expected_overall, "UNSUPPORTED": expected_overall}
    )
    if overall != required_overall:
        raise BuildValidationError(
            f"oracle truth balance is not exact overall 50/50: {dict(overall)}"
        )
    required_position = Counter(
        {
            "SUPPORTED": expected_per_position,
            "UNSUPPORTED": expected_per_position,
        }
    )
    for position, counts in enumerate(positions, 1):
        if counts != required_position:
            raise BuildValidationError(
                f"oracle truth balance is not exact 50/50 at position {position}: "
                f"{dict(counts)}"
            )


def _build_oracle_from_snapshot(
    snapshot: SuiteSnapshot,
    *,
    python_executable: str | Path,
    timeout_seconds: float,
):
    results = []
    python_versions = set()
    for case, source in zip(snapshot.manifest["cases"], snapshot.sources):
        claims = []
        for claim in case["claims"]:
            python_version, actual = _execute_claim(
                source,
                claim["function"],
                python_executable=python_executable,
                timeout_seconds=timeout_seconds,
            )
            python_versions.add(python_version)
            verdict = (
                "SUPPORTED"
                if canonical_json(actual) == canonical_json(claim["proposition"])
                else "UNSUPPORTED"
            )
            claims.append(
                {
                    "id": claim["id"],
                    "verdict": verdict,
                    "observation": actual,
                }
            )
        results.append(
            {
                "case_id": case["case_id"],
                "source": case["source"],
                "source_sha256": source.sha256,
                "claims": claims,
            }
        )

    if len(python_versions) != 1:
        raise OracleExecutionError("oracle children reported inconsistent runtimes")
    validate_oracle_balance(results)
    return {
        "schema_version": 1,
        "python_version": next(iter(python_versions)),
        "manifest_sha256": snapshot.manifest_sha256,
        "results": results,
    }


def opaque_token(experiment_id: str, namespace: str, value: str) -> str:
    material = f"{experiment_id}|{namespace}|{value}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:16]


def effective_request_sha256(unit) -> str:
    effective = {
        "system_prompt": unit["system_prompt"],
        "user_prompt": unit["user_prompt"],
        "response_schema": unit["response_schema"],
        "num_predict": unit["num_predict"],
    }
    return hashlib.sha256(canonical_json(effective).encode("utf-8")).hexdigest()


def _build_plan_from_snapshot(
    snapshot: SuiteSnapshot,
    *,
    num_predict: int,
):
    if type(num_predict) is not int or num_predict <= 0:
        raise BuildValidationError("num_predict must be a positive integer")
    experiment_id = snapshot.manifest["suite_id"]
    width = max(2, len(str(len(snapshot.manifest["cases"]))))
    units = []
    all_public_ids = set()

    for ordinal, (case, source) in enumerate(
        zip(snapshot.manifest["cases"], snapshot.sources),
        1,
    ):
        visible_source = (
            "source-" + opaque_token(experiment_id, "source", case["case_id"]) + ".py"
        )
        visible_ids = {
            claim["id"]: "Q-"
            + opaque_token(experiment_id, "claim", claim["id"])
            for claim in case["claims"]
        }
        expected_ids = [visible_ids[claim["id"]] for claim in case["claims"]]
        if all_public_ids.intersection(expected_ids):
            raise BuildValidationError("opaque public id collision")
        all_public_ids.update(expected_ids)

        source_packet = {
            "path": visible_source,
            "content": source.content_text,
        }
        claim_packet = [
            {
                "id": visible_ids[claim["id"]],
                "expression": f"{claim['function']}()",
                "description": claim["description"],
                "proposition_observation": claim["proposition"],
            }
            for claim in case["claims"]
        ]
        user_prompt = (
            "Evaluate all three claims using only the complete source packet below. "
            "Each expression is called in its own fresh interpreter.\n\n"
            "[SOURCE_PACKET]\n"
            + canonical_json(source_packet)
            + "\n\n[CLAIMS]\n"
            + canonical_json(claim_packet)
        )
        unit = {
            "plan_id": (
                f"semantic-{ordinal:0{width}d}-"
                + opaque_token(experiment_id, "unit", case["case_id"])
            ),
            "case_id": case["case_id"],
            "expected_ids": expected_ids,
            "internal_claim_ids": [claim["id"] for claim in case["claims"]],
            "system_prompt": SEMANTIC_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
            "response_schema": response_schema(expected_ids, allow_unknown=False),
            "num_predict": num_predict,
        }
        unit["effective_request_sha256"] = effective_request_sha256(unit)
        units.append(unit)

    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "units": units,
    }


def build_documents(
    *,
    root: Path | None = None,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_ORACLE_TIMEOUT_SECONDS,
    num_predict: int = DEFAULT_NUM_PREDICT,
):
    """Return ``(plan, oracle)`` from one immutable input snapshot."""

    snapshot = _load_suite_snapshot(root)
    executable = sys.executable if python_executable is None else python_executable
    oracle = _build_oracle_from_snapshot(
        snapshot,
        python_executable=executable,
        timeout_seconds=timeout_seconds,
    )
    plan = _build_plan_from_snapshot(snapshot, num_predict=num_predict)
    return plan, oracle


def build_documents_verified(**kwargs):
    """Build twice from disk and reject any byte-level nondeterminism."""

    first = build_documents(**kwargs)
    second = build_documents(**kwargs)
    if canonical_json(first) != canonical_json(second):
        raise BuildValidationError("v4 control documents are not deterministic")
    return first


def _write_new_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
        file.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plan-output",
        type=Path,
        default=ROOT / "control" / "run_plan.json",
    )
    parser.add_argument(
        "--oracle-output",
        type=Path,
        default=ROOT / "control" / "oracle_results.json",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_ORACLE_TIMEOUT_SECONDS,
    )
    args = parser.parse_args()
    if args.plan_output.exists() or args.oracle_output.exists():
        raise FileExistsError("control output already exists")
    plan, oracle = build_documents_verified(timeout_seconds=args.timeout_seconds)
    _write_new_json(args.plan_output, plan)
    _write_new_json(args.oracle_output, oracle)
    print(args.plan_output)
    print(args.oracle_output)


if __name__ == "__main__":
    main()
