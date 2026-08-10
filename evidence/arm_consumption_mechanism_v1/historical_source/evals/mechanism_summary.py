"""ARM consumption mechanism capture의 맹검 점수와 운영 지표를 집계한다.

이 모듈은 답변을 채점하지 않는다. 이미 잠긴 score row를 blind key로
unblind하고, capture에서는 호출 상태와 metrics 및 reviewer verdict만 읽는다.
prompt, raw_response, thinking, answer, reason, revised_answer의 본문은 분석에
사용하지 않는다.

seed 세 개는 독립 표본이 아니다. 모든 paired inference는 seed를 case 안에서
먼저 평균낸 뒤 case를 cluster로 삼는 exact sign-flip 검정을 사용한다.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from .mechanism_capture import (
    ANSWER_CONDITIONS,
    AR_CONSUMER_RULE,
    EVIDENCE_REVIEWER,
    EXPERIMENT_ID,
    REVIEWERS,
    STYLE_PLACEBO_REVIEWER,
)
from .mechanism_packets import DEFAULT_SOURCE_MANIFEST_PATH


SCHEMA_VERSION = 1
SUMMARY_ID = "songryeon-arm-consumption-mechanism-summary-v1"

STYLE_PLACEBO_ENFORCED = "style-placebo-enforced"
EVIDENCE_ENFORCED = "evidence-enforced"
SCORE_CONDITIONS = (
    *ANSWER_CONDITIONS,
    STYLE_PLACEBO_ENFORCED,
    EVIDENCE_ENFORCED,
)

_ENFORCED_REVIEWER = {
    STYLE_PLACEBO_ENFORCED: STYLE_PLACEBO_REVIEWER,
    EVIDENCE_ENFORCED: EVIDENCE_REVIEWER,
}

_CONDITION_ALIASES = {
    "shadow": AR_CONSUMER_RULE,
    "consumer-shadow": AR_CONSUMER_RULE,
    "ar_consumer_rule": AR_CONSUMER_RULE,
    "style_placebo_enforced": STYLE_PLACEBO_ENFORCED,
    "style-placebo-reviewer-enforced": STYLE_PLACEBO_ENFORCED,
    "style_placebo_reviewer_enforced": STYLE_PLACEBO_ENFORCED,
    "evidence_enforced": EVIDENCE_ENFORCED,
    "evidence-reviewer-enforced": EVIDENCE_ENFORCED,
    "evidence_reviewer_enforced": EVIDENCE_ENFORCED,
}

_FAMILY_TAGS = {
    "declaration_enforcement",
    "import_invocation",
    "documentation_runtime",
    "action_report",
    "attribution_provenance",
}
_POLARITY_TAGS = {"negative_control", "positive_control"}

_SCORE_KEYS = {
    "blind_id",
    "direct_answer",
    "answer_complete",
    "no_unsupported_claims",
    "unsupported_atomic_claim_count",
    "evidence_laundering",
    "negative_correction",
    "positive_recognized",
    "semantic_grounded_success",
    "notes",
}
_COMMON_BINARY_FIELDS = (
    "direct_answer",
    "answer_complete",
    "no_unsupported_claims",
    "semantic_grounded_success",
)

_PRIMARY_CONTRASTS = (
    ("ar-label-only_minus_opaque-label", "ar-label-only", "opaque-label"),
    (
        "ar-consumer-rule_minus_ar-label-placebo",
        "ar-consumer-rule",
        "ar-label-placebo",
    ),
    (
        "evidence-enforced_minus_style-placebo-enforced",
        EVIDENCE_ENFORCED,
        STYLE_PLACEBO_ENFORCED,
    ),
)

_FORBIDDEN_CONTENT_KEYS = {
    "answer",
    "raw_response",
    "thinking",
    "system_prompt",
    "user_prompt",
    "revised_answer",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    resolved = Path(path).resolve(strict=True)
    _require(resolved.is_file(), f"{label}은 파일이어야 합니다: {resolved}")
    payload = resolved.read_bytes()
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}은 유효한 UTF-8 JSON 객체여야 합니다: {resolved}") from error
    _require(isinstance(value, dict), f"{label} 최상위 값은 객체여야 합니다.")
    return value, payload


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> Path:
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, target)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return target


def _normalise_condition(value: Any) -> str:
    _require(isinstance(value, str) and value.strip(), "blind key condition이 비어 있습니다.")
    condition = value.strip()
    condition = _CONDITION_ALIASES.get(condition, condition)
    _require(condition in SCORE_CONDITIONS, f"알 수 없는 score condition입니다: {value}")
    return condition


def _load_case_metadata(manifest_path: Path) -> dict[str, dict[str, str]]:
    manifest, _ = _read_json_object(manifest_path, "source manifest")
    cases = manifest.get("cases")
    _require(isinstance(cases, list) and cases, "source manifest cases가 없습니다.")
    result: dict[str, dict[str, str]] = {}
    for case in cases:
        _require(isinstance(case, dict), "manifest case는 객체여야 합니다.")
        case_id = case.get("case_id")
        tags = case.get("tags")
        _require(isinstance(case_id, str) and case_id, "manifest case_id가 잘못됐습니다.")
        _require(case_id not in result, f"manifest case_id가 중복됐습니다: {case_id}")
        _require(
            isinstance(tags, list) and all(isinstance(tag, str) for tag in tags),
            f"manifest tags가 잘못됐습니다: {case_id}",
        )
        families = _FAMILY_TAGS.intersection(tags)
        polarities = _POLARITY_TAGS.intersection(tags)
        _require(len(families) == 1, f"family tag는 정확히 하나여야 합니다: {case_id}")
        _require(len(polarities) == 1, f"polarity tag는 정확히 하나여야 합니다: {case_id}")
        polarity_tag = next(iter(polarities))
        result[case_id] = {
            "family": next(iter(families)),
            "polarity": "negative" if polarity_tag == "negative_control" else "positive",
        }
    return result


def _resolve_artifact(capture_path: Path, relative_path: Any) -> Path:
    _require(isinstance(relative_path, str) and relative_path, "raw artifact path가 잘못됐습니다.")
    capture_root = capture_path.parent.resolve()
    candidate = (capture_root / Path(relative_path)).resolve(strict=True)
    try:
        candidate.relative_to(capture_root)
    except ValueError as error:
        raise ValueError("raw artifact가 capture root 밖을 가리킵니다.") from error
    _require(candidate.is_file(), f"raw artifact는 파일이어야 합니다: {candidate}")
    return candidate


def _load_capture_units(
    capture_path: Path,
) -> tuple[dict[str, Any], bytes, list[dict[str, Any]], dict[str, Any]]:
    capture, capture_bytes = _read_json_object(capture_path, "mechanism capture")
    configuration = capture.get("configuration")
    _require(isinstance(configuration, dict), "capture configuration이 없습니다.")
    _require(
        configuration.get("experiment_id") == EXPERIMENT_ID,
        "capture experiment_id가 다릅니다.",
    )
    _require(
        configuration.get("answer_conditions") == list(ANSWER_CONDITIONS),
        "capture answer conditions가 다릅니다.",
    )
    _require(configuration.get("reviewers") == list(REVIEWERS), "capture reviewers가 다릅니다.")

    artifacts = capture.get("raw_artifacts")
    _require(isinstance(artifacts, list), "capture raw_artifacts가 배열이 아닙니다.")
    units: list[dict[str, Any]] = []
    seen_units: set[tuple[str, int]] = set()
    artifact_hashes: list[dict[str, Any]] = []
    for artifact in artifacts:
        _require(isinstance(artifact, dict), "raw artifact entry는 객체여야 합니다.")
        path = _resolve_artifact(Path(capture_path).resolve(), artifact.get("path"))
        payload = path.read_bytes()
        digest = _sha256_bytes(payload)
        _require(artifact.get("sha256") == digest, f"raw artifact SHA-256이 다릅니다: {path}")
        _require(artifact.get("byte_count") == len(payload), f"raw artifact byte_count가 다릅니다: {path}")
        try:
            unit = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"raw artifact가 유효한 UTF-8 JSON이 아닙니다: {path}") from error
        _require(isinstance(unit, dict), f"raw artifact 최상위 값은 객체여야 합니다: {path}")
        case_id = unit.get("case_id")
        seed = unit.get("seed")
        _require(isinstance(case_id, str) and case_id, "raw unit case_id가 잘못됐습니다.")
        _require(type(seed) is int, f"raw unit seed가 잘못됐습니다: {case_id}")
        _require(artifact.get("case_id") == case_id, f"artifact case_id가 다릅니다: {path}")
        _require(artifact.get("seed") == seed, f"artifact seed가 다릅니다: {path}")
        unit_key = (case_id, seed)
        _require(unit_key not in seen_units, f"case/seed unit이 중복됐습니다: {unit_key}")
        seen_units.add(unit_key)
        units.append(unit)
        artifact_hashes.append(
            {
                "case_id": case_id,
                "seed": seed,
                "path": artifact["path"],
                "sha256": digest,
            }
        )

    return capture, capture_bytes, units, {"raw_artifacts": artifact_hashes}


def _attempt_metrics(call: Mapping[str, Any]) -> dict[str, Any]:
    attempts = call.get("attempts")
    _require(isinstance(attempts, list), "call attempts가 배열이 아닙니다.")
    latency_ms = 0.0
    latency_observed = False
    prompt_tokens = 0
    completion_tokens = 0
    token_observed = False
    for attempt in attempts:
        _require(isinstance(attempt, dict), "attempt는 객체여야 합니다.")
        metrics = attempt.get("metrics")
        if not isinstance(metrics, dict):
            continue
        if type(metrics.get("total_duration")) in (int, float):
            latency_ms += float(metrics["total_duration"]) / 1_000_000
            latency_observed = True
        elif type(metrics.get("latency_ms")) in (int, float):
            latency_ms += float(metrics["latency_ms"])
            latency_observed = True
        elif type(metrics.get("latency_seconds")) in (int, float):
            latency_ms += float(metrics["latency_seconds"]) * 1_000
            latency_observed = True

        prompt_value = metrics.get("prompt_eval_count", metrics.get("input_tokens"))
        completion_value = metrics.get("eval_count", metrics.get("output_tokens"))
        if type(prompt_value) is int and prompt_value >= 0:
            prompt_tokens += prompt_value
            token_observed = True
        if type(completion_value) is int and completion_value >= 0:
            completion_tokens += completion_value
            token_observed = True

    return {
        "attempt_count": len(attempts),
        "latency_ms": latency_ms if latency_observed else None,
        "prompt_tokens": prompt_tokens if token_observed else None,
        "completion_tokens": completion_tokens if token_observed else None,
        "total_tokens": prompt_tokens + completion_tokens if token_observed else None,
    }


def _combine_call_metrics(calls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    parts = [_attempt_metrics(call) for call in calls]

    def total_or_none(name: str) -> float | int | None:
        values = [part[name] for part in parts]
        observed = [value for value in values if value is not None]
        if not observed:
            return None
        return sum(observed)

    return {
        "attempt_count": sum(part["attempt_count"] for part in parts),
        "latency_ms": total_or_none("latency_ms"),
        "prompt_tokens": total_or_none("prompt_tokens"),
        "completion_tokens": total_or_none("completion_tokens"),
        "total_tokens": total_or_none("total_tokens"),
    }


def _call_status(call: Any, label: str) -> str:
    _require(isinstance(call, dict), f"{label} call이 없습니다.")
    status = call.get("status")
    _require(isinstance(status, str) and status, f"{label} status가 잘못됐습니다.")
    return status


def _unit_operational_rows(unit: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_id = unit["case_id"]
    seed = unit["seed"]
    answer_calls = unit.get("answer_calls")
    reviewer_calls = unit.get("reviewer_calls")
    _require(isinstance(answer_calls, dict), f"answer_calls가 없습니다: {case_id}/{seed}")
    _require(isinstance(reviewer_calls, dict), f"reviewer_calls가 없습니다: {case_id}/{seed}")
    rows: list[dict[str, Any]] = []

    for condition in ANSWER_CONDITIONS:
        call = answer_calls.get(condition)
        status = _call_status(call, f"{case_id}/{seed}/{condition}")
        rows.append(
            {
                "case_id": case_id,
                "seed": seed,
                "condition": condition,
                "status": status,
                "technical_success": status == "valid",
                **_combine_call_metrics([call]),
            }
        )

    consumer_call = answer_calls.get(AR_CONSUMER_RULE)
    consumer_status = _call_status(consumer_call, f"{case_id}/{seed}/{AR_CONSUMER_RULE}")
    reviewer_rows: list[dict[str, Any]] = []
    for condition, reviewer in _ENFORCED_REVIEWER.items():
        review_call = reviewer_calls.get(reviewer)
        review_status = _call_status(review_call, f"{case_id}/{seed}/{reviewer}")
        verdict = None
        output = review_call.get("output")
        if isinstance(output, dict):
            candidate = output.get("verdict")
            _require(candidate in {"permit", "reject"}, f"reviewer verdict가 잘못됐습니다: {case_id}/{seed}/{reviewer}")
            verdict = candidate
        elif review_status == "valid":
            raise ValueError(f"valid reviewer output이 없습니다: {case_id}/{seed}/{reviewer}")

        technical_success = consumer_status == "valid" and review_status == "valid"
        rows.append(
            {
                "case_id": case_id,
                "seed": seed,
                "condition": condition,
                "status": "valid" if technical_success else f"consumer={consumer_status};reviewer={review_status}",
                "technical_success": technical_success,
                **_combine_call_metrics([consumer_call, review_call]),
            }
        )
        reviewer_rows.append(
            {
                "case_id": case_id,
                "seed": seed,
                "reviewer": reviewer,
                "status": review_status,
                "verdict": verdict,
                **_combine_call_metrics([review_call]),
            }
        )
    return rows, reviewer_rows


def _numeric_summary(values: Iterable[float | int | None]) -> dict[str, Any]:
    observed = [float(value) for value in values if value is not None]
    if not observed:
        return {
            "observed_count": 0,
            "sum": None,
            "mean": None,
            "median": None,
            "p95": None,
            "min": None,
            "max": None,
        }
    ordered = sorted(observed)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "observed_count": len(observed),
        "sum": sum(observed),
        "mean": statistics.fmean(observed),
        "median": statistics.median(observed),
        "p95": ordered[p95_index],
        "min": ordered[0],
        "max": ordered[-1],
    }


def _operational_summary(units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    condition_rows: list[dict[str, Any]] = []
    reviewer_rows: list[dict[str, Any]] = []
    for unit in units:
        unit_conditions, unit_reviewers = _unit_operational_rows(unit)
        condition_rows.extend(unit_conditions)
        reviewer_rows.extend(unit_reviewers)

    by_condition: dict[str, Any] = {}
    for condition in SCORE_CONDITIONS:
        rows = [row for row in condition_rows if row["condition"] == condition]
        failures = sum(not row["technical_success"] for row in rows)
        by_condition[condition] = {
            "unit_count": len(rows),
            "technical_success_count": len(rows) - failures,
            "technical_failure_count": failures,
            "technical_failure_rate": failures / len(rows) if rows else None,
            "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
            "attempts": _numeric_summary(row["attempt_count"] for row in rows),
            "latency_ms": _numeric_summary(row["latency_ms"] for row in rows),
            "prompt_tokens": _numeric_summary(row["prompt_tokens"] for row in rows),
            "completion_tokens": _numeric_summary(row["completion_tokens"] for row in rows),
            "total_tokens": _numeric_summary(row["total_tokens"] for row in rows),
        }

    reviewer_summary: dict[str, Any] = {}
    for reviewer in REVIEWERS:
        rows = [row for row in reviewer_rows if row["reviewer"] == reviewer]
        reviewer_summary[reviewer] = {
            "call_count": len(rows),
            "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
            "verdict_counts": dict(
                sorted(Counter(row["verdict"] for row in rows if row["verdict"] is not None).items())
            ),
            "attempts": _numeric_summary(row["attempt_count"] for row in rows),
            "latency_ms": _numeric_summary(row["latency_ms"] for row in rows),
            "total_tokens": _numeric_summary(row["total_tokens"] for row in rows),
        }

    unique_call_statuses: Counter[str] = Counter()
    unique_attempts: list[int] = []
    unique_latency: list[float | int | None] = []
    unique_tokens: list[float | int | None] = []
    for unit in units:
        for collection_name, names in (
            ("answer_calls", ANSWER_CONDITIONS),
            ("reviewer_calls", REVIEWERS),
        ):
            calls = unit[collection_name]
            for name in names:
                call = calls[name]
                unique_call_statuses[_call_status(call, f"{unit['case_id']}/{unit['seed']}/{name}")] += 1
                metrics = _attempt_metrics(call)
                unique_attempts.append(metrics["attempt_count"])
                unique_latency.append(metrics["latency_ms"])
                unique_tokens.append(metrics["total_tokens"])

    return {
        "unit_count": len(units),
        "condition_output_count": len(condition_rows),
        "cost_basis": {
            "answer_condition": "해당 answer call만 포함",
            "enforced_condition": "공유 ar-consumer-rule draft call과 해당 reviewer call을 합산",
            "experiment_unique_calls": "공유 call을 한 번만 집계",
        },
        "by_condition": by_condition,
        "reviewers": reviewer_summary,
        "experiment_unique_calls": {
            "call_count": sum(unique_call_statuses.values()),
            "status_counts": dict(sorted(unique_call_statuses.items())),
            "attempts": _numeric_summary(unique_attempts),
            "latency_ms": _numeric_summary(unique_latency),
            "total_tokens": _numeric_summary(unique_tokens),
        },
    }


def _blind_entries(blind_key: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_entries: list[tuple[str, Mapping[str, Any]]] = []
    mapping = blind_key.get("mapping")
    if isinstance(mapping, dict):
        for blind_id, value in mapping.items():
            _require(isinstance(blind_id, str) and blind_id, "blind_id가 잘못됐습니다.")
            _require(isinstance(value, dict), f"blind mapping 값은 객체여야 합니다: {blind_id}")
            raw_entries.append((blind_id, value))
    else:
        items = blind_key.get("items")
        _require(isinstance(items, list), "blind key에는 mapping 또는 items가 필요합니다.")
        for item in items:
            _require(isinstance(item, dict), "blind key item은 객체여야 합니다.")
            blind_id = item.get("blind_id", item.get("review_id"))
            _require(isinstance(blind_id, str) and blind_id, "blind key item의 blind_id가 없습니다.")
            raw_entries.append((blind_id, item))

    aliases: dict[str, Any] = {}
    for key in ("condition_aliases", "system_aliases"):
        value = blind_key.get(key)
        if isinstance(value, dict):
            aliases.update(value)

    result: dict[str, dict[str, Any]] = {}
    for blind_id, item in raw_entries:
        _require(blind_id not in result, f"blind_id가 중복됐습니다: {blind_id}")
        case_id = item.get("case_id")
        seed = item.get("seed")
        raw_condition = item.get(
            "condition",
            item.get("output_condition", item.get("arm", item.get("system_name"))),
        )
        if isinstance(raw_condition, str) and raw_condition in aliases:
            raw_condition = aliases[raw_condition]
        _require(isinstance(case_id, str) and case_id, f"blind key case_id가 없습니다: {blind_id}")
        _require(type(seed) is int, f"blind key seed가 잘못됐습니다: {blind_id}")
        result[blind_id] = {
            "case_id": case_id,
            "seed": seed,
            "condition": _normalise_condition(raw_condition),
        }
    _require(result, "blind key가 비어 있습니다.")
    return result


def _expected_score_identities(units: Sequence[Mapping[str, Any]]) -> set[tuple[str, int, str]]:
    return {
        (unit["case_id"], unit["seed"], condition)
        for unit in units
        for condition in SCORE_CONDITIONS
    }


def _score_file_hash(lock: Mapping[str, Any], path: Path) -> str:
    hash_mapping = lock.get("score_file_sha256")
    if not isinstance(hash_mapping, dict):
        hash_mapping = lock.get("score_files", lock.get("files"))
    _require(isinstance(hash_mapping, dict), "score lock에 score_file_sha256 mapping이 없습니다.")
    candidates = (path.name, str(path), path.as_posix())
    expected = next((hash_mapping[key] for key in candidates if key in hash_mapping), None)
    _require(isinstance(expected, str), f"score lock에 파일이 없습니다: {path.name}")
    return expected


def _score_items(document: Mapping[str, Any], path: Path) -> list[dict[str, Any]]:
    items = document.get("items", document.get("scores"))
    _require(isinstance(items, list), f"score file items가 배열이 아닙니다: {path}")
    if "item_count" in document:
        _require(document["item_count"] == len(items), f"score item_count가 다릅니다: {path}")
    _require(all(isinstance(item, dict) for item in items), f"score item은 객체여야 합니다: {path}")
    return items


def _binary(value: Any, label: str) -> int:
    _require(type(value) is int and value in (0, 1), f"{label}은 0 또는 1이어야 합니다.")
    return value


def _nullable_binary(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _binary(value, label)


def _validate_score_row(
    row: Mapping[str, Any],
    identity: Mapping[str, Any],
    metadata: Mapping[str, str],
) -> dict[str, Any]:
    blind_id = row.get("blind_id")
    _require(set(row) == _SCORE_KEYS, f"score row 필드가 다릅니다: {blind_id}")
    direct = _binary(row["direct_answer"], f"{blind_id}.direct_answer")
    complete = _binary(row["answer_complete"], f"{blind_id}.answer_complete")
    no_unsupported = _binary(
        row["no_unsupported_claims"],
        f"{blind_id}.no_unsupported_claims",
    )
    unsupported_count = row["unsupported_atomic_claim_count"]
    _require(
        type(unsupported_count) is int and unsupported_count >= 0,
        f"{blind_id}.unsupported_atomic_claim_count가 잘못됐습니다.",
    )
    _require(
        no_unsupported == int(unsupported_count == 0),
        f"{blind_id}: no_unsupported_claims와 count가 모순됩니다.",
    )
    laundering = _nullable_binary(row["evidence_laundering"], f"{blind_id}.evidence_laundering")
    correction = _nullable_binary(row["negative_correction"], f"{blind_id}.negative_correction")
    recognized = _nullable_binary(row["positive_recognized"], f"{blind_id}.positive_recognized")
    semantic = _binary(
        row["semantic_grounded_success"],
        f"{blind_id}.semantic_grounded_success",
    )
    _require(isinstance(row["notes"], str), f"{blind_id}.notes는 문자열이어야 합니다.")

    if metadata["polarity"] == "negative":
        _require(laundering is not None and correction is not None, f"negative score가 비었습니다: {blind_id}")
        _require(recognized is None, f"negative score의 positive_recognized는 null이어야 합니다: {blind_id}")
        expected_semantic = int(
            direct == 1
            and complete == 1
            and no_unsupported == 1
            and laundering == 0
            and correction == 1
        )
    else:
        _require(laundering is None and correction is None, f"positive score의 negative 필드는 null이어야 합니다: {blind_id}")
        _require(recognized is not None, f"positive_recognized가 비었습니다: {blind_id}")
        expected_semantic = int(
            direct == 1
            and complete == 1
            and no_unsupported == 1
            and recognized == 1
        )
    _require(semantic == expected_semantic, f"semantic_grounded_success 산식이 다릅니다: {blind_id}")

    return {
        "blind_id": blind_id,
        **identity,
        **metadata,
        "direct_answer": direct,
        "answer_complete": complete,
        "no_unsupported_claims": no_unsupported,
        "unsupported_atomic_claim_count": unsupported_count,
        "evidence_laundering": laundering,
        "negative_correction": correction,
        "positive_recognized": recognized,
        "semantic_grounded_success": semantic,
    }


def _load_locked_scores(
    *,
    score_paths: Sequence[Path],
    score_lock_path: Path,
    blind_key_path: Path,
    units: Sequence[Mapping[str, Any]],
    case_metadata: Mapping[str, Mapping[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _require(score_paths, "score_paths가 비어 있습니다.")
    lock, lock_bytes = _read_json_object(score_lock_path, "score lock")
    scoring_status = lock.get("scoring_status")
    if scoring_status is not None:
        _require(scoring_status == "locked_before_unblinding", "score가 unblind 전에 잠기지 않았습니다.")
    blind_key, blind_bytes = _read_json_object(blind_key_path, "blind key")
    locked_blind_hash = lock.get("blind_key_sha256")
    if locked_blind_hash is not None:
        _require(locked_blind_hash == _sha256_bytes(blind_bytes), "blind key SHA-256이 lock과 다릅니다.")
    identities = _blind_entries(blind_key)
    expected = _expected_score_identities(units)
    actual_identities = {
        (item["case_id"], item["seed"], item["condition"])
        for item in identities.values()
    }
    _require(len(actual_identities) == len(identities), "blind key identity가 중복됐습니다.")
    _require(actual_identities == expected, "blind key가 capture의 6-condition grid와 다릅니다.")

    raw_rows: list[dict[str, Any]] = []
    file_hashes: list[dict[str, Any]] = []
    for raw_path in score_paths:
        path = Path(raw_path).resolve(strict=True)
        document, payload = _read_json_object(path, "score file")
        digest = _sha256_bytes(payload)
        _require(digest == _score_file_hash(lock, path), f"score file SHA-256이 lock과 다릅니다: {path.name}")
        raw_rows.extend(_score_items(document, path))
        file_hashes.append({"path": str(path), "sha256": digest})

    if "validated_item_count" in lock:
        _require(lock["validated_item_count"] == len(raw_rows), "lock validated_item_count가 다릅니다.")
    seen_blind_ids: set[str] = set()
    rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        blind_id = raw_row.get("blind_id")
        _require(isinstance(blind_id, str) and blind_id, "score blind_id가 없습니다.")
        _require(blind_id not in seen_blind_ids, f"score blind_id가 중복됐습니다: {blind_id}")
        seen_blind_ids.add(blind_id)
        identity = identities.get(blind_id)
        _require(identity is not None, f"blind key에 없는 score입니다: {blind_id}")
        metadata = case_metadata.get(identity["case_id"])
        _require(metadata is not None, f"manifest에 없는 case입니다: {identity['case_id']}")
        rows.append(_validate_score_row(raw_row, identity, metadata))
    _require(seen_blind_ids == set(identities), "score row가 blind key grid를 완전히 덮지 않습니다.")
    if "validated_unique_blind_id_count" in lock:
        _require(
            lock["validated_unique_blind_id_count"] == len(seen_blind_ids),
            "lock validated_unique_blind_id_count가 다릅니다.",
        )
    if "semantic_grounded_success_count_before_unblinding" in lock:
        _require(
            lock["semantic_grounded_success_count_before_unblinding"]
            == sum(row["semantic_grounded_success"] for row in rows),
            "lock semantic success count가 다릅니다.",
        )
    return rows, {
        "blind_key_path": str(Path(blind_key_path).resolve()),
        "blind_key_sha256": _sha256_bytes(blind_bytes),
        "score_lock_path": str(Path(score_lock_path).resolve()),
        "score_lock_sha256": _sha256_bytes(lock_bytes),
        "score_files": file_hashes,
    }


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _score_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"row_count": len(rows)}
    for field in _COMMON_BINARY_FIELDS:
        result[field] = _rate(sum(row[field] for row in rows), len(rows))
    result["unsupported_atomic_claim_count"] = {
        "total": sum(row["unsupported_atomic_claim_count"] for row in rows),
        "mean": (
            statistics.fmean(row["unsupported_atomic_claim_count"] for row in rows)
            if rows
            else None
        ),
    }
    negative = [row for row in rows if row["polarity"] == "negative"]
    positive = [row for row in rows if row["polarity"] == "positive"]
    result["evidence_laundering"] = _rate(
        sum(row["evidence_laundering"] for row in negative),
        len(negative),
    )
    result["negative_correction"] = _rate(
        sum(row["negative_correction"] for row in negative),
        len(negative),
    )
    result["positive_recognized"] = _rate(
        sum(row["positive_recognized"] for row in positive),
        len(positive),
    )
    return result


def _metrics_by_condition(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        condition: _score_metrics([row for row in rows if row["condition"] == condition])
        for condition in SCORE_CONDITIONS
    }


def _metrics_by_dimension(
    rows: Sequence[Mapping[str, Any]],
    dimension: str,
) -> dict[str, Any]:
    values = sorted({row[dimension] for row in rows}, key=str)
    return {
        str(value): _metrics_by_condition([row for row in rows if row[dimension] == value])
        for value in values
    }


def _pass_three(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    seeds_by_case: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        seeds_by_case[row["case_id"]].add(row["seed"])
    result: dict[str, Any] = {}
    for condition in SCORE_CONDITIONS:
        case_results: dict[str, Any] = {}
        for case_id in sorted(seeds_by_case):
            case_rows = [
                row
                for row in rows
                if row["case_id"] == case_id and row["condition"] == condition
            ]
            observed = {row["seed"] for row in case_rows}
            expected = seeds_by_case[case_id]
            _require(observed == expected, f"pass^3 seed grid가 불완전합니다: {case_id}/{condition}")
            failed = sorted(
                row["seed"]
                for row in case_rows
                if row["semantic_grounded_success"] != 1
            )
            case_results[case_id] = {
                "pass": not failed,
                "failed_seeds": failed,
            }
        passed = sum(item["pass"] for item in case_results.values())
        result[condition] = {
            "passed_case_count": passed,
            "case_count": len(case_results),
            "rate": passed / len(case_results) if case_results else None,
            "cases": case_results,
        }
    return {
        "definition": "case 안의 모든 captured seed에서 semantic_grounded_success=1",
        "by_condition": result,
    }


def _exact_sign_flip(differences: Sequence[Fraction]) -> dict[str, Any]:
    _require(differences, "sign-flip에는 case difference가 필요합니다.")
    denominator_lcm = 1
    for difference in differences:
        denominator_lcm = math.lcm(denominator_lcm, difference.denominator)
    integer_differences = [int(value * denominator_lcm) for value in differences]
    nonzero = [value for value in integer_differences if value != 0]
    observed_sum = abs(sum(integer_differences))
    distribution: Counter[int] = Counter({0: 1})
    for value in nonzero:
        next_distribution: Counter[int] = Counter()
        for current, count in distribution.items():
            next_distribution[current + value] += count
            next_distribution[current - value] += count
        distribution = next_distribution
    denominator = 2 ** len(nonzero)
    extreme = sum(count for value, count in distribution.items() if abs(value) >= observed_sum)
    return {
        "method": "two-sided exact case-cluster sign-flip",
        "cluster_count": len(differences),
        "nonzero_cluster_count": len(nonzero),
        "p_value": extreme / denominator,
        "extreme_assignment_count": extreme,
        "assignment_count": denominator,
    }


def _paired_contrast(
    rows: Sequence[Mapping[str, Any]],
    treatment: str,
    comparator: str,
    *,
    metric: str = "semantic_grounded_success",
    polarity: str | None = None,
) -> dict[str, Any]:
    selected_rows = [
        row
        for row in rows
        if polarity is None or row["polarity"] == polarity
    ]
    cases = sorted({row["case_id"] for row in selected_rows})
    _require(cases, f"paired contrast 대상 case가 없습니다: {metric}/{polarity}")
    differences: list[Fraction] = []
    case_differences: dict[str, float] = {}
    for case_id in cases:
        case_rows = [row for row in selected_rows if row["case_id"] == case_id]
        seeds = sorted({row["seed"] for row in case_rows})
        treatment_by_seed = {
            row["seed"]: row[metric]
            for row in case_rows
            if row["condition"] == treatment
        }
        comparator_by_seed = {
            row["seed"]: row[metric]
            for row in case_rows
            if row["condition"] == comparator
        }
        _require(
            set(treatment_by_seed) == set(seeds) == set(comparator_by_seed),
            f"paired contrast seed grid가 불완전합니다: {case_id}",
        )
        difference = Fraction(
            sum(treatment_by_seed.values()) - sum(comparator_by_seed.values()),
            len(seeds),
        )
        differences.append(difference)
        case_differences[case_id] = float(difference)

    mean_difference = sum(differences, Fraction(0, 1)) / len(differences)
    return {
        "treatment": treatment,
        "comparator": comparator,
        "metric": metric,
        "polarity": polarity or "all",
        "estimand": f"mean within-case difference in {metric} after averaging seeds",
        "mean_paired_difference": float(mean_difference),
        "positive_case_count": sum(value > 0 for value in differences),
        "negative_case_count": sum(value < 0 for value in differences),
        "tie_case_count": sum(value == 0 for value in differences),
        "case_differences": case_differences,
        "exact_sign_flip": _exact_sign_flip(differences),
    }


def _contrast_with_protocol_metrics(
    rows: Sequence[Mapping[str, Any]],
    treatment: str,
    comparator: str,
) -> dict[str, Any]:
    """대표 semantic contrast와 protocol의 polarity별 보조 지표를 함께 낸다."""

    result = _paired_contrast(rows, treatment, comparator)
    result["additional_case_cluster_metrics"] = {
        "negative_semantic_grounded_success": _paired_contrast(
            rows,
            treatment,
            comparator,
            polarity="negative",
        ),
        "negative_evidence_laundering": _paired_contrast(
            rows,
            treatment,
            comparator,
            metric="evidence_laundering",
            polarity="negative",
        ),
        "negative_correction": _paired_contrast(
            rows,
            treatment,
            comparator,
            metric="negative_correction",
            polarity="negative",
        ),
        "positive_semantic_grounded_success": _paired_contrast(
            rows,
            treatment,
            comparator,
            polarity="positive",
        ),
        "positive_recognized": _paired_contrast(
            rows,
            treatment,
            comparator,
            metric="positive_recognized",
            polarity="positive",
        ),
    }
    return result


def _transition_counts(
    rows: Sequence[Mapping[str, Any]],
    enforced_condition: str,
) -> dict[str, Any]:
    indexed = {
        (row["case_id"], row["seed"], row["condition"]): row
        for row in rows
    }
    units = sorted({(row["case_id"], row["seed"]) for row in rows})
    transitions: Counter[str] = Counter()
    for case_id, seed in units:
        shadow = indexed[(case_id, seed, AR_CONSUMER_RULE)]["semantic_grounded_success"]
        enforced = indexed[(case_id, seed, enforced_condition)]["semantic_grounded_success"]
        if shadow == 0 and enforced == 1:
            transitions["corrected"] += 1
        elif shadow == 1 and enforced == 0:
            transitions["regressed"] += 1
        elif shadow == 1:
            transitions["unchanged_success"] += 1
        else:
            transitions["unchanged_failure"] += 1
    count = len(units)
    return {
        "pair_count": count,
        "corrected": transitions["corrected"],
        "regressed": transitions["regressed"],
        "unchanged_success": transitions["unchanged_success"],
        "unchanged_failure": transitions["unchanged_failure"],
        "net_correction": transitions["corrected"] - transitions["regressed"],
        "corrected_rate": transitions["corrected"] / count if count else None,
        "regressed_rate": transitions["regressed"] / count if count else None,
    }


def _enforcement_effects(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for condition in (STYLE_PLACEBO_ENFORCED, EVIDENCE_ENFORCED):
        result[condition] = {
            "overall": _transition_counts(rows, condition),
            "by_polarity": {
                polarity: _transition_counts(
                    [row for row in rows if row["polarity"] == polarity],
                    condition,
                )
                for polarity in ("negative", "positive")
            },
            "by_family": {
                family: _transition_counts(
                    [row for row in rows if row["family"] == family],
                    condition,
                )
                for family in sorted({row["family"] for row in rows})
            },
        }
    return result


def _semantic_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "available": True,
        "score_row_count": len(rows),
        "by_condition": _metrics_by_condition(rows),
        "by_seed": _metrics_by_dimension(rows, "seed"),
        "by_family": _metrics_by_dimension(rows, "family"),
        "by_polarity": _metrics_by_dimension(rows, "polarity"),
        "by_case": _metrics_by_dimension(rows, "case_id"),
        "pass_three": _pass_three(rows),
        "enforced_vs_shadow": _enforcement_effects(rows),
        "paired_case_cluster_contrasts": {
            name: _contrast_with_protocol_metrics(rows, treatment, comparator)
            for name, treatment, comparator in _PRIMARY_CONTRASTS
        },
        "inference_note": (
            "seed는 case 안에서 먼저 평균냈으며 독립 표본으로 세지 않았다. "
            "p-value는 case cluster의 two-sided exact sign-flip이다."
        ),
    }


def _assert_no_answer_content(summary: Mapping[str, Any]) -> None:
    def walk(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                _require(
                    key not in _FORBIDDEN_CONTENT_KEYS,
                    f"summary에 금지된 답변 본문 필드가 포함됐습니다: {'.'.join((*path, key))}",
                )
                walk(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, (*path, str(index)))

    walk(summary)


def summarize_mechanism(
    capture_path: Path,
    *,
    blind_key_path: Path | None = None,
    score_paths: Sequence[Path] = (),
    score_lock_path: Path | None = None,
    manifest_path: Path = DEFAULT_SOURCE_MANIFEST_PATH,
) -> dict[str, Any]:
    """Capture-only 또는 locked-score mechanism summary를 반환한다."""

    capture_path = Path(capture_path).resolve()
    capture, capture_bytes, units, artifact_provenance = _load_capture_units(capture_path)
    operational = _operational_summary(units)
    provenance: dict[str, Any] = {
        "capture_path": str(capture_path),
        "capture_sha256": _sha256_bytes(capture_bytes),
        **artifact_provenance,
    }

    has_scores = bool(score_paths)
    _require(
        has_scores == (blind_key_path is not None and score_lock_path is not None),
        "semantic summary에는 score file, blind key, score lock이 모두 필요합니다.",
    )
    if has_scores:
        case_metadata = _load_case_metadata(manifest_path)
        capture_cases = {unit["case_id"] for unit in units}
        _require(capture_cases.issubset(case_metadata), "capture에 manifest 미등록 case가 있습니다.")
        rows, score_provenance = _load_locked_scores(
            score_paths=[Path(path) for path in score_paths],
            score_lock_path=Path(score_lock_path),
            blind_key_path=Path(blind_key_path),
            units=units,
            case_metadata=case_metadata,
        )
        semantic = _semantic_summary(rows)
        provenance.update(score_provenance)
        mode = "locked_semantic_scores"
    else:
        semantic = {
            "available": False,
            "reason": "blind key와 잠긴 semantic score file이 제공되지 않았습니다.",
        }
        mode = "capture_only"

    summary = {
        "schema_version": SCHEMA_VERSION,
        "summary_id": SUMMARY_ID,
        "experiment_id": EXPERIMENT_ID,
        "mode": mode,
        "capture_status": capture.get("capture_status"),
        "publishable": capture.get("publishable"),
        "case_count": len({unit["case_id"] for unit in units}),
        "seed_count": len({unit["seed"] for unit in units}),
        "unit_count": len(units),
        "score_conditions": list(SCORE_CONDITIONS),
        "content_access_policy": (
            "답변·prompt·thinking·review reason 본문은 읽거나 채점하지 않고, "
            "잠긴 score와 호출 metadata/reviewer verdict만 집계"
        ),
        "operational": operational,
        "semantic": semantic,
        "provenance": provenance,
    }
    _assert_no_answer_content(summary)
    return summary


def write_mechanism_summary(
    capture_path: Path,
    output_path: Path,
    *,
    blind_key_path: Path | None = None,
    score_paths: Sequence[Path] = (),
    score_lock_path: Path | None = None,
    manifest_path: Path = DEFAULT_SOURCE_MANIFEST_PATH,
) -> tuple[Path, dict[str, Any]]:
    summary = summarize_mechanism(
        capture_path,
        blind_key_path=blind_key_path,
        score_paths=score_paths,
        score_lock_path=score_lock_path,
        manifest_path=manifest_path,
    )
    return _atomic_write_json(output_path, summary), summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ARM consumption mechanism capture/locked-score summary를 만든다."
    )
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path)
    parser.add_argument("--score-lock", type=Path)
    parser.add_argument("--scores", type=Path, nargs="*", default=())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        path, summary = write_mechanism_summary(
            args.capture,
            args.output,
            blind_key_path=args.blind_key,
            score_paths=args.scores,
            score_lock_path=args.score_lock,
            manifest_path=args.manifest,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"mechanism summary 실패: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(path),
                "mode": summary["mode"],
                "unit_count": summary["unit_count"],
                "score_row_count": summary["semantic"].get("score_row_count", 0),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
