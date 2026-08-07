"""Run one no-retry local or cloud A-only audit over the frozen cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Mapping

from llm import CodexAccountIntegrationClient, OllamaClient
from llm.client import (
    DEFAULT_BASE_URL,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_TIMEOUT_SECONDS,
)

from .prompts import (
    AUDIT_NUM_PREDICT,
    AUDIT_SCHEMA,
    build_audit_prompts,
    canonical_json,
    parse_audit_output,
)
from .freeze import verify_freeze_publication
from . import schemas


EXPERIMENT_ID = "songryeon-hybrid-a-only-audit-pilot-v1-2"
ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
SOURCE_PATH = ROOT / "source_snapshot.json"
FREEZE_PATH = ROOT / "FREEZE.json"
OUTPUT_ROOT = WORKSPACE_ROOT / ".tmp" / "evals" / "hybrid_audit_v1_2"

LOCAL_CONDITION = "local-a-only-auditor"
CLOUD_CONDITION = "cloud-a-only-auditor"
CONDITIONS = (LOCAL_CONDITION, CLOUD_CONDITION)

LOCAL_MODEL = "gemma4:26b"
LOCAL_NUM_CTX = 16_384
CLOUD_MODEL = "gpt-5.6-sol"
CLOUD_EFFORT = "medium"
FORBIDDEN_CLOUD_AUTH_ENV = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CODEX_ACCESS_TOKEN",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("SHA-256 입력은 문자열이어야 합니다.")
    return sha256_bytes(value.encode("utf-8"))


def load_strict_json(path: Path) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")

    def reject_constant(value: str) -> None:
        raise ValueError(f"JSON 표준에 없는 상수입니다: {value}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"중복 JSON key입니다: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw,
        parse_constant=reject_constant,
        object_pairs_hook=unique_object,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON 문서 최상위 값은 객체여야 합니다.")
    return value


def _atomic_write_json(path: Path, document: Mapping[str, Any]) -> None:
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
            file.write((canonical_json(document) + "\n").encode("utf-8"))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json_exclusive(path: Path, document: Mapping[str, Any]) -> None:
    """Create one durable JSON file without replacing an existing path."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (canonical_json(document) + "\n").encode("utf-8")
    try:
        descriptor = os.open(
            str(path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError:
        raise FileExistsError(
            f"append-only journal path already exists: {path}"
        ) from None
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _reserve_attempt(output_path: Path) -> Path:
    lock_path = output_path.with_suffix(".attempt.lock")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"canonical 결과가 이미 있습니다: {output_path}")
    payload = canonical_json(
        {
            "experiment_id": EXPERIMENT_ID,
            "output_path": str(output_path.resolve()),
            "status": "attempt_reserved",
        }
    ).encode("utf-8") + b"\n"
    try:
        descriptor = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError:
        raise FileExistsError(
            f"canonical attempt가 이미 예약됐습니다: {lock_path}"
        ) from None
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return lock_path


def _verify_freeze() -> tuple[dict[str, Any], dict[str, Any], str]:
    if not FREEZE_PATH.exists():
        raise FileNotFoundError("모델 호출 전에 FREEZE.json을 만들어야 합니다.")
    freeze = load_strict_json(FREEZE_PATH)
    payload_sha = freeze.get("freeze_payload_sha256")
    payload = dict(freeze)
    payload.pop("freeze_payload_sha256", None)
    if payload_sha != sha256_text(canonical_json(payload)):
        raise RuntimeError("FREEZE.json payload hash가 일치하지 않습니다.")
    verify_freeze_publication(freeze)
    files = freeze.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("freeze file hash 목록이 없습니다.")
    for relative_path, expected_sha in files.items():
        path = WORKSPACE_ROOT / relative_path
        if not path.is_file():
            raise RuntimeError(f"동결 파일이 없습니다: {relative_path}")
        actual_sha = sha256_bytes(path.read_bytes())
        if actual_sha != expected_sha:
            raise RuntimeError(f"동결 파일이 바뀌었습니다: {relative_path}")
    source = load_strict_json(SOURCE_PATH)
    schemas.validate_source_snapshot(source)
    source_sha = sha256_bytes(SOURCE_PATH.read_bytes())
    if files.get("evals/hybrid_audit_v1/source_snapshot.json") != source_sha:
        raise RuntimeError("source snapshot hash가 freeze와 다릅니다.")
    return freeze, source, source_sha


def _validate_no_cloud_api_auth(environment: Mapping[str, str]) -> None:
    present = [name for name in FORBIDDEN_CLOUD_AUTH_ENV if name in environment]
    if present:
        raise RuntimeError(
            "Codex 계정 감사 실행은 API/access-token 환경 변수를 거부합니다: "
            + ", ".join(present)
        )


def _build_client(condition: str, args: argparse.Namespace):
    if condition == LOCAL_CONDITION:
        client = OllamaClient(
            base_url=args.base_url,
            model_name=LOCAL_MODEL,
            timeout_seconds=args.timeout_seconds,
            num_ctx=LOCAL_NUM_CTX,
            keep_alive=args.keep_alive,
            temperature=0,
            seed=42,
        )
        readiness = client.check_ready()
        return client, {
            **readiness,
            "provider": client.provider,
            "execution_mode": client.execution_mode,
            "temperature": client.temperature,
            "seed": client.seed,
            "num_ctx": client.num_ctx,
        }
    if condition == CLOUD_CONDITION:
        _validate_no_cloud_api_auth(os.environ)
        client = CodexAccountIntegrationClient(
            model_name=CLOUD_MODEL,
            reasoning_effort=CLOUD_EFFORT,
        )
        readiness = client.check_configuration()
        return client, {**readiness, "tools_allowed": False}
    raise ValueError(f"알 수 없는 condition입니다: {condition}")


def _safe_error(error: BaseException) -> dict[str, str]:
    return {
        "type": type(error).__name__,
        "message": str(error)[:500],
    }


def _new_artifact(
    *,
    condition: str,
    source: Mapping[str, Any],
    source_sha: str,
    freeze: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "condition": condition,
        "run_state": "running",
        "source_snapshot_id": source["snapshot_id"],
        "source_snapshot_sha256": source_sha,
        "freeze_payload_sha256": freeze["freeze_payload_sha256"],
        "model_readiness": dict(readiness),
        "planned_case_ids": [case["case_id"] for case in source["cases"]],
        "started_at_unix": time.time(),
        "finished_at_unix": None,
        "rows": [],
        "summary": None,
    }


def _run_case(
    client,
    case: Mapping[str, Any],
    *,
    runner_attempt: int,
    checkpoint_before_invocation: Callable[[Mapping[str, Any]], None],
) -> dict[str, Any]:
    # Project first.  Nothing outside this schemas-owned boundary may become
    # prompt material, even when a source case carries goals, oracle labels,
    # earlier reviews, or other R memory beside the allowed fields.
    material = schemas.audit_prompt_material(case)
    if type(runner_attempt) is not int or runner_attempt < 1:
        raise ValueError("runner_attempt must be a positive integer")
    if not callable(checkpoint_before_invocation):
        raise TypeError("checkpoint_before_invocation must be callable")

    started = time.time()
    system_prompt, user_prompt = build_audit_prompts(
        a_records=material["a_records"],
        candidate_draft=material["draft"],
    )
    row: dict[str, Any] = {
        "case_id": case["case_id"],
        "runner_attempt": runner_attempt,
        "state": "invocation_reserved",
        "started_at_unix": started,
        "finished_at_unix": None,
        "latency_ms": None,
        "a_records_sha256": sha256_text(
            canonical_json(material["a_records"])
        ),
        "draft_sha256": sha256_text(material["draft"]),
        "system_prompt_sha256": sha256_text(system_prompt),
        "user_prompt_sha256": sha256_text(user_prompt),
        "raw_response": "",
        "raw_response_sha256": None,
        "thinking": "",
        "parsed_output": None,
        "requested_model": getattr(client, "model_name", None),
        "client_reported_model": None,
        "client_done_reason": None,
        "metrics": {},
        "error": None,
    }
    # This callback must durably persist the reserved row.  If it fails, the
    # exception propagates and the model is never invoked.
    checkpoint_before_invocation(row)
    try:
        reply = client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=AUDIT_SCHEMA,
            num_predict=AUDIT_NUM_PREDICT,
        )
        row["raw_response"] = reply.content
        row["raw_response_sha256"] = sha256_text(reply.content)
        row["thinking"] = reply.thinking
        row["client_reported_model"] = reply.model
        row["client_done_reason"] = reply.done_reason
        row["metrics"] = reply.metrics
        row["parsed_output"] = parse_audit_output(reply.content)
        row["state"] = "valid"
    except Exception as error:
        row["state"] = "failed"
        row["error"] = _safe_error(error)
    finished = time.time()
    row["finished_at_unix"] = finished
    row["latency_ms"] = round((finished - started) * 1000, 3)
    return row


def _summarize_rows(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    state_counts: dict[str, int] = {}
    total_latency = 0.0
    metric_totals: dict[str, int | float] = {}
    for row in rows:
        state = row["state"]
        state_counts[state] = state_counts.get(state, 0) + 1
        total_latency += float(row["latency_ms"])
        for key, value in row["metrics"].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metric_totals[key] = metric_totals.get(key, 0) + value
    return {
        "planned_rows": len(rows),
        "state_counts": state_counts,
        "latency_ms_sum": round(total_latency, 3),
        "metric_totals": metric_totals,
    }


def run_condition(condition: str, args: argparse.Namespace) -> Path:
    freeze, source, source_sha = _verify_freeze()
    client = None
    client, readiness = _build_client(condition, args)
    output_directory = OUTPUT_ROOT / freeze["freeze_payload_sha256"]
    output_path = output_directory / f"{condition}.json"
    _reserve_attempt(output_path)
    journal_directory = output_path.with_suffix(".journal")
    journal_directory.mkdir(parents=True, exist_ok=False)
    artifact = _new_artifact(
        condition=condition,
        source=source,
        source_sha=source_sha,
        freeze=freeze,
        readiness=readiness,
    )
    _write_json_exclusive(journal_directory / "0000-start.json", artifact)
    try:
        for runner_attempt, case in enumerate(source["cases"], 1):
            def checkpoint_before_invocation(
                reserved_row: Mapping[str, Any],
            ) -> None:
                _write_json_exclusive(
                    journal_directory
                    / f"{runner_attempt:04d}-reserved.json",
                    {
                        "schema_version": 1,
                        "experiment_id": EXPERIMENT_ID,
                        "condition": condition,
                        "freeze_payload_sha256": freeze[
                            "freeze_payload_sha256"
                        ],
                        "model_readiness": readiness,
                        "row": dict(reserved_row),
                    },
                )

            row = _run_case(
                client,
                case,
                runner_attempt=runner_attempt,
                checkpoint_before_invocation=checkpoint_before_invocation,
            )
            artifact["rows"].append(row)
            _write_json_exclusive(
                journal_directory / f"{runner_attempt:04d}-result.json",
                row,
            )
        artifact["run_state"] = "complete"
        artifact["finished_at_unix"] = time.time()
        artifact["summary"] = _summarize_rows(artifact["rows"])
        _write_json_exclusive(output_path, artifact)
        return output_path
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("condition", choices=CONDITIONS)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument("--keep-alive", default=DEFAULT_KEEP_ALIVE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_path = run_condition(args.condition, args)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
