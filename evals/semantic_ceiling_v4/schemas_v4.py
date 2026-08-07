"""Strict JSON and native structured-output contracts for semantic ceiling v4."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Iterable


CLAIM_KEYS = {"id", "verdict", "observation", "reason"}
OBSERVATION_KEYS = {"kind", "value", "exception"}
WIRE_OBSERVATION_KEYS = {"kind", "value_json", "exception"}
EXCEPTION_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def canonical_json(value) -> str:
    """Return the single canonical JSON representation used for hashes/equality."""

    serialized = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    # json.dumps can preserve lone surrogates in a str. They are not valid UTF-8
    # artifacts, so reject them at the common serialization boundary.
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
    """Decode exactly one RFC-8259-compatible value without key repair."""

    if not isinstance(text, str):
        raise TypeError("JSON input must be text")
    value = json.loads(
        text,
        parse_constant=_reject_non_json_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
    # This catches overflow such as 1e999 and lone Unicode surrogates after
    # decoding, in addition to proving that the decoded value is JSON-safe.
    canonical_json(value)
    return value


def load_strict_json(path):
    return strict_json_loads(Path(path).read_text(encoding="utf-8"))


def validate_observation(value, *, allow_unknown: bool = False) -> str | None:
    if not isinstance(value, dict) or set(value) != OBSERVATION_KEYS:
        return "observation_schema_mismatch"

    kind = value["kind"]
    if kind == "return":
        if value["exception"] is not None:
            return "return_exception_must_be_null"
        try:
            canonical_json(value["value"])
        except (TypeError, ValueError, UnicodeError, RecursionError):
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


def encode_wire_observation(value, *, allow_unknown: bool = False):
    error = validate_observation(value, allow_unknown=allow_unknown)
    if error:
        raise ValueError(f"invalid typed observation: {error}")
    return {
        "kind": value["kind"],
        "value_json": canonical_json(value["value"]),
        "exception": value["exception"],
    }


def decode_wire_observation(value, *, allow_unknown: bool = False):
    """Decode value_json once and return the typed observation plus an error."""

    if not isinstance(value, dict) or set(value) != WIRE_OBSERVATION_KEYS:
        return None, "wire_observation_schema_mismatch"

    kind = value["kind"]
    if not isinstance(kind, str):
        return None, "wire_observation_kind_invalid"
    value_json = value["value_json"]
    if not isinstance(value_json, str):
        return None, "value_json_not_string"
    if kind in {"raise", "unknown"} and value_json != "null":
        return None, f"{kind}_value_json_must_be_null"

    try:
        decoded = strict_json_loads(value_json)
    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
        UnicodeError,
        RecursionError,
    ):
        return None, "value_json_not_strict_json"

    typed = {
        "kind": kind,
        "value": decoded,
        "exception": value["exception"],
    }
    error = validate_observation(typed, allow_unknown=allow_unknown)
    if error:
        return None, error
    return typed, None


def _normalize_ids(ids: Iterable[str]) -> tuple[str, ...]:
    if isinstance(ids, (str, bytes)):
        raise ValueError("expected ids must be an iterable of distinct strings")
    normalized = tuple(ids)
    if not normalized or any(not isinstance(item, str) or not item for item in normalized):
        raise ValueError("expected ids must be nonempty strings")
    if len(set(normalized)) != len(normalized):
        raise ValueError("expected ids must be unique")
    return normalized


def parse_response(
    text,
    expected_ids,
    *,
    allowed_verdicts=("SUPPORTED", "UNSUPPORTED"),
    allow_unknown: bool = False,
):
    """Parse a model response without repairing either JSON layer."""

    try:
        ids = _normalize_ids(expected_ids)
        document = strict_json_loads(text)
    except (
        AttributeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        UnicodeError,
        RecursionError,
    ):
        return None, "answer_is_not_strict_json"

    if not isinstance(document, dict) or set(document) != {"claims"}:
        return None, "top_level_schema_mismatch"
    claims = document["claims"]
    if not isinstance(claims, list) or len(claims) != len(ids):
        return None, "claim_count_mismatch"

    expected = set(ids)
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

        observation, error = decode_wire_observation(
            claim["observation"],
            allow_unknown=allow_unknown,
        )
        if error:
            return None, error
        normalized = dict(claim)
        normalized["observation"] = observation
        by_id[claim_id] = normalized

    return by_id, None


def _observation_schema(*, allow_unknown: bool):
    variants = [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "value_json", "exception"],
            "properties": {
                "kind": {"type": "string", "enum": ["return"]},
                "value_json": {"type": "string", "minLength": 1},
                "exception": {"type": "null"},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "value_json", "exception"],
            "properties": {
                "kind": {"type": "string", "enum": ["raise"]},
                "value_json": {"type": "string", "enum": ["null"]},
                "exception": {
                    "type": "string",
                    "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
                },
            },
        },
    ]
    if allow_unknown:
        variants.append(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "value_json", "exception"],
                "properties": {
                    "kind": {"type": "string", "enum": ["unknown"]},
                    "value_json": {"type": "string", "enum": ["null"]},
                    "exception": {"type": "null"},
                },
            }
        )
    return {"anyOf": variants}


def response_schema(ids, *, allow_unknown: bool = False):
    """Return a Sol-native schema: object root and only nested ``anyOf``."""

    normalized_ids = _normalize_ids(ids)
    verdicts = ["SUPPORTED", "UNSUPPORTED"]
    if allow_unknown:
        verdicts.append("INSUFFICIENT")

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["claims"],
        "properties": {
            "claims": {
                "type": "array",
                "minItems": len(normalized_ids),
                "maxItems": len(normalized_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "verdict", "observation", "reason"],
                    "properties": {
                        "id": {"type": "string", "enum": list(normalized_ids)},
                        "verdict": {"type": "string", "enum": verdicts},
                        "observation": _observation_schema(
                            allow_unknown=allow_unknown
                        ),
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
            }
        },
    }
