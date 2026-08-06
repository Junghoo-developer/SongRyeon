"""동결된 live capture를 블라인드 기계 채점하고 조건별 결과를 연다."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from .protocol import (
    BLINDING_COMMITMENT_FILENAME,
    BLIND_KEY_FILENAME,
    CAPTURE_FILENAME,
    CATEGORIES,
    EXECUTION_COUNT,
    EXPERIMENT_ID,
    FREEZE_FILENAME,
    LABEL_TAGS,
    _blind_mapping,
    _identity_rows,
    canonical_json_sha256,
    load_study,
    read_json_object,
    verify_freeze,
    _write_new_json,
)


BLIND_PACKET_FILENAME = "BLIND_PACKET.json"
BLIND_SCORES_FILENAME = "BLIND_SCORES.json"
SCORE_LOCK_FILENAME = "SCORE_LOCK.json"
SUMMARY_FILENAME = "SUMMARY.json"
REVEAL_FILENAME = "REVEAL.json"
_VERDICT_LINE = re.compile(r"^VERDICT: (SUPPORTED|UNSUPPORTED)$")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REVEAL_KEYS = {
    "schema_version", "experiment_id", "reveal_status", "revealed_at",
    "secret_hex", "mapping", "mapping_sha256", "secret_sha256",
    "packet_sha256", "scores_sha256", "score_lock_sha256",
    "public_proof", "reveal_sha256",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _resolve_inside(root: Path, relative: str, label: str) -> Path:
    _require(isinstance(relative, str) and relative, f"{label} 경로가 없습니다.")
    root = root.resolve(strict=True)
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label}이 capture 폴더 밖을 가리킵니다.") from error
    return path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                event = json.loads(line)
                _require(
                    isinstance(event, dict),
                    f"raw artifact {line_number}번 event가 객체가 아닙니다.",
                )
                events.append(event)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("raw artifact는 유효한 UTF-8 JSONL이어야 합니다.") from error
    return events


def _event_type_counts(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(
        event.get("information_type", "<missing>")
        for event in events
    ).items()))


def _final_delivery_answer_id(event: Mapping[str, Any]) -> str | None:
    try:
        value = json.loads(event["information"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    answer_id = value.get("answer_information_id")
    return answer_id if isinstance(answer_id, str) else None


def _verify_raw_artifact(
    block_root: Path,
    capture: Mapping[str, Any],
    *,
    maximum_tool_calls: int,
) -> str:
    """capture 요약을 원본 JSONL의 질문·답변·도구 event와 직접 대조한다."""

    artifact = capture.get("raw_memory_artifact")
    _require(isinstance(artifact, dict), "raw memory artifact가 없습니다.")
    artifact_path = _resolve_inside(block_root, artifact.get("path"), "raw artifact")
    _require(artifact_path.is_file(), "raw artifact가 파일이 아닙니다.")
    payload = artifact_path.read_bytes()
    digest = _sha256_bytes(payload)
    _require(artifact.get("sha256") == digest, "raw artifact hash가 다릅니다.")
    _require(artifact.get("byte_count") == len(payload), "raw artifact byte 수가 다릅니다.")
    _require(artifact.get("format") == "songryeon-memory-jsonl", "raw artifact format이 다릅니다.")
    _require("parse_error" not in artifact, "capture 시 raw JSONL parse error가 기록됐습니다.")

    events = _read_jsonl(artifact_path)
    counts = _event_type_counts(events)
    _require(artifact.get("event_count") == len(events), "raw artifact event 수가 다릅니다.")
    _require(artifact.get("information_type_counts") == counts, "raw artifact event type 집계가 다릅니다.")

    tool_calls = capture.get("tool_call_count")
    _require(
        isinstance(tool_calls, int)
        and not isinstance(tool_calls, bool)
        and 0 <= tool_calls <= maximum_tool_calls,
        "capture tool_call_count가 공통 예산 밖입니다.",
    )
    _require(tool_calls == counts.get("tool_raw_name", 0), "capture tool_call_count가 raw JSONL과 다릅니다.")
    _require(
        capture.get("model_exchange_count") == counts.get("model_raw_status", 0),
        "capture model_exchange_count가 raw JSONL과 다릅니다.",
    )

    question = capture.get("evaluated_question")
    turn_id = capture.get("turn_id")
    _require(isinstance(question, str) and question, "capture evaluated_question이 없습니다.")
    current_user_inputs = [
        event for event in events
        if event.get("information_type") == "user_input"
        and event.get("information") == question
        and (turn_id is None or event.get("turn_id") == turn_id)
    ]
    _require(current_user_inputs, "raw JSONL에서 현재 평가 질문의 user_input을 찾지 못했습니다.")

    completed = capture.get("completed")
    answer = capture.get("answer")
    error = capture.get("error")
    wall_clock_exhausted = capture.get("wall_clock_limit_exhausted")
    _require(isinstance(completed, bool), "capture completed는 bool이어야 합니다.")
    _require(isinstance(wall_clock_exhausted, bool), "wall-clock 상태는 bool이어야 합니다.")
    if completed:
        _require(isinstance(turn_id, str) and turn_id, "완료 capture turn_id가 없습니다.")
        _require(isinstance(answer, str) and answer, "완료 capture answer가 없습니다.")
        _require(error is None, "완료 capture에 error가 함께 있습니다.")
        _require(wall_clock_exhausted is False, "완료 capture가 wall-clock 한도를 소진했습니다.")
    else:
        _require(isinstance(error, dict), "미완료 capture에는 보존된 error가 필요합니다.")

    if answer is not None:
        _require(isinstance(answer, str) and answer, "capture answer는 문자열 또는 null이어야 합니다.")
        _require(isinstance(turn_id, str) and turn_id, "answer가 있는 capture turn_id가 없습니다.")
        answer_records = [
            event
            for event in events
            if event.get("information_type") == "node3_answer"
            and event.get("information") == answer
            and isinstance(event.get("information_id"), str)
            and isinstance(event.get("turn_id"), str)
            and event["turn_id"].startswith(turn_id)
        ]
        _require(
            len(answer_records) == 1,
            "raw JSONL에서 capture answer의 node3_answer가 정확히 하나가 아닙니다.",
        )
        answer_id = answer_records[0]["information_id"]
        deliveries = [
            event
            for event in events
            if event.get("information_type") == "final_delivery"
            and isinstance(event.get("turn_id"), str)
            and event["turn_id"].startswith(f"{turn_id}-final")
            and _final_delivery_answer_id(event) == answer_id
        ]
        _require(
            len(deliveries) == 1,
            "raw JSONL final_delivery가 capture answer를 유일하게 가리키지 않습니다.",
        )
    elif not events:
        _require(not completed and isinstance(error, dict), "빈 raw artifact는 명시적 실패에서만 허용됩니다.")
    return digest


def _expected_label(case) -> str:
    labels = [LABEL_TAGS[tag] for tag in case.tags if tag in LABEL_TAGS]
    _require(len(labels) == 1, f"{case.case_id} label tag가 잘못됐습니다.")
    return labels[0]


def _category(case) -> str:
    values = [tag for tag in case.tags if tag in CATEGORIES]
    _require(len(values) == 1, f"{case.case_id} category가 잘못됐습니다.")
    return values[0]


def _mapping_by_identity(key: Mapping[str, Any]) -> dict[tuple[int, str, str], str]:
    mapping = {}
    for row in key.get("mapping", []):
        identity = (row.get("seed"), row.get("variant"), row.get("case_id"))
        _require(identity not in mapping, "blind key identity가 중복됐습니다.")
        mapping[identity] = row.get("blind_id")
    _require(len(mapping) == EXECUTION_COUNT, "blind key identity 수가 다릅니다.")
    return mapping


def _read_and_verify_capture(
    experiment_root: Path,
    run: Mapping[str, Any],
    freeze: Mapping[str, Any],
    study,
) -> list[dict[str, Any]]:
    block_root = experiment_root / run["output_subdir"]
    capture_path = block_root / CAPTURE_FILENAME
    document = read_json_object(capture_path, f"block {run['block']} capture")
    _require(document.get("capture_status") == "live_raw_draft", "capture 상태가 live raw draft가 아닙니다.")
    _require(document.get("review_status") == "draft", "capture는 채점 전 draft여야 합니다.")
    _require(document.get("publishable") is False, "raw capture는 publishable일 수 없습니다.")
    _require(document.get("uses_external_api") is False, "외부 API capture는 이 실험에서 금지됩니다.")

    manifest_info = document.get("manifest", {})
    _require(manifest_info.get("manifest_id") == study.manifest.manifest_id, "capture manifest ID가 다릅니다.")
    _require(manifest_info.get("manifest_sha256") == study.manifest.sha256, "capture manifest hash가 다릅니다.")
    _require(manifest_info.get("case_count") == len(study.manifest.cases), "capture case 수가 다릅니다.")
    conditions = document.get("conditions", {})
    _require(conditions.get("expected_manifest_sha256") == study.manifest.sha256, "capture가 frozen manifest hash를 강제하지 않았습니다.")
    _require(
        conditions.get("expected_system_source_tree_sha256")
        == freeze["system_under_test"]["tree_sha256"],
        "capture가 frozen SUT hash를 강제하지 않았습니다.",
    )
    _require(conditions.get("captured_system_source_tree_sha256") == freeze["system_under_test"]["tree_sha256"], "capture SUT hash가 동결값과 다릅니다.")
    _require(conditions.get("architecture_backbone") == study.plan["model"]["name"], "capture backbone이 다릅니다.")
    _require(conditions.get("architecture_variants") == run["variants"], "capture variant 순서가 사전 계획과 다릅니다.")
    _require(conditions.get("architecture_comparison_complete") is True, "세 variant 비교가 완전하지 않습니다.")
    _require(conditions.get("same_model_generation_configuration") is True, "모델 생성 설정이 같지 않습니다.")
    _require(conditions.get("same_case_wall_clock_limit_seconds") == study.plan["case_wall_clock_limit_seconds"], "case wall-clock 조건이 다릅니다.")

    systems = document.get("systems")
    _require(isinstance(systems, list) and len(systems) == 3, "capture system은 3개여야 합니다.")
    system_by_name = {}
    for system in systems:
        _require(isinstance(system, dict), "system metadata는 객체여야 합니다.")
        name = system.get("system_name")
        variant = system.get("variant")
        _require(name not in system_by_name, "system_name이 중복됐습니다.")
        _require(variant in run["variants"], "알 수 없는 variant입니다.")
        _require(system.get("backbone") == study.plan["model"]["name"], "system backbone이 다릅니다.")
        _require(system.get("provider") == "ollama", "system provider는 ollama여야 합니다.")
        execution_profile = system.get("execution_profile")
        _require(
            execution_profile == "contest_local_or_self_hosted"
            and "external_api" not in execution_profile.lower(),
            "system execution profile은 로컬 contest 실행이어야 합니다.",
        )
        _require(system.get("model_id") == study.plan["model"]["digest"], "system model digest가 사전 계획과 다릅니다.")
        contract = study.plan["variant_contracts"][variant]
        _require(system.get("system_wrapper") == contract["system_wrapper"], "system wrapper가 사전 계획과 다릅니다.")
        _require(system.get("node4_mode") == contract["node4_mode"], "node4 mode가 사전 계획과 다릅니다.")
        runtime_contract = system.get("runtime_contract")
        _require(isinstance(runtime_contract, dict), "runtime contract가 없습니다.")
        _require(
            runtime_contract.get("maximum_tool_calls_per_case")
            == contract["maximum_tool_calls_per_case"],
            "runtime contract의 도구 호출 상한이 다릅니다.",
        )
        configuration = system.get("configuration", {})
        expected_configuration = study.plan["model"]
        _require(configuration.get("seed") == run["seed"], "system seed가 다릅니다.")
        _require(configuration.get("base_url") == expected_configuration["base_url"], "system base_url이 사전 계획과 다릅니다.")
        for key in ("num_ctx", "temperature", "timeout_seconds", "keep_alive"):
            _require(configuration.get(key) == expected_configuration[key], f"system {key}가 다릅니다.")
        system_by_name[name] = variant
    _require([system_by_name[system["system_name"]] for system in systems] == run["variants"], "system 실행 순서가 plan과 다릅니다.")

    captures = document.get("captures")
    _require(isinstance(captures, list), "captures는 배열이어야 합니다.")
    expected_pairs = {
        (name, case.case_id)
        for name in system_by_name
        for case in study.manifest.cases
    }
    actual_pairs = [(row.get("system_name"), row.get("case_id")) for row in captures]
    _require(len(actual_pairs) == len(set(actual_pairs)), "capture case/system이 중복됐습니다.")
    _require(set(actual_pairs) == expected_pairs, "capture case/system 행렬이 완전하지 않습니다.")

    normalized = []
    for capture in captures:
        case_id = capture["case_id"]
        system_name = capture["system_name"]
        variant = system_by_name[system_name]
        _require(capture.get("manifest_question") == study.manifest.questions[case_id], "capture 질문 귀속이 다릅니다.")
        _require(capture.get("evaluated_question") == study.manifest.questions[case_id], "평가 질문이 manifest와 다릅니다.")
        artifact = capture.get("raw_memory_artifact")
        raw_artifact_sha256 = _verify_raw_artifact(
            block_root,
            capture,
            maximum_tool_calls=study.plan["maximum_tool_calls_per_case"],
        )
        normalized.append({
            "seed": run["seed"],
            "variant": variant,
            "case_id": case_id,
            "answer": capture.get("answer"),
            "completed": capture.get("completed") is True,
            "error_type": (
                capture.get("error", {}).get("type")
                if isinstance(capture.get("error"), dict)
                else None
            ),
            "raw_artifact_sha256": raw_artifact_sha256,
            "tool_call_count": capture.get("tool_call_count"),
            "model_call_count": capture.get("model_call_count"),
            "latency_ms": capture.get("latency_ms"),
        })
    return normalized


def _source_bundle(study, case_id: str) -> list[dict[str, str]]:
    values = []
    fixture_input = study.manifest.fixture_inputs[case_id]
    for relative in fixture_input["paths"]:
        path = study.manifest.project_fixture_root / relative
        values.append({
            "path": relative,
            "content": path.read_text(encoding="utf-8"),
        })
    return values


def _build_packet_document(
    root: Path,
    study,
    freeze: Mapping[str, Any],
    key: Mapping[str, Any],
    commitment: Mapping[str, Any],
) -> dict[str, Any]:
    """원시 capture 전체를 다시 읽어 결정적인 blind packet을 계산한다."""

    mapping = _mapping_by_identity(key)

    normalized = []
    for run in study.plan["runs"]:
        normalized.extend(_read_and_verify_capture(root, run, freeze, study))
    _require(len(normalized) == EXECUTION_COUNT, "정규화 capture 수가 계획과 다릅니다.")

    items = []
    seen = set()
    for row in normalized:
        identity = (row["seed"], row["variant"], row["case_id"])
        blind_id = mapping.get(identity)
        _require(isinstance(blind_id, str), "capture identity의 blind ID가 없습니다.")
        _require(blind_id not in seen, "blind packet ID가 중복됐습니다.")
        seen.add(blind_id)
        items.append({
            "blind_id": blind_id,
            "question": study.manifest.questions[row["case_id"]],
            "fixture_sources": _source_bundle(study, row["case_id"]),
            "answer": row["answer"],
            "completed": row["completed"],
            "error_type": row["error_type"],
            "raw_artifact_sha256": row["raw_artifact_sha256"],
        })
    items.sort(key=lambda item: item["blind_id"])
    _require([item["blind_id"] for item in items] == sorted(seen), "blind packet 순서가 결정적이지 않습니다.")

    core = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "packet_status": "condition_masked_unscored",
        "publishable": False,
        "mapping_commitment_sha256": commitment["mapping_sha256"],
        "item_count": len(items),
        "items": items,
    }
    return {**core, "packet_sha256": canonical_json_sha256(core)}


def build_blind_packet(experiment_root: Path) -> dict[str, Any]:
    """세 block을 검증하고 system/seed/case identity를 제거한 단일 packet을 만든다."""

    root = Path(experiment_root).resolve(strict=True)
    verify_freeze(root)
    study = load_study()
    freeze = read_json_object(root / FREEZE_FILENAME, "freeze")
    key = read_json_object(root / BLIND_KEY_FILENAME, "blind key")
    commitment = read_json_object(root / BLINDING_COMMITMENT_FILENAME, "blinding commitment")
    document = _build_packet_document(root, study, freeze, key, commitment)
    _write_new_json(root / BLIND_PACKET_FILENAME, document)
    return document


def _verify_packet_against_raw(
    root: Path,
    study,
    freeze: Mapping[str, Any],
    key: Mapping[str, Any],
    commitment: Mapping[str, Any],
) -> dict[str, Any]:
    """저장 packet이 현재 원시 capture에서 다시 계산한 문서와 정확히 같은지 본다."""

    stored = read_json_object(root / BLIND_PACKET_FILENAME, "blind packet")
    expected = _build_packet_document(root, study, freeze, key, commitment)
    _require(stored == expected, "blind packet이 원시 capture에서 다시 계산한 결과와 다릅니다.")
    _verify_packet(stored)
    return stored


def parse_verdict(answer: Any, completed: bool) -> tuple[str | None, str]:
    """정답을 모른 채 고정 verdict 한 줄만 해석한다."""

    if completed is not True:
        return None, "incomplete_run"
    if not isinstance(answer, str) or not answer.strip():
        return None, "missing_answer"
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    first = _VERDICT_LINE.fullmatch(lines[0]) if lines else None
    if first is None:
        return None, "invalid_first_nonempty_line"
    verdict_lines = [line for line in lines if _VERDICT_LINE.fullmatch(line)]
    if len(verdict_lines) != 1:
        return None, "duplicate_verdict_line"
    return first.group(1), "valid"


def _verify_packet(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    packet_sha256 = document.get("packet_sha256")
    core = {key: value for key, value in document.items() if key != "packet_sha256"}
    _require(packet_sha256 == canonical_json_sha256(core), "blind packet self-hash가 다릅니다.")
    _require(document.get("experiment_id") == EXPERIMENT_ID, "blind packet experiment ID가 다릅니다.")
    _require(document.get("packet_status") == "condition_masked_unscored", "blind packet 상태가 다릅니다.")
    _require(document.get("publishable") is False, "미채점 packet은 publishable일 수 없습니다.")
    items = document.get("items")
    _require(isinstance(items, list) and len(items) == EXECUTION_COUNT, "blind packet item 수가 다릅니다.")
    ids = [item.get("blind_id") for item in items]
    _require(len(ids) == len(set(ids)) and ids == sorted(ids), "blind packet ID가 중복됐거나 정렬되지 않았습니다.")
    forbidden = {"system", "system_name", "variant", "seed", "case_id", "expected", "label", "tags"}
    for item in items:
        _require(not (set(item) & forbidden), "blind item이 조건 또는 정답 metadata를 누설합니다.")
        _require(isinstance(item.get("blind_id"), str), "blind ID가 없습니다.")
        _require(isinstance(item.get("fixture_sources"), list), "blind item source가 없습니다.")
        sha = item.get("raw_artifact_sha256")
        _require(isinstance(sha, str) and _SHA256.fullmatch(sha), "raw artifact hash가 잘못됐습니다.")
    return items


def _build_scores_document(packet: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for item in packet["items"]:
        verdict, status = parse_verdict(item.get("answer"), item.get("completed"))
        rows.append({
            "blind_id": item["blind_id"],
            "predicted_verdict": verdict,
            "parse_status": status,
        })
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "score_status": "parsed_without_condition_or_answer_key",
        "publishable": False,
        "packet_sha256": packet["packet_sha256"],
        "item_count": len(rows),
        "rows": rows,
    }


def lock_blind_scores(
    experiment_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """정답 label과 identity key를 사용하지 않고 verdict를 파싱해 lock한다."""

    root = Path(experiment_root).resolve(strict=True)
    verify_freeze(root, verify_key=False)
    packet = read_json_object(root / BLIND_PACKET_FILENAME, "blind packet")
    _verify_packet(packet)
    scores = _build_scores_document(packet)
    scores_sha256 = canonical_json_sha256(scores)
    _write_new_json(root / BLIND_SCORES_FILENAME, scores)
    timestamp = datetime.now(timezone.utc) if now is None else now
    _require(timestamp.tzinfo is not None, "score lock 시각은 timezone-aware여야 합니다.")
    lock = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "lock_status": "scores_locked_before_unblinding",
        "locked_at": timestamp.astimezone(timezone.utc).isoformat(),
        "packet_sha256": packet["packet_sha256"],
        "scores_sha256": scores_sha256,
        "item_count": len(scores["rows"]),
        "publishable": False,
    }
    _write_new_json(root / SCORE_LOCK_FILENAME, lock)
    return lock


def _verified_scores(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    packet = read_json_object(root / BLIND_PACKET_FILENAME, "blind packet")
    _verify_packet(packet)
    scores = read_json_object(root / BLIND_SCORES_FILENAME, "blind scores")
    lock = read_json_object(root / SCORE_LOCK_FILENAME, "score lock")
    _require(scores == _build_scores_document(packet), "blind scores가 packet에서 다시 계산한 결과와 다릅니다.")
    _require(set(lock) == {
        "schema_version", "experiment_id", "lock_status", "locked_at",
        "packet_sha256", "scores_sha256", "item_count", "publishable",
    }, "score lock 필드가 다릅니다.")
    _require(lock.get("schema_version") == 1, "score lock schema version이 다릅니다.")
    _require(lock.get("experiment_id") == EXPERIMENT_ID, "score lock experiment ID가 다릅니다.")
    _require(lock.get("lock_status") == "scores_locked_before_unblinding", "score lock 상태가 다릅니다.")
    _require(isinstance(lock.get("locked_at"), str) and lock["locked_at"], "score lock 시각이 없습니다.")
    _require(lock.get("publishable") is False, "score lock은 publishable일 수 없습니다.")
    _require(lock.get("packet_sha256") == packet["packet_sha256"], "score lock packet hash가 다릅니다.")
    _require(lock.get("scores_sha256") == canonical_json_sha256(scores), "score lock 이후 점수가 바뀌었습니다.")
    _require(lock.get("item_count") == EXECUTION_COUNT, "score lock item 수가 다릅니다.")
    rows = scores.get("rows")
    _require(isinstance(rows, list) and len(rows) == EXECUTION_COUNT, "blind score 행 수가 다릅니다.")
    packet_ids = [item["blind_id"] for item in packet["items"]]
    _require([row.get("blind_id") for row in rows] == packet_ids, "blind score ID 또는 순서가 packet과 다릅니다.")
    return packet, scores, lock


def _metric_block(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    positive = [row for row in rows if row["expected_verdict"] == "SUPPORTED"]
    negative = [row for row in rows if row["expected_verdict"] == "UNSUPPORTED"]
    correct = sum(row["verdict_correct"] for row in rows)
    completed = sum(row["completed"] for row in rows)
    valid = sum(row["parse_status"] == "valid" for row in rows)
    laundering = sum(
        row["predicted_verdict"] == "SUPPORTED"
        for row in negative
    )
    recognized = sum(
        row["predicted_verdict"] == "SUPPORTED"
        for row in positive
    )
    underclaim = sum(
        row["predicted_verdict"] == "UNSUPPORTED"
        for row in positive
    )
    return {
        "planned_count": total,
        "completed_count": completed,
        "format_valid_count": valid,
        "verdict_correct_count": correct,
        "mechanical_verdict_accuracy": correct / total if total else 0.0,
        "negative_control_count": len(negative),
        "unsupported_as_supported_proxy_count": laundering,
        "unsupported_as_supported_proxy_rate": laundering / len(negative) if negative else 0.0,
        "positive_control_count": len(positive),
        "supported_verdict_correct_count": recognized,
        "supported_verdict_accuracy": recognized / len(positive) if positive else 0.0,
        "positive_underclaim_count": underclaim,
        "invalid_or_incomplete_count": total - valid,
    }


def _verify_reveal_document(
    reveal: Mapping[str, Any],
    *,
    study,
    commitment: Mapping[str, Any],
    packet: Mapping[str, Any],
    scores: Mapping[str, Any],
    lock: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """공개 secret부터 mapping·commitment·score lock까지 한 체인으로 검증한다."""

    _require(set(reveal) == _REVEAL_KEYS, "reveal 필드가 다릅니다.")
    core = {key: value for key, value in reveal.items() if key != "reveal_sha256"}
    _require(reveal.get("reveal_sha256") == canonical_json_sha256(core), "reveal self-hash가 다릅니다.")
    _require(reveal.get("schema_version") == 1, "reveal schema version이 다릅니다.")
    _require(reveal.get("experiment_id") == EXPERIMENT_ID, "reveal experiment ID가 다릅니다.")
    _require(reveal.get("reveal_status") == "mapping_revealed_after_score_lock", "reveal 상태가 다릅니다.")
    _require(isinstance(reveal.get("revealed_at"), str) and reveal["revealed_at"], "reveal 시각이 없습니다.")
    _require(reveal.get("public_proof") is True, "reveal은 공개 증명이어야 합니다.")
    secret_hex = reveal.get("secret_hex")
    _require(isinstance(secret_hex, str), "reveal secret이 없습니다.")
    try:
        secret = bytes.fromhex(secret_hex)
    except ValueError as error:
        raise ValueError("reveal secret hex가 잘못됐습니다.") from error
    _require(len(secret) >= 32, "reveal secret은 32 bytes 이상이어야 합니다.")
    expected_mapping = _blind_mapping(_identity_rows(study), secret)
    expected_mapping_sha256 = canonical_json_sha256(expected_mapping)
    _require(reveal.get("mapping") == expected_mapping, "reveal mapping이 secret에서 재계산한 값과 다릅니다.")
    _require(reveal.get("mapping_sha256") == expected_mapping_sha256, "reveal mapping hash가 다릅니다.")
    _require(commitment.get("mapping_sha256") == expected_mapping_sha256, "reveal mapping이 사전 commitment와 다릅니다.")
    secret_sha256 = hashlib.sha256(secret).hexdigest()
    _require(reveal.get("secret_sha256") == secret_sha256, "reveal secret hash가 다릅니다.")
    _require(commitment.get("secret_sha256") == secret_sha256, "reveal secret이 사전 commitment와 다릅니다.")
    _require(reveal.get("packet_sha256") == packet["packet_sha256"], "reveal packet hash가 다릅니다.")
    _require(reveal.get("scores_sha256") == canonical_json_sha256(scores), "reveal scores hash가 다릅니다.")
    _require(reveal.get("scores_sha256") == lock["scores_sha256"], "reveal scores가 score lock과 다릅니다.")
    _require(reveal.get("score_lock_sha256") == canonical_json_sha256(lock), "reveal score lock hash가 다릅니다.")
    return expected_mapping


def _build_summary_document(
    *,
    freeze_status: Mapping[str, Any],
    study,
    packet: Mapping[str, Any],
    scores: Mapping[str, Any],
    lock: Mapping[str, Any],
    commitment: Mapping[str, Any],
    reveal: Mapping[str, Any],
) -> dict[str, Any]:
    mapping = {row["blind_id"]: row for row in reveal["mapping"]}
    case_by_id = {case.case_id: case for case in study.manifest.cases}
    packet_by_id = {item["blind_id"]: item for item in packet["items"]}

    rows = []
    for score in scores["rows"]:
        blind_id = score["blind_id"]
        identity = mapping.get(blind_id)
        _require(identity is not None, "blind score의 identity가 key에 없습니다.")
        case = case_by_id[identity["case_id"]]
        expected = _expected_label(case)
        item = packet_by_id[blind_id]
        verdict_correct = (
            score["parse_status"] == "valid"
            and score["predicted_verdict"] == expected
        )
        rows.append({
            "blind_id": blind_id,
            "block": identity["block"],
            "seed": identity["seed"],
            "variant": identity["variant"],
            "case_id": identity["case_id"],
            "category": _category(case),
            "expected_verdict": expected,
            "predicted_verdict": score["predicted_verdict"],
            "parse_status": score["parse_status"],
            "completed": item["completed"],
            "verdict_correct": verdict_correct,
        })
    _require(len(rows) == EXECUTION_COUNT, "unblind 행 수가 계획과 다릅니다.")

    variants = sorted({row["variant"] for row in rows})
    metrics = {
        variant: _metric_block([row for row in rows if row["variant"] == variant])
        for variant in variants
    }
    by_category = {
        variant: {
            category: _metric_block([
                row for row in rows
                if row["variant"] == variant and row["category"] == category
            ])
            for category in CATEGORIES
        }
        for variant in variants
    }
    pair_index = {
        (row["seed"], row["case_id"], row["variant"]): row
        for row in rows
    }
    gains = losses = ties = 0
    for seed in {row["seed"] for row in rows}:
        for case in study.manifest.cases:
            no_node4 = pair_index[(seed, case.case_id, "songryeon-no-node4")]
            full = pair_index[(seed, case.case_id, "songryeon-full")]
            if full["verdict_correct"] and not no_node4["verdict_correct"]:
                gains += 1
            elif no_node4["verdict_correct"] and not full["verdict_correct"]:
                losses += 1
            else:
                ties += 1

    full = metrics["songryeon-full"]
    comparators = [metrics["single-tool-agent"], metrics["songryeon-no-node4"]]
    directional_gate = {
        "full_verdict_correct_above_both_comparators": all(
            full["verdict_correct_count"] > value["verdict_correct_count"]
            for value in comparators
        ),
        "full_unsupported_as_supported_proxy_below_both_comparators": all(
            full["unsupported_as_supported_proxy_count"] < value["unsupported_as_supported_proxy_count"]
            for value in comparators
        ),
        "positive_guardrail_within_two_runs_of_best_comparator": (
            full["supported_verdict_correct_count"]
            >= max(value["supported_verdict_correct_count"] for value in comparators) - 2
        ),
    }
    directional_gate["claim_allowed"] = all(directional_gate.values())

    required_audit = set(commitment["required_human_audit_blind_ids"])
    required_audit.update(
        row["blind_id"] for row in rows if not row["verdict_correct"]
    )
    summary = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "summary_status": "unblinded_mechanical_scores_human_audit_required",
        "publishable": False,
        "publication_gate_status": "human_audit_required",
        "scope_warning": (
            "합성 Python holdout의 첫 verdict 기계 채점이며 설명의 사실성·출처 표기는 "
            "사람 감사 전 미검증입니다. 실제 업무 전체, 환각 제거, Node4 단독 인과효과 "
            "또는 통계적 유의성을 뜻하지 않습니다."
        ),
        "provenance": {
            **freeze_status,
            "packet_sha256": packet["packet_sha256"],
            "scores_sha256": lock["scores_sha256"],
            "mapping_sha256": commitment["mapping_sha256"],
            "reveal_sha256": reveal["reveal_sha256"],
            "complete_execution_matrix": len(rows) == EXECUTION_COUNT,
            "failure_rows_preserved": True,
        },
        "metrics_by_variant": metrics,
        "metrics_by_variant_and_category": by_category,
        "full_vs_no_node4_end_to_end_pairs": {
            "full_gain_count": gains,
            "full_loss_count": losses,
            "tie_count": ties,
            "warning": "독립 실행 비교이며 같은 Node3 초안에 대한 순수 Node4 인과효과가 아닙니다.",
        },
        "preregistered_directional_gate": directional_gate,
        "required_human_audit_blind_ids": sorted(required_audit),
        "rows": rows,
    }
    summary["summary_sha256"] = canonical_json_sha256(summary)
    return summary


def unblind_summary(
    experiment_root: Path,
    *,
    public_proof_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """score lock 뒤에만 key를 열어 정답·조건별 요약을 만든다."""

    root = Path(experiment_root).resolve(strict=True)
    freeze_status = verify_freeze(root)
    study = load_study()
    freeze = read_json_object(root / FREEZE_FILENAME, "freeze")
    key = read_json_object(root / BLIND_KEY_FILENAME, "blind key")
    commitment = read_json_object(root / BLINDING_COMMITMENT_FILENAME, "blinding commitment")
    packet = _verify_packet_against_raw(root, study, freeze, key, commitment)
    stored_packet, scores, lock = _verified_scores(root)
    _require(stored_packet == packet, "검증 중 blind packet이 달라졌습니다.")

    proof_root = None
    if public_proof_dir is not None:
        proof_root = Path(public_proof_dir).resolve(strict=True)
        verify_freeze(proof_root, verify_key=False)
        public_freeze = read_json_object(proof_root / FREEZE_FILENAME, "public freeze")
        public_commitment = read_json_object(
            proof_root / BLINDING_COMMITMENT_FILENAME,
            "public blinding commitment",
        )
        _require(public_freeze == freeze, "public proof freeze가 private freeze와 다릅니다.")
        _require(
            public_commitment == commitment,
            "public proof commitment가 private commitment와 다릅니다.",
        )

    timestamp = datetime.now(timezone.utc) if now is None else now
    _require(timestamp.tzinfo is not None, "reveal 시각은 timezone-aware여야 합니다.")
    reveal = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "reveal_status": "mapping_revealed_after_score_lock",
        "revealed_at": timestamp.astimezone(timezone.utc).isoformat(),
        "secret_hex": key["secret_hex"],
        "mapping": key["mapping"],
        "mapping_sha256": key["mapping_sha256"],
        "secret_sha256": commitment["secret_sha256"],
        "packet_sha256": packet["packet_sha256"],
        "scores_sha256": lock["scores_sha256"],
        "score_lock_sha256": canonical_json_sha256(lock),
        "public_proof": True,
    }
    reveal["reveal_sha256"] = canonical_json_sha256(reveal)
    _verify_reveal_document(
        reveal,
        study=study,
        commitment=commitment,
        packet=packet,
        scores=scores,
        lock=lock,
    )
    summary = _build_summary_document(
        freeze_status=freeze_status,
        study=study,
        packet=packet,
        scores=scores,
        lock=lock,
        commitment=commitment,
        reveal=reveal,
    )

    _write_new_json(root / REVEAL_FILENAME, reveal)
    _write_new_json(root / SUMMARY_FILENAME, summary)
    if proof_root is not None:
        for filename, document in (
            (BLIND_PACKET_FILENAME, packet),
            (BLIND_SCORES_FILENAME, scores),
            (SCORE_LOCK_FILENAME, lock),
            (REVEAL_FILENAME, reveal),
            (SUMMARY_FILENAME, summary),
        ):
            _write_new_json(proof_root / filename, document)
        verify_public_result(proof_root)
    return summary


def verify_unblinded_summary(experiment_root: Path) -> dict[str, Any]:
    """원시 로그부터 summary까지 private 결과 체인을 읽기 전용으로 재계산한다."""

    root = Path(experiment_root).resolve(strict=True)
    freeze_status = verify_freeze(root)
    study = load_study()
    freeze = read_json_object(root / FREEZE_FILENAME, "freeze")
    key = read_json_object(root / BLIND_KEY_FILENAME, "blind key")
    commitment = read_json_object(root / BLINDING_COMMITMENT_FILENAME, "blinding commitment")
    packet = _verify_packet_against_raw(root, study, freeze, key, commitment)
    stored_packet, scores, lock = _verified_scores(root)
    _require(stored_packet == packet, "검증 중 blind packet이 달라졌습니다.")
    reveal = read_json_object(root / REVEAL_FILENAME, "reveal")
    _verify_reveal_document(
        reveal,
        study=study,
        commitment=commitment,
        packet=packet,
        scores=scores,
        lock=lock,
    )
    expected = _build_summary_document(
        freeze_status=freeze_status,
        study=study,
        packet=packet,
        scores=scores,
        lock=lock,
        commitment=commitment,
        reveal=reveal,
    )
    stored = read_json_object(root / SUMMARY_FILENAME, "summary")
    _require(stored == expected, "summary가 원시 capture와 잠긴 점수에서 재계산한 결과와 다릅니다.")
    return stored


def verify_public_result(public_proof_dir: Path) -> dict[str, Any]:
    """secret 공개 뒤의 공개 proof 체인을 원시 로그 없이 독립 검증한다."""

    root = Path(public_proof_dir).resolve(strict=True)
    freeze_status = verify_freeze(root, verify_key=False)
    study = load_study()
    commitment = read_json_object(root / BLINDING_COMMITMENT_FILENAME, "blinding commitment")
    packet, scores, lock = _verified_scores(root)
    reveal = read_json_object(root / REVEAL_FILENAME, "reveal")
    _verify_reveal_document(
        reveal,
        study=study,
        commitment=commitment,
        packet=packet,
        scores=scores,
        lock=lock,
    )
    expected = _build_summary_document(
        freeze_status=freeze_status,
        study=study,
        packet=packet,
        scores=scores,
        lock=lock,
        commitment=commitment,
        reveal=reveal,
    )
    stored = read_json_object(root / SUMMARY_FILENAME, "summary")
    _require(stored == expected, "공개 summary가 공개 proof 체인에서 재계산한 결과와 다릅니다.")
    return {
        "experiment_id": EXPERIMENT_ID,
        "public_result_verified": True,
        "summary_sha256": stored["summary_sha256"],
        "item_count": EXECUTION_COUNT,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="동결 holdout raw capture를 blind 기계 채점합니다.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("packet", "score"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--experiment-root", type=Path, required=True)
    unblind_parser = subparsers.add_parser("unblind")
    unblind_parser.add_argument("--experiment-root", type=Path, required=True)
    unblind_parser.add_argument(
        "--public-proof-dir",
        type=Path,
        default=None,
        help="score lock 뒤 검증 가능한 결과 체인을 추가할 공개 proof 폴더",
    )
    verify_public_parser = subparsers.add_parser("verify-public")
    verify_public_parser.add_argument("--public-proof-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "packet":
            result = build_blind_packet(args.experiment_root)
        elif args.command == "score":
            result = lock_blind_scores(args.experiment_root)
        elif args.command == "unblind":
            result = unblind_summary(
                args.experiment_root,
                public_proof_dir=args.public_proof_dir,
            )
        else:
            result = verify_public_result(args.public_proof_dir)
    except (OSError, TypeError, ValueError) as error:
        print(f"contest holdout {args.command} 실패: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
