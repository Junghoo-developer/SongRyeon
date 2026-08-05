"""model-scale evidence pack의 경로·SHA-256·coverage를 오프라인 검증한다."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .model_scale_capture import (
    ARTIFACT_MANIFEST_FILENAME,
    BLIND_KEY_FILENAME,
    CAPTURE_FILENAME,
    EXPERIMENT_KIND,
    PROTOCOL_FILENAME,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path, label):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}을 읽을 수 없습니다.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label}의 최상위 값은 JSON 객체여야 합니다.")
    return value


def _resolve_artifact(root, relative_path):
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("artifact path는 비어 있지 않은 문자열이어야 합니다.")
    candidate = (root / Path(relative_path)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("artifact path가 evidence pack 밖을 가리킵니다.") from error
    if not candidate.is_file():
        raise ValueError(f"artifact 파일이 없습니다: {relative_path}")
    return candidate


def verify_evidence_pack(directory):
    """모든 선언 파일과 내부 run 연결이 바뀌지 않았는지 검사한다."""

    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("evidence pack 경로는 폴더여야 합니다.")
    manifest_path = root / ARTIFACT_MANIFEST_FILENAME
    artifact_manifest = _read_json(manifest_path, "artifact_manifest")
    entries = artifact_manifest.get("artifacts")
    if not isinstance(entries, list):
        raise ValueError("artifact_manifest.artifacts는 배열이어야 합니다.")
    if artifact_manifest.get("artifact_count") != len(entries):
        raise ValueError("artifact_count가 실제 선언 수와 다릅니다.")

    declared_paths = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "path",
            "sha256",
            "byte_count",
        }:
            raise ValueError("artifact 선언 형식이 올바르지 않습니다.")
        relative_path = entry["path"]
        if relative_path in declared_paths:
            raise ValueError(f"artifact path가 중복됐습니다: {relative_path}")
        declared_paths.add(relative_path)
        path = _resolve_artifact(root, relative_path)
        if path.stat().st_size != entry["byte_count"]:
            raise ValueError(f"artifact byte_count가 다릅니다: {relative_path}")
        if _sha256(path) != entry["sha256"]:
            raise ValueError(f"artifact SHA-256이 다릅니다: {relative_path}")

    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != ARTIFACT_MANIFEST_FILENAME
        and not path.name.endswith(".tmp")
    }
    if actual_paths != declared_paths:
        raise ValueError("artifact 파일 집합이 manifest와 다릅니다.")

    protocol_path = root / PROTOCOL_FILENAME
    capture_path = root / CAPTURE_FILENAME
    blind_key_path = root / BLIND_KEY_FILENAME
    protocol = _read_json(protocol_path, "protocol")
    capture = _read_json(capture_path, "capture")
    if protocol.get("experiment_kind") != EXPERIMENT_KIND:
        raise ValueError("protocol experiment_kind가 다릅니다.")
    if capture.get("experiment_kind") != EXPERIMENT_KIND:
        raise ValueError("capture experiment_kind가 다릅니다.")
    if _sha256(protocol_path) != capture.get("protocol_sha256"):
        raise ValueError("capture의 protocol SHA-256 연결이 다릅니다.")
    if _sha256(blind_key_path) != capture.get("blind_key_file_sha256"):
        raise ValueError("capture의 blind key SHA-256 연결이 다릅니다.")

    schedule = capture.get("schedule")
    captures = capture.get("captures")
    coverage = capture.get("coverage")
    if not isinstance(schedule, list) or not isinstance(captures, list):
        raise ValueError("schedule과 captures는 배열이어야 합니다.")
    if not isinstance(coverage, dict):
        raise ValueError("coverage는 객체여야 합니다.")
    planned_ids = [item.get("run_id") for item in schedule]
    captured_ids = [item.get("run_id") for item in captures]
    if len(set(planned_ids)) != len(planned_ids):
        raise ValueError("schedule run_id가 중복됐습니다.")
    if len(set(captured_ids)) != len(captured_ids):
        raise ValueError("capture run_id가 중복됐습니다.")
    if planned_ids != captured_ids:
        raise ValueError("schedule과 capture run 순서 또는 coverage가 다릅니다.")
    if coverage.get("planned_run_count") != len(schedule):
        raise ValueError("planned_run_count가 다릅니다.")
    if coverage.get("captured_run_count") != len(captures):
        raise ValueError("captured_run_count가 다릅니다.")

    for captured in captures:
        for field in ("raw_memory_artifact", "transcript_artifact"):
            artifact = captured.get(field)
            if not isinstance(artifact, dict):
                raise ValueError(f"{field} 연결이 없습니다.")
            artifact_path = _resolve_artifact(root, artifact.get("path"))
            if _sha256(artifact_path) != artifact.get("sha256"):
                raise ValueError(f"{field} SHA-256 연결이 다릅니다.")

    return {
        "verified": True,
        "artifact_count": len(entries),
        "run_count": len(captures),
        "protocol_sha256": _sha256(protocol_path),
        "artifact_manifest_sha256": _sha256(manifest_path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SongRyeon model-scale evidence pack을 오프라인 검증합니다."
    )
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_evidence_pack(args.directory)
    except (OSError, TypeError, ValueError) as error:
        print(f"evidence pack 검증 실패: {error}", file=sys.stderr)
        return 1
    print(
        "evidence pack 검증 완료: "
        f"runs={result['run_count']}, artifacts={result['artifact_count']}, "
        f"protocol={result['protocol_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
