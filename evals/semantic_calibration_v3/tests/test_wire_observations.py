from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schemas import (
    canonical_json,
    decode_wire_observation,
    encode_wire_observation,
    parse_error_stage,
    parse_response,
    response_schema,
)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        1,
        1.0,
        "둘",
        "null",
        "[1,2]",
        [1, 2, False, None],
        {"outer": {"items": [1, "둘", False], "n": 3}},
    ],
)
def test_typed_return_values_round_trip_through_wire_once(value):
    typed = {"kind": "return", "value": value, "exception": None}
    wire = encode_wire_observation(typed, allow_unknown=False)
    decoded, error = decode_wire_observation(wire, allow_unknown=False)
    assert error is None
    assert canonical_json(decoded) == canonical_json(typed)


def test_json_looking_string_is_decoded_exactly_once():
    typed = {"kind": "return", "value": "null", "exception": None}
    wire = encode_wire_observation(typed, allow_unknown=False)
    assert wire["value_json"] == '"null"'
    decoded, error = decode_wire_observation(wire, allow_unknown=False)
    assert error is None
    assert decoded["value"] == "null"
    assert decoded["value"] is not None


def test_bool_int_and_float_remain_distinct_after_round_trip():
    encoded = [
        encode_wire_observation(
            {"kind": "return", "value": value, "exception": None},
            allow_unknown=False,
        )
        for value in (True, 1, 1.0)
    ]
    assert [item["value_json"] for item in encoded] == ["true", "1", "1.0"]
    decoded = [
        decode_wire_observation(item, allow_unknown=False)[0]["value"]
        for item in encoded
    ]
    assert type(decoded[0]) is bool
    assert type(decoded[1]) is int
    assert type(decoded[2]) is float


@pytest.mark.parametrize(
    ("value_json", "expected_error"),
    [
        ("", "value_json_not_strict_json"),
        (" ", "value_json_not_strict_json"),
        ("{", "value_json_not_strict_json"),
        ('{"a":1,"a":2}', "value_json_not_strict_json"),
        ("NaN", "value_json_not_strict_json"),
        ("Infinity", "value_json_not_strict_json"),
        ("-Infinity", "value_json_not_strict_json"),
        ("1 trailing", "value_json_not_strict_json"),
        ("1e999", "value_json_not_strict_json"),
    ],
)
def test_invalid_inner_json_is_rejected_without_repair(value_json, expected_error):
    wire = {"kind": "return", "value_json": value_json, "exception": None}
    assert decode_wire_observation(wire, allow_unknown=False)[1] == expected_error


def test_deep_inner_json_is_a_parse_failure_not_a_crash():
    value_json = "[" * 2_000 + "0" + "]" * 2_000
    wire = {"kind": "return", "value_json": value_json, "exception": None}
    assert (
        decode_wire_observation(wire, allow_unknown=False)[1]
        == "value_json_not_strict_json"
    )


@pytest.mark.parametrize(
    "value_json",
    [
        r'"\ud800"',
        r'"\udc00"',
        r'{"\ud800":"bad key"}',
        r'{"nested":["\udc00"]}',
    ],
)
def test_unpaired_surrogates_in_inner_json_are_rejected(value_json):
    wire = {"kind": "return", "value_json": value_json, "exception": None}
    assert (
        decode_wire_observation(wire, allow_unknown=False)[1]
        == "value_json_not_strict_json"
    )


@pytest.mark.parametrize("value_json", [r'"\ud83d\ude00"', '"😀"'])
def test_paired_surrogate_and_real_non_bmp_character_are_allowed(value_json):
    wire = {"kind": "return", "value_json": value_json, "exception": None}
    decoded, error = decode_wire_observation(wire, allow_unknown=False)
    assert error is None
    assert decoded["value"] == "😀"


def test_unpaired_surrogate_in_outer_reason_is_a_parse_failure_not_score_crash():
    answer = (
        '{"claims":[{"id":"X","verdict":"SUPPORTED",'
        '"observation":{"kind":"return","value_json":"1",'
        '"exception":null},"reason":"\\ud800"}]}'
    )
    assert parse_response(answer, ["X"], allow_unknown=False)[1] == (
        "answer_is_not_strict_json"
    )


@pytest.mark.parametrize(
    "wire",
    [
        {"kind": "return", "value": 1, "exception": None},
        {"kind": "return", "value_json": "1", "exception": None, "extra": 1},
        {"kind": "return", "value_json": 1, "exception": None},
        {"kind": [], "value_json": "1", "exception": None},
    ],
)
def test_old_extra_and_non_string_wire_shapes_are_rejected(wire):
    _, error = decode_wire_observation(wire, allow_unknown=False)
    assert error in {
        "wire_observation_schema_mismatch",
        "value_json_not_string",
        "wire_observation_kind_invalid",
    }


@pytest.mark.parametrize("value_json", [" null ", "NULL", '"null"', "0"])
def test_raise_requires_exact_four_character_null(value_json):
    wire = {
        "kind": "raise",
        "value_json": value_json,
        "exception": "ValueError",
    }
    assert (
        decode_wire_observation(wire, allow_unknown=False)[1]
        == "raise_value_json_must_be_null"
    )


def test_raise_and_unknown_rules_are_normalized_and_enforced():
    raised = {
        "kind": "raise",
        "value_json": "null",
        "exception": "ValueError",
    }
    assert decode_wire_observation(raised, allow_unknown=False) == (
        {"kind": "raise", "value": None, "exception": "ValueError"},
        None,
    )
    bad_exception = {**raised, "exception": "not valid"}
    assert (
        decode_wire_observation(bad_exception, allow_unknown=False)[1]
        == "raise_exception_invalid"
    )

    unknown = {"kind": "unknown", "value_json": "null", "exception": None}
    assert decode_wire_observation(unknown, allow_unknown=True) == (
        {"kind": "unknown", "value": None, "exception": None},
        None,
    )
    assert (
        decode_wire_observation(unknown, allow_unknown=False)[1]
        == "observation_kind_invalid"
    )
    bad_unknown = {**unknown, "value_json": " null "}
    assert (
        decode_wire_observation(bad_unknown, allow_unknown=True)[1]
        == "unknown_value_json_must_be_null"
    )


def test_return_requires_null_exception():
    wire = {
        "kind": "return",
        "value_json": "1",
        "exception": "ValueError",
    }
    assert (
        decode_wire_observation(wire, allow_unknown=False)[1]
        == "return_exception_must_be_null"
    )


def test_parse_response_returns_typed_observation_and_classifies_boundaries():
    answer = json.dumps(
        {
            "claims": [
                {
                    "id": "X",
                    "verdict": "SUPPORTED",
                    "observation": {
                        "kind": "return",
                        "value_json": "[1,2]",
                        "exception": None,
                    },
                    "reason": "wire round trip",
                }
            ]
        }
    )
    parsed, error = parse_response(answer, ["X"], allow_unknown=False)
    assert error is None
    assert parsed["X"]["observation"] == {
        "kind": "return",
        "value": [1, 2],
        "exception": None,
    }

    malformed = answer.replace('"[1,2]"', '"[1,2] trailing"')
    assert parse_response(malformed, ["X"], allow_unknown=False)[1] == (
        "value_json_not_strict_json"
    )
    assert parse_error_stage("answer_is_not_strict_json") == "outer_json_or_schema"
    assert parse_error_stage("value_json_not_strict_json") == "inner_json_decode"
    assert parse_error_stage("return_exception_must_be_null") == (
        "normalized_observation"
    )


def test_provider_schema_has_fixed_wire_keys_and_no_unconstrained_value_schema():
    schema = response_schema(["X"], allow_unknown=True)
    variants = schema["properties"]["claims"]["items"]["properties"][
        "observation"
    ]["oneOf"]
    assert len(variants) == 3
    for variant in variants:
        assert variant["required"] == ["kind", "value_json", "exception"]
        assert set(variant["properties"]) == {"kind", "value_json", "exception"}
        assert variant["additionalProperties"] is False
    assert variants[0]["properties"]["value_json"] == {
        "type": "string",
        "minLength": 1,
    }
    assert variants[1]["properties"]["value_json"] == {"const": "null"}
    assert variants[2]["properties"]["value_json"] == {"const": "null"}
