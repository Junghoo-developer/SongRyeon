
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
CONDITIONS = {
    "opaque-label",
    "ar-label-only",
    "ar-label-placebo",
    "ar-consumer-rule",
    "style-placebo-enforced",
    "evidence-enforced",
}
METRICS = (
    "direct_answer",
    "answer_complete",
    "unsupported_atomic_claim_count",
    "no_unsupported_claims",
    "evidence_laundering",
    "negative_correction",
    "positive_recognized",
    "semantic_grounded_success",
)


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: object) -> str:
    return sha256_bytes(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def content_files(root: Path) -> set[str]:
    result = set()
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result.add(path.relative_to(root).as_posix())
    return result


def verify_manifest(root: Path = ROOT) -> dict[str, int]:
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    entries = manifest["files"]
    declared = {entry["path"] for entry in entries}
    actual = content_files(root) - {"MANIFEST.json", "SHA256SUMS"}
    if declared != actual:
        fail(f"manifest path set mismatch: missing={sorted(declared-actual)}, extra={sorted(actual-declared)}")
    for entry in entries:
        path = root / entry["path"]
        if path.stat().st_size != entry["bytes"]:
            fail(f"size mismatch: {entry['path']}")
        if sha256_file(path) != entry["sha256"]:
            fail(f"sha256 mismatch: {entry['path']}")

    sum_rows = []
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        sum_rows.append((digest, relative))
    expected_sum_paths = content_files(root) - {"SHA256SUMS"}
    if {relative for _, relative in sum_rows} != expected_sum_paths:
        fail("SHA256SUMS path set mismatch")
    for digest, relative in sum_rows:
        if sha256_file(root / relative) != digest:
            fail(f"SHA256SUMS mismatch: {relative}")
    return {"manifest_file_count": len(entries), "sha256sums_file_count": len(sum_rows)}


def load_rows(root: Path = ROOT) -> list[dict[str, object]]:
    rows = []
    with (root / "data" / "public_score_rows.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    result = {}
    for condition in sorted(CONDITIONS):
        selected = [row for row in rows if row["condition"] == condition]
        negative = [row for row in selected if row["polarity"] == "negative"]
        positive = [row for row in selected if row["polarity"] == "positive"]
        result[condition] = {
            "total": {
                "n": len(selected),
                "semantic_grounded_success": sum(int(row["semantic_grounded_success"]) for row in selected),
            },
            "negative": {
                "n": len(negative),
                "semantic_grounded_success": sum(int(row["semantic_grounded_success"]) for row in negative),
                "evidence_laundering": sum(int(row["evidence_laundering"]) for row in negative),
            },
            "positive": {
                "n": len(positive),
                "semantic_grounded_success": sum(int(row["semantic_grounded_success"]) for row in positive),
                "positive_recognized": sum(int(row["positive_recognized"]) for row in positive),
            },
        }
    return result


def verify_rows(rows: list[dict[str, object]], root: Path = ROOT, crosscheck: bool = True) -> dict[str, object]:
    if len(rows) != 540:
        fail(f"expected 540 rows, got {len(rows)}")
    if {row["condition"] for row in rows} != CONDITIONS:
        fail("condition set mismatch")
    row_ids = set()
    identities = set()
    for row in rows:
        row_id = row["row_id"]
        identity = (row["condition"], row["case_id"], row["seed"])
        if row_id in row_ids or identity in identities:
            fail(f"duplicate row identity: {row_id}")
        row_ids.add(row_id)
        identities.add(identity)
        unsigned = dict(row)
        claimed_hash = unsigned.pop("row_sha256")
        if canonical_sha256(unsigned) != claimed_hash:
            fail(f"row hash mismatch: {row_id}")
        for metric in ("direct_answer", "answer_complete", "no_unsupported_claims", "semantic_grounded_success"):
            if row[metric] not in (0, 1):
                fail(f"non-binary {metric}: {row_id}")
        if not isinstance(row["unsupported_atomic_claim_count"], int) or row["unsupported_atomic_claim_count"] < 0:
            fail(f"invalid unsupported claim count: {row_id}")
        if row["polarity"] == "negative":
            if row["evidence_laundering"] not in (0, 1) or row["negative_correction"] not in (0, 1) or row["positive_recognized"] is not None:
                fail(f"negative metric shape mismatch: {row_id}")
        elif row["polarity"] == "positive":
            if row["positive_recognized"] not in (0, 1) or row["evidence_laundering"] is not None or row["negative_correction"] is not None:
                fail(f"positive metric shape mismatch: {row_id}")
        else:
            fail(f"unknown polarity: {row_id}")

    for condition in CONDITIONS:
        selected = [row for row in rows if row["condition"] == condition]
        if len(selected) != 90:
            fail(f"condition denominator mismatch: {condition}")
        if len({row["case_id"] for row in selected}) != 30:
            fail(f"case count mismatch: {condition}")
        for case_id in {row["case_id"] for row in selected}:
            seeds = {row["seed"] for row in selected if row["case_id"] == case_id}
            if seeds != {42, 43, 44}:
                fail(f"seed set mismatch: {condition}/{case_id}")
        if sum(row["polarity"] == "negative" for row in selected) != 45 or sum(row["polarity"] == "positive" for row in selected) != 45:
            fail(f"polarity denominator mismatch: {condition}")

    summary = aggregate(rows)
    style = summary["style-placebo-enforced"]
    evidence = summary["evidence-enforced"]
    observed = {
        "negative_laundering": [style["negative"]["evidence_laundering"], style["negative"]["n"], evidence["negative"]["evidence_laundering"], evidence["negative"]["n"]],
        "positive_strict": [style["positive"]["semantic_grounded_success"], style["positive"]["n"], evidence["positive"]["semantic_grounded_success"], evidence["positive"]["n"]],
    }
    expected = {
        "negative_laundering": [15, 45, 1, 45],
        "positive_strict": [43, 45, 45, 45],
    }
    if observed != expected:
        fail(f"headline claim mismatch: {observed}")

    claims = json.loads((root / "CLAIMS.json").read_text(encoding="utf-8"))
    if claims["claim_status"] != "exploratory_not_publishable" or claims["publishable"] is not False:
        fail("claim ceiling missing")
    if claims["all_condition_counts_recomputed_from_public_rows"] != summary:
        fail("CLAIMS.json aggregation mismatch")

    if crosscheck:
        key = json.loads((root / "data" / "blind_key_public.json").read_text(encoding="utf-8"))
        key_by_id = {item["blind_id"]: item for item in key["items"]}
        packet_by_id = {}
        packet_source = {}
        for name in ("blind_packet_001.json", "blind_packet_002.json", "blind_packet_003.json"):
            packet = json.loads((root / "upstream_records" / name).read_text(encoding="utf-8"))
            for index, item in enumerate(packet["items"]):
                if "thinking" in item or "reasoning" in item:
                    fail(f"hidden reasoning field present: {name}/{index}")
                packet_by_id[item["blind_id"]] = item
                packet_source[item["blind_id"]] = (name, index)
        score_by_id = {}
        score_source = {}
        for name in ("scores-chunk-1.json", "scores-chunk-2.json", "scores-chunk-3.json"):
            path = root / "upstream_records" / name
            score = json.loads(path.read_text(encoding="utf-8"))
            for index, item in enumerate(score["items"]):
                score_by_id[item["blind_id"]] = item
                score_source[item["blind_id"]] = (name, sha256_file(path), index)
        if set(key_by_id) != set(packet_by_id) or set(key_by_id) != set(score_by_id) or len(key_by_id) != 540:
            fail("upstream identity set mismatch")
        for row in rows:
            blind_id = row["blind_id"]
            key_item = key_by_id[blind_id]
            packet_item = packet_by_id[blind_id]
            score_item = score_by_id[blind_id]
            normalized = {"style_placebo_enforced": "style-placebo-enforced", "evidence_enforced": "evidence-enforced"}.get(key_item["condition"], key_item["condition"])
            if (row["case_id"], row["seed"], row["condition"], row["raw_artifact_sha256"]) != (key_item["case_id"], key_item["seed"], normalized, key_item["raw_artifact_sha256"]):
                fail(f"public key mismatch: {row['row_id']}")
            if (row["family"], row["polarity"], row["source_blind_packet_file"], row["source_blind_packet_item_index"]) != (packet_item["family"], packet_item["polarity"], *packet_source[blind_id]):
                fail(f"blind packet mismatch: {row['row_id']}")
            if (row["source_score_file"], row["source_score_file_sha256"], row["source_score_item_index"]) != score_source[blind_id]:
                fail(f"score source mismatch: {row['row_id']}")
            for metric in METRICS:
                if row[metric] != score_item[metric]:
                    fail(f"metric mismatch {metric}: {row['row_id']}")

        with (root / "data" / "public_score_rows.csv").open(encoding="utf-8", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        if len(csv_rows) != 540 or [row["row_id"] for row in csv_rows] != [row["row_id"] for row in rows]:
            fail("CSV/JSONL row identity mismatch")

    return {"row_count": len(rows), "condition_count": len(CONDITIONS), "headline": observed, "all_conditions": summary}


def privacy_scan(root: Path = ROOT) -> dict[str, int]:
    forbidden = [re.compile(r"(?i)C:\\\\Users\\"), re.compile(r"(?i)/Users/"), re.compile(r"(?i)/home/"), re.compile(r"(?i)\\bpeter\\b"), re.compile(r'(?i)"(?:thinking|reasoning)"\\s*:')]
    scanned = 0
    for relative in sorted(content_files(root)):
        if relative == "verify.py":
            continue
        path = root / relative
        if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".md", ".py", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        scanned += 1
        for pattern in forbidden:
            if pattern.search(text):
                fail(f"privacy pattern {pattern.pattern!r} found in {relative}")
    forbidden_names = {"blind_key.json", "unblinded_summary.json"}
    if forbidden_names & {Path(item).name for item in content_files(root)}:
        fail("unsanitized upstream file present")
    return {"privacy_scanned_text_files": scanned}


def verify(root: Path = ROOT) -> dict[str, object]:
    result = {"status": "PASS"}
    result.update(verify_manifest(root))
    result.update(privacy_scan(root))
    result.update(verify_rows(load_rows(root), root, crosscheck=True))
    lineage = json.loads((root / "SOURCE_LINEAGE.json").read_text(encoding="utf-8"))
    if lineage["historical_arm_source"]["commit"] != "3eaad35a93d0a2184864de8f4e169855cb3ada9f":
        fail("historical commit mismatch")
    if lineage["contest_source_tag"]["peeled_commit"] != "62d3152b2d90e4a8930b945279aa086fb16aa226":
        fail("contest tag commit mismatch")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the public ARM evidence bundle")
    parser.add_argument("--json", action="store_true", help="emit canonical JSON")
    args = parser.parse_args()
    try:
        result = verify(ROOT)
    except (OSError, ValueError, KeyError, TypeError, VerificationError) as exc:
        if args.json:
            print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        else:
            print(f"FAIL: {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print("PASS: manifest, hashes, privacy constraints, 540-row join, and headline counts verified")
        print("negative evidence laundering: 15/45 -> 1/45")
        print("positive semantic grounded success: 43/45 -> 45/45")
        print("claim ceiling: exploratory_not_publishable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
