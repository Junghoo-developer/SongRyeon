from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from songryeon_core.tools.workspace_policy import (
    WORKSPACE_CODE_EXTENSIONS,
    WORKSPACE_DOCUMENT_EXTENSIONS,
    iter_workspace_files,
    workspace_file_rejection_reason,
    workspace_source_kind,
)


SOURCE_TIME_METADATA_GENERATOR = "CODE:SOURCE_TIME_METADATA_INSPECTOR"
SOURCE_TIME_SCOPES = {"document", "code"}


def explicit_source_time_paths_from_text(
    *,
    document_root: str | Path,
    code_root: str | Path,
    text: str,
) -> list[dict[str, str]]:
    """사용자 문장에 정확히 적힌 실제 문서/코드 좌표만 복사한다.

    이 함수는 파일의 시간이나 중요도를 비교하지 않는다. 현재 workspace에 실제로 있는
    허용 파일의 상대경로를 사용자 입력과 문자 그대로 대조해 L2가 선택 가능한 절대 좌표
    목록만 만든다.
    """

    normalized_text = text.replace("\\", "/")
    matches: list[tuple[int, int, str, str]] = []
    for source_scope, root_value, extensions in (
        ("document", document_root, WORKSPACE_DOCUMENT_EXTENSIONS),
        ("code", code_root, WORKSPACE_CODE_EXTENSIONS),
    ):
        root = Path(root_value).resolve()
        for path in iter_workspace_files(root=root, allowed_extensions=extensions):
            source_path = path.resolve().relative_to(root).as_posix()
            aliases = [source_path, f"{root.name}/{source_path}"]
            reference_indices = [
                index
                for alias in aliases
                if (index := _exact_path_reference_index(normalized_text, alias)) is not None
            ]
            if not reference_indices:
                continue
            matches.append(
                (min(reference_indices), -len(source_path), source_scope, source_path)
            )

    matches.sort()
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _, _, source_scope, source_path in matches:
        key = (source_scope, source_path)
        if key in seen:
            continue
        seen.add(key)
        result.append({"source_scope": source_scope, "source_path": source_path})
    return result


def inspect_source_time_metadata(
    *,
    document_root: str | Path,
    code_root: str | Path,
    source_scope: str,
    source_path: str,
    observed_at_utc: str | None = None,
) -> dict[str, object]:
    """정확한 한 파일의 시간·hash를 의미 판단 없이 읽는다.

    이 함수는 어떤 파일이 최신이거나 중요하다고 고르지 않는다. 호출자가 지정한
    상대경로 하나가 안전한 읽기 경계 안에 있을 때만 절대 메타데이터를 반환한다.
    """

    if source_scope not in SOURCE_TIME_SCOPES:
        raise ValueError(f"unknown source time scope: {source_scope}")

    observation_time = observed_at_utc or datetime.now(timezone.utc).isoformat()
    root = Path(document_root if source_scope == "document" else code_root).resolve()
    allowed_extensions = (
        WORKSPACE_DOCUMENT_EXTENSIONS
        if source_scope == "document"
        else WORKSPACE_CODE_EXTENSIONS
    )
    base_payload: dict[str, object] = {
        "source_scope": source_scope,
        "requested_source_path": source_path,
        "root_path": root.as_posix(),
        "relative_path": None,
        "inspection_status": "not_inspected",
        "exists": False,
        "observed_at_utc": observation_time,
        "modified_at_utc": None,
        "size_bytes": None,
        "content_hash_sha256": None,
        "hash_algorithm": "sha256",
        "source_kind": None,
        "generated_by": SOURCE_TIME_METADATA_GENERATOR,
        "info_class": "absolute",
        "semantic_judgement_status": "not_run",
    }

    if not source_path.strip():
        return {**base_payload, "inspection_status": "empty_source_path"}

    raw_path = Path(source_path)
    if raw_path.is_absolute():
        return {**base_payload, "inspection_status": "absolute_path_rejected"}

    candidate = root / raw_path
    rejection_reason = workspace_file_rejection_reason(
        root=root,
        path=candidate,
        allowed_extensions=allowed_extensions,
    )
    if rejection_reason is not None:
        return {**base_payload, "inspection_status": rejection_reason}

    resolved = candidate.resolve()
    try:
        content = resolved.read_bytes()
        stat = resolved.stat()
    except OSError as exc:
        return {
            **base_payload,
            "inspection_status": "read_failed",
            "failure_type": type(exc).__name__,
        }

    return {
        **base_payload,
        "relative_path": resolved.relative_to(root).as_posix(),
        "inspection_status": "ok",
        "exists": True,
        "modified_at_utc": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat(),
        "size_bytes": stat.st_size,
        "content_hash_sha256": hashlib.sha256(content).hexdigest(),
        "source_kind": workspace_source_kind(resolved),
    }


def _exact_path_reference_index(text: str, path_reference: str) -> int | None:
    """긴 경로 속 부분문자열을 별도 파일 좌표로 오인하지 않게 경계를 검사한다."""

    search_start = 0
    while True:
        index = text.find(path_reference, search_start)
        if index < 0:
            return None
        end = index + len(path_reference)
        before_ok = index == 0 or not _is_path_token_character(text[index - 1])
        after_ok = end == len(text) or not _is_path_token_character(text[end])
        if before_ok and after_ok:
            return index
        search_start = index + 1


def _is_path_token_character(character: str) -> bool:
    return character.isascii() and (
        character.isalnum() or character in {"_", "-", ".", "/"}
    )


__all__ = [
    "SOURCE_TIME_METADATA_GENERATOR",
    "SOURCE_TIME_SCOPES",
    "explicit_source_time_paths_from_text",
    "inspect_source_time_metadata",
]
