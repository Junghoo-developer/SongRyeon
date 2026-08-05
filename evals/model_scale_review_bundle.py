"""Build a blinded, reviewer-facing bundle from a model-scale evidence pack.

The source evidence pack is read-only.  This module verifies it first, then
reconstructs the execution trace from each raw memory JSONL.  In particular,
``tool_result_content`` is included only when it is the exact slice selected
from the hidden tool result in the same tool ``turn_id``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from .model_scale_capture import (
    ARTIFACT_MANIFEST_FILENAME,
    BLIND_KEY_FILENAME,
    CAPTURE_FILENAME,
    DEFAULT_MODEL_CEILING_MANIFEST,
    PROTOCOL_FILENAME,
)
from .model_scale_verify import verify_evidence_pack
from .runner import SCHEMA_VERSION, load_manifest


REVIEW_PACKET_FILENAME = "review_packet.json"
REVIEWER_PROTOCOL_FILENAME = "reviewer_protocol.md"
REVIEW_BUNDLE_VERSION = "model-scale-review-bundle-v1"
CASE_MATERIAL_DIRECTORY = "case_material"
NORMALIZER_SOURCE_FILENAME = "normalizer_source.py"
DEFAULT_CHUNK_CHARACTERS = 2_000
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_REQUIRED_EXPERIMENT_SOURCE_PATHS = {
    "agent_tools/files.py",
    "evals/model_scale_capture.py",
    "evals/model_scale_verify.py",
    "evals/runner.py",
    "evals/schema.py",
    "memory/tool_records.py",
    "nodes/parsing.py",
    "nodes/retention.py",
}
_RETENTION_TYPES = {
    "tool_retention_applied",
    "tool_omit_recovery_applied",
}
_RAW_TYPES = {
    "tool_raw_arguments",
    "tool_raw_content",
    "tool_raw_error",
    "tool_raw_name",
    "tool_raw_success",
}


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path):
    return _sha256_bytes(Path(path).read_bytes())


def _resolve_chunk_bounds(raw_text, chunk_id):
    """Frozen copy of the experiment runtime's deterministic chunk contract."""

    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("chunk_id가 필요합니다.")
    chunks = []
    current_start = 0
    current_length = 0
    position = 0
    for line in raw_text.splitlines(keepends=True):
        line_start = position
        line_end = line_start + len(line)
        position = line_end
        if current_length and (
            current_length + len(line) > DEFAULT_CHUNK_CHARACTERS
        ):
            chunks.append((current_start, line_start))
            current_start = line_start
            current_length = 0
        remaining_start = line_start
        remaining_length = len(line)
        while remaining_length > DEFAULT_CHUNK_CHARACTERS:
            split_end = remaining_start + DEFAULT_CHUNK_CHARACTERS
            chunks.append((remaining_start, split_end))
            remaining_start = split_end
            remaining_length -= DEFAULT_CHUNK_CHARACTERS
            current_start = remaining_start
        if remaining_length:
            if current_length == 0:
                current_start = remaining_start
            current_length += remaining_length
    if current_length:
        chunks.append((current_start, len(raw_text)))
    indexed = {
        f"chunk-{index:04d}": bounds
        for index, bounds in enumerate(chunks, start=1)
    }
    if "".join(raw_text[start:end] for start, end in chunks) != raw_text:
        raise ValueError("결정론적 chunk가 원문을 보존하지 못했습니다.")
    try:
        return indexed[chunk_id]
    except KeyError:
        raise ValueError("chunk_id가 결정론적 chunk 목록에 없습니다.") from None


def _canonical_json_sha256(value):
    raw = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(raw)


def _verify_experiment_source_snapshot(protocol):
    """Bind current parsing dependencies to the exact experiment-time tree."""

    snapshot = protocol.get("source_snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("algorithm") != "sha256(raw-bytes)":
        raise ValueError("protocol source_snapshot 형식이 잘못됐습니다.")
    files = snapshot.get("files")
    if not isinstance(files, list) or snapshot.get("file_count") != len(files):
        raise ValueError("protocol source_snapshot files가 완전하지 않습니다.")
    seen = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("source snapshot item은 객체여야 합니다.")
        relative = item.get("path")
        expected = item.get("sha256")
        if (
            not isinstance(relative, str)
            or not relative
            or relative in seen
            or not isinstance(expected, str)
            or _SHA256_PATTERN.fullmatch(expected) is None
        ):
            raise ValueError("source snapshot path/hash가 잘못됐습니다.")
        seen.add(relative)
        source = (PROJECT_DIRECTORY / Path(relative)).resolve()
        try:
            source.relative_to(PROJECT_DIRECTORY)
        except ValueError as error:
            raise ValueError("source snapshot path가 project 밖입니다.") from error
        if not source.is_file() or _sha256_path(source) != expected:
            raise ValueError(
                f"실험 당시 source snapshot과 현재 파일이 다릅니다: {relative}"
            )
    if not _REQUIRED_EXPERIMENT_SOURCE_PATHS.issubset(seen):
        raise ValueError("source snapshot에 normalizer 필수 계약 파일이 없습니다.")
    return snapshot.get("tree_sha256")


def _read_json(path, label):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}을(를) 읽을 수 없습니다.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label}의 최상위는 JSON 객체여야 합니다.")
    return value


def _read_jsonl(path):
    records = []
    try:
        with Path(path).open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(
                        f"raw JSONL {line_number}번 레코드가 객체가 아닙니다."
                    )
                records.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("raw memory JSONL을 완전히 읽을 수 없습니다.") from error
    return records


def _write_json_atomic(value, path):
    destination = Path(path)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, destination)
    return destination


def _write_text_atomic(value, path):
    destination = Path(path)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, destination)
    return destination


def _prepare_output_directory(path, source_root):
    destination = Path(path).resolve()
    source = Path(source_root).resolve()
    if destination == source:
        raise ValueError("파생 검토 묶음은 원본 evidence pack과 분리해야 합니다.")
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise ValueError("파생 검토 묶음을 원본 evidence pack 안에 쓸 수 없습니다.")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("출력 폴더는 없거나 비어 있어야 합니다.")
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def _one(records, information_type, tool_turn_id):
    matches = [
        record
        for _, record in records
        if record.get("information_type") == information_type
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{tool_turn_id}: {information_type}는 정확히 하나여야 합니다."
        )
    return matches[0]


def _absolute(record, label):
    if (
        record.get("information_class") != "absolute"
        or record.get("code_verifiable") is not True
    ):
        raise ValueError(f"{label}은(는) A 기록이어야 합니다.")


def _json_object_information(record, label):
    try:
        value = json.loads(record.get("information"))
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}의 information은 JSON 객체여야 합니다.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label}의 information은 JSON 객체여야 합니다.")
    return value


def _validate_retention_payload(payload, tool_name, arguments, label):
    if payload.get("tool_name") != tool_name:
        raise ValueError(f"{label}의 tool_name이 raw 기록과 다릅니다.")
    if payload.get("arguments") != arguments:
        raise ValueError(f"{label}의 arguments가 raw 기록과 다릅니다.")
    mode = payload.get("mode")
    if mode not in {"full", "excerpt", "chunk", "omit"}:
        raise ValueError(f"{label}의 retention mode가 잘못됐습니다.")
    start = payload.get("start")
    end = payload.get("end")
    if mode in {"full", "omit"}:
        if start is not None or end is not None:
            raise ValueError(f"{label}의 full/omit 범위는 null이어야 합니다.")
    elif not (
        type(start) is int
        and type(end) is int
        and 0 <= start < end
    ):
        raise ValueError(f"{label}의 slice 범위가 잘못됐습니다.")
    return mode, start, end


def _selection(raw_text, mode, start, end, label):
    if mode == "omit":
        return None
    if mode == "full":
        return raw_text
    if end > len(raw_text):
        raise ValueError(f"{label}의 end가 raw 원문 길이를 넘습니다.")
    return raw_text[start:end]


def _validate_retention_contract(
    payload,
    raw_text,
    mode,
    start,
    end,
    *,
    recovery,
    label,
):
    """Authenticate the runtime's short-text/chunk retention contract."""

    expected_keys = {
        "arguments",
        "end",
        "mode",
        "start",
        "tool_name",
    }
    if mode == "chunk":
        expected_keys.add("chunk_id")
    if recovery:
        expected_keys.update({"candidate_number", "previous_mode"})
    if set(payload) != expected_keys:
        raise ValueError(f"{label}: applied retention key 집합이 다릅니다.")

    is_long = len(raw_text) > DEFAULT_CHUNK_CHARACTERS
    if is_long and mode not in {"chunk", "omit"}:
        raise ValueError(f"{label}: 긴 원문은 chunk 또는 omit만 허용됩니다.")
    if not is_long and mode == "chunk":
        raise ValueError(f"{label}: 짧은 원문에는 chunk를 사용할 수 없습니다.")

    if mode == "chunk":
        chunk_id = payload.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            raise ValueError(f"{label}: chunk_id가 필요합니다.")
        expected_start, expected_end = _resolve_chunk_bounds(raw_text, chunk_id)
        if start != expected_start or end != expected_end:
            raise ValueError(f"{label}: chunk 경계가 결정론적 경계와 다릅니다.")
    elif payload.get("chunk_id") is not None:
        raise ValueError(f"{label}: non-chunk에 chunk_id가 있습니다.")

    selected = _selection(raw_text, mode, start, end, label)
    if selected is not None and len(selected) > DEFAULT_CHUNK_CHARACTERS:
        raise ValueError(f"{label}: 선택 본문이 2,000자를 넘습니다.")

    if recovery:
        candidate_number = payload.get("candidate_number")
        if (
            mode == "omit"
            or payload.get("previous_mode") != "omit"
            or type(candidate_number) is not int
            or candidate_number < 1
        ):
            raise ValueError(f"{label}: omit recovery 계약이 잘못됐습니다.")
    elif "candidate_number" in payload or "previous_mode" in payload:
        raise ValueError(f"{label}: 초기 retention에 recovery 필드가 있습니다.")


def _retention_trace(
    records,
    *,
    tool_sequence,
    tool_turn_id,
    tool_name,
    arguments,
    raw_text,
    raw_source_id,
):
    raw_source_matches = [
        (index, record)
        for index, record in records
        if record.get("information_id") == raw_source_id
        and record.get("information_type")
        in {"tool_raw_content", "tool_raw_error"}
    ]
    if len(raw_source_matches) != 1:
        raise ValueError(f"{tool_turn_id}: active raw source가 유일하지 않습니다.")
    raw_source_index = raw_source_matches[0][0]
    source_links = [
        (index, record)
        for index, record in records
        if record.get("information_type")
        in {
            "tool_raw_selection_source_id",
            "tool_raw_omit_recovery_source_id",
        }
    ]
    retention_events = [
        (index, record)
        for index, record in records
        if record.get("information_type") in _RETENTION_TYPES
    ]
    result_events = [
        (index, record)
        for index, record in records
        if record.get("information_type") == "tool_result_content"
    ]
    if len(retention_events) not in {1, 2}:
        raise ValueError(
            f"{tool_turn_id}: retention은 1개 또는 omit recovery를 포함한 2개여야 합니다."
        )
    if len(source_links) != len(retention_events):
        raise ValueError(f"{tool_turn_id}: retention source 연결 수가 다릅니다.")
    if not isinstance(raw_source_id, str) or not raw_source_id:
        raise ValueError(f"{tool_turn_id}: active raw source ID가 없습니다.")
    if any(
        record.get("information") != raw_source_id
        for _, record in source_links
    ):
        raise ValueError(f"{tool_turn_id}: retention source ID가 raw 원문과 다릅니다.")
    for _, record in source_links:
        _absolute(record, f"{tool_turn_id} retention source")

    if retention_events[0][1].get("information_type") != "tool_retention_applied":
        raise ValueError(f"{tool_turn_id}: 첫 retention 종류가 잘못됐습니다.")
    if len(retention_events) == 2 and (
        retention_events[1][1].get("information_type")
        != "tool_omit_recovery_applied"
    ):
        raise ValueError(f"{tool_turn_id}: 두 번째 retention은 omit recovery여야 합니다.")

    retentions = []
    public = []
    used_result_indices = set()
    previous_mode = None
    for retention_sequence, (record_index, record) in enumerate(
        retention_events,
        start=1,
    ):
        _absolute(record, f"{tool_turn_id} retention")
        payload = _json_object_information(record, "retention")
        mode, start, end = _validate_retention_payload(
            payload,
            tool_name,
            arguments,
            "retention",
        )
        recovery = retention_sequence == 2
        _validate_retention_contract(
            payload,
            raw_text,
            mode,
            start,
            end,
            recovery=recovery,
            label=f"{tool_turn_id} retention",
        )
        expected_source_type = (
            "tool_raw_omit_recovery_source_id"
            if recovery
            else "tool_raw_selection_source_id"
        )
        source_index, source_record = source_links[retention_sequence - 1]
        lower_bound = (
            retention_events[retention_sequence - 2][0]
            if recovery
            else raw_source_index
        )
        if (
            source_record.get("information_type") != expected_source_type
            or not lower_bound < source_index < record_index
        ):
            raise ValueError(f"{tool_turn_id}: retention source 순서가 잘못됐습니다.")
        if retention_sequence == 2 and previous_mode != "omit":
            raise ValueError(f"{tool_turn_id}: omit 이후에만 recovery할 수 있습니다.")
        next_index = (
            retention_events[retention_sequence][0]
            if retention_sequence < len(retention_events)
            else max(index for index, _ in records) + 1
        )
        matching_results = [
            (index, result)
            for index, result in result_events
            if record_index < index < next_index
        ]
        expected_content = _selection(
            raw_text,
            mode,
            start,
            end,
            f"{tool_turn_id} retention",
        )
        if expected_content is None:
            if matching_results:
                raise ValueError(f"{tool_turn_id}: omit 뒤에 공개 원문이 있습니다.")
            selected_count = 0
        else:
            if len(matching_results) != 1:
                raise ValueError(
                    f"{tool_turn_id}: non-omit retention에는 result가 정확히 하나여야 합니다."
                )
            result_index, result_record = matching_results[0]
            _absolute(result_record, f"{tool_turn_id} tool_result_content")
            content = result_record.get("information")
            if not isinstance(content, str) or content != expected_content:
                raise ValueError(
                    f"{tool_turn_id}: tool_result_content가 raw exact slice와 다릅니다."
                )
            used_result_indices.add(result_index)
            selected_count = len(content)
            public.append(
                {
                    "tool_sequence": tool_sequence,
                    "retention_sequence": retention_sequence,
                    "mode": mode,
                    "start": start,
                    "end": end,
                    "selected_character_count": selected_count,
                    "content_sha256": _sha256_bytes(content.encode("utf-8")),
                    "content": content,
                }
            )
        retentions.append(
            {
                "sequence": retention_sequence,
                "mode": mode,
                "start": start,
                "end": end,
                "selected_character_count": selected_count,
                "downstream_public": expected_content is not None,
            }
        )
        previous_mode = mode

    if used_result_indices != {index for index, _ in result_events}:
        raise ValueError(f"{tool_turn_id}: retention에 연결되지 않은 result가 있습니다.")
    return retentions, public


def _fixture_memory(records):
    fixtures = []
    seen_ids = set()
    for _, record in records:
        if record.get("information_type") != "fixture_memory":
            continue
        record_id = record.get("information_id")
        information_class = record.get("information_class")
        information = record.get("information")
        if (
            not isinstance(record_id, str)
            or not record_id
            or record_id in seen_ids
            or information_class not in {"absolute", "relative"}
            or not isinstance(information, str)
        ):
            raise ValueError("fixture_memory 기록이 완전하지 않습니다.")
        expected_verifiable = information_class == "absolute"
        if record.get("code_verifiable") is not expected_verifiable:
            raise ValueError("fixture_memory의 A/R과 code_verifiable이 다릅니다.")
        seen_ids.add(record_id)
        fixtures.append(
            {
                "sequence": len(fixtures) + 1,
                "record_id": record_id,
                "information_class": information_class,
                "code_verifiable": expected_verifiable,
                "information": information,
            }
        )
    return fixtures


def _expected_case_input(manifest, case_id):
    fixture_input = manifest.fixture_inputs[case_id]
    if fixture_input.get("kind") == "conversation":
        turns = fixture_input.get("turns")
        if not isinstance(turns, list) or not turns:
            raise ValueError("conversation fixture가 완전하지 않습니다.")
        return turns[-1]["content"], len(turns) - 1, turns
    question = manifest.questions[case_id]
    return (
        question,
        0,
        [{"role": "user", "content": question, "evaluate": True}],
    )


def _expected_fixture_memory(manifest, case_id):
    fixture_input = manifest.fixture_inputs[case_id]
    if fixture_input.get("kind") not in {"memory_records", "project_and_memory"}:
        return []
    records = fixture_input.get("records")
    if not isinstance(records, list):
        raise ValueError("fixture memory manifest가 완전하지 않습니다.")
    expected = []
    for sequence, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError("fixture memory manifest 항목이 객체가 아닙니다.")
        information_class = record.get("information_class")
        expected.append(
            {
                "sequence": sequence,
                "record_id": record.get("record_id"),
                "information_class": information_class,
                "code_verifiable": information_class == "absolute",
                "information": record.get("information"),
            }
        )
    return expected


def _blinded_error(error):
    """Expose failure presence without copying provider-identifying text."""

    if error is None:
        return None
    if not isinstance(error, dict):
        raise ValueError("capture error는 null 또는 객체여야 합니다.")
    return {"present": True}


def _validate_blind_key(blind_key, capture_document):
    aliases = blind_key.get("system_aliases")
    systems = capture_document.get("systems")
    if not isinstance(aliases, dict) or not isinstance(systems, list):
        raise ValueError("blind key alias 또는 capture systems 형식이 잘못됐습니다.")
    system_names = {
        system.get("system_name")
        for system in systems
        if isinstance(system, dict)
        and isinstance(system.get("system_name"), str)
        and system.get("system_name")
    }
    if len(system_names) != len(systems) or set(aliases) != system_names:
        raise ValueError("blind alias와 capture system 집합이 다릅니다.")
    alias_values = list(aliases.values())
    if (
        any(
            not isinstance(alias, str)
            or re.fullmatch(r"System [A-Z]+", alias) is None
            for alias in alias_values
        )
        or len(set(alias_values)) != len(alias_values)
    ):
        raise ValueError("blind system alias가 안전하지 않거나 중복됐습니다.")
    return aliases


def _identity_strings(capture_document):
    values = set()
    for system in capture_document.get("systems", []):
        for key in (
            "system_name",
            "model_name",
            "provider",
            "execution_profile",
        ):
            value = system.get(key)
            if isinstance(value, str) and len(value) >= 4:
                values.add(value)
    return values


def _reject_identity_leaks(packet, identity_strings):
    packet_text = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    leaked = [value for value in identity_strings if value in packet_text]
    if leaked:
        raise ValueError("blind review packet에 system identity가 노출됐습니다.")


def _gate_limit_exhaustions(records):
    """Recompute Node2/Node4 limit events from the immutable A route log."""

    records_by_turn = {}
    for _, record in records:
        turn_id = record.get("turn_id")
        if isinstance(turn_id, str) and turn_id:
            records_by_turn.setdefault(turn_id, []).append(record)

    exhausted = {"node2": False, "node4": False}
    for turn_id, turn_records in records_by_turn.items():
        sources = [
            record
            for record in turn_records
            if record.get("information_type") == "source"
            and record.get("information") in exhausted
        ]
        if not sources:
            continue
        if len(sources) != 1:
            raise ValueError(f"{turn_id}: gate source는 정확히 하나여야 합니다.")
        _absolute(sources[0], f"{turn_id} gate source")
        reviewer = sources[0]["information"]
        actions = [
            record
            for record in turn_records
            if record.get("information_type") == "action"
        ]
        if len(actions) != 1:
            raise ValueError(f"{turn_id}: gate action은 정확히 하나여야 합니다.")
        _absolute(actions[0], f"{turn_id} gate action")
        action = _json_object_information(actions[0], f"{turn_id} gate action")
        outcome = action.get("outcome")
        ignored = action.get("rejection_ignored")
        if outcome not in {
            "permit_applied",
            "reject_applied",
            "reject_ignored_limit",
        }:
            raise ValueError(f"{turn_id}: gate outcome이 잘못됐습니다.")
        expected_ignored = outcome == "reject_ignored_limit"
        if ignored is not expected_ignored:
            raise ValueError(f"{turn_id}: gate limit 표시가 outcome과 다릅니다.")
        if expected_ignored:
            if exhausted[reviewer]:
                raise ValueError(f"{turn_id}: gate limit 사건이 중복됐습니다.")
            exhausted[reviewer] = True
    return exhausted


def _execution_trace(records, capture):
    indexed = list(enumerate(records))
    information_ids = [record.get("information_id") for record in records]
    if (
        any(not isinstance(value, str) or not value for value in information_ids)
        or len(set(information_ids)) != len(information_ids)
    ):
        raise ValueError("raw JSONL information_id가 없거나 중복됐습니다.")
    declared_artifact = capture.get("raw_memory_artifact")
    if not isinstance(declared_artifact, dict):
        raise ValueError("capture에 raw_memory_artifact가 없습니다.")
    if declared_artifact.get("parse_error") is not None:
        raise ValueError("parse_error가 있는 raw memory는 검토 묶음으로 파생할 수 없습니다.")
    if declared_artifact.get("event_count") != len(records):
        raise ValueError("raw event_count가 실제 레코드 수와 다릅니다.")
    actual_counts = dict(
        sorted(
            Counter(
                record.get("information_type", "<missing>")
                for record in records
            ).items()
        )
    )
    if declared_artifact.get("information_type_counts") != actual_counts:
        raise ValueError("raw information_type_counts가 실제 레코드와 다릅니다.")

    tool_turn_order = []
    records_by_turn = {}
    for index, record in indexed:
        information_type = record.get("information_type")
        if information_type != "tool_raw_name":
            continue
        turn_id = record.get("turn_id")
        if not isinstance(turn_id, str) or not turn_id:
            raise ValueError("tool_raw_name에 turn_id가 없습니다.")
        if turn_id in records_by_turn:
            raise ValueError(f"{turn_id}: tool_raw_name이 중복됐습니다.")
        tool_turn_order.append(turn_id)
        records_by_turn[turn_id] = []

    trace_types = _RAW_TYPES | _RETENTION_TYPES | {
        "tool_raw_selection_source_id",
        "tool_raw_omit_recovery_source_id",
        "tool_result_content",
    }
    for index, record in indexed:
        if record.get("information_type") not in trace_types:
            continue
        turn_id = record.get("turn_id")
        if turn_id not in records_by_turn:
            raise ValueError(f"{turn_id}: raw name이 없는 orphan tool 기록입니다.")
        records_by_turn[turn_id].append((index, record))

    parent_turn_id = capture.get("turn_id")
    if tool_turn_order and (
        not isinstance(parent_turn_id, str)
        or any(
            not tool_turn_id.startswith(parent_turn_id + "-tool-")
            for tool_turn_id in tool_turn_order
        )
    ):
        raise ValueError("도구 기록이 capture의 현재 turn_id에 속하지 않습니다.")

    tool_calls = []
    downstream = []
    for sequence, tool_turn_id in enumerate(tool_turn_order, start=1):
        grouped = records_by_turn[tool_turn_id]
        raw = {
            name: _one(grouped, name, tool_turn_id)
            for name in _RAW_TYPES
        }
        for name, record in raw.items():
            _absolute(record, f"{tool_turn_id} {name}")
        name = raw["tool_raw_name"].get("information")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{tool_turn_id}: tool name이 잘못됐습니다.")
        arguments = _json_object_information(
            raw["tool_raw_arguments"],
            "tool_raw_arguments",
        )
        path = arguments.get("path")
        if path is not None and not isinstance(path, str):
            raise ValueError(f"{tool_turn_id}: path는 문자열 또는 null이어야 합니다.")
        success = raw["tool_raw_success"].get("information")
        if not isinstance(success, bool):
            raise ValueError(f"{tool_turn_id}: tool success는 bool이어야 합니다.")
        raw_record = raw[
            "tool_raw_content" if success else "tool_raw_error"
        ]
        raw_text = raw_record.get("information")
        if not isinstance(raw_text, str):
            raise ValueError(f"{tool_turn_id}: 선택 원문은 문자열이어야 합니다.")
        retentions, public = _retention_trace(
            grouped,
            tool_sequence=sequence,
            tool_turn_id=tool_turn_id,
            tool_name=name,
            arguments=arguments,
            raw_text=raw_text,
            raw_source_id=raw_record.get("information_id"),
        )
        tool_calls.append(
            {
                "sequence": sequence,
                "name": name,
                "arguments": arguments,
                "path": path,
                "success": success,
                "retentions": retentions,
            }
        )
        downstream.extend(public)

    declared_count = capture.get("tool_call_count")
    if type(declared_count) is not int or declared_count != len(tool_calls):
        raise ValueError("capture tool_call_count가 raw tool trace와 다릅니다.")
    gate_limits = _gate_limit_exhaustions(indexed)
    for reviewer in ("node2", "node4"):
        field = f"{reviewer}_limit_exhausted"
        if not isinstance(capture.get(field), bool):
            raise ValueError(f"capture {field}는 bool이어야 합니다.")
        if capture[field] is not gate_limits[reviewer]:
            raise ValueError(f"capture {field}가 raw gate A와 다릅니다.")

    return {
        "tool_calls": tool_calls,
        "tool_call_count": declared_count,
        "node2_limit_exhausted": capture["node2_limit_exhausted"],
        "node4_limit_exhausted": capture["node4_limit_exhausted"],
        "fixture_memory": _fixture_memory(indexed),
    }, downstream


def _resolve_raw_path(root, capture):
    artifact = capture.get("raw_memory_artifact")
    if not isinstance(artifact, dict):
        raise ValueError("capture raw_memory_artifact가 없습니다.")
    relative = artifact.get("path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("raw artifact path가 잘못됐습니다.")
    path = (root / Path(relative)).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("raw artifact가 evidence pack 밖을 가리킵니다.") from error
    if not path.is_file():
        raise ValueError("raw artifact 파일이 없습니다.")
    return path


def _reviewer_protocol(
    parent_manifest_sha256,
    manifest_id,
    item_count,
    normalizer_sha256,
):
    return f"""# SongRyeon blinded reviewer protocol

## 상태

- Bundle version: `{REVIEW_BUNDLE_VERSION}`
- Items: {item_count}
- Frozen case manifest: `{manifest_id}`
- Parent artifact manifest SHA-256: `{parent_manifest_sha256}`
- Normalizer source SHA-256: `{normalizer_sha256}`
- 이 묶음은 시스템 정체를 제거한 파생 검토용이며 원본 evidence pack을 수정하지 않는다.

## 검토 순서

1. `expected_a_facts`를 정답 판정으로 자동 승격하지 말고, 순서가 보존된 기대 조건으로만 읽는다.
2. `observed_execution_a.tool_calls`에서 실제 도구 순서·인자·성공 여부를 확인한다.
3. 답변의 코드 주장은 `downstream_public_a`의 공개 본문으로만 대조한다. `omit`된 원문은 이 배열에 없다.
4. `supported_code_claims`는 허용 주장 목록이지 모델 답변의 자동 정답 판정이 아니다. 각 주장의 문자 span과 A 본문을 수동으로 대조한다.
5. 완료 실패, error, Node2/Node4 한도 소진을 분모에서 제외하지 않는다.
6. 두 검토자가 독립적으로 판정한 뒤 불일치 해소 기록을 남긴다. 정체 키는 모든 판정을 잠긴 뒤에만 연다.

## 파일럿 정규화 주의

- 동결 manifest의 `tool_call.1.*`와 `retention.1.*`은 첫 물리 호출을 뜻하는지,
  첫 관련 호출을 뜻하는지 사전에 명확히 정의되지 않았다.
- 따라서 이 파일럿의 단일 `strict_task_success`를 확정 점수로 공개하지 않는다.
- 민감도 분석이 필요하면 (a) 물리 순번을 그대로 적용한 결과와 (b) 같은 접두사의
  name/path/success 조건을 한 실제 호출이 모두 만족하는지 본 사후 관련-호출 결과를
  둘 다 기록한다. (b)는 반드시 **post-hoc sensitivity**라고 표시한다.
- 다음 confirmatory manifest에서는 ordinal 문자열 대신 명시적 call selector를 사용한다.

## A 권한 경계

- `observed_execution_a`는 raw memory의 코드 기록에서 다시 구성한 실행 사실이다.
- `downstream_public_a`는 같은 tool turn의 숨김 원문과 실제 `tool_result_content`가 exact slice로 일치한 경우만 있다.
- 이 자료는 답변 정확도를 자동 채점하지 않는다.
"""


def _copy_case_material(manifest, destination):
    """Copy only frozen synthetic material so reviewers need no source checkout."""

    material_root = destination / CASE_MATERIAL_DIRECTORY
    manifest_destination = material_root / "manifest.json"
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_raw_sha256 = _sha256_path(manifest.path)
    shutil.copyfile(manifest.path, manifest_destination)
    if _sha256_path(manifest_destination) != manifest_raw_sha256:
        raise ValueError("복사된 case manifest hash가 원본과 다릅니다.")
    for fixture in (*manifest.source_fixtures, *manifest.boundary_fixtures):
        source = (manifest.path.parent / fixture.path).resolve()
        target = material_root / Path(fixture.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        source_sha256 = _sha256_path(source)
        shutil.copyfile(source, target)
        if _sha256_path(target) != source_sha256:
            raise ValueError(f"복사된 fixture hash가 다릅니다: {fixture.path}")
    copied = load_manifest(manifest_destination)
    if copied.manifest_id != manifest.manifest_id or copied.sha256 != manifest.sha256:
        raise ValueError("복사된 case material이 frozen manifest와 다릅니다.")


def _write_artifact_manifest(
    output_dir,
    parent_manifest_sha256,
    normalizer_sha256,
):
    artifacts = []
    for path in sorted(output_dir.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.name == ARTIFACT_MANIFEST_FILENAME:
            continue
        raw = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": _sha256_bytes(raw),
                "byte_count": len(raw),
            }
        )
    return _write_json_atomic(
        {
            "schema_version": SCHEMA_VERSION,
            "bundle_version": REVIEW_BUNDLE_VERSION,
            "algorithm": "sha256(raw-bytes)",
            "provenance": {
                "parent_artifact_manifest_sha256": parent_manifest_sha256,
                "normalizer_source_sha256": normalizer_sha256,
            },
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
        },
        output_dir / ARTIFACT_MANIFEST_FILENAME,
    )


def _reject_forbidden_identity_keys(value):
    forbidden = {
        "model_name",
        "provider",
        "raw_artifact_sha256",
        "raw_memory_artifact",
        "run_id",
        "system_name",
    }
    if isinstance(value, dict):
        if forbidden.intersection(value):
            raise ValueError("review packet에 identity join key가 있습니다.")
        for nested in value.values():
            _reject_forbidden_identity_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_identity_keys(nested)


def verify_model_scale_review_bundle(
    directory,
    *,
    expected_artifact_manifest_sha256=None,
):
    """Verify the self-contained derived packet without the parent raw pack."""

    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("review bundle 경로는 폴더여야 합니다.")
    manifest_path = root / ARTIFACT_MANIFEST_FILENAME
    manifest_sha256 = _sha256_path(manifest_path)
    if expected_artifact_manifest_sha256 is not None and (
        not isinstance(expected_artifact_manifest_sha256, str)
        or _SHA256_PATTERN.fullmatch(expected_artifact_manifest_sha256) is None
        or expected_artifact_manifest_sha256 != manifest_sha256
    ):
        raise ValueError("외부에 고정한 review bundle hash와 다릅니다.")
    artifact_manifest = _read_json(manifest_path, "review artifact_manifest")
    artifacts = artifact_manifest.get("artifacts")
    if (
        artifact_manifest.get("algorithm") != "sha256(raw-bytes)"
        or not isinstance(artifacts, list)
        or artifact_manifest.get("artifact_count") != len(artifacts)
    ):
        raise ValueError("review artifact manifest 형식이 잘못됐습니다.")
    declared = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("review artifact 항목은 객체여야 합니다.")
        relative = artifact.get("path")
        if not isinstance(relative, str) or not relative or relative in declared:
            raise ValueError("review artifact path가 없거나 중복됐습니다.")
        declared.add(relative)
        path = (root / Path(relative)).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("review artifact가 bundle 밖을 가리킵니다.") from error
        if (
            not path.is_file()
            or path.stat().st_size != artifact.get("byte_count")
            or _sha256_path(path) != artifact.get("sha256")
        ):
            raise ValueError(f"review artifact hash/size가 다릅니다: {relative}")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != ARTIFACT_MANIFEST_FILENAME
    }
    if actual != declared:
        raise ValueError("review bundle의 선언 파일 집합과 실제 집합이 다릅니다.")

    packet = _read_json(root / REVIEW_PACKET_FILENAME, REVIEW_PACKET_FILENAME)
    items = packet.get("items")
    if (
        packet.get("publishable") is not False
        or packet.get("automatic_answer_grading") is not False
        or not isinstance(items, list)
        or packet.get("item_count") != len(items)
        or packet.get("items_sha256") != _canonical_json_sha256(items)
    ):
        raise ValueError("review packet의 상태 또는 item hash가 잘못됐습니다.")
    _reject_forbidden_identity_keys(packet)
    provenance = packet.get("provenance")
    manifest_provenance = artifact_manifest.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(manifest_provenance, dict):
        raise ValueError("review bundle provenance가 없습니다.")
    normalizer_path = root / NORMALIZER_SOURCE_FILENAME
    normalizer_sha256 = _sha256_path(normalizer_path)
    if (
        provenance.get("normalizer_source_sha256") != normalizer_sha256
        or manifest_provenance.get("normalizer_source_sha256")
        != normalizer_sha256
        or provenance.get("parent_artifact_manifest_sha256")
        != manifest_provenance.get("parent_artifact_manifest_sha256")
    ):
        raise ValueError("review bundle provenance hash가 다릅니다.")
    copied_manifest = load_manifest(
        root / CASE_MATERIAL_DIRECTORY / "manifest.json"
    )
    if (
        copied_manifest.manifest_id != provenance.get("manifest_id")
        or copied_manifest.sha256 != provenance.get("manifest_sha256")
    ):
        raise ValueError("review case material이 packet provenance와 다릅니다.")
    return {
        "artifact_manifest_sha256": manifest_sha256,
        "artifact_count": len(artifacts),
        "item_count": len(items),
        "items_sha256": packet["items_sha256"],
        "parent_artifact_manifest_sha256": provenance[
            "parent_artifact_manifest_sha256"
        ],
    }


def build_model_scale_review_bundle(
    evidence_pack,
    *,
    output_dir,
    manifest_path=DEFAULT_MODEL_CEILING_MANIFEST,
    expected_parent_manifest_sha256=None,
):
    """Create a separate, blinded review bundle without changing the source."""

    root = Path(evidence_pack).resolve()
    verification = verify_evidence_pack(root)
    parent_manifest_path = root / ARTIFACT_MANIFEST_FILENAME
    parent_manifest_sha256 = _sha256_path(parent_manifest_path)
    if expected_parent_manifest_sha256 is not None:
        if (
            not isinstance(expected_parent_manifest_sha256, str)
            or _SHA256_PATTERN.fullmatch(expected_parent_manifest_sha256) is None
            or expected_parent_manifest_sha256 != parent_manifest_sha256
        ):
            raise ValueError("외부에 고정한 parent artifact hash와 다릅니다.")
    normalizer_source = Path(__file__).resolve()
    normalizer_sha256 = _sha256_path(normalizer_source)
    if verification.get("artifact_manifest_sha256") != parent_manifest_sha256:
        raise ValueError("parent artifact manifest SHA-256 검증이 다릅니다.")

    manifest = load_manifest(manifest_path)
    protocol = _read_json(root / PROTOCOL_FILENAME, "protocol.json")
    source_tree_sha256 = _verify_experiment_source_snapshot(protocol)
    capture_document = _read_json(root / CAPTURE_FILENAME, "capture.json")
    blind_key = _read_json(root / BLIND_KEY_FILENAME, "blind_key.json")
    aliases = _validate_blind_key(blind_key, capture_document)
    declared_manifest = capture_document.get("manifest")
    if not isinstance(declared_manifest, dict) or (
        declared_manifest.get("manifest_id") != manifest.manifest_id
        or declared_manifest.get("manifest_sha256") != manifest.sha256
    ):
        raise ValueError("capture의 manifest가 입력 manifest와 다릅니다.")

    captures = capture_document.get("captures")
    key_items = blind_key.get("items")
    if not isinstance(captures, list) or not isinstance(key_items, list):
        raise ValueError("capture와 blind key items는 배열이어야 합니다.")
    key_by_run = {}
    for value in key_items:
        if not isinstance(value, dict):
            raise ValueError("blind key item은 객체여야 합니다.")
        run_id = value.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in key_by_run:
            raise ValueError("blind key run_id가 없거나 중복됐습니다.")
        key_by_run[run_id] = value

    case_by_id = {case.case_id: case for case in manifest.cases}
    packet_items = []
    seen_runs = set()
    seen_review_ids = set()
    for capture in captures:
        if not isinstance(capture, dict):
            raise ValueError("capture item은 JSON 객체여야 합니다.")
        run_id = capture.get("run_id")
        if not isinstance(run_id, str) or run_id in seen_runs:
            raise ValueError("capture run_id가 없거나 중복됐습니다.")
        seen_runs.add(run_id)
        key = key_by_run.get(run_id)
        if key is None or key.get("system_name") != capture.get("system_name"):
            raise ValueError("capture와 blind key의 시스템 연결이 다릅니다.")
        review_id = key.get("review_id")
        alias = key.get("blind_system_alias")
        if (
            not isinstance(review_id, str)
            or re.fullmatch(r"[0-9a-f]{16}", review_id) is None
            or review_id in seen_review_ids
            or not isinstance(alias, str)
            or aliases.get(capture.get("system_name")) != alias
        ):
            raise ValueError("blind review ID 또는 alias가 잘못됐습니다.")
        seen_review_ids.add(review_id)
        case_id = capture.get("case_id")
        case = case_by_id.get(case_id)
        if case is None:
            raise ValueError(f"manifest에 없는 case입니다: {case_id}")
        raw_path = _resolve_raw_path(root, capture)
        records = _read_jsonl(raw_path)
        observed, downstream = _execution_trace(records, capture)
        expected_memory = _expected_fixture_memory(manifest, case_id)
        if observed["fixture_memory"] != expected_memory:
            raise ValueError("raw fixture_memory가 frozen manifest와 다릅니다.")
        question = capture.get("evaluated_question")
        completed = capture.get("completed")
        if not isinstance(question, str) or not isinstance(completed, bool):
            raise ValueError("capture question/completed 형식이 잘못됐습니다.")
        answer = capture.get("answer")
        error = capture.get("error")
        if completed:
            if not isinstance(answer, str) or not answer.strip() or error is not None:
                raise ValueError("completed capture의 answer/error가 모순됩니다.")
        elif error is None:
            raise ValueError("미완료 capture에는 error가 필요합니다.")
        expected_question, expected_index, expected_turns = _expected_case_input(
            manifest,
            case_id,
        )
        if (
            capture.get("manifest_question") != manifest.questions[case_id]
            or question != expected_question
            or capture.get("evaluated_turn_index") != expected_index
            or capture.get("conversation_turns") != expected_turns
        ):
            raise ValueError("capture conversation이 frozen manifest와 다릅니다.")
        packet_items.append(
            {
                "review_id": review_id,
                "blind_system_alias": alias,
                "case_id": case_id,
                "question": question,
                "answer": answer,
                "completed": completed,
                "error": _blinded_error(error),
                "expected_a_facts": [
                    fact.to_dict() for fact in case.expected_a_facts
                ],
                "supported_code_claims": list(case.supported_code_claims),
                "observed_execution_a": observed,
                "downstream_public_a": downstream,
            }
        )

    if seen_runs != set(key_by_run):
        raise ValueError("capture와 blind key의 run 집합이 다릅니다.")
    packet_items.sort(key=lambda value: value["review_id"])
    destination = _prepare_output_directory(output_dir, root)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "bundle_version": REVIEW_BUNDLE_VERSION,
        "packet_status": "unscored_blind_review_ready",
        "publishable": False,
        "automatic_answer_grading": False,
        "provenance": {
            "parent_artifact_manifest_sha256": parent_manifest_sha256,
            "parent_evidence_pack_verified": True,
            "external_parent_pin_verified": (
                expected_parent_manifest_sha256 is not None
            ),
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "normalizer_source_sha256": normalizer_sha256,
            "experiment_source_tree_sha256": source_tree_sha256,
        },
        "item_count": len(packet_items),
        "items_sha256": _canonical_json_sha256(packet_items),
        "items": packet_items,
    }
    _reject_identity_leaks(packet, _identity_strings(capture_document))
    # Close the verify/read time-of-check gap before emitting the derived files.
    verify_evidence_pack(root)
    if _sha256_path(parent_manifest_path) != parent_manifest_sha256:
        raise ValueError("parent evidence pack이 파생 처리 중 변경됐습니다.")
    packet_path = _write_json_atomic(
        packet,
        destination / REVIEW_PACKET_FILENAME,
    )
    protocol_path = _write_text_atomic(
        _reviewer_protocol(
            parent_manifest_sha256,
            manifest.manifest_id,
            len(packet_items),
            normalizer_sha256,
        ),
        destination / REVIEWER_PROTOCOL_FILENAME,
    )
    _copy_case_material(manifest, destination)
    shutil.copyfile(
        normalizer_source,
        destination / NORMALIZER_SOURCE_FILENAME,
    )
    if (
        _sha256_path(destination / NORMALIZER_SOURCE_FILENAME)
        != normalizer_sha256
    ):
        raise ValueError("복사된 normalizer source hash가 다릅니다.")
    artifact_manifest_path = _write_artifact_manifest(
        destination,
        parent_manifest_sha256,
        normalizer_sha256,
    )
    return {
        "output_directory": destination,
        "review_packet_path": packet_path,
        "reviewer_protocol_path": protocol_path,
        "artifact_manifest_path": artifact_manifest_path,
        "packet": packet,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="검증된 model-scale evidence pack에서 blind review bundle을 만듭니다."
    )
    parser.add_argument("evidence_pack", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MODEL_CEILING_MANIFEST,
    )
    parser.add_argument(
        "--expected-parent-sha256",
        help="실험 직후 외부에 고정한 parent artifact_manifest SHA-256",
    )
    args = parser.parse_args(argv)
    try:
        result = build_model_scale_review_bundle(
            args.evidence_pack,
            output_dir=args.output_dir,
            manifest_path=args.manifest,
            expected_parent_manifest_sha256=args.expected_parent_sha256,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"review bundle 생성 실패: {error}", file=sys.stderr)
        return 1
    print(f"review bundle: {result['output_directory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
