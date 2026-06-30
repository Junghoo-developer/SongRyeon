from __future__ import annotations

from pathlib import Path


DEFAULT_CODE_FILE_EXTENSIONS = {
    ".py",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
}
DEFAULT_IGNORED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


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
) -> dict[str, object]:
    """Workspace 안의 코드 파일 하나를 읽기 전용으로 반환한다."""

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
            "line_count": 0,
            "size_bytes": 0,
            "truncated": False,
            "max_chars": max_chars,
        }

    path = resolved["path"]
    assert isinstance(path, Path)
    text = path.read_text(encoding="utf-8", errors="replace")
    returned_text = text[:max_chars]
    return {
        "root": str(root_path),
        "file_path": _relative_posix_path(root_path=root_path, path=path),
        "exists": True,
        "read_status": "ok",
        "text": returned_text,
        "char_count": len(text),
        "line_count": _line_count(text),
        "size_bytes": path.stat().st_size,
        "truncated": len(text) > len(returned_text),
        "max_chars": max_chars,
    }


def _iter_code_files(
    *,
    root_path: Path,
    allowed_extensions: set[str],
) -> list[Path]:
    if not root_path.exists():
        return []
    files: list[Path] = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if _has_ignored_part(path):
            continue
        if path.suffix.lower() not in allowed_extensions:
            continue
        files.append(path)
    return sorted(files, key=lambda item: _relative_posix_path(root_path=root_path, path=item))


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
    candidate = (root_path / raw_path).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        return {"status": "path_outside_workspace_rejected"}
    if _has_ignored_part(candidate):
        return {"status": "ignored_path_rejected"}
    if not candidate.exists():
        return {"status": "not_found"}
    if not candidate.is_file():
        return {"status": "not_file"}
    if candidate.suffix.lower() not in DEFAULT_CODE_FILE_EXTENSIONS:
        return {"status": "unsupported_extension"}
    return {"status": "ok", "path": candidate}


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


def _has_ignored_part(path: Path) -> bool:
    return any(part in DEFAULT_IGNORED_DIR_NAMES for part in path.parts)


def _relative_posix_path(*, root_path: Path, path: Path) -> str:
    return path.relative_to(root_path).as_posix()


def _line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def _truncate(text: str, max_chars: int) -> str:
    if max_chars < 4 or len(text) <= max_chars:
        return text[:max_chars]
    return f"{text[: max_chars - 3].rstrip()}..."
