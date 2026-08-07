"""Pure data contracts for the local-worker/cloud-auditor study.

This module intentionally contains no model client.  It defines the narrow
boundary that an auditor may see and the deterministic routing policy used by
the study.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re


SNAPSHOT_CASE_COUNT = 30
AUDIT_INPUT_KEYS = {"a_records"}
A_RECORD_KEYS = {
    "provenance_id",
    "tool_name",
    "arguments",
    "success",
    "content",
    "error",
    "information_class",
    "code_verifiable",
}
AUDIT_OUTPUT_KEYS = {"verdict", "reason"}
AUDIT_VERDICTS = {"permit", "reject"}
PROVENANCE_ID = re.compile(r"^A-[0-9a-f]{64}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SnapshotValidationError(ValueError):
    """A source snapshot or one of its projections violates the study contract."""


def canonical_json(value) -> str:
    """Return the canonical UTF-8 JSON representation used for all hashes."""

    serialized = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    serialized.encode("utf-8", errors="strict")
    return serialized


def _reject_non_json_constant(value):
    raise ValueError(f"non-JSON constant: {value}")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(text):
    """Decode one strict JSON value without repairing duplicate keys or NaN."""

    if not isinstance(text, str):
        raise TypeError("JSON input must be text")
    value = json.loads(
        text,
        parse_constant=_reject_non_json_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
    canonical_json(value)
    return value


def _require_exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != expected:
        raise SnapshotValidationError(f"{label} schema mismatch")


def _require_nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise SnapshotValidationError(f"{label} must be a nonempty string")


def _require_sha256(value, label):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise SnapshotValidationError(f"{label} must be a lowercase SHA-256")


def deterministic_a_provenance_id(
    case_id: str,
    packet_sha256: str,
    ordinal: int,
) -> str:
    """Create a stable identity for one A record copied into the audit view."""

    _require_nonempty_string(case_id, "case_id")
    _require_sha256(packet_sha256, "packet_sha256")
    if type(ordinal) is not int or ordinal < 1:
        raise SnapshotValidationError("A record ordinal must be a positive integer")
    material = (
        f"hybrid-audit-v1|A|{case_id}|{packet_sha256}|{ordinal}"
    ).encode("utf-8")
    return "A-" + hashlib.sha256(material).hexdigest()


def validate_audit_input(audit_input) -> None:
    """Validate the A-only packet visible to both local and cloud auditors."""

    _require_exact_keys(audit_input, AUDIT_INPUT_KEYS, "audit_input")
    records = audit_input["a_records"]
    if not isinstance(records, list) or not records:
        raise SnapshotValidationError("audit_input.a_records must be nonempty")

    provenance_ids = set()
    for index, record in enumerate(records, 1):
        _require_exact_keys(record, A_RECORD_KEYS, f"A record {index}")
        provenance_id = record["provenance_id"]
        if not isinstance(provenance_id, str) or not PROVENANCE_ID.fullmatch(
            provenance_id
        ):
            raise SnapshotValidationError("A record provenance_id is invalid")
        if provenance_id in provenance_ids:
            raise SnapshotValidationError("A record provenance_id must be unique")
        provenance_ids.add(provenance_id)

        _require_nonempty_string(record["tool_name"], "A record tool_name")
        if not isinstance(record["arguments"], dict):
            raise SnapshotValidationError("A record arguments must be an object")
        try:
            canonical_json(record["arguments"])
        except (TypeError, ValueError, UnicodeError, RecursionError) as failure:
            raise SnapshotValidationError(
                "A record arguments must contain strict JSON values"
            ) from failure
        if type(record["success"]) is not bool:
            raise SnapshotValidationError("A record success must be boolean")
        if not isinstance(record["content"], str):
            raise SnapshotValidationError("A record content must be text")
        if record["error"] is not None and not isinstance(record["error"], str):
            raise SnapshotValidationError("A record error must be text or null")
        if record["information_class"] != "absolute":
            raise SnapshotValidationError("audit_input may contain only absolute records")
        if record["code_verifiable"] is not True:
            raise SnapshotValidationError("audit_input may contain only code-verifiable records")


def audit_prompt_material(case) -> dict:
    """Project a case to the only material an auditor prompt may receive.

    The active goal, fixture R, historical local review, preliminary score, and
    expected verdict are deliberately unreachable through this return value.
    """

    if not isinstance(case, dict):
        raise SnapshotValidationError("case must be an object")
    _require_nonempty_string(case.get("local_draft"), "local_draft")
    audit_input = case.get("audit_input")
    validate_audit_input(audit_input)
    return {
        "draft": case["local_draft"],
        "a_records": deepcopy(audit_input["a_records"]),
    }


def validate_audit_output(output) -> None:
    """Validate one auditor decision without interpreting or repairing it."""

    _require_exact_keys(output, AUDIT_OUTPUT_KEYS, "audit output")
    if output["verdict"] not in AUDIT_VERDICTS:
        raise SnapshotValidationError("audit verdict must be permit or reject")
    _require_nonempty_string(output["reason"], "audit reason")


def audit_output_schema() -> dict:
    """Return the shared native structured-output schema for both auditors."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdict", "reason"],
        "properties": {
            "verdict": {"type": "string", "enum": ["permit", "reject"]},
            "reason": {"type": "string", "minLength": 1},
        },
    }


def resolve_audit_route(output) -> str:
    """Map a valid audit decision to a route, never to a rewritten answer."""

    validate_audit_output(output)
    if output["verdict"] == "permit":
        return "accept_local_draft"
    return "request_local_revision"


def _fixture_memory(case):
    source_packet = case.get("source_packet") if isinstance(case, dict) else None
    payload = source_packet.get("payload") if isinstance(source_packet, dict) else None
    fixture_memory = payload.get("fixture_memory") if isinstance(payload, dict) else None
    if not isinstance(fixture_memory, list):
        raise SnapshotValidationError("source_packet fixture_memory must be a list")
    return fixture_memory


def risk_features(case) -> dict:
    """Compute the predeclared static C3 escalation features.

    No model verdict, historical reviewer result, preliminary score, expected
    label, or answer quality measurement is read here.
    """

    if not isinstance(case, dict):
        raise SnapshotValidationError("case must be an object")
    case_id = case.get("case_id")
    _require_nonempty_string(case_id, "case_id")
    audit_input = case.get("audit_input")
    validate_audit_input(audit_input)
    records = audit_input["a_records"]

    any_failed_a = any(not record["success"] for record in records)
    has_excluded_r = bool(_fixture_memory(case))
    multi_a = len(records) > 1
    total_a_characters = sum(len(record["content"]) for record in records)
    large_a = total_a_characters >= 500
    risk_score = (
        4 * int(any_failed_a)
        + 3 * int(has_excluded_r)
        + 2 * int(multi_a)
        + int(large_a)
    )
    tie_breaker = hashlib.sha256(
        ("hybrid-audit-v1|" + case_id).encode("utf-8")
    ).hexdigest()
    return {
        "any_failed_a": any_failed_a,
        "has_excluded_r": has_excluded_r,
        "multi_a": multi_a,
        "total_a_characters": total_a_characters,
        "large_a": large_a,
        "risk_score": risk_score,
        "tie_breaker": tie_breaker,
    }


def select_escalation_case_ids(cases, count: int = 8) -> list[str]:
    """Select the static C3 cloud-audit subset without reading any outcomes."""

    if not isinstance(cases, list) or not cases:
        raise SnapshotValidationError("cases must be a nonempty list")
    if type(count) is not int or count < 1 or count > len(cases):
        raise SnapshotValidationError("escalation count is out of range")

    ranked = []
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise SnapshotValidationError("case must be an object")
        case_id = case.get("case_id")
        _require_nonempty_string(case_id, "case_id")
        if case_id in seen:
            raise SnapshotValidationError("case_id must be unique")
        seen.add(case_id)
        features = risk_features(case)
        ranked.append((case_id, features))

    ranked.sort(key=lambda item: (-item[1]["risk_score"], item[1]["tie_breaker"]))
    return [case_id for case_id, _ in ranked[:count]]


def _validate_file_reference(value, label):
    _require_exact_keys(value, {"path", "sha256"}, label)
    _require_nonempty_string(value["path"], f"{label} path")
    _require_sha256(value["sha256"], f"{label} sha256")


def _validate_source_packet(value, label):
    _require_exact_keys(value, {"packet_sha256", "payload"}, label)
    _require_sha256(value["packet_sha256"], f"{label} packet_sha256")
    payload = value["payload"]
    _require_exact_keys(
        payload,
        {"active_goal", "fixture_memory", "tool_results"},
        f"{label} payload",
    )
    _require_nonempty_string(payload["active_goal"], f"{label} active_goal")
    if not isinstance(payload["fixture_memory"], list):
        raise SnapshotValidationError(f"{label} fixture_memory must be a list")
    if not isinstance(payload["tool_results"], list) or not payload["tool_results"]:
        raise SnapshotValidationError(f"{label} tool_results must be nonempty")


def _validate_historical_reference(value, label):
    _require_exact_keys(
        value,
        {"local_evidence_reviewer", "blind_preliminary_score"},
        label,
    )
    reviewer = value["local_evidence_reviewer"]
    _require_exact_keys(reviewer, {"reviewer_id", "status", "output"}, "reviewer")
    if reviewer["reviewer_id"] != "evidence-reviewer" or reviewer["status"] != "valid":
        raise SnapshotValidationError("historical reviewer identity/status mismatch")
    output = reviewer["output"]
    _require_exact_keys(
        output,
        {"verdict", "reason", "revised_answer"},
        "historical reviewer output",
    )
    if output["verdict"] not in AUDIT_VERDICTS:
        raise SnapshotValidationError("historical reviewer verdict is invalid")
    _require_nonempty_string(output["reason"], "historical reviewer reason")
    _require_nonempty_string(
        output["revised_answer"],
        "historical reviewer revised_answer",
    )

    score = value["blind_preliminary_score"]
    _require_exact_keys(score, {"scorer_type", "item"}, "preliminary score")
    if score["scorer_type"] != "blind_ai_preliminary":
        raise SnapshotValidationError("preliminary scorer type mismatch")
    item = score["item"]
    if not isinstance(item, dict):
        raise SnapshotValidationError("preliminary score item must be an object")
    _require_nonempty_string(item.get("blind_id"), "preliminary blind_id")
    if type(item.get("no_unsupported_claims")) is not int or item[
        "no_unsupported_claims"
    ] not in {0, 1}:
        raise SnapshotValidationError(
            "preliminary no_unsupported_claims must be integer 0 or 1"
        )


def _snapshot_id(document_without_id) -> str:
    digest = hashlib.sha256(
        canonical_json(document_without_id).encode("utf-8")
    ).hexdigest()
    return "hybrid-audit-source-" + digest


def add_snapshot_id(document_without_id) -> dict:
    """Return a copy with its content-derived snapshot identity attached."""

    if not isinstance(document_without_id, dict) or "snapshot_id" in document_without_id:
        raise SnapshotValidationError("snapshot body must omit snapshot_id")
    result = deepcopy(document_without_id)
    result["snapshot_id"] = _snapshot_id(document_without_id)
    return result


def validate_source_snapshot(snapshot) -> None:
    """Validate the complete 30-case source snapshot and separation boundaries."""

    _require_exact_keys(
        snapshot,
        {
            "schema_version",
            "snapshot_id",
            "selection",
            "source_provenance",
            "cases",
        },
        "source snapshot",
    )
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1:
        raise SnapshotValidationError("snapshot schema_version must be integer 1")

    body = {key: value for key, value in snapshot.items() if key != "snapshot_id"}
    if snapshot["snapshot_id"] != _snapshot_id(body):
        raise SnapshotValidationError("snapshot_id does not match snapshot content")

    selection = snapshot["selection"]
    _require_exact_keys(
        selection,
        {
            "seed",
            "answer_condition",
            "historical_reviewer",
            "score_source",
            "case_count",
        },
        "selection",
    )
    if selection != {
        "seed": 42,
        "answer_condition": "ar-consumer-rule",
        "historical_reviewer": "evidence-reviewer",
        "score_source": "blind_ai_preliminary",
        "case_count": SNAPSHOT_CASE_COUNT,
    }:
        raise SnapshotValidationError("selection contract mismatch")

    provenance = snapshot["source_provenance"]
    _require_exact_keys(
        provenance,
        {"evidence_packets", "blind_key", "score_lock", "score_files"},
        "source_provenance",
    )
    for name in ("evidence_packets", "blind_key", "score_lock"):
        _validate_file_reference(provenance[name], name)
    if not isinstance(provenance["score_files"], list) or not provenance["score_files"]:
        raise SnapshotValidationError("source_provenance score_files must be nonempty")
    for index, reference in enumerate(provenance["score_files"], 1):
        _validate_file_reference(reference, f"score file {index}")

    cases = snapshot["cases"]
    if not isinstance(cases, list) or len(cases) != SNAPSHOT_CASE_COUNT:
        raise SnapshotValidationError(
            f"source snapshot must contain exactly {SNAPSHOT_CASE_COUNT} cases"
        )
    case_ids = set()
    artifact_paths = set()
    provenance_ids = set()
    for index, case in enumerate(cases, 1):
        _require_exact_keys(
            case,
            {
                "case_id",
                "source_artifact",
                "source_packet",
                "local_draft",
                "audit_input",
                "expected_audit_verdict",
                "historical_reference",
            },
            f"case {index}",
        )
        case_id = case["case_id"]
        _require_nonempty_string(case_id, f"case {index} id")
        if case_id in case_ids:
            raise SnapshotValidationError("case_id must be unique")
        case_ids.add(case_id)

        _validate_file_reference(case["source_artifact"], "source_artifact")
        artifact_path = case["source_artifact"]["path"]
        if artifact_path in artifact_paths:
            raise SnapshotValidationError("source artifact path must be unique")
        artifact_paths.add(artifact_path)

        _validate_source_packet(case["source_packet"], "source_packet")
        packet = {
            "case_id": case_id,
            "payload": case["source_packet"]["payload"],
        }
        packet_sha256 = hashlib.sha256(
            canonical_json(packet).encode("utf-8")
        ).hexdigest()
        if packet_sha256 != case["source_packet"]["packet_sha256"]:
            raise SnapshotValidationError("source packet hash mismatch")

        _require_nonempty_string(case["local_draft"], "local_draft")
        validate_audit_input(case["audit_input"])
        source_records = case["source_packet"]["payload"]["tool_results"]
        audit_records = case["audit_input"]["a_records"]
        if len(source_records) != len(audit_records):
            raise SnapshotValidationError("audit_input must include every source A record")
        for ordinal, (source_record, audit_record) in enumerate(
            zip(source_records, audit_records),
            1,
        ):
            expected_provenance = deterministic_a_provenance_id(
                case_id,
                case["source_packet"]["packet_sha256"],
                ordinal,
            )
            if audit_record["provenance_id"] != expected_provenance:
                raise SnapshotValidationError("A record provenance_id mismatch")
            if expected_provenance in provenance_ids:
                raise SnapshotValidationError("A record provenance_id must be globally unique")
            provenance_ids.add(expected_provenance)
            without_id = {
                key: value
                for key, value in audit_record.items()
                if key != "provenance_id"
            }
            if canonical_json(source_record) != canonical_json(without_id):
                raise SnapshotValidationError(
                    "audit_input A record differs from source tool result"
                )

        if case["expected_audit_verdict"] not in AUDIT_VERDICTS:
            raise SnapshotValidationError("expected audit verdict is invalid")
        _validate_historical_reference(
            case["historical_reference"],
            "historical_reference",
        )
        score_item = case["historical_reference"]["blind_preliminary_score"][
            "item"
        ]
        expected_from_score = (
            "permit" if score_item["no_unsupported_claims"] == 1 else "reject"
        )
        if case["expected_audit_verdict"] != expected_from_score:
            raise SnapshotValidationError(
                "expected audit verdict does not match preliminary score"
            )
