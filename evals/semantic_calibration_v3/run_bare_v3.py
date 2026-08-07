"""Run the frozen v3 contract preflight or paired bare semantic plan."""

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
    raise RuntimeError("scored runner must be executed by direct file path, not -m")
if __name__ == "__main__":
    _prepare_scored_imports()
else:
    sys.pycache_prefix = None
    sys.dont_write_bytecode = True

import argparse
import atexit
import hashlib
import json
from pathlib import Path
import time
import uuid


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
RUN_OUTPUT_ROOT = WORKSPACE_ROOT / ".tmp" / "evals" / "semantic_calibration_v3"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artifacts import SYSTEM_NAME, validate_artifact_document
from freeze_v3 import (
    freeze_publication,
    package_versions,
    sha256,
    verify_freeze,
    verify_freeze_publication,
)
from llm import OllamaClient
from schemas import load_strict_json
from seal_v3 import verify_public_evidence
from score_v3 import score_contract_document


def write_checkpoint(path, document):
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


def acquire_output_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    descriptor = os.open(
        str(lock_path),
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
    )
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
    finally:
        os.close(descriptor)

    def release():
        lock_path.unlink(missing_ok=True)

    atexit.register(release)
    return lock_path


def ensure_output_path_is_safe(output, protected_paths):
    resolved = output.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("run output must be outside the tracked calibration suite")
    protected = {Path(path).resolve() for path in protected_paths if path is not None}
    if resolved in protected:
        raise ValueError("run output collides with an input or freeze artifact")


def canonical_output_path(freeze_sha, stage):
    if stage not in {"contract", "semantic"}:
        raise ValueError("unknown run stage")
    return RUN_OUTPUT_ROOT / freeze_sha / f"{stage}.json"


def require_canonical_output(path, freeze_sha, stage):
    expected = canonical_output_path(freeze_sha, stage).resolve()
    if path.resolve() != expected:
        raise ValueError(f"{stage} output must use canonical freeze-scoped path: {expected}")


def load_existing(
    path,
    *,
    units,
    expected_stage,
    expected_freeze_sha,
    expected_freeze_publication,
    expected_plan_sha,
    expected_model_contract,
    expected_readiness,
    expected_contract_preflight,
):
    document = load_strict_json(path)
    validate_artifact_document(
        document,
        units=units,
        expected_stage=expected_stage,
        expected_freeze_sha=expected_freeze_sha,
        expected_freeze_publication=expected_freeze_publication,
        expected_plan_sha=expected_plan_sha,
        expected_model_contract=expected_model_contract,
        expected_readiness=expected_readiness,
        expected_contract_preflight=expected_contract_preflight,
        require_exact_rows=False,
        allow_started=True,
        allowed_run_states={"running"},
    )
    for row in document["rows"]:
        if row["state"] != "finished":
            raise RuntimeError(
                "checkpoint contains an indeterminate started call; "
                "do not retry it in the same scored run"
            )
    return document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("contract", "semantic"), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--contract-results", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    freeze = verify_freeze(args.freeze)
    freeze_sha = sha256(args.freeze)
    publication = freeze_publication(args.freeze) if args.stage == "contract" else None
    if args.output is None:
        args.output = canonical_output_path(freeze_sha, args.stage)
    require_canonical_output(args.output, freeze_sha, args.stage)
    if args.stage == "semantic":
        canonical_contract = canonical_output_path(freeze_sha, "contract")
        if args.contract_results is None:
            args.contract_results = canonical_contract
        elif args.contract_results.resolve() != canonical_contract.resolve():
            raise ValueError(
                "semantic stage must use the canonical contract artifact for this freeze"
            )
    ensure_output_path_is_safe(
        args.output,
        [
            args.freeze,
            args.contract_results,
            ROOT / "control" / "run_plan.json",
            ROOT / "control" / "oracle_results.json",
            ROOT / "manifest.json",
            ROOT / "contract_cases.json",
        ],
    )
    if args.resume and not args.output.exists():
        raise FileNotFoundError("--resume requires an existing checkpoint")
    if not args.resume and args.output.exists():
        raise FileExistsError(
            "canonical output already exists; the same freeze cannot start another run"
        )
    acquire_output_lock(args.output)

    if package_versions() != freeze["package_versions"]:
        raise ValueError("evaluation package versions changed")
    plan = load_strict_json(ROOT / "control" / "run_plan.json")
    plan_sha = sha256(ROOT / "control" / "run_plan.json")
    units = plan[f"{args.stage}_units"]
    expected_count = 4 if args.stage == "contract" else 48
    if len(units) != expected_count:
        raise ValueError("frozen run plan unit count differs")

    client = OllamaClient(
        model_name=freeze["model_contract"]["model_name"],
        timeout_seconds=freeze["model_contract"]["timeout_seconds"],
        num_ctx=freeze["model_contract"]["num_ctx"],
        keep_alive=freeze["model_contract"]["keep_alive"],
        temperature=freeze["model_contract"]["temperature"],
        seed=freeze["model_contract"]["seed"],
    )
    readiness = client.check_ready()
    if readiness != freeze["model_readiness"]:
        raise RuntimeError("Ollama server/model identity differs from freeze")

    contract_preflight = None
    if args.stage == "semantic":
        if args.contract_results is None:
            raise ValueError("semantic stage requires --contract-results")
        contract_sha_before = sha256(args.contract_results)
        contract_document = load_strict_json(args.contract_results)
        if sha256(args.contract_results) != contract_sha_before:
            raise RuntimeError("contract preflight artifact changed while reading")
        publication = contract_document.get("freeze_publication")
        verify_freeze_publication(publication, args.freeze)
        verify_public_evidence(
            args.contract_results,
            freeze_sha,
            "contract",
            publication["remote_ref"],
        )
        validate_artifact_document(
            contract_document,
            units=plan["contract_units"],
            expected_stage="contract",
            expected_freeze_sha=freeze_sha,
            expected_freeze_publication=publication,
            expected_plan_sha=plan_sha,
            expected_model_contract=freeze["model_contract"],
            expected_readiness=readiness,
            expected_contract_preflight=None,
            require_exact_rows=True,
            allow_started=False,
            allowed_run_states={"complete"},
        )
        contract_score = score_contract_document(contract_document)
        if not contract_score["passed"]:
            raise RuntimeError("contract preflight did not pass 4/4")
        contract_preflight = {
            "sha256": contract_sha_before,
            "run_id": contract_document["run_id"],
        }

    if args.resume:
        document = load_existing(
            args.output,
            units=units,
            expected_stage=args.stage,
            expected_freeze_sha=freeze_sha,
            expected_freeze_publication=publication,
            expected_plan_sha=plan_sha,
            expected_model_contract=freeze["model_contract"],
            expected_readiness=readiness,
            expected_contract_preflight=contract_preflight,
        )
    else:
        document = {
            "schema_version": 1,
            "stage": args.stage,
            "system_name": SYSTEM_NAME,
            "freeze_sha256": freeze_sha,
            "freeze_publication": publication,
            "run_plan_sha256": plan_sha,
            "model_contract": freeze["model_contract"],
            "model_readiness": readiness,
            "run_id": uuid.uuid4().hex,
            "run_state": "running",
            "final_readiness": None,
            "contract_preflight": contract_preflight,
            "rows": [],
        }
    for unit_index in range(len(document["rows"]), len(units)):
        unit = units[unit_index]
        effective = {
            "system_prompt": unit["system_prompt"],
            "user_prompt": unit["user_prompt"],
            "response_schema": unit["response_schema"],
        }
        effective_sha = hashlib.sha256(
            json.dumps(
                effective,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        if effective_sha != unit["effective_request_sha256"]:
            raise ValueError("effective request differs from frozen plan")
        attempt_id = (
            f"{document['run_id']}:{unit_index + 1}:{unit['plan_id']}"
        )
        started_row = {
            "schema_version": 1,
            "plan_id": unit["plan_id"],
            "stage": unit["stage"],
            "mode": unit["mode"],
            "case_id": unit["case_id"],
            "difficulty": unit["difficulty"],
            "expected_ids": unit["expected_ids"],
            "internal_claim_ids": unit["internal_claim_ids"],
            "effective_request_sha256": unit["effective_request_sha256"],
            "completed": False,
            "answer": "",
            "error": None,
            "latency_ms": 0,
            "model_call_count": 0,
            "agent_tool_calls": [],
            "model_metrics": {},
            "model_reply": None,
            "state": "started",
            "attempt_id": attempt_id,
        }
        document["rows"].append(started_row)
        validate_artifact_document(
            document,
            units=units,
            expected_stage=args.stage,
            expected_freeze_sha=freeze_sha,
            expected_freeze_publication=publication,
            expected_plan_sha=plan_sha,
            expected_model_contract=freeze["model_contract"],
            expected_readiness=readiness,
            expected_contract_preflight=contract_preflight,
            require_exact_rows=False,
            allow_started=True,
            allowed_run_states={"running"},
        )
        write_checkpoint(args.output, document)
        started = time.perf_counter_ns()
        answer = ""
        error = None
        metrics = {}
        model_reply = None
        try:
            reply = client.complete(
                system_prompt=unit["system_prompt"],
                user_prompt=unit["user_prompt"],
                response_schema=unit["response_schema"],
                num_predict=unit["num_predict"],
            )
            answer = reply.content
            metrics = reply.metrics
            model_reply = {
                "model": reply.model,
                "done_reason": reply.done_reason,
                "thinking": reply.thinking,
            }
            if reply.model != freeze["model_contract"]["model_name"]:
                error = "ModelProtocolError: returned model differs from freeze"
            elif reply.done_reason != "stop":
                error = "ModelProtocolError: done_reason is not stop"
            elif reply.thinking != "":
                error = "ModelProtocolError: think=false returned hidden thinking"
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
        document["rows"][-1] = {
            **started_row,
            "state": "finished",
            "completed": error is None and bool(answer.strip()),
            "answer": answer,
            "error": error,
            "latency_ms": round(
                (time.perf_counter_ns() - started) / 1_000_000,
                3,
            ),
            "model_call_count": 1,
            "model_metrics": metrics,
            "model_reply": model_reply,
        }
        validate_artifact_document(
            document,
            units=units,
            expected_stage=args.stage,
            expected_freeze_sha=freeze_sha,
            expected_freeze_publication=publication,
            expected_plan_sha=plan_sha,
            expected_model_contract=freeze["model_contract"],
            expected_readiness=readiness,
            expected_contract_preflight=contract_preflight,
            require_exact_rows=False,
            allow_started=False,
            allowed_run_states={"running"},
        )
        write_checkpoint(args.output, document)
        print(f"[{len(document['rows'])}/{len(units)}] {unit['plan_id']}", flush=True)

    final_readiness = None
    try:
        verify_freeze(args.freeze)
        final_readiness = client.check_ready()
        if final_readiness != freeze["model_readiness"]:
            raise RuntimeError("Ollama server/model identity changed during run")
    except Exception:
        document["run_state"] = "invalid"
        document["final_readiness"] = final_readiness
        validate_artifact_document(
            document,
            units=units,
            expected_stage=args.stage,
            expected_freeze_sha=freeze_sha,
            expected_freeze_publication=publication,
            expected_plan_sha=plan_sha,
            expected_model_contract=freeze["model_contract"],
            expected_readiness=readiness,
            expected_contract_preflight=contract_preflight,
            require_exact_rows=True,
            allow_started=False,
            allowed_run_states={"invalid"},
        )
        write_checkpoint(args.output, document)
        raise
    document["run_state"] = "complete"
    document["final_readiness"] = final_readiness
    validate_artifact_document(
        document,
        units=units,
        expected_stage=args.stage,
        expected_freeze_sha=freeze_sha,
        expected_freeze_publication=publication,
        expected_plan_sha=plan_sha,
        expected_model_contract=freeze["model_contract"],
        expected_readiness=readiness,
        expected_contract_preflight=contract_preflight,
        require_exact_rows=True,
        allow_started=False,
        allowed_run_states={"complete"},
    )
    write_checkpoint(args.output, document)
    print(args.output)


if __name__ == "__main__":
    main()
