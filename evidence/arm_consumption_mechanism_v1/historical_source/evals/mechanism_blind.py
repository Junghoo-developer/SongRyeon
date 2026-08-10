"""검증된 mechanism capture를 condition-metadata-masked 채점 묶음으로 만든다.

90개 case×seed unit에서 네 answer arm과 두 reviewer 적용 결과만 꺼낸다.
consumer draft는 이미 ``ar-consumer-rule`` answer이므로 ``shadow``를 별도
항목으로 복제하지 않는다. 실패·invalid·None도 ITT 분모에 남긴다.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import sys
import tempfile

from .mechanism_capture import (
    ANSWER_CONDITIONS,
    AR_CONSUMER_RULE,
    EVIDENCE_REVIEWER,
    MECHANISM_SEEDS,
    STYLE_PLACEBO_REVIEWER,
)
from .mechanism_packets import DEFAULT_SOURCE_MANIFEST_PATH, canonical_json_sha256
from .mechanism_verify import DEFAULT_RUN_PLAN_PATH, verify_capture
from .runner import PROJECT_DIRECTORY, load_manifest


SCHEMA_VERSION = 1
BUNDLE_ID = "songryeon-arm-consumption-mechanism-blind-v1"
BLIND_ITEM_COUNT = 540
BLIND_CHUNK_COUNT = 3
BLIND_CHUNK_SIZE = 180
BLIND_KEY_FILENAME = "blind_key.json"
PROVENANCE_FILENAME = "provenance.json"
RUBRIC_FILENAME = "SCORING_RUBRIC.md"

DEFAULT_CAPTURE_PATH = (
    PROJECT_DIRECTORY
    / ".tmp"
    / "evals"
    / "arm_consumption_mechanism_v1"
    / "capture.json"
)
DEFAULT_PACKET_PATH = (
    PROJECT_DIRECTORY
    / ".tmp"
    / "evals"
    / "arm_consumption_mechanism_inputs_v1"
    / "evidence_packets.json"
)
DEFAULT_OUTPUT_DIRECTORY = (
    PROJECT_DIRECTORY
    / ".tmp"
    / "evals"
    / "arm_consumption_mechanism_blind_v1"
)
DEFAULT_SCORING_RUBRIC_PATH = (
    Path(__file__).resolve().parent
    / "evidence_laundering_cases"
    / RUBRIC_FILENAME
)
FROZEN_SCORING_RUBRIC_SHA256 = (
    "9b753f530a73988724c32b34c1724fe0f05013ec907d97c0f3cd457d4e64ccf5"
)

STYLE_PLACEBO_ENFORCED = "style_placebo_enforced"
EVIDENCE_ENFORCED = "evidence_enforced"
BLIND_SOURCE_CONDITIONS = (
    *ANSWER_CONDITIONS,
    STYLE_PLACEBO_ENFORCED,
    EVIDENCE_ENFORCED,
)
_DERIVED_REVIEWER = {
    STYLE_PLACEBO_ENFORCED: STYLE_PLACEBO_REVIEWER,
    EVIDENCE_ENFORCED: EVIDENCE_REVIEWER,
}
_FAMILIES = {
    "declaration_enforcement",
    "import_invocation",
    "documentation_runtime",
    "action_report",
    "attribution_provenance",
}
_POLARITY_TAGS = {
    "negative_control": "negative",
    "positive_control": "positive",
}
_ITEM_KEYS = {
    "blind_id",
    "question",
    "answer",
    "error",
    "completed",
    "family",
    "polarity",
    "expected_a_facts",
    "supported_claims",
}
_KEY_ITEM_KEYS = {
    "blind_id",
    "seed",
    "case_id",
    "condition",
    "raw_artifact_sha256",
}
_FORBIDDEN_BLIND_FIELD_NAMES = {
    "condition",
    "conditions",
    "seed",
    "seeds",
    "order",
    "system",
    "systems",
    "system_name",
    "model",
    "model_name",
    "case_id",
    "packet_index",
    "raw_artifact_sha256",
}


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _serialized_json(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _read_json_object(path, label):
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"{label}는 JSON 파일이어야 합니다.")
    raw = resolved.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {constant}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}는 유효한 UTF-8 JSON이어야 합니다.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} 최상위 값은 객체여야 합니다.")
    return resolved, raw, value


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _require_exact_keys(value, keys, label):
    _require(isinstance(value, dict), f"{label}은 객체여야 합니다.")
    missing = sorted(keys - set(value))
    unknown = sorted(set(value) - keys)
    _require(
        not missing and not unknown,
        f"{label} 필드가 다릅니다. missing={missing}, unknown={unknown}",
    )


def _portable_path(path):
    resolved = Path(path).resolve(strict=True)
    try:
        return resolved.relative_to(PROJECT_DIRECTORY.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_raw_artifact(root, relative, label):
    _require(isinstance(relative, str) and relative, f"{label} path가 잘못됐습니다.")
    portable = PurePosixPath(relative)
    _require(
        not portable.is_absolute()
        and relative == portable.as_posix()
        and all(part not in {"", ".", ".."} for part in portable.parts),
        f"{label} path는 안전한 POSIX 상대경로여야 합니다.",
    )
    candidate = (root / Path(*portable.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label}가 capture 폴더 밖을 가리킵니다.") from error
    _require(candidate.is_file(), f"{label}는 파일이어야 합니다.")
    return candidate


def _case_labels(case):
    families = _FAMILIES.intersection(case.tags)
    polarities = set(_POLARITY_TAGS).intersection(case.tags)
    _require(len(families) == 1, f"{case.case_id} family tag는 하나여야 합니다.")
    _require(len(polarities) == 1, f"{case.case_id} polarity tag는 하나여야 합니다.")
    return next(iter(families)), _POLARITY_TAGS[next(iter(polarities))]


def _call_answer(call, label):
    _require(isinstance(call, dict), f"{label} call은 객체여야 합니다.")
    status = call.get("status")
    _require(isinstance(status, str) and status, f"{label} status가 필요합니다.")
    output = call.get("output")
    if status == "valid":
        _require(isinstance(output, dict), f"{label} valid output이 없습니다.")
        answer = output.get("answer")
        _require(
            isinstance(answer, str) and answer.strip(),
            f"{label} valid answer가 비었습니다.",
        )
        return answer, None, True
    _require(output is None, f"{label} invalid call에 output이 남았습니다.")
    return None, "output_unavailable", False


def _derived_answer(unit, condition):
    derived = unit.get("derived_outputs")
    _require(isinstance(derived, dict), "raw unit derived_outputs가 필요합니다.")
    value = derived.get(condition)
    if isinstance(value, str) and value.strip():
        return value, None, True
    _require(value is None, f"{condition} 파생 출력 형식이 잘못됐습니다.")

    consumer = unit["answer_calls"][AR_CONSUMER_RULE]
    if not isinstance(consumer.get("output"), dict):
        status = consumer.get("status")
    else:
        reviewer = unit["reviewer_calls"][_DERIVED_REVIEWER[condition]]
        status = reviewer.get("status")
    _require(isinstance(status, str) and status, "파생 실패 status가 필요합니다.")
    return None, "output_unavailable", False


def _source_rows(capture_path, manifest):
    capture_file, capture_raw, capture = _read_json_object(
        capture_path,
        "mechanism capture",
    )
    _require(capture.get("capture_status") == "complete", "capture가 complete가 아닙니다.")
    _require(capture.get("planned_unit_count") == 90, "planned unit은 90개여야 합니다.")
    _require(capture.get("completed_unit_count") == 90, "completed unit은 90개여야 합니다.")
    artifacts = capture.get("raw_artifacts")
    _require(isinstance(artifacts, list) and len(artifacts) == 90, "raw artifact는 90개여야 합니다.")

    case_by_index = dict(enumerate(manifest.cases))
    expected_units = {
        (seed, packet_index)
        for seed in MECHANISM_SEEDS
        for packet_index in case_by_index
    }
    seen_units = set()
    rows = []
    root = capture_file.parent.resolve(strict=True)

    for artifact_index, artifact in enumerate(artifacts):
        label = f"raw_artifacts[{artifact_index}]"
        _require(isinstance(artifact, dict), f"{label}은 객체여야 합니다.")
        unit_key = (artifact.get("seed"), artifact.get("packet_index"))
        _require(unit_key in expected_units, f"{label} unit key가 예정에 없습니다.")
        _require(unit_key not in seen_units, f"{label} unit key가 중복됐습니다.")
        seen_units.add(unit_key)

        raw_path = _resolve_raw_artifact(root, artifact.get("path"), label)
        raw_bytes = raw_path.read_bytes()
        raw_sha256 = _sha256_bytes(raw_bytes)
        _require(artifact.get("byte_count") == len(raw_bytes), f"{label} byte_count가 다릅니다.")
        _require(artifact.get("sha256") == raw_sha256, f"{label} SHA-256이 다릅니다.")
        try:
            unit = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"{label} raw unit JSON이 잘못됐습니다.") from error
        _require(isinstance(unit, dict), f"{label} raw unit은 객체여야 합니다.")

        seed, packet_index = unit_key
        case = case_by_index[packet_index]
        _require(unit.get("seed") == seed, f"{label} seed가 다릅니다.")
        _require(unit.get("packet_index") == packet_index, f"{label} packet index가 다릅니다.")
        _require(
            unit.get("case_id") == artifact.get("case_id") == case.case_id,
            f"{label} case ID가 다릅니다.",
        )
        answer_calls = unit.get("answer_calls")
        reviewer_calls = unit.get("reviewer_calls")
        _require(
            isinstance(answer_calls, dict)
            and set(answer_calls) == set(ANSWER_CONDITIONS),
            f"{label} answer call grid가 다릅니다.",
        )
        _require(isinstance(reviewer_calls, dict), f"{label} reviewer_calls가 필요합니다.")

        family, polarity = _case_labels(case)
        common = {
            "question": manifest.questions[case.case_id],
            "family": family,
            "polarity": polarity,
            "expected_a_facts": [fact.to_dict() for fact in case.expected_a_facts],
            "supported_claims": list(case.supported_code_claims),
        }
        for condition in ANSWER_CONDITIONS:
            answer, error, completed = _call_answer(
                answer_calls[condition],
                f"{label}.{condition}",
            )
            rows.append(
                {
                    "identity": {
                        "seed": seed,
                        "case_id": case.case_id,
                        "condition": condition,
                        "raw_artifact_sha256": raw_sha256,
                    },
                    "item": {
                        **common,
                        "answer": answer,
                        "error": error,
                        "completed": completed,
                    },
                }
            )
        for condition in (STYLE_PLACEBO_ENFORCED, EVIDENCE_ENFORCED):
            answer, error, completed = _derived_answer(unit, condition)
            rows.append(
                {
                    "identity": {
                        "seed": seed,
                        "case_id": case.case_id,
                        "condition": condition,
                        "raw_artifact_sha256": raw_sha256,
                    },
                    "item": {
                        **common,
                        "answer": answer,
                        "error": error,
                        "completed": completed,
                    },
                }
            )

    _require(seen_units == expected_units, "30×3 unit grid가 완전하지 않습니다.")
    _require(len(rows) == BLIND_ITEM_COUNT, "blind source row는 540개여야 합니다.")
    return capture_file, capture_raw, rows


def _blind_documents(rows, secret, rubric_sha256):
    _require(isinstance(secret, bytes) and len(secret) >= 32, "blinding secret은 32바이트 이상이어야 합니다.")
    ranked = []
    blind_ids = set()
    for row in rows:
        identity_text = _canonical_json(row["identity"]).encode("utf-8")
        rank = hmac.new(secret, identity_text, hashlib.sha256).hexdigest()
        blind_id = f"blind-{rank}"
        _require(blind_id not in blind_ids, "blind ID 충돌이 발생했습니다.")
        blind_ids.add(blind_id)
        ranked.append(
            (
                rank,
                {
                    "blind_id": blind_id,
                    **row["item"],
                },
                {
                    "blind_id": blind_id,
                    **row["identity"],
                },
            )
        )
    ranked.sort(key=lambda value: value[0])
    items = [value[1] for value in ranked]
    key_items = [value[2] for value in ranked]

    packets = []
    for chunk_index in range(BLIND_CHUNK_COUNT):
        start = chunk_index * BLIND_CHUNK_SIZE
        chunk_items = items[start : start + BLIND_CHUNK_SIZE]
        core = {
            "schema_version": SCHEMA_VERSION,
            "bundle_id": BUNDLE_ID,
            "packet_status": "unscored_condition_metadata_masked",
            "publishable": False,
            "chunk_index": chunk_index + 1,
            "chunk_count": BLIND_CHUNK_COUNT,
            "item_count": len(chunk_items),
            "scoring_rubric_sha256": rubric_sha256,
            "items": chunk_items,
        }
        packets.append({**core, "packet_sha256": canonical_json_sha256(core)})

    key_core = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "warning": "블라인드 채점과 score hash 고정 전에는 이 파일을 열지 마십시오.",
        "blinding_method": "HMAC-SHA256(identity), ascending digest order",
        "blinding_secret_hex": secret.hex(),
        "item_count": len(key_items),
        "items": key_items,
    }
    key = {**key_core, "key_sha256": canonical_json_sha256(key_core)}
    return packets, key


def _forbidden_field_paths(value, path="$"):
    found = []
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _FORBIDDEN_BLIND_FIELD_NAMES:
                found.append(f"{path}.{key}")
            found.extend(_forbidden_field_paths(nested, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_forbidden_field_paths(nested, f"{path}[{index}]"))
    return found


def _validate_packet_documents(packets):
    _require(isinstance(packets, list) and len(packets) == 3, "blind packet은 3개여야 합니다.")
    seen_ids = set()
    total = 0
    completed_count = 0
    packet_keys = {
        "schema_version",
        "bundle_id",
        "packet_status",
        "publishable",
        "chunk_index",
        "chunk_count",
        "item_count",
        "scoring_rubric_sha256",
        "items",
        "packet_sha256",
    }
    for expected_index, packet in enumerate(packets, start=1):
        _require_exact_keys(packet, packet_keys, f"blind packet {expected_index}")
        core = {key: value for key, value in packet.items() if key != "packet_sha256"}
        _require(packet["packet_sha256"] == canonical_json_sha256(core), "blind packet self-hash가 다릅니다.")
        _require(packet["schema_version"] == SCHEMA_VERSION, "blind packet schema가 다릅니다.")
        _require(packet["bundle_id"] == BUNDLE_ID, "blind packet bundle ID가 다릅니다.")
        _require(packet["packet_status"] == "unscored_condition_metadata_masked", "blind packet status가 다릅니다.")
        _require(packet["publishable"] is False, "미채점 packet은 publishable=false여야 합니다.")
        _require(packet["chunk_index"] == expected_index, "blind packet chunk index가 다릅니다.")
        _require(packet["chunk_count"] == 3, "blind packet chunk count가 다릅니다.")
        items = packet["items"]
        _require(isinstance(items, list) and len(items) == 180, "각 blind packet은 180 items여야 합니다.")
        _require(packet["item_count"] == 180, "blind packet item_count가 다릅니다.")
        forbidden = _forbidden_field_paths(packet)
        _require(not forbidden, f"blind packet에 금지 metadata field가 있습니다: {forbidden[:3]}")

        for item_index, item in enumerate(items):
            label = f"blind packet {expected_index}.items[{item_index}]"
            _require_exact_keys(item, _ITEM_KEYS, label)
            blind_id = item["blind_id"]
            _require(
                isinstance(blind_id, str)
                and blind_id.startswith("blind-")
                and len(blind_id) == 70,
                f"{label} blind ID가 잘못됐습니다.",
            )
            _require(blind_id not in seen_ids, f"{label} blind ID가 중복됐습니다.")
            seen_ids.add(blind_id)
            _require(isinstance(item["question"], str) and item["question"].strip(), f"{label} question이 비었습니다.")
            _require(item["family"] in _FAMILIES, f"{label} family가 잘못됐습니다.")
            _require(item["polarity"] in {"negative", "positive"}, f"{label} polarity가 잘못됐습니다.")
            _require(isinstance(item["expected_a_facts"], list), f"{label} expected_a_facts가 배열이 아닙니다.")
            _require(isinstance(item["supported_claims"], list), f"{label} supported_claims가 배열이 아닙니다.")
            _require(isinstance(item["completed"], bool), f"{label} completed가 bool이 아닙니다.")
            if item["completed"]:
                _require(isinstance(item["answer"], str) and item["answer"].strip(), f"{label} answer가 비었습니다.")
                _require(item["error"] is None, f"{label} completed/error가 모순됩니다.")
                completed_count += 1
            else:
                _require(item["answer"] is None, f"{label} incomplete answer는 null이어야 합니다.")
                _require(isinstance(item["error"], str) and item["error"], f"{label} incomplete error가 필요합니다.")
        total += len(items)
    _require(total == BLIND_ITEM_COUNT, "blind item 총수는 540이어야 합니다.")
    return {"item_count": total, "completed_item_count": completed_count, "incomplete_item_count": total - completed_count}


def _prepare_output_directory(output_dir):
    destination = Path(output_dir).resolve()
    if destination.exists():
        _require(destination.is_dir(), "output_dir은 폴더여야 합니다.")
        _require(not any(destination.iterdir()), "비어 있지 않은 output_dir은 덮어쓰지 않습니다.")
    else:
        destination.mkdir(parents=True)
    return destination


def _write_new_file(path, content):
    _require(not path.exists(), f"기존 출력 파일은 덮어쓰지 않습니다: {path.name}")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _artifact(path, self_hash_name, self_hash):
    raw = path.read_bytes()
    return {
        "path": path.name,
        "byte_count": len(raw),
        "file_sha256": _sha256_bytes(raw),
        self_hash_name: self_hash,
    }


def _provenance_core(
    *,
    capture_path,
    capture_raw,
    packet_path,
    run_plan_path,
    manifest,
    rubric_path,
    rubric_raw,
    packet_artifacts,
    key_artifact,
    secret,
    counts,
    verification,
):
    packet_file = Path(packet_path).resolve(strict=True)
    run_plan_file = Path(run_plan_path).resolve(strict=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "study_status": "unscored_condition_metadata_masked",
        "publishable": False,
        "warning": "blind_key.json은 모든 채점과 score hash 고정 뒤에만 여십시오.",
        "capture": {
            "path": _portable_path(capture_path),
            "file_sha256": _sha256_bytes(capture_raw),
            "verified_unit_count": verification["unit_count"],
        },
        "evidence_packets": {
            "path": _portable_path(packet_file),
            "file_sha256": _sha256_bytes(packet_file.read_bytes()),
            "packet_set_sha256": verification["packet_set_sha256"],
        },
        "run_plan": {
            "path": _portable_path(run_plan_file),
            "file_sha256": _sha256_bytes(run_plan_file.read_bytes()),
        },
        "derivation_source": {
            "path": _portable_path(__file__),
            "byte_count": Path(__file__).resolve(strict=True).stat().st_size,
            "file_sha256": _sha256_bytes(
                Path(__file__).resolve(strict=True).read_bytes()
            ),
        },
        "manifest": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "case_count": len(manifest.cases),
        },
        "scoring_rubric": {
            "source_path": _portable_path(rubric_path),
            "copied_path": RUBRIC_FILENAME,
            "byte_count": len(rubric_raw),
            "file_sha256": _sha256_bytes(rubric_raw),
        },
        "blinding": {
            "method": "HMAC-SHA256(identity), ascending digest order",
            "secret_sha256_commitment": _sha256_bytes(secret),
            "metadata_masking_scope": "condition, seed, source order, system/model",
        },
        "chunk_count": BLIND_CHUNK_COUNT,
        "chunk_size": BLIND_CHUNK_SIZE,
        **counts,
        "blind_packet_files": packet_artifacts,
        "blind_key_file": key_artifact,
    }


def write_mechanism_blind_bundle(
    *,
    capture_path=DEFAULT_CAPTURE_PATH,
    packet_path=DEFAULT_PACKET_PATH,
    output_dir=DEFAULT_OUTPUT_DIRECTORY,
    run_plan_path=DEFAULT_RUN_PLAN_PATH,
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
    scoring_rubric_path=DEFAULT_SCORING_RUBRIC_PATH,
    blinding_secret=None,
):
    """검증된 90-unit capture에서 3×180 blind bundle을 새 폴더에 쓴다."""

    verification = verify_capture(
        capture_path,
        packet_path,
        run_plan_path=run_plan_path,
        manifest_path=manifest_path,
    )
    _require(verification["unit_count"] == 90, "검증된 capture unit은 90개여야 합니다.")
    manifest = load_manifest(manifest_path)
    capture_file, capture_raw, rows = _source_rows(capture_path, manifest)

    rubric_file = Path(scoring_rubric_path).resolve(strict=True)
    rubric_raw = rubric_file.read_bytes()
    rubric_sha256 = _sha256_bytes(rubric_raw)
    _require(
        rubric_sha256 == FROZEN_SCORING_RUBRIC_SHA256,
        "SCORING_RUBRIC.md가 동결 hash와 다릅니다.",
    )
    secret = secrets.token_bytes(32) if blinding_secret is None else blinding_secret
    packets, key = _blind_documents(rows, secret, rubric_sha256)
    counts = _validate_packet_documents(packets)

    destination = _prepare_output_directory(output_dir)
    _write_new_file(destination / RUBRIC_FILENAME, rubric_raw)
    packet_artifacts = []
    for index, packet in enumerate(packets, start=1):
        path = destination / f"blind_packet_{index:03d}.json"
        _write_new_file(path, _serialized_json(packet))
        packet_artifacts.append(
            _artifact(path, "packet_sha256", packet["packet_sha256"])
        )
    key_path = destination / BLIND_KEY_FILENAME
    _write_new_file(key_path, _serialized_json(key))
    key_artifact = _artifact(key_path, "key_sha256", key["key_sha256"])

    provenance_core = _provenance_core(
        capture_path=capture_file,
        capture_raw=capture_raw,
        packet_path=packet_path,
        run_plan_path=run_plan_path,
        manifest=manifest,
        rubric_path=rubric_file,
        rubric_raw=rubric_raw,
        packet_artifacts=packet_artifacts,
        key_artifact=key_artifact,
        secret=secret,
        counts=counts,
        verification=verification,
    )
    provenance = {
        **provenance_core,
        "provenance_sha256": canonical_json_sha256(provenance_core),
    }
    _write_new_file(
        destination / PROVENANCE_FILENAME,
        _serialized_json(provenance),
    )
    summary = validate_mechanism_blind_bundle(
        destination,
        capture_path=capture_path,
        packet_path=packet_path,
        run_plan_path=run_plan_path,
        manifest_path=manifest_path,
        scoring_rubric_path=scoring_rubric_path,
    )
    return destination, summary


def validate_mechanism_blind_bundle(
    output_dir,
    *,
    capture_path=DEFAULT_CAPTURE_PATH,
    packet_path=DEFAULT_PACKET_PATH,
    run_plan_path=DEFAULT_RUN_PLAN_PATH,
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
    scoring_rubric_path=DEFAULT_SCORING_RUBRIC_PATH,
):
    """blind packet·key·provenance를 source capture에서 완전히 재생 검증한다."""

    root = Path(output_dir).resolve(strict=True)
    _require(root.is_dir(), "blind bundle output은 폴더여야 합니다.")
    expected_names = {
        RUBRIC_FILENAME,
        BLIND_KEY_FILENAME,
        PROVENANCE_FILENAME,
        *(f"blind_packet_{index:03d}.json" for index in range(1, 4)),
    }
    _require({path.name for path in root.iterdir()} == expected_names, "blind bundle 파일 집합이 다릅니다.")

    verification = verify_capture(
        capture_path,
        packet_path,
        run_plan_path=run_plan_path,
        manifest_path=manifest_path,
    )
    manifest = load_manifest(manifest_path)
    capture_file, capture_raw, rows = _source_rows(capture_path, manifest)
    rubric_file = Path(scoring_rubric_path).resolve(strict=True)
    rubric_raw = rubric_file.read_bytes()
    _require(_sha256_bytes(rubric_raw) == FROZEN_SCORING_RUBRIC_SHA256, "source rubric hash가 다릅니다.")
    _require((root / RUBRIC_FILENAME).read_bytes() == rubric_raw, "복사된 scoring rubric이 다릅니다.")

    _, _, key = _read_json_object(root / BLIND_KEY_FILENAME, "blind key")
    key_keys = {
        "schema_version",
        "bundle_id",
        "warning",
        "blinding_method",
        "blinding_secret_hex",
        "item_count",
        "items",
        "key_sha256",
    }
    _require_exact_keys(key, key_keys, "blind key")
    key_core = {name: value for name, value in key.items() if name != "key_sha256"}
    _require(key["key_sha256"] == canonical_json_sha256(key_core), "blind key self-hash가 다릅니다.")
    try:
        secret = bytes.fromhex(key["blinding_secret_hex"])
    except (TypeError, ValueError) as error:
        raise ValueError("blind key secret 형식이 잘못됐습니다.") from error
    _require(len(secret) >= 32, "blind key secret은 32바이트 이상이어야 합니다.")
    _require(key["item_count"] == 540 and isinstance(key["items"], list), "blind key item 수가 다릅니다.")
    for index, item in enumerate(key["items"]):
        _require_exact_keys(item, _KEY_ITEM_KEYS, f"blind key.items[{index}]")

    packets = []
    for index in range(1, 4):
        _, _, packet = _read_json_object(
            root / f"blind_packet_{index:03d}.json",
            f"blind packet {index}",
        )
        packets.append(packet)
    counts = _validate_packet_documents(packets)
    expected_packets, expected_key = _blind_documents(
        rows,
        secret,
        FROZEN_SCORING_RUBRIC_SHA256,
    )
    _require(packets == expected_packets, "blind packets이 source capture 재생 결과와 다릅니다.")
    _require(key == expected_key, "blind key가 source identity 재생 결과와 다릅니다.")

    packet_artifacts = [
        _artifact(
            root / f"blind_packet_{index:03d}.json",
            "packet_sha256",
            packets[index - 1]["packet_sha256"],
        )
        for index in range(1, 4)
    ]
    key_artifact = _artifact(
        root / BLIND_KEY_FILENAME,
        "key_sha256",
        key["key_sha256"],
    )
    _, _, provenance = _read_json_object(root / PROVENANCE_FILENAME, "provenance")
    provenance_core = _provenance_core(
        capture_path=capture_file,
        capture_raw=capture_raw,
        packet_path=packet_path,
        run_plan_path=run_plan_path,
        manifest=manifest,
        rubric_path=rubric_file,
        rubric_raw=rubric_raw,
        packet_artifacts=packet_artifacts,
        key_artifact=key_artifact,
        secret=secret,
        counts=counts,
        verification=verification,
    )
    expected_provenance = {
        **provenance_core,
        "provenance_sha256": canonical_json_sha256(provenance_core),
    }
    _require(provenance == expected_provenance, "provenance가 source와 file hash에서 재생되지 않습니다.")
    return {
        "bundle_id": BUNDLE_ID,
        **counts,
        "chunk_count": 3,
        "chunk_size": 180,
        "packet_file_sha256": [entry["file_sha256"] for entry in packet_artifacts],
        "key_file_sha256": key_artifact["file_sha256"],
        "key_sha256": key["key_sha256"],
        "provenance_file_sha256": _sha256_bytes((root / PROVENANCE_FILENAME).read_bytes()),
        "provenance_sha256": provenance["provenance_sha256"],
        "rubric_file_sha256": FROZEN_SCORING_RUBRIC_SHA256,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        description="검증된 mechanism capture에서 3×180 blind review bundle을 만듭니다."
    )
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE_PATH)
    parser.add_argument("--packets", type=Path, default=DEFAULT_PACKET_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parser.add_argument("--run-plan", type=Path, default=DEFAULT_RUN_PLAN_PATH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST_PATH)
    parser.add_argument("--scoring-rubric", type=Path, default=DEFAULT_SCORING_RUBRIC_PATH)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        output_dir, summary = write_mechanism_blind_bundle(
            capture_path=args.capture,
            packet_path=args.packets,
            output_dir=args.output_dir,
            run_plan_path=args.run_plan,
            manifest_path=args.manifest,
            scoring_rubric_path=args.scoring_rubric,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"mechanism blind bundle 생성 중단: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print(f"저장: {output_dir}")
    print("주의: blind_key.json은 채점과 score hash 고정 뒤에만 여십시오.")
    return 0


__all__ = [
    "BLIND_CHUNK_COUNT",
    "BLIND_CHUNK_SIZE",
    "BLIND_ITEM_COUNT",
    "BUNDLE_ID",
    "DEFAULT_CAPTURE_PATH",
    "DEFAULT_OUTPUT_DIRECTORY",
    "DEFAULT_PACKET_PATH",
    "validate_mechanism_blind_bundle",
    "write_mechanism_blind_bundle",
]


if __name__ == "__main__":
    raise SystemExit(main())
