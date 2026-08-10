"""Reconcile two blind rating sets before ARM-mechanism unblinding.

Only public blind packets and blind score rows are consumed.  The private
``blind_key.json`` and every condition mapping remain outside this workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

from .mechanism_blind import (
    BLIND_CHUNK_COUNT,
    BLIND_CHUNK_SIZE,
    BLIND_ITEM_COUNT,
    BUNDLE_ID,
)
from .mechanism_packets import canonical_json_sha256
from . import mechanism_score_verify as score_verify


SCHEMA_VERSION = 1
ADJUDICATION_PACKET_FILENAME = "adjudication_packet.json"
ADJUDICATIONS_FILENAME = "adjudications.json"
RATING_PROVENANCE_FILENAME = "rating_provenance.json"
RATER_A_FILENAMES = tuple(
    f"ratings-a-chunk-{index}.json"
    for index in range(1, BLIND_CHUNK_COUNT + 1)
)
RATER_B_FILENAMES = tuple(
    f"ratings-b-chunk-{index}.json"
    for index in range(1, BLIND_CHUNK_COUNT + 1)
)
FINAL_SCORE_FILENAMES = tuple(
    f"scores-chunk-{index}.json"
    for index in range(1, BLIND_CHUNK_COUNT + 1)
)
_RATER_SCORER_TYPE = {
    "a": "blind_ai_preliminary",
    "b": "blind_ai_preliminary_b",
}

_RATING_DOCUMENT_KEYS = {
    "schema_version",
    "bundle_id",
    "chunk_number",
    "scorer_type",
    "item_count",
    "items",
}
_DECISION_FIELDS = (
    "direct_answer",
    "answer_complete",
    "unsupported_atomic_claim_count",
    "no_unsupported_claims",
    "evidence_laundering",
    "negative_correction",
    "positive_recognized",
    "semantic_grounded_success",
)
_ADJUDICATION_ITEM_KEYS = {
    "blind_id",
    "blind_item",
    "blind_item_sha256",
    "rating_a",
    "rating_a_sha256",
    "rating_b",
    "rating_b_sha256",
    "differing_fields",
}
_ADJUDICATION_PACKET_KEYS = {
    "schema_version",
    "bundle_id",
    "status",
    "publishable",
    "item_count",
    "comparison_fields",
    "blind_packet_sha256",
    "rating_file_sha256",
    "items",
    "adjudication_packet_sha256",
}
_ADJUDICATIONS_KEYS = {
    "schema_version",
    "bundle_id",
    "adjudication_packet_sha256",
    "item_count",
    "items",
}
_RATING_PROVENANCE_KEYS = {
    "schema_version",
    "bundle_id",
    "status",
    "blind_packet_sha256",
    "rating_file_sha256",
    "adjudication_packet_file_sha256",
    "adjudications_file_sha256",
    "final_score_file_sha256",
    "validated_item_count_per_rater",
    "agreement_count",
    "disagreement_count",
    "adjudicated_item_count",
    "semantic_grounded_success_count",
    "rating_provenance_sha256",
}
_PRIVATE_METADATA_TOKENS = {
    "condition",
    "conditions",
    "seed",
    "seeds",
    "model",
    "models",
    "key",
    "keys",
}
_PRIVATE_METADATA_NAMES = {
    "case_id",
    "case_ids",
    "packet_index",
    "raw_artifact",
    "raw_artifact_sha256",
    "source_identity",
    "blinding_secret",
    "blinding_secret_hex",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_exact_keys(value: Any, expected: set[str], label: str) -> None:
    score_verify._require_exact_keys(value, expected, label)


def _normalized_field_name(value: Any) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _is_private_metadata_field(value: Any) -> bool:
    normalized = _normalized_field_name(value)
    parts = set(normalized.split("_"))
    return bool(
        parts.intersection(_PRIVATE_METADATA_TOKENS)
        or normalized in _PRIVATE_METADATA_NAMES
        or normalized.startswith("blind_key")
        or normalized.startswith("blinding_key")
    )


def _private_metadata_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if _is_private_metadata_field(key):
                found.append(f"{path}.{key}")
            found.extend(_private_metadata_paths(nested, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_private_metadata_paths(nested, f"{path}[{index}]"))
    return found


def _reject_private_metadata(value: Any, label: str) -> None:
    forbidden = _private_metadata_paths(value)
    _require(
        not forbidden,
        f"{label} contains condition/seed/model/key metadata: {forbidden[:3]}",
    )


def _read_json_object(path: Path, label: str):
    return score_verify._read_json_object(path, label)


def _serialized_json(value: Mapping[str, Any]) -> bytes:
    return score_verify._serialized_json(value)


def _resolve_bundle_directory(bundle_dir: Path) -> Path:
    return score_verify._resolve_bundle_directory(bundle_dir)


def _load_public_items(
    root: Path,
    packet_info: Mapping[str, Any],
) -> tuple[list[list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    items_by_chunk: list[list[dict[str, Any]]] = []
    items_by_id: dict[str, dict[str, Any]] = {}
    for chunk_index, filename in enumerate(score_verify.PACKET_FILENAMES, start=1):
        _path, _payload, packet = _read_json_object(
            root / filename,
            f"blind packet {chunk_index}",
        )
        _reject_private_metadata(packet, filename)
        items = packet["items"]
        expected_ids = packet_info["ids_by_chunk"][chunk_index - 1]
        _require(
            [item["blind_id"] for item in items] == expected_ids,
            f"{filename} public item order changed during validation",
        )
        items_by_chunk.append(items)
        for item in items:
            items_by_id[item["blind_id"]] = item
    _require(
        len(items_by_id) == BLIND_ITEM_COUNT,
        "public packets must contain exactly 540 unique blind items",
    )
    return items_by_chunk, items_by_id


def _rating_filenames(rater: str) -> tuple[str, ...]:
    if rater == "a":
        return RATER_A_FILENAMES
    if rater == "b":
        return RATER_B_FILENAMES
    raise ValueError(f"unknown blind rater: {rater}")


def _load_rating_set(
    root: Path,
    *,
    rater: str,
    packet_info: Mapping[str, Any],
) -> dict[str, Any]:
    filenames = _rating_filenames(rater)
    discovered = {
        path.name for path in root.glob(f"ratings-{rater}-chunk-*.json")
    }
    _require(
        discovered == set(filenames),
        f"rater {rater.upper()} must have exactly three 180-row rating chunks",
    )

    rows_by_chunk: list[list[dict[str, Any]]] = []
    rows_by_id: dict[str, dict[str, Any]] = {}
    file_hashes: dict[str, str] = {}
    semantic_count = 0

    for chunk_index, filename in enumerate(filenames, start=1):
        _path, payload, document = _read_json_object(
            root / filename,
            f"rater {rater.upper()} chunk {chunk_index}",
        )
        _reject_private_metadata(document, filename)
        _require_exact_keys(
            document,
            _RATING_DOCUMENT_KEYS,
            f"rater {rater.upper()} chunk {chunk_index}",
        )
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
        expected_scorer_type = _RATER_SCORER_TYPE[rater]
        _require(
            document["scorer_type"] == expected_scorer_type,
            f"{filename} scorer_type must be {expected_scorer_type}",
        )
        _require(
            type(document["item_count"]) is int
            and document["item_count"] == BLIND_CHUNK_SIZE,
            f"{filename} item_count is invalid",
        )
        rows = document["items"]
        _require(
            isinstance(rows, list) and len(rows) == BLIND_CHUNK_SIZE,
            f"{filename} must contain exactly 180 rating rows",
        )
        expected_ids = packet_info["ids_by_chunk"][chunk_index - 1]
        for row_index, row in enumerate(rows):
            expected_id = expected_ids[row_index]
            semantic_count += score_verify._validate_score_row(
                row,
                expected_blind_id=expected_id,
                polarity=packet_info["metadata_by_id"][expected_id]["polarity"],
                label=f"{filename}.items[{row_index}]",
            )
            _require(
                expected_id not in rows_by_id,
                f"rater {rater.upper()} has duplicate blind_id: {expected_id}",
            )
            rows_by_id[expected_id] = row
        rows_by_chunk.append(rows)
        file_hashes[filename] = score_verify._sha256_bytes(payload)

    _require(
        len(rows_by_id) == BLIND_ITEM_COUNT
        and set(rows_by_id) == set(packet_info["metadata_by_id"]),
        f"rater {rater.upper()} must cover all 540 public blind IDs exactly once",
    )
    return {
        "rows_by_chunk": rows_by_chunk,
        "rows_by_id": rows_by_id,
        "file_hashes": file_hashes,
        "semantic_count": semantic_count,
    }


def _differing_fields(
    rating_a: Mapping[str, Any],
    rating_b: Mapping[str, Any],
) -> list[str]:
    return [
        field
        for field in _DECISION_FIELDS
        if rating_a[field] != rating_b[field]
    ]


def _load_reconciliation_inputs(bundle_dir: Path) -> dict[str, Any]:
    root = _resolve_bundle_directory(bundle_dir)
    packet_info = score_verify._load_blind_packets(root)
    items_by_chunk, items_by_id = _load_public_items(root, packet_info)
    rating_a = _load_rating_set(
        root,
        rater="a",
        packet_info=packet_info,
    )
    rating_b = _load_rating_set(
        root,
        rater="b",
        packet_info=packet_info,
    )
    ordered_ids = [
        blind_id
        for chunk_ids in packet_info["ids_by_chunk"]
        for blind_id in chunk_ids
    ]
    disagreements = [
        blind_id
        for blind_id in ordered_ids
        if _differing_fields(
            rating_a["rows_by_id"][blind_id],
            rating_b["rows_by_id"][blind_id],
        )
    ]
    return {
        "root": root,
        "packet_info": packet_info,
        "items_by_chunk": items_by_chunk,
        "items_by_id": items_by_id,
        "ordered_ids": ordered_ids,
        "rating_a": rating_a,
        "rating_b": rating_b,
        "disagreement_ids": disagreements,
    }


def _rating_hashes(inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rater_a": inputs["rating_a"]["file_hashes"],
        "rater_b": inputs["rating_b"]["file_hashes"],
    }


def _rating_summary(inputs: Mapping[str, Any]) -> dict[str, Any]:
    disagreement_count = len(inputs["disagreement_ids"])
    return {
        "bundle_id": BUNDLE_ID,
        "validated_item_count_per_rater": BLIND_ITEM_COUNT,
        "validated_unique_blind_id_count_per_rater": BLIND_ITEM_COUNT,
        "agreement_count": BLIND_ITEM_COUNT - disagreement_count,
        "disagreement_count": disagreement_count,
        "blind_packet_sha256": inputs["packet_info"]["packet_file_hashes"],
        "rating_file_sha256": _rating_hashes(inputs),
        "rater_a_semantic_grounded_success_count": inputs["rating_a"][
            "semantic_count"
        ],
        "rater_b_semantic_grounded_success_count": inputs["rating_b"][
            "semantic_count"
        ],
    }


def validate_mechanism_ratings(bundle_dir: Path) -> dict[str, Any]:
    """Validate both complete blind rating sets and report disagreements."""

    return _rating_summary(_load_reconciliation_inputs(bundle_dir))


def _adjudication_packet_document(inputs: Mapping[str, Any]) -> dict[str, Any]:
    items = []
    for blind_id in inputs["disagreement_ids"]:
        blind_item = inputs["items_by_id"][blind_id]
        rating_a = inputs["rating_a"]["rows_by_id"][blind_id]
        rating_b = inputs["rating_b"]["rows_by_id"][blind_id]
        items.append(
            {
                "blind_id": blind_id,
                "blind_item": blind_item,
                "blind_item_sha256": canonical_json_sha256(blind_item),
                "rating_a": rating_a,
                "rating_a_sha256": canonical_json_sha256(rating_a),
                "rating_b": rating_b,
                "rating_b_sha256": canonical_json_sha256(rating_b),
                "differing_fields": _differing_fields(rating_a, rating_b),
            }
        )
    core = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "status": "awaiting_blind_adjudication",
        "publishable": False,
        "item_count": len(items),
        "comparison_fields": list(_DECISION_FIELDS),
        "blind_packet_sha256": inputs["packet_info"]["packet_file_hashes"],
        "rating_file_sha256": _rating_hashes(inputs),
        "items": items,
    }
    return {
        **core,
        "adjudication_packet_sha256": canonical_json_sha256(core),
    }


def _load_expected_adjudication_packet(
    inputs: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    root = inputs["root"]
    _path, payload, document = _read_json_object(
        root / ADJUDICATION_PACKET_FILENAME,
        "adjudication packet",
    )
    _reject_private_metadata(document, "adjudication packet")
    _require_exact_keys(
        document,
        _ADJUDICATION_PACKET_KEYS,
        "adjudication packet",
    )
    packet_items = document["items"] if isinstance(document.get("items"), list) else []
    for index, item in enumerate(packet_items):
        _require_exact_keys(
            item,
            _ADJUDICATION_ITEM_KEYS,
            f"adjudication packet.items[{index}]",
        )
    expected = _adjudication_packet_document(inputs)
    _require(
        document == expected,
        "adjudication_packet.json does not match current public packets and ratings",
    )
    return payload, document


def validate_mechanism_adjudication_packet(bundle_dir: Path) -> dict[str, Any]:
    """Require the adjudication packet to be an exact rating-derived artifact."""

    inputs = _load_reconciliation_inputs(bundle_dir)
    payload, document = _load_expected_adjudication_packet(inputs)
    return {
        **_rating_summary(inputs),
        "adjudication_packet_sha256": document["adjudication_packet_sha256"],
        "adjudication_packet_file_sha256": score_verify._sha256_bytes(payload),
    }


def write_mechanism_adjudication_packet(
    bundle_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Atomically create the disagreement-only public adjudication packet."""

    root = _resolve_bundle_directory(bundle_dir)
    target = root / ADJUDICATION_PACKET_FILENAME
    _require(not target.exists(), f"refusing to overwrite existing {target.name}")
    initial = _load_reconciliation_inputs(root)
    immediately_before = _load_reconciliation_inputs(root)
    _require(
        _adjudication_packet_document(initial)
        == _adjudication_packet_document(immediately_before),
        "public packets or ratings changed while preparing adjudication",
    )
    document = _adjudication_packet_document(initial)
    score_verify._write_new_file(target, _serialized_json(document))
    return target, validate_mechanism_adjudication_packet(root)


def _load_adjudications(
    inputs: Mapping[str, Any],
    adjudication_packet: Mapping[str, Any],
) -> tuple[bytes, dict[str, dict[str, Any]]]:
    root = inputs["root"]
    _path, payload, document = _read_json_object(
        root / ADJUDICATIONS_FILENAME,
        "adjudications",
    )
    _reject_private_metadata(document, "adjudications")
    _require_exact_keys(document, _ADJUDICATIONS_KEYS, "adjudications")
    _require(
        type(document["schema_version"]) is int
        and document["schema_version"] == SCHEMA_VERSION,
        "adjudications schema_version is invalid",
    )
    _require(document["bundle_id"] == BUNDLE_ID, "adjudications bundle_id is invalid")
    _require(
        document["adjudication_packet_sha256"]
        == adjudication_packet["adjudication_packet_sha256"],
        "adjudications do not bind the current adjudication packet",
    )
    expected_ids = inputs["disagreement_ids"]
    rows = document["items"]
    _require(
        type(document["item_count"]) is int
        and document["item_count"] == len(expected_ids),
        "adjudications item_count must equal the disagreement count",
    )
    _require(
        isinstance(rows, list) and len(rows) == len(expected_ids),
        "adjudications must exactly cover all disagreements",
    )
    rows_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        blind_id = expected_ids[index]
        score_verify._validate_score_row(
            row,
            expected_blind_id=blind_id,
            polarity=inputs["packet_info"]["metadata_by_id"][blind_id]["polarity"],
            label=f"adjudications.items[{index}]",
        )
        _require(blind_id not in rows_by_id, f"duplicate adjudication: {blind_id}")
        rows_by_id[blind_id] = row
    _require(
        set(rows_by_id) == set(expected_ids),
        "adjudications must cover each disagreement exactly once",
    )
    return payload, rows_by_id


def _final_score_documents(
    inputs: Mapping[str, Any],
    adjudicated_rows: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    documents = []
    for chunk_index, chunk_ids in enumerate(
        inputs["packet_info"]["ids_by_chunk"],
        start=1,
    ):
        rows = [
            dict(
                adjudicated_rows.get(
                    blind_id,
                    inputs["rating_a"]["rows_by_id"][blind_id],
                )
            )
            for blind_id in chunk_ids
        ]
        documents.append(
            {
                "schema_version": SCHEMA_VERSION,
                "bundle_id": BUNDLE_ID,
                "chunk_number": chunk_index,
                "scorer_type": score_verify.SCORER_TYPE,
                "item_count": BLIND_CHUNK_SIZE,
                "items": rows,
            }
        )
    return documents


def _validate_final_score_selection(
    inputs: Mapping[str, Any],
    adjudicated_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, str], int]:
    expected_documents = _final_score_documents(inputs, adjudicated_rows)
    file_hashes: dict[str, str] = {}
    semantic_count = 0
    for filename, expected in zip(FINAL_SCORE_FILENAMES, expected_documents):
        _path, payload, document = _read_json_object(
            inputs["root"] / filename,
            filename,
        )
        _reject_private_metadata(document, filename)
        _require(
            document == expected,
            f"{filename} does not implement agreement-A/adjudicated selection",
        )
        semantic_count += sum(
            row["semantic_grounded_success"] for row in document["items"]
        )
        file_hashes[filename] = score_verify._sha256_bytes(payload)
    return file_hashes, semantic_count


def _rating_provenance_document(
    inputs: Mapping[str, Any],
    *,
    adjudication_packet_payload: bytes,
    adjudications_payload: bytes,
    final_score_hashes: Mapping[str, str],
    semantic_count: int,
) -> dict[str, Any]:
    disagreement_count = len(inputs["disagreement_ids"])
    core = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "status": "finalized_before_unblinding",
        "blind_packet_sha256": inputs["packet_info"]["packet_file_hashes"],
        "rating_file_sha256": _rating_hashes(inputs),
        "adjudication_packet_file_sha256": score_verify._sha256_bytes(
            adjudication_packet_payload
        ),
        "adjudications_file_sha256": score_verify._sha256_bytes(
            adjudications_payload
        ),
        "final_score_file_sha256": dict(final_score_hashes),
        "validated_item_count_per_rater": BLIND_ITEM_COUNT,
        "agreement_count": BLIND_ITEM_COUNT - disagreement_count,
        "disagreement_count": disagreement_count,
        "adjudicated_item_count": disagreement_count,
        "semantic_grounded_success_count": semantic_count,
    }
    return {**core, "rating_provenance_sha256": canonical_json_sha256(core)}


def _load_finalization_inputs(bundle_dir: Path) -> dict[str, Any]:
    inputs = _load_reconciliation_inputs(bundle_dir)
    packet_payload, adjudication_packet = _load_expected_adjudication_packet(inputs)
    adjudications_payload, adjudicated_rows = _load_adjudications(
        inputs,
        adjudication_packet,
    )
    return {
        "inputs": inputs,
        "adjudication_packet_payload": packet_payload,
        "adjudication_packet": adjudication_packet,
        "adjudications_payload": adjudications_payload,
        "adjudicated_rows": adjudicated_rows,
    }


def _finalization_fingerprint(loaded: Mapping[str, Any]) -> dict[str, Any]:
    inputs = loaded["inputs"]
    return {
        "final_score_documents": _final_score_documents(
            inputs,
            loaded["adjudicated_rows"],
        ),
        "blind_packet_sha256": inputs["packet_info"]["packet_file_hashes"],
        "rating_file_sha256": _rating_hashes(inputs),
        "adjudication_packet_file_sha256": score_verify._sha256_bytes(
            loaded["adjudication_packet_payload"]
        ),
        "adjudications_file_sha256": score_verify._sha256_bytes(
            loaded["adjudications_payload"]
        ),
    }


def validate_mechanism_rating_finalization(bundle_dir: Path) -> dict[str, Any]:
    """Validate reconciled final scores and their complete file provenance."""

    loaded = _load_finalization_inputs(bundle_dir)
    inputs = loaded["inputs"]
    final_hashes, semantic_count = _validate_final_score_selection(
        inputs,
        loaded["adjudicated_rows"],
    )
    _path, _payload, provenance = _read_json_object(
        inputs["root"] / RATING_PROVENANCE_FILENAME,
        "rating provenance",
    )
    _reject_private_metadata(provenance, "rating provenance")
    _require_exact_keys(
        provenance,
        _RATING_PROVENANCE_KEYS,
        "rating provenance",
    )
    expected = _rating_provenance_document(
        inputs,
        adjudication_packet_payload=loaded["adjudication_packet_payload"],
        adjudications_payload=loaded["adjudications_payload"],
        final_score_hashes=final_hashes,
        semantic_count=semantic_count,
    )
    _require(
        provenance == expected,
        "rating_provenance.json does not match current reconciliation files",
    )
    return {
        **_rating_summary(inputs),
        "adjudicated_item_count": len(loaded["adjudicated_rows"]),
        "semantic_grounded_success_count": semantic_count,
        "final_score_file_sha256": final_hashes,
        "status": "finalized_before_unblinding",
    }


def finalize_mechanism_ratings(
    bundle_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Exclusively write final scores in packet order and commit provenance last."""

    root = _resolve_bundle_directory(bundle_dir)
    targets = [
        *(root / filename for filename in FINAL_SCORE_FILENAMES),
        root / RATING_PROVENANCE_FILENAME,
    ]
    existing = [path.name for path in targets if path.exists()]
    _require(not existing, f"refusing to overwrite reconciliation outputs: {existing}")

    initial = _load_finalization_inputs(root)
    immediately_before = _load_finalization_inputs(root)
    _require(
        _finalization_fingerprint(initial)
        == _finalization_fingerprint(immediately_before),
        "ratings or adjudications changed while preparing final scores",
    )

    documents = _final_score_documents(
        initial["inputs"],
        initial["adjudicated_rows"],
    )
    for target, document in zip(targets[:3], documents):
        score_verify._write_new_file(target, _serialized_json(document))

    final_hashes, semantic_count = _validate_final_score_selection(
        initial["inputs"],
        initial["adjudicated_rows"],
    )
    provenance = _rating_provenance_document(
        initial["inputs"],
        adjudication_packet_payload=initial["adjudication_packet_payload"],
        adjudications_payload=initial["adjudications_payload"],
        final_score_hashes=final_hashes,
        semantic_count=semantic_count,
    )
    provenance_path = targets[-1]
    score_verify._write_new_file(provenance_path, _serialized_json(provenance))
    return provenance_path, validate_mechanism_rating_finalization(root)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile two complete public blind ARM rating sets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("validate", "validate both rating sets and report disagreements"),
        ("prepare", "atomically create adjudication_packet.json"),
        ("finalize", "create reconciled score chunks and rating provenance"),
        ("verify-final", "verify existing final scores and provenance"),
    ):
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("bundle_dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            result = validate_mechanism_ratings(args.bundle_dir)
        elif args.command == "prepare":
            path, result = write_mechanism_adjudication_packet(args.bundle_dir)
            result = {**result, "adjudication_packet_path": str(path)}
        elif args.command == "finalize":
            path, result = finalize_mechanism_ratings(args.bundle_dir)
            result = {**result, "rating_provenance_path": str(path)}
        else:
            result = validate_mechanism_rating_finalization(args.bundle_dir)
    except (OSError, TypeError, ValueError) as error:
        print(f"mechanism rating reconciliation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "ADJUDICATION_PACKET_FILENAME",
    "ADJUDICATIONS_FILENAME",
    "FINAL_SCORE_FILENAMES",
    "RATER_A_FILENAMES",
    "RATER_B_FILENAMES",
    "RATING_PROVENANCE_FILENAME",
    "finalize_mechanism_ratings",
    "validate_mechanism_adjudication_packet",
    "validate_mechanism_rating_finalization",
    "validate_mechanism_ratings",
    "write_mechanism_adjudication_packet",
]


if __name__ == "__main__":
    raise SystemExit(main())
