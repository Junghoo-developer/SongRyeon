"""Build the 30-case source snapshot for the hybrid audit experiment.

The builder performs no model calls.  It copies one already captured local
draft per held-out case (seed 42, ``ar-consumer-rule``), the exact A records,
and historical evaluation results into separated fields.  Future audit runners
must use :func:`evals.hybrid_audit_v1.schemas.audit_prompt_material` rather than
passing a complete snapshot case to a model.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

if __package__:
    from .schemas import (
        SNAPSHOT_CASE_COUNT,
        SnapshotValidationError,
        add_snapshot_id,
        canonical_json,
        deterministic_a_provenance_id,
        strict_json_loads,
        validate_source_snapshot,
    )
else:
    from schemas import (  # type: ignore[no-redef]
        SNAPSHOT_CASE_COUNT,
        SnapshotValidationError,
        add_snapshot_id,
        canonical_json,
        deterministic_a_provenance_id,
        strict_json_loads,
        validate_source_snapshot,
    )


ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT_ROOT = ROOT.parents[1]
EVIDENCE_PACKETS_RELATIVE = Path(
    ".tmp/evals/arm_consumption_mechanism_inputs_v1/evidence_packets.json"
)
RAW_SEED_RELATIVE = Path(
    ".tmp/evals/arm_consumption_mechanism_v1/raw/seed-42"
)
BLIND_RELATIVE = Path(".tmp/evals/arm_consumption_mechanism_blind_v1")
ANSWER_CONDITION = "ar-consumer-rule"
HISTORICAL_REVIEWER = "evidence-reviewer"
PRELIMINARY_SCORER = "blind_ai_preliminary"
SEED = 42


class SourceBuildError(SnapshotValidationError):
    """The historical source artifacts cannot produce the declared snapshot."""


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _resolve_inside(project_root: Path, relative: Path, *, directory: bool) -> Path:
    candidate = project_root / relative
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(project_root)
    except (FileNotFoundError, OSError, ValueError) as failure:
        raise SourceBuildError(f"source path escapes or is missing: {relative}") from failure
    if directory and not resolved.is_dir():
        raise SourceBuildError(f"source path is not a directory: {relative}")
    if not directory and not resolved.is_file():
        raise SourceBuildError(f"source path is not a file: {relative}")
    return resolved


def _read_strict_json(path: Path):
    content = path.read_bytes()
    if content.startswith(b"\xef\xbb\xbf"):
        raise SourceBuildError(f"JSON must be UTF-8 without a BOM: {path.name}")
    try:
        text = content.decode("utf-8", errors="strict")
        value = strict_json_loads(text)
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RecursionError,
    ) as failure:
        raise SourceBuildError(f"source is not strict UTF-8 JSON: {path.name}") from failure
    return value, content


def _relative_reference(project_root: Path, path: Path, content: bytes) -> dict:
    try:
        relative = path.relative_to(project_root).as_posix()
    except ValueError as failure:
        raise SourceBuildError("source file is outside project_root") from failure
    return {"path": relative, "sha256": _sha256_bytes(content)}


def _require_dict(value, label):
    if not isinstance(value, dict):
        raise SourceBuildError(f"{label} must be an object")
    return value


def _require_list(value, label):
    if not isinstance(value, list):
        raise SourceBuildError(f"{label} must be a list")
    return value


def _load_evidence_packets(project_root: Path):
    path = _resolve_inside(
        project_root,
        EVIDENCE_PACKETS_RELATIVE,
        directory=False,
    )
    document, content = _read_strict_json(path)
    _require_dict(document, "evidence packet document")
    packets = _require_list(document.get("packets"), "evidence packets")
    if document.get("packet_count") != SNAPSHOT_CASE_COUNT or len(packets) != SNAPSHOT_CASE_COUNT:
        raise SourceBuildError(
            f"evidence packet source must contain exactly {SNAPSHOT_CASE_COUNT} cases"
        )

    packet_by_case = {}
    ordered_case_ids = []
    for packet in packets:
        _require_dict(packet, "evidence packet")
        if set(packet) != {"case_id", "packet_sha256", "payload"}:
            raise SourceBuildError("evidence packet schema mismatch")
        case_id = packet["case_id"]
        if not isinstance(case_id, str) or not case_id:
            raise SourceBuildError("evidence packet case_id is invalid")
        if case_id in packet_by_case:
            raise SourceBuildError(f"duplicate evidence packet case_id: {case_id}")
        calculated = _sha256_bytes(
            canonical_json(
                {"case_id": case_id, "payload": packet["payload"]}
            ).encode("utf-8")
        )
        if packet["packet_sha256"] != calculated:
            raise SourceBuildError(f"evidence packet hash mismatch: {case_id}")
        packet_by_case[case_id] = packet
        ordered_case_ids.append(case_id)
    return path, content, packet_by_case, ordered_case_ids


def _load_raw_artifacts(project_root: Path):
    directory = _resolve_inside(
        project_root,
        RAW_SEED_RELATIVE,
        directory=True,
    )
    paths = sorted(directory.glob("*.json"), key=lambda item: item.name)
    if len(paths) != SNAPSHOT_CASE_COUNT:
        raise SourceBuildError(
            f"seed-42 source must contain exactly {SNAPSHOT_CASE_COUNT} JSON artifacts"
        )

    by_case = {}
    packet_indexes = set()
    for path in paths:
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(directory)
        except ValueError as failure:
            raise SourceBuildError("raw artifact path escapes seed directory") from failure
        artifact, content = _read_strict_json(resolved)
        _require_dict(artifact, "raw artifact")
        if artifact.get("seed") != SEED:
            raise SourceBuildError(f"raw artifact seed is not {SEED}: {path.name}")
        case_id = artifact.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise SourceBuildError(f"raw artifact case_id is invalid: {path.name}")
        if case_id in by_case:
            raise SourceBuildError(f"duplicate raw case_id: {case_id}")
        packet_index = artifact.get("packet_index")
        if type(packet_index) is not int or not 0 <= packet_index < SNAPSHOT_CASE_COUNT:
            raise SourceBuildError(f"raw packet_index is invalid: {case_id}")
        if packet_index in packet_indexes:
            raise SourceBuildError(f"duplicate raw packet_index: {packet_index}")
        packet_indexes.add(packet_index)

        answer_calls = _require_dict(artifact.get("answer_calls"), "answer_calls")
        answer_call = _require_dict(
            answer_calls.get(ANSWER_CONDITION),
            f"{ANSWER_CONDITION} answer call",
        )
        if answer_call.get("status") != "valid":
            raise SourceBuildError(f"local draft is not valid: {case_id}")
        answer_output = _require_dict(answer_call.get("output"), "answer output")
        if set(answer_output) != {"answer"}:
            raise SourceBuildError(f"local draft output schema mismatch: {case_id}")
        draft = answer_output["answer"]
        if not isinstance(draft, str) or not draft.strip():
            raise SourceBuildError(f"local draft is empty: {case_id}")

        reviewer_calls = _require_dict(
            artifact.get("reviewer_calls"),
            "reviewer_calls",
        )
        reviewer = _require_dict(
            reviewer_calls.get(HISTORICAL_REVIEWER),
            f"{HISTORICAL_REVIEWER} result",
        )
        if reviewer.get("status") != "valid":
            raise SourceBuildError(f"historical reviewer is not valid: {case_id}")
        reviewer_output = _require_dict(
            reviewer.get("output"),
            "historical reviewer output",
        )
        if set(reviewer_output) != {"verdict", "reason", "revised_answer"}:
            raise SourceBuildError(
                f"historical reviewer output schema mismatch: {case_id}"
            )

        by_case[case_id] = {
            "artifact": artifact,
            "content": content,
            "path": resolved,
            "sha256": _sha256_bytes(content),
            "draft": draft,
            "reviewer_output": reviewer_output,
        }

    if packet_indexes != set(range(SNAPSHOT_CASE_COUNT)):
        raise SourceBuildError("raw packet_index coverage is incomplete")
    return by_case


def _load_blind_sources(project_root: Path):
    directory = _resolve_inside(project_root, BLIND_RELATIVE, directory=True)
    blind_key_path = _resolve_inside(
        project_root,
        BLIND_RELATIVE / "blind_key.json",
        directory=False,
    )
    score_lock_path = _resolve_inside(
        project_root,
        BLIND_RELATIVE / "score_lock.json",
        directory=False,
    )
    blind_key, blind_key_content = _read_strict_json(blind_key_path)
    score_lock, score_lock_content = _read_strict_json(score_lock_path)
    _require_dict(blind_key, "blind key")
    _require_dict(score_lock, "score lock")
    if score_lock.get("scorer_type") != PRELIMINARY_SCORER:
        raise SourceBuildError("score lock is not the blind preliminary score")
    if score_lock.get("scoring_status") != "locked_before_unblinding":
        raise SourceBuildError("preliminary score was not locked before unblinding")

    expected_score_hashes = _require_dict(
        score_lock.get("score_file_sha256"),
        "score file hashes",
    )
    if not expected_score_hashes:
        raise SourceBuildError("score lock contains no score files")
    score_items = {}
    score_references = []
    for filename in sorted(expected_score_hashes):
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise SourceBuildError("score filename is not a plain filename")
        path = _resolve_inside(
            project_root,
            BLIND_RELATIVE / filename,
            directory=False,
        )
        score_document, content = _read_strict_json(path)
        actual_hash = _sha256_bytes(content)
        if expected_score_hashes[filename] != actual_hash:
            raise SourceBuildError(f"locked score hash mismatch: {filename}")
        _require_dict(score_document, "score document")
        if score_document.get("scorer_type") != PRELIMINARY_SCORER:
            raise SourceBuildError(f"score source is not preliminary: {filename}")
        items = _require_list(score_document.get("items"), "score items")
        if score_document.get("item_count") != len(items):
            raise SourceBuildError(f"score item_count mismatch: {filename}")
        for item in items:
            _require_dict(item, "score item")
            blind_id = item.get("blind_id")
            if not isinstance(blind_id, str) or not blind_id:
                raise SourceBuildError("score item blind_id is invalid")
            if blind_id in score_items:
                raise SourceBuildError(f"duplicate preliminary score: {blind_id}")
            score_items[blind_id] = item
        score_references.append(_relative_reference(project_root, path, content))

    if score_lock.get("validated_item_count") != len(score_items):
        raise SourceBuildError("locked score item coverage mismatch")
    if score_lock.get("validated_unique_blind_id_count") != len(score_items):
        raise SourceBuildError("locked unique score item coverage mismatch")

    key_items = _require_list(blind_key.get("items"), "blind key items")
    selected_key_items = {}
    for item in key_items:
        _require_dict(item, "blind key item")
        if item.get("seed") != SEED or item.get("condition") != ANSWER_CONDITION:
            continue
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise SourceBuildError("selected blind key case_id is invalid")
        if case_id in selected_key_items:
            raise SourceBuildError(f"duplicate selected blind key case: {case_id}")
        selected_key_items[case_id] = item

    if len(selected_key_items) != SNAPSHOT_CASE_COUNT:
        raise SourceBuildError(
            f"blind key must select exactly {SNAPSHOT_CASE_COUNT} cases"
        )
    return {
        "directory": directory,
        "blind_key_path": blind_key_path,
        "blind_key_content": blind_key_content,
        "score_lock_path": score_lock_path,
        "score_lock_content": score_lock_content,
        "score_references": score_references,
        "score_items": score_items,
        "selected_key_items": selected_key_items,
    }


def _audit_input(case_id: str, packet: dict) -> dict:
    payload = _require_dict(packet["payload"], "evidence payload")
    if set(payload) != {"active_goal", "fixture_memory", "tool_results"}:
        raise SourceBuildError(f"evidence payload schema mismatch: {case_id}")
    tool_results = _require_list(payload["tool_results"], "tool_results")
    if not tool_results:
        raise SourceBuildError(f"case has no A records: {case_id}")

    records = []
    for ordinal, source_record in enumerate(tool_results, 1):
        _require_dict(source_record, "tool result")
        if source_record.get("information_class") != "absolute":
            raise SourceBuildError(f"non-A tool result in audit source: {case_id}")
        if source_record.get("code_verifiable") is not True:
            raise SourceBuildError(f"non-verifiable tool result in audit source: {case_id}")
        record = deepcopy(source_record)
        record["provenance_id"] = deterministic_a_provenance_id(
            case_id,
            packet["packet_sha256"],
            ordinal,
        )
        records.append(record)
    return {"a_records": records}


def build_source_snapshot(*, project_root: Path | None = None) -> dict:
    """Build the complete deterministic snapshot from already captured artifacts."""

    root = (
        DEFAULT_PROJECT_ROOT if project_root is None else Path(project_root)
    ).resolve(strict=True)
    evidence_path, evidence_content, packets, ordered_case_ids = _load_evidence_packets(
        root
    )
    raw_by_case = _load_raw_artifacts(root)
    blind = _load_blind_sources(root)

    expected_case_ids = set(ordered_case_ids)
    if set(raw_by_case) != expected_case_ids:
        raise SourceBuildError("raw artifacts and evidence packets cover different cases")
    if set(blind["selected_key_items"]) != expected_case_ids:
        raise SourceBuildError("blind key and evidence packets cover different cases")

    cases = []
    for expected_index, case_id in enumerate(ordered_case_ids):
        packet = packets[case_id]
        raw = raw_by_case[case_id]
        artifact = raw["artifact"]
        if artifact.get("packet_index") != expected_index:
            raise SourceBuildError(f"raw packet order mismatch: {case_id}")
        if artifact.get("packet_sha256") != packet["packet_sha256"]:
            raise SourceBuildError(f"raw/evidence packet hash mismatch: {case_id}")

        key_item = blind["selected_key_items"][case_id]
        if key_item.get("raw_artifact_sha256") != raw["sha256"]:
            raise SourceBuildError(f"blind key raw hash mismatch: {case_id}")
        blind_id = key_item.get("blind_id")
        if not isinstance(blind_id, str) or blind_id not in blind["score_items"]:
            raise SourceBuildError(f"preliminary score is missing: {case_id}")
        score_item = blind["score_items"][blind_id]
        if type(score_item.get("no_unsupported_claims")) is not int or score_item[
            "no_unsupported_claims"
        ] not in {0, 1}:
            raise SourceBuildError(
                f"preliminary no_unsupported_claims is invalid: {case_id}"
            )
        expected_verdict = (
            "permit" if score_item["no_unsupported_claims"] == 1 else "reject"
        )

        cases.append(
            {
                "case_id": case_id,
                "source_artifact": _relative_reference(
                    root,
                    raw["path"],
                    raw["content"],
                ),
                "source_packet": {
                    "packet_sha256": packet["packet_sha256"],
                    "payload": deepcopy(packet["payload"]),
                },
                "local_draft": raw["draft"],
                "audit_input": _audit_input(case_id, packet),
                "expected_audit_verdict": expected_verdict,
                "historical_reference": {
                    "local_evidence_reviewer": {
                        "reviewer_id": HISTORICAL_REVIEWER,
                        "status": "valid",
                        "output": deepcopy(raw["reviewer_output"]),
                    },
                    "blind_preliminary_score": {
                        "scorer_type": PRELIMINARY_SCORER,
                        "item": deepcopy(score_item),
                    },
                },
            }
        )

    body = {
        "schema_version": 1,
        "selection": {
            "seed": SEED,
            "answer_condition": ANSWER_CONDITION,
            "historical_reviewer": HISTORICAL_REVIEWER,
            "score_source": PRELIMINARY_SCORER,
            "case_count": SNAPSHOT_CASE_COUNT,
        },
        "source_provenance": {
            "evidence_packets": _relative_reference(
                root,
                evidence_path,
                evidence_content,
            ),
            "blind_key": _relative_reference(
                root,
                blind["blind_key_path"],
                blind["blind_key_content"],
            ),
            "score_lock": _relative_reference(
                root,
                blind["score_lock_path"],
                blind["score_lock_content"],
            ),
            "score_files": blind["score_references"],
        },
        "cases": cases,
    }
    snapshot = add_snapshot_id(body)
    validate_source_snapshot(snapshot)
    return snapshot


def build_source_snapshot_verified(*, project_root: Path | None = None) -> dict:
    """Build twice and reject byte-level nondeterminism before any experiment."""

    first = build_source_snapshot(project_root=project_root)
    second = build_source_snapshot(project_root=project_root)
    if canonical_json(first) != canonical_json(second):
        raise SourceBuildError("source snapshot build is not deterministic")
    return first


def write_new_snapshot(path: Path, snapshot: dict) -> None:
    """Write a validated snapshot once; never overwrite an experiment source."""

    validate_source_snapshot(snapshot)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(snapshot, ensure_ascii=False, allow_nan=False, indent=2))
        file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = build_source_snapshot_verified(project_root=args.project_root)
    write_new_snapshot(args.output, snapshot)
    print(args.output)


if __name__ == "__main__":
    main()
