from __future__ import annotations

from pathlib import Path

from songryeon_core.tools.workspace_policy import (
    WORKSPACE_CODE_EXTENSIONS,
    WORKSPACE_EXCLUDED_DIR_NAMES,
    iter_workspace_files,
    workspace_file_rejection_reason,
)

DEFAULT_CODE_FILE_EXTENSIONS = set(WORKSPACE_CODE_EXTENSIONS)
DEFAULT_IGNORED_DIR_NAMES = set(WORKSPACE_EXCLUDED_DIR_NAMES)


def explicit_code_file_paths_from_text(
    *,
    root: str | Path,
    text: str,
    include_extensions: list[str] | None = None,
) -> list[str]:
    """사용자 문장에 문자 그대로 등장한 실제 workspace 코드 경로만 반환한다.

    이 함수는 파일의 의미나 중요도를 추측하지 않는다. 허용 확장자의 실제 파일 목록과
    슬래시를 통일한 입력 문자열을 대조하고, 완전한 경로 토큰으로 등장한 항목만 복사한다.
    반환 순서는 사용자가 문장에 적은 순서다.
    """

    root_path = Path(root).resolve()
    allowed_extensions = _normalized_extensions(include_extensions)
    normalized_text = text.replace("\\", "/")
    matches: list[tuple[int, str]] = []
    for path in _iter_code_files(
        root_path=root_path,
        allowed_extensions=allowed_extensions,
    ):
        relative_path = _relative_posix_path(root_path=root_path, path=path)
        reference_index = _exact_path_reference_index(
            text=normalized_text,
            relative_path=relative_path,
        )
        if reference_index is not None:
            matches.append((reference_index, relative_path))
    # 같은 위치에서 실제 경로가 겹치면 긴 경로가 사용자가 쓴 전체 토큰에 더 가깝다.
    # 중요도 판단이 아니라 실제 workspace 경로 문자열의 prefix 충돌 제거다.
    matches.sort(key=lambda item: (item[0], -len(item[1]), item[1]))
    selected: list[tuple[int, str]] = []
    occupied_starts: set[int] = set()
    for index, relative_path in matches:
        if index in occupied_starts:
            continue
        occupied_starts.add(index)
        selected.append((index, relative_path))
    return [relative_path for _, relative_path in selected]


def list_code_files(
    *,
    root: str | Path,
    max_files: int = 500,
    include_extensions: list[str] | None = None,
) -> dict[str, object]:
    """Workspace 안의 읽기 가능한 코드/설정 파일 목록을 절대정보로 반환한다."""

    root_path = Path(root).resolve()
    allowed_extensions = _normalized_extensions(include_extensions)
    files: list[dict[str, object]] = []
    total_count = 0
    for path in _iter_code_files(root_path=root_path, allowed_extensions=allowed_extensions):
        total_count += 1
        if len(files) >= max_files:
            continue
        files.append(_file_listing_item(root_path=root_path, path=path))

    return {
        "root": str(root_path),
        "allowed_extensions": sorted(allowed_extensions),
        "file_count": total_count,
        "returned_file_count": len(files),
        "truncated": total_count > len(files),
        "files": files,
    }


def search_code(
    *,
    root: str | Path,
    query: str,
    max_results: int = 50,
    max_line_chars: int = 240,
    include_extensions: list[str] | None = None,
) -> dict[str, object]:
    """Workspace 코드 파일에서 단순 부분문자열 검색 결과를 절대정보로 반환한다."""

    root_path = Path(root).resolve()
    allowed_extensions = _normalized_extensions(include_extensions)
    normalized_query = query.strip()
    if not normalized_query:
        return {
            "root": str(root_path),
            "query": query,
            "match_count": 0,
            "returned_match_count": 0,
            "file_match_count": 0,
            "truncated": False,
            "results": [],
        }

    query_key = normalized_query.casefold()
    results: list[dict[str, object]] = []
    matched_files: set[str] = set()
    match_count = 0
    for path in _iter_code_files(root_path=root_path, allowed_extensions=allowed_extensions):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        relative_path = _relative_posix_path(root_path=root_path, path=path)
        for line_number, line in enumerate(lines, start=1):
            if query_key not in line.casefold():
                continue
            match_count += 1
            matched_files.add(relative_path)
            if len(results) >= max_results:
                continue
            line_text = line.strip()
            truncated = len(line_text) > max_line_chars
            results.append(
                {
                    "result_id": f"code_match_{len(results) + 1:04d}",
                    "file_path": relative_path,
                    "line_number": line_number,
                    "line_text": _truncate(line_text, max_line_chars),
                    "line_text_truncated": truncated,
                    "line_char_count": len(line_text),
                }
            )

    return {
        "root": str(root_path),
        "query": normalized_query,
        "match_count": match_count,
        "returned_match_count": len(results),
        "file_match_count": len(matched_files),
        "truncated": match_count > len(results),
        "results": results,
    }


def read_code_file(
    *,
    root: str | Path,
    file_path: str,
    max_chars: int = 12000,
    start_char: int = 0,
) -> dict[str, object]:
    """Workspace 코드 파일의 지정 문자 구간을 읽기 전용으로 반환한다.

    `range_start_char`는 포함하고 `range_end_char_exclusive`는 포함하지 않는다.
    이 구간 표기는 다음 L revision이 같은 앞부분을 다시 읽지 않도록 만드는
    절대정보 기반이다. 어느 구간이 중요한지는 이 함수가 판단하지 않는다.
    """

    if not isinstance(start_char, int) or isinstance(start_char, bool):
        raise TypeError("read_code_file.start_char must be an integer")
    if start_char < 0:
        raise ValueError("read_code_file.start_char must not be negative")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool):
        raise TypeError("read_code_file.max_chars must be an integer")
    if max_chars < 1:
        raise ValueError("read_code_file.max_chars must be positive")

    root_path = Path(root).resolve()
    resolved = _resolve_code_file(root_path=root_path, file_path=file_path)
    if resolved["status"] != "ok":
        return {
            "root": str(root_path),
            "file_path": file_path,
            "exists": False,
            "read_status": resolved["status"],
            "text": "",
            "char_count": 0,
            "total_char_count": 0,
            "returned_char_count": 0,
            "line_count": 0,
            "size_bytes": 0,
            "truncated": False,
            "truncated_before": False,
            "truncated_after": False,
            "requested_start_char": start_char,
            "range_start_char": 0,
            "range_end_char_exclusive": 0,
            "max_chars": max_chars,
        }

    path = resolved["path"]
    assert isinstance(path, Path)
    text = path.read_text(encoding="utf-8", errors="replace")
    total_char_count = len(text)
    range_start_char = min(start_char, total_char_count)
    range_end_char_exclusive = min(range_start_char + max_chars, total_char_count)
    returned_text = text[range_start_char:range_end_char_exclusive]
    truncated_before = range_start_char > 0
    truncated_after = range_end_char_exclusive < total_char_count
    return {
        "root": str(root_path),
        "file_path": _relative_posix_path(root_path=root_path, path=path),
        "exists": True,
        "read_status": "ok" if start_char <= total_char_count else "range_start_out_of_bounds",
        "text": returned_text,
        "char_count": total_char_count,
        "total_char_count": total_char_count,
        "returned_char_count": len(returned_text),
        "line_count": _line_count(text),
        "size_bytes": path.stat().st_size,
        "truncated": truncated_before or truncated_after,
        "truncated_before": truncated_before,
        "truncated_after": truncated_after,
        "requested_start_char": start_char,
        "range_start_char": range_start_char,
        "range_end_char_exclusive": range_end_char_exclusive,
        "max_chars": max_chars,
    }


def _iter_code_files(
    *,
    root_path: Path,
    allowed_extensions: set[str],
) -> list[Path]:
    if not root_path.exists():
        return []
    return iter_workspace_files(
        root=root_path,
        allowed_extensions=allowed_extensions,
    )


def _file_listing_item(*, root_path: Path, path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "file_path": _relative_posix_path(root_path=root_path, path=path),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "line_count": _line_count(text),
    }


def _resolve_code_file(*, root_path: Path, file_path: str) -> dict[str, object]:
    raw_path = Path(file_path)
    if raw_path.is_absolute():
        return {"status": "absolute_path_rejected"}
    candidate = root_path / raw_path
    reason = workspace_file_rejection_reason(
        root=root_path,
        path=candidate,
        allowed_extensions=DEFAULT_CODE_FILE_EXTENSIONS,
    )
    if reason is not None:
        return {"status": reason}
    return {"status": "ok", "path": candidate.resolve()}


def _normalized_extensions(include_extensions: list[str] | None) -> set[str]:
    if not include_extensions:
        return set(DEFAULT_CODE_FILE_EXTENSIONS)
    result: set[str] = set()
    for extension in include_extensions:
        value = extension.strip().lower()
        if not value:
            continue
        if not value.startswith("."):
            value = f".{value}"
        result.add(value)
    return result or set(DEFAULT_CODE_FILE_EXTENSIONS)


def _relative_posix_path(*, root_path: Path, path: Path) -> str:
    return path.relative_to(root_path).as_posix()


def _exact_path_reference_index(*, text: str, relative_path: str) -> int | None:
    """긴 경로 안의 짧은 파일명 조각을 별도 경로로 오인하지 않게 경계를 확인한다."""

    search_start = 0
    while True:
        index = text.find(relative_path, search_start)
        if index < 0:
            return None
        end = index + len(relative_path)
        before_ok = index == 0 or not _is_path_token_character(text[index - 1])
        after_ok = end == len(text) or not _is_path_token_character(text[end])
        if before_ok and after_ok:
            return index
        search_start = index + 1


def _is_path_token_character(character: str) -> bool:
    # 지원 파일은 허용 확장자로 끝난다. 확장자 뒤 한글은 파일명의 연장이 아니라
    # 자연어 조사일 수 있으므로 ASCII 경로 문법만 경계 판정에 사용한다.
    return character.isascii() and (
        character.isalnum() or character in {"_", "-", ".", "/"}
    )


def _line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def _truncate(text: str, max_chars: int) -> str:
    if max_chars < 4 or len(text) <= max_chars:
        return text[:max_chars]
    return f"{text[: max_chars - 3].rstrip()}..."
