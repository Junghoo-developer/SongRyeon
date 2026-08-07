from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from freeze_v3 import create_freeze, frozen_paths
from run_bare_v3 import (
    SYSTEM_NAME,
    _prepare_scored_imports,
    acquire_output_lock,
    canonical_output_path,
    ensure_output_path_is_safe as ensure_run_output_is_safe,
    load_existing,
    require_canonical_output,
)
from score_v3 import (
    ensure_output_path_is_safe as ensure_score_output_is_safe,
    require_completed_run,
    run_completed_cleanly,
    score_contract_document,
    validate_contract_preflight_binding,
)
from seal_v3 import canonical_run_path, public_evidence_path, write_bytes_once


READINESS = {"ollama_version": "test", "model": "gemma4:26b"}
MODEL_CONTRACT = {"model_name": "gemma4:26b"}
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
                    "observation": claim["observation"],
                    "reason": "fixture-derived test answer",
                }
                for claim in claims
            ]
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def contract_rows(run_id="contract-run"):
    cases = load("contract_cases.json")["cases"]
    units = load("control/run_plan.json")["contract_units"]
    return [
        {
            "schema_version": 1,
            "plan_id": unit["plan_id"],
            "stage": unit["stage"],
            "case_id": case["case_id"],
            "mode": unit["mode"],
            "difficulty": unit["difficulty"],
            "expected_ids": unit["expected_ids"],
            "internal_claim_ids": unit["internal_claim_ids"],
            "effective_request_sha256": unit["effective_request_sha256"],
            "attempt_id": f"{run_id}:{index}:{unit['plan_id']}",
            "completed": True,
            "answer": answer(case["claims"]),
            "error": None,
            "latency_ms": 1,
            "model_call_count": 1,
            "agent_tool_calls": [],
            "model_metrics": {},
            "model_reply": {
                "model": "gemma4:26b",
                "done_reason": "stop",
                "thinking": "",
            },
            "state": "finished",
        }
        for index, (case, unit) in enumerate(zip(cases, units), 1)
    ]


def completed_contract_document():
    return {
        "schema_version": 1,
        "stage": "contract",
        "system_name": SYSTEM_NAME,
        "freeze_sha256": HASH,
        "freeze_publication": PUBLICATION,
        "run_plan_sha256": HASH,
        "run_id": "contract-run",
        "run_state": "complete",
        "model_readiness": READINESS,
        "final_readiness": READINESS,
        "model_contract": MODEL_CONTRACT,
        "contract_preflight": None,
        "rows": contract_rows(),
    }


def checkpoint_document(unit, *, state="running", row_state="finished"):
    run_id = "checkpoint-run"
    finished = row_state == "finished"
    row = {
        "schema_version": 1,
        "plan_id": unit["plan_id"],
        "stage": unit["stage"],
        "mode": unit["mode"],
        "case_id": unit["case_id"],
        "difficulty": unit["difficulty"],
        "expected_ids": unit["expected_ids"],
        "internal_claim_ids": unit["internal_claim_ids"],
        "effective_request_sha256": unit["effective_request_sha256"],
        "completed": finished,
        "answer": "{}" if finished else "",
        "error": None,
        "latency_ms": 1 if finished else 0,
        "model_call_count": 1 if finished else 0,
        "agent_tool_calls": [],
        "model_metrics": {},
        "model_reply": (
            {"model": "gemma4:26b", "done_reason": "stop", "thinking": ""}
            if finished
            else None
        ),
        "state": row_state,
        "attempt_id": f"{run_id}:1:{unit['plan_id']}",
    }
    return {
        "schema_version": 1,
        "stage": "contract",
        "system_name": SYSTEM_NAME,
        "freeze_sha256": HASH,
        "freeze_publication": PUBLICATION,
        "run_plan_sha256": HASH,
        "model_contract": MODEL_CONTRACT,
        "model_readiness": READINESS,
        "run_id": run_id,
        "run_state": state,
        "final_readiness": READINESS if state == "complete" else None,
        "contract_preflight": None,
        "rows": [row],
    }


def load_checkpoint(path, unit):
    return load_existing(
        path,
        units=[unit],
        expected_stage="contract",
        expected_freeze_sha=HASH,
        expected_freeze_publication=PUBLICATION,
        expected_plan_sha=HASH,
        expected_model_contract=MODEL_CONTRACT,
        expected_readiness=READINESS,
        expected_contract_preflight=None,
    )


def test_only_clean_complete_runs_are_scorable():
    document = completed_contract_document()
    assert run_completed_cleanly(document)
    assert score_contract_document(document)["passed"] is True

    running = deepcopy(document)
    running["run_state"] = "running"
    running["final_readiness"] = None
    assert run_completed_cleanly(running) is False
    assert score_contract_document(running)["passed"] is False
    with pytest.raises(ValueError, match="did not complete cleanly"):
        require_completed_run(running, "contract result")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("completed", False),
        ("model_reply", None),
        ("model_reply", {"model": "wrong", "done_reason": "stop", "thinking": ""}),
        ("model_reply", {"model": "gemma4:26b", "done_reason": "length", "thinking": ""}),
        ("model_reply", {"model": "gemma4:26b", "done_reason": "stop", "thinking": "hidden"}),
    ],
)
def test_invalid_execution_metadata_never_gets_contract_credit(field, value):
    document = completed_contract_document()
    document["rows"][0][field] = value
    assert score_contract_document(document)["passed"] is False
    assert score_contract_document(document)["exact_tasks"] == 3


def test_missing_reordered_and_extra_rows_break_matrix():
    original = completed_contract_document()
    variants = []
    missing = deepcopy(original)
    missing["rows"].pop()
    variants.append(missing)
    reordered = deepcopy(original)
    reordered["rows"][0], reordered["rows"][1] = (
        reordered["rows"][1],
        reordered["rows"][0],
    )
    variants.append(reordered)
    extra = deepcopy(original)
    extra["rows"].append(deepcopy(extra["rows"][-1]))
    variants.append(extra)
    assert all(score_contract_document(item)["matrix_ok"] is False for item in variants)


def test_resume_validates_header_rows_and_refuses_indeterminate_call(tmp_path):
    unit = load("control/run_plan.json")["contract_units"][0]
    path = tmp_path / "checkpoint.json"

    valid = checkpoint_document(unit)
    path.write_text(json.dumps(valid), encoding="utf-8")
    assert load_checkpoint(path, unit)["run_state"] == "running"

    bad_header = deepcopy(valid)
    bad_header["freeze_sha256"] = "tampered"
    path.write_text(json.dumps(bad_header), encoding="utf-8")
    with pytest.raises(ValueError, match="freeze differs"):
        load_checkpoint(path, unit)

    bad_row = deepcopy(valid)
    bad_row["rows"][0]["effective_request_sha256"] = "tampered"
    path.write_text(json.dumps(bad_row), encoding="utf-8")
    with pytest.raises(ValueError, match="row identity differs"):
        load_checkpoint(path, unit)

    started = checkpoint_document(unit, row_state="started")
    path.write_text(json.dumps(started), encoding="utf-8")
    with pytest.raises(RuntimeError, match="indeterminate started call"):
        load_checkpoint(path, unit)

    complete = checkpoint_document(unit, state="complete")
    path.write_text(json.dumps(complete), encoding="utf-8")
    with pytest.raises(ValueError, match="run state is not allowed"):
        load_checkpoint(path, unit)


def test_semantic_result_is_bound_to_exact_contract_artifact():
    contract = completed_contract_document()
    semantic = {"contract_preflight": {"sha256": "abc", "run_id": "contract-run"}}
    validate_contract_preflight_binding(semantic, contract, "abc")
    semantic["contract_preflight"]["sha256"] = "different"
    with pytest.raises(ValueError, match="binding mismatch"):
        validate_contract_preflight_binding(semantic, contract, "abc")


def test_output_lock_and_protected_paths(tmp_path):
    output = tmp_path / "run.json"
    lock = acquire_output_lock(output)
    try:
        with pytest.raises(FileExistsError):
            acquire_output_lock(output)
    finally:
        lock.unlink(missing_ok=True)
    with pytest.raises(ValueError, match="tracked calibration suite"):
        ensure_run_output_is_safe(ROOT / "bad-run.json", [])
    with pytest.raises(ValueError, match="tracked calibration suite"):
        ensure_score_output_is_safe(ROOT / "bad-score.json", [])
    canonical = canonical_output_path("abc", "contract")
    require_canonical_output(canonical, "abc", "contract")
    with pytest.raises(ValueError, match="canonical freeze-scoped path"):
        require_canonical_output(tmp_path / "second-attempt.json", "abc", "contract")


@pytest.mark.parametrize("bad_value", [True, 1.0])
def test_model_call_count_requires_exact_integer_type(bad_value):
    document = completed_contract_document()
    document["rows"][0]["model_call_count"] = bad_value
    assert score_contract_document(document)["matrix_ok"] is False


def test_exact_row_schema_rejects_missing_and_extra_fields():
    missing = completed_contract_document()
    missing["rows"][0].pop("model_metrics")
    extra = completed_contract_document()
    extra["rows"][0]["invented"] = True
    assert score_contract_document(missing)["matrix_ok"] is False
    assert score_contract_document(extra)["matrix_ok"] is False
    assert score_contract_document([])["matrix_ok"] is False


@pytest.mark.parametrize("metrics", [{"eval_count": True}, {"eval_count": -1}, {"eval_count": 1.0}, {"invented": 1}])
def test_model_metrics_use_the_frozen_client_contract(metrics):
    document = completed_contract_document()
    document["rows"][0]["model_metrics"] = metrics
    assert score_contract_document(document)["matrix_ok"] is False


def test_freeze_cannot_be_overwritten_and_includes_all_llm_code(tmp_path):
    existing = tmp_path / "FREEZE.json"
    existing.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        create_freeze(existing)
    frozen = {path.resolve() for path in frozen_paths()}
    suite_files = {
        path.resolve()
        for path in ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.relative_to(ROOT).parts
        and ".pytest_cache" not in path.relative_to(ROOT).parts
        and path.name not in {"FREEZE.json", "FREEZE.json.tmp"}
    }
    assert (ROOT / "artifacts.py").resolve() in frozen
    assert suite_files <= frozen
    assert (WORKSPACE_ROOT / ".gitattributes").resolve() in frozen
    attributes = (WORKSPACE_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert ".gitattributes text eol=lf" in attributes
    assert "evals/semantic_calibration_v3/** text eol=lf" in attributes
    assert "evidence/semantic_calibration_v3/** text eol=lf" in attributes
    assert "llm/**/*.py text eol=lf" in attributes
    llm_sources = {path.resolve() for path in (WORKSPACE_ROOT / "llm").glob("*.py")}
    assert llm_sources
    assert llm_sources <= frozen


def test_scored_import_guard_clears_external_prefix_and_rejects_cache_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("run_bare_v3.os.walk", lambda root: [])
    sys.pycache_prefix = str(tmp_path / "external-cache")
    _prepare_scored_imports()
    assert sys.pycache_prefix is None

    monkeypatch.setattr(
        "run_bare_v3.os.walk",
        lambda root: [(str(root), ["__pycache__"], [])],
    )
    with pytest.raises(RuntimeError, match="bytecode caches"):
        _prepare_scored_imports()


def test_evidence_seal_paths_are_freeze_scoped_and_outside_the_suite():
    run_path = canonical_run_path(HASH, "contract")
    evidence_path = public_evidence_path(HASH, "contract")
    assert HASH in run_path.parts
    assert HASH in evidence_path.parts
    assert ROOT not in evidence_path.parents
    assert evidence_path.name == "contract.json"


def test_evidence_seal_is_atomic_and_never_overwrites(tmp_path):
    destination = tmp_path / "evidence" / "contract.json"
    write_bytes_once(destination, b"first canonical artifact\n")
    assert destination.read_bytes() == b"first canonical artifact\n"

    with pytest.raises(FileExistsError):
        write_bytes_once(destination, b"replacement artifact\n")

    assert destination.read_bytes() == b"first canonical artifact\n"
    assert list(destination.parent.glob("*.tmp")) == []
