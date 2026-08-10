"""Validate and lock blind scores for the ARM-consumption mechanism study.

This module deliberately reconstructs score coverage from the three public
blind packets.  It never reads ``blind_key.json`` or condition mappings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping

from .mechanism_blind import (
    BLIND_CHUNK_COUNT,
    BLIND_CHUNK_SIZE,
    BLIND_ITEM_COUNT,
    BUNDLE_ID,
)
from .mechanism_packets import canonical_json_sha256


SCHEMA_VERSION = 1
SCORE_LOCK_FILENAME = "score_lock.json"
SCORER_TYPE = "blind_ai_preliminary"
PACKET_FILENAMES = tuple(
    f"blind_packet_{index:03d}.json"
    for index in range(1, BLIND_CHUNK_COUNT + 1)
)
SCORE_FILENAMES = tuple(
    f"scores-chunk-{index}.json"
    for index in range(1, BLIND_CHUNK_COUNT + 1)
)

_PACKET_KEYS = {
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
_PACKET_ITEM_KEYS = {
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
_PACKET_FORBIDDEN_FIELD_NAMES = {
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
_FAMILIES = {
    "declaration_enforcement",
    "import_invocation",
    "documentation_runtime",
    "action_report",
    "attribution_provenance",
}
_SCORE_DOCUMENT_KEYS = {
    "schema_version",
    "bundle_id",
    "chunk_number",
    "scorer_type",
    "item_count",
    "items",
}
_SCORE_ROW_KEYS = {
    "blind_id",
    "direct_answer",
    "answer_complete",
    "unsupported_atomic_claim_count",
    "no_unsupported_claims",
    "evidence_laundering",
    "negative_correction",
    "positive_recognized",
    "semantic_grounded_success",
    "notes",
}
_PROVENANCE_KEYS = {
    "schema_version",
    "bundle_id",
    "study_status",
    "publishable",
    "warning",
    "capture",
    "evidence_packets",
    "run_plan",
    "derivation_source",
    "manifest",
    "scoring_rubric",
    "blinding",
    "chunk_count",
    "chunk_size",
    "item_count",
    "completed_item_count",
    "incomplete_item_count",
    "blind_packet_files",
    "blind_key_file",
    "provenance_sha256",
}
_LOCK_KEYS = {
    "schema_version",
    "packet_id",
    "blind_packet_sha256",
    "provenance_sha256",
    "score_file_sha256",
    "validated_item_count",
    "validated_unique_blind_id_count",
    "semantic_grounded_success_count_before_unblinding",
    "scoring_status",
    "scorer_type",
}
_BLIND_ID_PATTERN = re.compile(r"blind-[0-9a-f]{64}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_exact_keys(
    value: Any,
    expected: set[str],
    label: str,
) -> None:
    _require(isinstance(value, dict), f"{label} must be an object")
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    _require(
        not missing and not unknown,
        f"{label} has the wrong fields: missing={missing}, unknown={unknown}",
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _serialized_json(value: Mapping[str, Any]) -> bytes:
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


def _read_json_object(
    path: Path,
    label: str,
) -> tuple[Path, bytes, dict[str, Any]]:
    resolved = Path(path).resolve(strict=True)
    _require(resolved.is_file(), f"{label} must be a file: {resolved}")
    payload = resolved.read_bytes()

    def reject_duplicate_keys(pairs):
        value = {}
        for key, nested in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = nested
        return value

    try:
        value = json.loads(
            payload.decode("utf-8"),
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {constant}")
            ),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{label} must be a strict UTF-8 JSON object") from error
    _require(isinstance(value, dict), f"{label} must be a JSON object")
    return resolved, payload, value


def _resolve_bundle_directory(bundle_dir: Path) -> Path:
    root = Path(bundle_dir).resolve(strict=True)
    _require(root.is_dir(), f"bundle must be a directory: {root}")
    return root


def _normalized_field_name(value: Any) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _forbidden_field_paths(
    value: Any,
    forbidden_names: set[str],
    *,
    path: str = "$",
) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if _normalized_field_name(key) in forbidden_names:
                found.append(f"{path}.{key}")
            found.extend(
                _forbidden_field_paths(
                    nested,
                    forbidden_names,
                    path=f"{path}.{key}",
                )
            )
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(
                _forbidden_field_paths(
                    nested,
                    forbidden_names,
                    path=f"{path}[{index}]",
                )
            )
    return found


def _is_score_metadata_field(value: Any) -> bool:
    normalized = _normalized_field_name(value)
    parts = set(normalized.split("_"))
    return bool(
        parts.intersection(
            {"condition", "conditions", "seed", "seeds", "key", "keys"}
        )
        or normalized
        in {
            "case_id",
            "case_ids",
            "packet_index",
            "raw_artifact",
            "raw_artifact_sha256",
            "source_identity",
            "blinding_secret",
            "blinding_secret_hex",
        }
        or normalized.startswith("blind_key")
        or normalized.startswith("blinding_key")
    )


def _score_metadata_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if _is_score_metadata_field(key):
                found.append(f"{path}.{key}")
            found.extend(_score_metadata_paths(nested, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_score_metadata_paths(nested, f"{path}[{index}]"))
    return found


def _binary(value: Any, label: str) -> int:
    _require(type(value) is int and value in (0, 1), f"{label} must be 0 or 1")
    return value


def _nullable_binary(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _binary(value, label)


def _validate_packet_item(item: Any, label: str) -> dict[str, Any]:
    _require_exact_keys(item, _PACKET_ITEM_KEYS, label)
    blind_id = item["blind_id"]
    _require(
        isinstance(blind_id, str) and _BLIND_ID_PATTERN.fullmatch(blind_id),
        f"{label}.blind_id is invalid",
    )
    _require(
        isinstance(item["question"], str) and item["question"].strip(),
        f"{label}.question must be non-empty",
    )
    _require(item["family"] in _FAMILIES, f"{label}.family is invalid")
    _require(
        item["polarity"] in {"negative", "positive"},
        f"{label}.polarity is invalid",
    )
    _require(
        isinstance(item["expected_a_facts"], list),
        f"{label}.expected_a_facts must be an array",
    )
    _require(
        isinstance(item["supported_claims"], list),
        f"{label}.supported_claims must be an array",
    )
    _require(type(item["completed"]) is bool, f"{label}.completed must be boolean")
    if item["completed"]:
        _require(
            isinstance(item["answer"], str) and item["answer"].strip(),
            f"{label}.answer must be non-empty when completed",
        )
        _require(item["error"] is None, f"{label}.error must be null when completed")
    else:
        _require(item["answer"] is None, f"{label}.answer must be null when incomplete")
        _require(
            isinstance(item["error"], str) and item["error"],
            f"{label}.error must be non-empty when incomplete",
        )
    return item


def _load_blind_packets(root: Path) -> dict[str, Any]:
    discovered = {path.name for path in root.glob("blind_packet_*.json")}
    _require(
        discovered == set(PACKET_FILENAMES),
        "bundle must contain exactly blind_packet_001.json through blind_packet_003.json",
    )

    ids_by_chunk: list[list[str]] = []
    metadata_by_id: dict[str, dict[str, Any]] = {}
    packet_file_hashes: dict[str, str] = {}
    packet_artifacts: list[dict[str, Any]] = []
    completed_count = 0
    rubric_sha256: str | None = None

    for expected_index, filename in enumerate(PACKET_FILENAMES, start=1):
        path, payload, packet = _read_json_object(root / filename, f"blind packet {expected_index}")
        _require_exact_keys(packet, _PACKET_KEYS, f"blind packet {expected_index}")
        forbidden = _forbidden_field_paths(packet, _PACKET_FORBIDDEN_FIELD_NAMES)
        _require(
            not forbidden,
            f"blind packet contains forbidden metadata: {forbidden[:3]}",
        )

        core = {key: value for key, value in packet.items() if key != "packet_sha256"}
        _require(
            packet["packet_sha256"] == canonical_json_sha256(core),
            f"{filename} packet_sha256 does not match its content",
        )
        _require(
            type(packet["schema_version"]) is int
            and packet["schema_version"] == SCHEMA_VERSION,
            f"{filename} schema_version is invalid",
        )
        _require(packet["bundle_id"] == BUNDLE_ID, f"{filename} bundle_id is invalid")
        _require(
            packet["packet_status"] == "unscored_condition_metadata_masked",
            f"{filename} packet_status is invalid",
        )
        _require(packet["publishable"] is False, f"{filename} publishable must be false")
        _require(
            type(packet["chunk_index"]) is int and packet["chunk_index"] == expected_index,
            f"{filename} chunk_index is invalid",
        )
        _require(
            type(packet["chunk_count"]) is int
            and packet["chunk_count"] == BLIND_CHUNK_COUNT,
            f"{filename} chunk_count is invalid",
        )
        _require(
            type(packet["item_count"]) is int
            and packet["item_count"] == BLIND_CHUNK_SIZE,
            f"{filename} item_count is invalid",
        )
        _require(
            isinstance(packet["items"], list)
            and len(packet["items"]) == BLIND_CHUNK_SIZE,
            f"{filename} must contain exactly {BLIND_CHUNK_SIZE} items",
        )
        _require(
            isinstance(packet["scoring_rubric_sha256"], str)
            and _SHA256_PATTERN.fullmatch(packet["scoring_rubric_sha256"]),
            f"{filename} scoring_rubric_sha256 is invalid",
        )
        if rubric_sha256 is None:
            rubric_sha256 = packet["scoring_rubric_sha256"]
        _require(
            packet["scoring_rubric_sha256"] == rubric_sha256,
            "blind packet chunks disagree on scoring_rubric_sha256",
        )

        chunk_ids: list[str] = []
        for item_index, raw_item in enumerate(packet["items"]):
            label = f"{filename}.items[{item_index}]"
            item = _validate_packet_item(raw_item, label)
            blind_id = item["blind_id"]
            _require(
                blind_id not in metadata_by_id,
                f"blind packet contains duplicate blind_id: {blind_id}",
            )
            metadata_by_id[blind_id] = {
                "polarity": item["polarity"],
                "completed": item["completed"],
            }
            chunk_ids.append(blind_id)
            completed_count += int(item["completed"])
        ids_by_chunk.append(chunk_ids)

        file_sha256 = _sha256_bytes(payload)
        packet_file_hashes[filename] = file_sha256
        packet_artifacts.append(
            {
                "path": path.name,
                "byte_count": len(payload),
                "file_sha256": file_sha256,
                "packet_sha256": packet["packet_sha256"],
            }
        )

    _require(
        len(metadata_by_id) == BLIND_ITEM_COUNT,
        f"blind packets must reconstruct exactly {BLIND_ITEM_COUNT} unique IDs",
    )
    return {
        "ids_by_chunk": ids_by_chunk,
        "metadata_by_id": metadata_by_id,
        "packet_file_hashes": packet_file_hashes,
        "packet_artifacts": packet_artifacts,
        "completed_item_count": completed_count,
        "incomplete_item_count": BLIND_ITEM_COUNT - completed_count,
        "scoring_rubric_sha256": rubric_sha256,
    }


def _validate_provenance(root: Path, packet_info: Mapping[str, Any]) -> str:
    _path, payload, provenance = _read_json_object(
        root / "provenance.json",
        "provenance",
    )
    _require_exact_keys(provenance, _PROVENANCE_KEYS, "provenance")
    core = {
        key: value
        for key, value in provenance.items()
        if key != "provenance_sha256"
    }
    _require(
        provenance["provenance_sha256"] == canonical_json_sha256(core),
        "provenance_sha256 does not match provenance content",
    )
    _require(
        type(provenance["schema_version"]) is int
        and provenance["schema_version"] == SCHEMA_VERSION,
        "provenance schema_version is invalid",
    )
    _require(provenance["bundle_id"] == BUNDLE_ID, "provenance bundle_id is invalid")
    _require(
        provenance["study_status"] == "unscored_condition_metadata_masked",
        "provenance study_status is invalid",
    )
    _require(provenance["publishable"] is False, "provenance publishable must be false")
    _require(
        type(provenance["chunk_count"]) is int
        and provenance["chunk_count"] == BLIND_CHUNK_COUNT,
        "provenance chunk_count is invalid",
    )
    _require(
        type(provenance["chunk_size"]) is int
        and provenance["chunk_size"] == BLIND_CHUNK_SIZE,
        "provenance chunk_size is invalid",
    )
    _require(
        type(provenance["item_count"]) is int
        and provenance["item_count"] == BLIND_ITEM_COUNT,
        "provenance item_count is invalid",
    )
    _require(
        provenance["completed_item_count"] == packet_info["completed_item_count"],
        "provenance completed_item_count disagrees with blind packets",
    )
    _require(
        provenance["incomplete_item_count"] == packet_info["incomplete_item_count"],
        "provenance incomplete_item_count disagrees with blind packets",
    )
    _require(
        provenance["blind_packet_files"] == packet_info["packet_artifacts"],
        "provenance blind_packet_files do not match the public packet files",
    )
    scoring_rubric = provenance["scoring_rubric"]
    _require(isinstance(scoring_rubric, dict), "provenance scoring_rubric must be an object")
    _require(
        scoring_rubric.get("file_sha256") == packet_info["scoring_rubric_sha256"],
        "provenance scoring rubric hash disagrees with blind packets",
    )
    return _sha256_bytes(payload)


def _validate_score_row(
    row: Any,
    *,
    expected_blind_id: str,
    polarity: str,
    label: str,
) -> int:
    _require_exact_keys(row, _SCORE_ROW_KEYS, label)
    _require(row["blind_id"] == expected_blind_id, f"{label}.blind_id breaks chunk reconstruction")
    direct = _binary(row["direct_answer"], f"{label}.direct_answer")
    complete = _binary(row["answer_complete"], f"{label}.answer_complete")
    unsupported_count = row["unsupported_atomic_claim_count"]
    _require(
        type(unsupported_count) is int and unsupported_count >= 0,
        f"{label}.unsupported_atomic_claim_count must be a non-negative integer",
    )
    no_unsupported = _binary(
        row["no_unsupported_claims"],
        f"{label}.no_unsupported_claims",
    )
    _require(
        no_unsupported == int(unsupported_count == 0),
        f"{label}.no_unsupported_claims disagrees with unsupported_atomic_claim_count",
    )
    laundering = _nullable_binary(
        row["evidence_laundering"],
        f"{label}.evidence_laundering",
    )
    correction = _nullable_binary(
        row["negative_correction"],
        f"{label}.negative_correction",
    )
    recognized = _nullable_binary(
        row["positive_recognized"],
        f"{label}.positive_recognized",
    )
    semantic = _binary(
        row["semantic_grounded_success"],
        f"{label}.semantic_grounded_success",
    )
    _require(isinstance(row["notes"], str), f"{label}.notes must be a string")

    if polarity == "negative":
        _require(
            laundering is not None and correction is not None,
            f"{label} requires negative-polarity scores",
        )
        _require(
            recognized is None,
            f"{label}.positive_recognized must be null for negative polarity",
        )
        expected_semantic = int(
            direct == 1
            and complete == 1
            and no_unsupported == 1
            and laundering == 0
            and correction == 1
        )
    else:
        _require(
            laundering is None and correction is None,
            f"{label} negative-polarity fields must be null for positive polarity",
        )
        _require(
            recognized is not None,
            f"{label}.positive_recognized is required for positive polarity",
        )
        expected_semantic = int(
            direct == 1
            and complete == 1
            and no_unsupported == 1
            and recognized == 1
        )
    _require(
        semantic == expected_semantic,
        f"{label}.semantic_grounded_success does not match component scores",
    )
    return semantic


def _load_scores(root: Path, packet_info: Mapping[str, Any]) -> dict[str, Any]:
    discovered = {path.name for path in root.glob("scores-chunk-*.json")}
    _require(
        discovered == set(SCORE_FILENAMES),
        "bundle must contain exactly scores-chunk-1.json through scores-chunk-3.json",
    )
    score_file_hashes: dict[str, str] = {}
    seen_ids: set[str] = set()
    semantic_count = 0
    item_count = 0

    for chunk_index, filename in enumerate(SCORE_FILENAMES, start=1):
        _path, payload, document = _read_json_object(
            root / filename,
            f"score chunk {chunk_index}",
        )
        forbidden = _score_metadata_paths(document)
        _require(
            not forbidden,
            f"{filename} contains condition/seed/key metadata: {forbidden[:3]}",
        )
        _require_exact_keys(document, _SCORE_DOCUMENT_KEYS, f"score chunk {chunk_index}")
        _require(
            type(document["schema_version"]) is int
            and document["schema_version"] == SCHEMA_VERSION,
            f"{filename} schema_version is invalid",
        )
        _require(document["bundle_id"] == BUNDLE_ID, f"{filename} bundle_id is invalid")
        _require(
            type(document["chunk_number"]) is int
            and document["chunk_number"] == chunk_index,
            f"{filename} chunk_number is invalid",
        )
        _require(
            document["scorer_type"] == SCORER_TYPE,
            f"{filename} scorer_type must be {SCORER_TYPE}",
        )
        _require(
            type(document["item_count"]) is int
            and document["item_count"] == BLIND_CHUNK_SIZE,
            f"{filename} item_count is invalid",
        )
        rows = document["items"]
        _require(
            isinstance(rows, list) and len(rows) == BLIND_CHUNK_SIZE,
            f"{filename} must contain exactly {BLIND_CHUNK_SIZE} score rows",
        )

        expected_ids = packet_info["ids_by_chunk"][chunk_index - 1]
        for row_index, row in enumerate(rows):
            expected_blind_id = expected_ids[row_index]
            label = f"{filename}.items[{row_index}]"
            semantic_count += _validate_score_row(
                row,
                expected_blind_id=expected_blind_id,
                polarity=packet_info["metadata_by_id"][expected_blind_id]["polarity"],
                label=label,
            )
            blind_id = row["blind_id"]
            _require(blind_id not in seen_ids, f"duplicate score blind_id: {blind_id}")
            seen_ids.add(blind_id)
        item_count += len(rows)
        score_file_hashes[filename] = _sha256_bytes(payload)

    expected_ids = set(packet_info["metadata_by_id"])
    _require(item_count == BLIND_ITEM_COUNT, "score documents must contain exactly 540 rows")
    _require(
        seen_ids == expected_ids and len(seen_ids) == BLIND_ITEM_COUNT,
        "score documents must cover every blind packet ID exactly once",
    )
    return {
        "score_file_hashes": score_file_hashes,
        "validated_item_count": item_count,
        "validated_unique_blind_id_count": len(seen_ids),
        "semantic_grounded_success_count_before_unblinding": semantic_count,
    }


def validate_mechanism_score_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Validate public blind packets, provenance, and all three score chunks."""

    root = _resolve_bundle_directory(bundle_dir)
    packet_info = _load_blind_packets(root)
    provenance_file_sha256 = _validate_provenance(root, packet_info)
    score_info = _load_scores(root, packet_info)
    return {
        "packet_id": BUNDLE_ID,
        "blind_packet_sha256": packet_info["packet_file_hashes"],
        "provenance_sha256": provenance_file_sha256,
        "score_file_sha256": score_info["score_file_hashes"],
        "validated_item_count": score_info["validated_item_count"],
        "validated_unique_blind_id_count": score_info[
            "validated_unique_blind_id_count"
        ],
        "semantic_grounded_success_count_before_unblinding": score_info[
            "semantic_grounded_success_count_before_unblinding"
        ],
        "scorer_type": SCORER_TYPE,
    }


def _lock_document(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_id": summary["packet_id"],
        "blind_packet_sha256": summary["blind_packet_sha256"],
        "provenance_sha256": summary["provenance_sha256"],
        "score_file_sha256": summary["score_file_sha256"],
        "validated_item_count": summary["validated_item_count"],
        "validated_unique_blind_id_count": summary[
            "validated_unique_blind_id_count"
        ],
        "semantic_grounded_success_count_before_unblinding": summary[
            "semantic_grounded_success_count_before_unblinding"
        ],
        "scoring_status": "locked_before_unblinding",
        "scorer_type": SCORER_TYPE,
    }


def _write_new_file(path: Path, payload: bytes) -> Path:
    target = Path(path).resolve()
    _require(not target.exists(), f"refusing to overwrite existing {target.name}")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            raise ValueError(f"refusing to overwrite existing {target.name}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return target


def validate_mechanism_score_lock(bundle_dir: Path) -> dict[str, Any]:
    """Revalidate the score bundle and require an exact matching score lock."""

    root = _resolve_bundle_directory(bundle_dir)
    summary = validate_mechanism_score_bundle(root)
    _path, _payload, lock = _read_json_object(
        root / SCORE_LOCK_FILENAME,
        "score lock",
    )
    _require_exact_keys(lock, _LOCK_KEYS, "score lock")
    _require(
        lock == _lock_document(summary),
        "score_lock.json does not match the current packet, provenance, and score files",
    )
    return {**summary, "scoring_status": "locked_before_unblinding"}


def write_mechanism_score_lock(
    bundle_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Validate twice, create ``score_lock.json`` exclusively, then validate again."""

    root = _resolve_bundle_directory(bundle_dir)
    lock_path = root / SCORE_LOCK_FILENAME
    _require(not lock_path.exists(), f"refusing to overwrite existing {SCORE_LOCK_FILENAME}")

    initial = validate_mechanism_score_bundle(root)
    _require(not lock_path.exists(), f"refusing to overwrite existing {SCORE_LOCK_FILENAME}")
    immediately_before_write = validate_mechanism_score_bundle(root)
    _require(
        immediately_before_write == initial,
        "bundle changed while score lock was being prepared",
    )
    _write_new_file(lock_path, _serialized_json(_lock_document(initial)))
    verified = validate_mechanism_score_lock(root)
    return lock_path, verified


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate three ARM-consumption blind score chunks and atomically "
            "create score_lock.json without reading blind_key.json."
        )
    )
    parser.add_argument("bundle_dir", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="validate packets, provenance, and scores without writing a lock",
    )
    mode.add_argument(
        "--verify-lock",
        action="store_true",
        help="validate an existing score_lock.json against current files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.validate_only:
            summary = validate_mechanism_score_bundle(args.bundle_dir)
        elif args.verify_lock:
            summary = validate_mechanism_score_lock(args.bundle_dir)
        else:
            lock_path, summary = write_mechanism_score_lock(args.bundle_dir)
            summary = {**summary, "score_lock_path": str(lock_path)}
    except (OSError, TypeError, ValueError) as error:
        print(f"mechanism score validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "PACKET_FILENAMES",
    "SCORER_TYPE",
    "SCORE_FILENAMES",
    "SCORE_LOCK_FILENAME",
    "validate_mechanism_score_bundle",
    "validate_mechanism_score_lock",
    "write_mechanism_score_lock",
]


if __name__ == "__main__":
    raise SystemExit(main())
