"""Single source of truth for the v3 typed response contract."""

from __future__ import annotations

import json
import re


CLAIM_KEYS = {"id", "verdict", "observation", "reason"}
OBSERVATION_KEYS = {"kind", "value", "exception"}
EXCEPTION_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def canonical_json(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


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
    return json.loads(
        text,
        parse_constant=_reject_non_json_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )


def load_strict_json(path):
    return strict_json_loads(path.read_text(encoding="utf-8"))


def validate_observation(value, *, allow_unknown: bool) -> str | None:
    if not isinstance(value, dict) or set(value) != OBSERVATION_KEYS:
        return "observation_schema_mismatch"
    kind = value["kind"]
    if kind == "return":
        if value["exception"] is not None:
            return "return_exception_must_be_null"
        try:
            canonical_json(value["value"])
        except (TypeError, ValueError):
            return "return_value_not_json"
        return None
    if kind == "raise":
        if value["value"] is not None:
            return "raise_value_must_be_null"
        exception = value["exception"]
        if not isinstance(exception, str) or not EXCEPTION_NAME.fullmatch(exception):
            return "raise_exception_invalid"
        return None
    if kind == "unknown" and allow_unknown:
        if value["value"] is not None or value["exception"] is not None:
            return "unknown_payload_must_be_null"
        return None
    return "observation_kind_invalid"


def parse_response(
    text,
    expected_ids,
    *,
    allowed_verdicts=("SUPPORTED", "UNSUPPORTED"),
    allow_unknown=False,
):
    try:
        document = strict_json_loads(text.strip())
    except (AttributeError, json.JSONDecodeError, ValueError):
        return None, "answer_is_not_strict_json"
    if not isinstance(document, dict) or set(document) != {"claims"}:
        return None, "top_level_schema_mismatch"
    claims = document["claims"]
    if not isinstance(claims, list) or len(claims) != len(expected_ids):
        return None, "claim_count_mismatch"
    expected = set(expected_ids)
    by_id = {}
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS:
            return None, "claim_schema_mismatch"
        claim_id = claim["id"]
        if (
            not isinstance(claim_id, str)
            or claim_id not in expected
            or claim_id in by_id
        ):
            return None, "claim_identity_mismatch"
        if claim["verdict"] not in allowed_verdicts:
            return None, "verdict_invalid"
        if not isinstance(claim["reason"], str) or not claim["reason"].strip():
            return None, "reason_invalid"
        error = validate_observation(
            claim["observation"],
            allow_unknown=allow_unknown,
        )
        if error:
            return None, error
        by_id[claim_id] = claim
    return by_id, None


def response_schema(ids, *, allow_unknown: bool):
    verdicts = ["SUPPORTED", "UNSUPPORTED"]
    if allow_unknown:
        verdicts.append("INSUFFICIENT")
    observation_variants = [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "value", "exception"],
            "properties": {
                "kind": {"const": "return"},
                "value": {},
                "exception": {"type": "null"},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "value", "exception"],
            "properties": {
                "kind": {"const": "raise"},
                "value": {"type": "null"},
                "exception": {
                    "type": "string",
                    "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
                },
            },
        },
    ]
    if allow_unknown:
        observation_variants.append(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "value", "exception"],
                "properties": {
                    "kind": {"const": "unknown"},
                    "value": {"type": "null"},
                    "exception": {"type": "null"},
                },
            }
        )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["claims"],
        "properties": {
            "claims": {
                "type": "array",
                "minItems": len(ids),
                "maxItems": len(ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "verdict", "observation", "reason"],
                    "properties": {
                        "id": {"type": "string", "enum": list(ids)},
                        "verdict": {"type": "string", "enum": verdicts},
                        "observation": {"oneOf": observation_variants},
                        "reason": {"type": "string", "minLength": 1, "pattern": "\\S"},
                    },
                },
            }
        },
    }
