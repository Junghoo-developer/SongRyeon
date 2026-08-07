"""Shared fail-closed schema for v3 runner and scorer artifacts."""

from __future__ import annotations

import math
import re


SYSTEM_NAME = "bare-gemma4-26b-complete-source-v3"
DOCUMENT_KEYS = {
    "schema_version",
    "stage",
    "system_name",
    "freeze_sha256",
    "freeze_publication",
    "run_plan_sha256",
    "model_contract",
    "model_readiness",
    "run_id",
    "run_state",
    "final_readiness",
    "contract_preflight",
    "rows",
}
ROW_KEYS = {
    "schema_version",
    "plan_id",
    "stage",
    "mode",
    "case_id",
    "difficulty",
    "expected_ids",
    "internal_claim_ids",
    "effective_request_sha256",
    "completed",
    "answer",
    "error",
    "latency_ms",
    "model_call_count",
    "agent_tool_calls",
    "model_metrics",
    "model_reply",
    "state",
    "attempt_id",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
MODEL_METRIC_KEYS = {
    "total_duration",
    "load_duration",
    "prompt_eval_count",
    "prompt_eval_duration",
    "eval_count",
    "eval_duration",
}


def _is_nonnegative_number(value):
    return bool(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def validate_document_header(
    document,
    *,
    expected_stage,
    expected_freeze_sha,
    expected_freeze_publication,
    expected_plan_sha,
    expected_model_contract,
    expected_readiness,
    expected_contract_preflight,
):
    if not isinstance(document, dict) or set(document) != DOCUMENT_KEYS:
        raise ValueError("checkpoint document schema differs")
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise ValueError("checkpoint schema version differs")
    if document.get("stage") != expected_stage:
        raise ValueError("existing checkpoint stage differs")
    if document.get("system_name") != SYSTEM_NAME:
        raise ValueError("existing checkpoint system differs")
    if document.get("freeze_sha256") != expected_freeze_sha:
        raise ValueError("existing checkpoint freeze differs")
    if not isinstance(document["freeze_sha256"], str) or SHA256.fullmatch(
        document["freeze_sha256"]
    ) is None:
        raise ValueError("checkpoint freeze hash is invalid")
    if document.get("freeze_publication") != expected_freeze_publication:
        raise ValueError("existing checkpoint freeze publication differs")
    publication = document["freeze_publication"]
    if (
        not isinstance(publication, dict)
        or set(publication) != {"commit", "remote_ref"}
        or not isinstance(publication["commit"], str)
        or GIT_COMMIT.fullmatch(publication["commit"]) is None
        or not isinstance(publication["remote_ref"], str)
        or not publication["remote_ref"]
    ):
        raise ValueError("checkpoint freeze publication is invalid")
    if document.get("run_plan_sha256") != expected_plan_sha:
        raise ValueError("existing checkpoint plan differs")
    if not isinstance(document["run_plan_sha256"], str) or SHA256.fullmatch(
        document["run_plan_sha256"]
    ) is None:
        raise ValueError("checkpoint plan hash is invalid")
    if document.get("model_contract") != expected_model_contract:
        raise ValueError("existing checkpoint model contract differs")
    if document.get("model_readiness") != expected_readiness:
        raise ValueError("existing checkpoint model readiness differs")
    if document.get("contract_preflight") != expected_contract_preflight:
        raise ValueError("existing checkpoint contract preflight differs")
    binding = document["contract_preflight"]
    if binding is not None and (
        not isinstance(binding, dict)
        or set(binding) != {"sha256", "run_id"}
        or not isinstance(binding["sha256"], str)
        or SHA256.fullmatch(binding["sha256"]) is None
        or not isinstance(binding["run_id"], str)
        or not binding["run_id"]
    ):
        raise ValueError("checkpoint contract preflight binding is invalid")
    if expected_stage == "contract" and binding is not None:
        raise ValueError("contract checkpoint cannot reference a preflight")
    if expected_stage == "semantic" and binding is None:
        raise ValueError("semantic checkpoint requires a contract preflight")
    if document.get("run_state") not in {"running", "complete", "invalid"}:
        raise ValueError("existing checkpoint run state is invalid")
    if document["run_state"] == "running" and document.get("final_readiness") is not None:
        raise ValueError("running checkpoint cannot have final readiness")
    if (
        document["run_state"] == "complete"
        and document.get("final_readiness") != expected_readiness
    ):
        raise ValueError("completed checkpoint final readiness differs")
    if not isinstance(document.get("rows"), list):
        raise ValueError("existing checkpoint rows are invalid")
    if not isinstance(document.get("run_id"), str) or not document["run_id"]:
        raise ValueError("existing checkpoint run id is invalid")


def validate_row(row, unit, *, run_id, index, expected_model_name):
    if not isinstance(row, dict) or set(row) != ROW_KEYS:
        raise ValueError("checkpoint row schema differs")
    if type(row.get("schema_version")) is not int or row["schema_version"] != 1:
        raise ValueError("checkpoint row schema version differs")
    expected_identity = (
        row.get("plan_id") == unit["plan_id"]
        and row.get("stage") == unit["stage"]
        and row.get("mode") == unit["mode"]
        and row.get("case_id") == unit["case_id"]
        and row.get("difficulty") == unit["difficulty"]
        and type(row.get("expected_ids")) is list
        and row["expected_ids"] == unit["expected_ids"]
        and type(row.get("internal_claim_ids")) is list
        and row["internal_claim_ids"] == unit["internal_claim_ids"]
        and row.get("effective_request_sha256") == unit["effective_request_sha256"]
        and row.get("attempt_id") == f"{run_id}:{index}:{unit['plan_id']}"
    )
    if not expected_identity:
        raise ValueError("checkpoint row identity differs from frozen plan")
    if type(row.get("completed")) is not bool:
        raise ValueError("checkpoint completion flag is invalid")
    if not isinstance(row.get("answer"), str):
        raise ValueError("checkpoint answer is not a string")
    if row.get("error") is not None and (
        not isinstance(row["error"], str) or not row["error"]
    ):
        raise ValueError("checkpoint error is invalid")
    if not _is_nonnegative_number(row.get("latency_ms")):
        raise ValueError("checkpoint latency is invalid")
    if type(row.get("model_call_count")) is not int:
        raise ValueError("checkpoint model call count is invalid")
    if row.get("agent_tool_calls") != []:
        raise ValueError("bare checkpoint cannot contain agent tool calls")
    if not isinstance(row.get("model_metrics"), dict):
        raise ValueError("checkpoint model metrics are invalid")
    if not set(row["model_metrics"]) <= MODEL_METRIC_KEYS or any(
        type(value) is not int or value < 0
        for value in row["model_metrics"].values()
    ):
        raise ValueError("checkpoint model metric values are invalid")
    reply = row.get("model_reply")
    if reply is not None:
        if not isinstance(reply, dict) or set(reply) != {"model", "done_reason", "thinking"}:
            raise ValueError("checkpoint model reply metadata is invalid")
        if not isinstance(reply["model"], str) or not reply["model"]:
            raise ValueError("checkpoint reply model is invalid")
        if reply["done_reason"] is not None and (
            not isinstance(reply["done_reason"], str) or not reply["done_reason"]
        ):
            raise ValueError("checkpoint done reason is invalid")
        if not isinstance(reply["thinking"], str):
            raise ValueError("checkpoint thinking metadata is invalid")

    state = row.get("state")
    if state == "started":
        if not (
            row["completed"] is False
            and row["answer"] == ""
            and row["error"] is None
            and row["latency_ms"] == 0
            and row["model_call_count"] == 0
            and row["model_metrics"] == {}
            and reply is None
        ):
            raise ValueError("started checkpoint row has impossible execution fields")
        return
    if state != "finished" or row["model_call_count"] != 1:
        raise ValueError("checkpoint row execution state is invalid")
    if row["completed"]:
        if not (
            row["error"] is None
            and bool(row["answer"].strip())
            and isinstance(reply, dict)
            and reply["model"] == expected_model_name
            and reply["done_reason"] == "stop"
            and reply["thinking"] == ""
        ):
            raise ValueError("completed checkpoint row violates execution contract")
    elif not isinstance(row["error"], str) or not row["error"]:
        raise ValueError("failed checkpoint row must preserve a nonempty error")


def validate_artifact_document(
    document,
    *,
    units,
    expected_stage,
    expected_freeze_sha,
    expected_freeze_publication,
    expected_plan_sha,
    expected_model_contract,
    expected_readiness,
    expected_contract_preflight,
    require_exact_rows,
    allow_started,
    allowed_run_states,
):
    validate_document_header(
        document,
        expected_stage=expected_stage,
        expected_freeze_sha=expected_freeze_sha,
        expected_freeze_publication=expected_freeze_publication,
        expected_plan_sha=expected_plan_sha,
        expected_model_contract=expected_model_contract,
        expected_readiness=expected_readiness,
        expected_contract_preflight=expected_contract_preflight,
    )
    if document["run_state"] not in allowed_run_states:
        raise ValueError("checkpoint run state is not allowed here")
    rows = document["rows"]
    if require_exact_rows and len(rows) != len(units):
        raise ValueError("checkpoint row count differs from frozen plan")
    if len(rows) > len(units):
        raise ValueError("checkpoint contains extra rows")
    started_indices = []
    for index, (row, unit) in enumerate(zip(rows, units), 1):
        validate_row(
            row,
            unit,
            run_id=document["run_id"],
            index=index,
            expected_model_name=expected_model_contract["model_name"],
        )
        if row["state"] == "started":
            started_indices.append(index)
    if started_indices:
        if not allow_started:
            raise ValueError("checkpoint contains an unfinished started row")
        if started_indices != [len(rows)]:
            raise ValueError("only the final checkpoint row may be started")
    if document["run_state"] == "complete" and (
        len(rows) != len(units) or started_indices
    ):
        raise ValueError("complete checkpoint does not contain all finished rows")


def scoring_matrix_valid(document, units, *, expected_stage):
    if not isinstance(document, dict):
        return False
    try:
        validate_artifact_document(
            document,
            units=units,
            expected_stage=expected_stage,
            expected_freeze_sha=document.get("freeze_sha256"),
            expected_freeze_publication=document.get("freeze_publication"),
            expected_plan_sha=document.get("run_plan_sha256"),
            expected_model_contract=document.get("model_contract"),
            expected_readiness=document.get("model_readiness"),
            expected_contract_preflight=document.get("contract_preflight"),
            require_exact_rows=True,
            allow_started=False,
            allowed_run_states={"complete"},
        )
    except (KeyError, TypeError, ValueError):
        return False
    return True
