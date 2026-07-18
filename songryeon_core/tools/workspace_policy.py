from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from urllib.parse import urlparse


WORKSPACE_DOCUMENT_EXTENSIONS = frozenset({".md", ".txt"})
WORKSPACE_CODE_EXTENSIONS = frozenset({".py", ".json", ".toml", ".yaml", ".yml"})
WORKSPACE_SUPPORTED_EXTENSIONS = frozenset(
    {*WORKSPACE_DOCUMENT_EXTENSIONS, *WORKSPACE_CODE_EXTENSIONS}
)

# 이 목록은 파일 의미를 추측하는 휴리스틱이 아니다. 사용자가 승인한 읽기 금지 정책이다.
WORKSPACE_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".songryeon_core_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "env",
        "node_modules",
        "venv",
    }
)
WORKSPACE_EXCLUDED_FILE_NAMES = frozenset(
    {
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "secrets.json",
        "secrets.toml",
        "secrets.yaml",
        "secrets.yml",
        "service-account.json",
    }
)
WORKSPACE_EXCLUDED_SECRET_SUFFIXES = frozenset({".key", ".p12", ".pem", ".pfx"})


def workspace_file_rejection_reason(
    *,
    root: str | Path,
    path: str | Path,
    allowed_extensions: set[str] | frozenset[str] | None = None,
) -> str | None:
    """업무 폴더 파일을 읽어도 되는지 의미 판단 없이 정책으로 검사한다."""

    root_path = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_path / candidate

    if _has_symlink_component(root_path=root_path, candidate=candidate):
        return "symbolic_link_rejected"

    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(root_path)
    except ValueError:
        return "path_outside_workspace_rejected"

    current_parent = root_path
    for part in relative.parts[:-1]:
        current_parent = current_parent / part
        if workspace_directory_is_excluded(current_parent):
            return "excluded_directory_policy"
    if not resolved.exists():
        return "not_found"
    if not resolved.is_file():
        return "not_file"

    name = resolved.name.casefold()
    if name == ".env" or name.startswith(".env."):
        return "secret_filename_policy"
    if name in WORKSPACE_EXCLUDED_FILE_NAMES:
        return "secret_filename_policy"
    if resolved.suffix.casefold() in WORKSPACE_EXCLUDED_SECRET_SUFFIXES:
        return "secret_suffix_policy"

    extensions = allowed_extensions or WORKSPACE_SUPPORTED_EXTENSIONS
    normalized_extensions = {value.casefold() for value in extensions}
    if resolved.suffix.casefold() not in normalized_extensions:
        return "unsupported_extension"
    return None


def workspace_source_kind(path: str | Path) -> str:
    """허용 확장자 정책에 따라 문서와 코드/설정 좌표를 분리한다."""

    suffix = Path(path).suffix.casefold()
    if suffix in WORKSPACE_DOCUMENT_EXTENSIONS:
        return "workspace_document"
    if suffix in WORKSPACE_CODE_EXTENSIONS:
        return "workspace_code_or_config"
    raise ValueError(f"unsupported workspace file extension: {suffix}")


def iter_workspace_files(
    *,
    root: str | Path,
    allowed_extensions: set[str] | frozenset[str],
) -> list[Path]:
    """제외 폴더를 한 번에 잘라내며 허용 파일만 안정적으로 순회한다."""

    root_path = Path(root).resolve()
    if not root_path.exists():
        return []
    normalized_extensions = {value.casefold() for value in allowed_extensions}
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root_path, followlinks=False):
        current = Path(current_root)
        safe_dirs: list[str] = []
        for dir_name in dir_names:
            directory = current / dir_name
            if directory.is_symlink() or workspace_directory_is_excluded(directory):
                continue
            try:
                directory.resolve().relative_to(root_path)
            except ValueError:
                continue
            safe_dirs.append(dir_name)
        dir_names[:] = sorted(safe_dirs)

        for file_name in sorted(file_names):
            path = current / file_name
            if path.is_symlink():
                continue
            reason = _workspace_file_name_rejection_reason(
                path=path,
                allowed_extensions=normalized_extensions,
            )
            if reason is not None:
                continue
            try:
                path.resolve().relative_to(root_path)
            except ValueError:
                continue
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root_path).as_posix())


def workspace_directory_is_excluded(path: str | Path) -> bool:
    directory = Path(path)
    if directory.name.casefold() in WORKSPACE_EXCLUDED_DIR_NAMES:
        return True
    # 가상환경의 폴더 이름은 자유롭다. pyvenv.cfg는 이름 추측이 아닌 Python의 구조 표지다.
    return (directory / "pyvenv.cfg").is_file()


def workspace_qwen_endpoint_is_local(endpoint: str | None) -> bool:
    """업무 원문을 받을 Qwen endpoint가 현재 컴퓨터 안에 있는지 검사한다."""

    if endpoint is None or not endpoint.strip():
        # endpoint가 없으면 기존 Ollama Python client를 사용하므로 로컬 경로다.
        return True
    value = endpoint.strip()
    parsed = urlparse(value if "://" in value else f"http://{value}")
    hostname = parsed.hostname
    if hostname is None:
        return False
    if hostname.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _workspace_file_name_rejection_reason(
    *,
    path: Path,
    allowed_extensions: set[str],
) -> str | None:
    name = path.name.casefold()
    if name == ".env" or name.startswith(".env."):
        return "secret_filename_policy"
    if name in WORKSPACE_EXCLUDED_FILE_NAMES:
        return "secret_filename_policy"
    if path.suffix.casefold() in WORKSPACE_EXCLUDED_SECRET_SUFFIXES:
        return "secret_suffix_policy"
    if path.suffix.casefold() not in allowed_extensions:
        return "unsupported_extension"
    return None


def _has_symlink_component(*, root_path: Path, candidate: Path) -> bool:
    """root 아래 경로 조각 중 symbolic link가 있으면 원본 접근을 막는다."""

    try:
        lexical_relative = candidate.absolute().relative_to(root_path.absolute())
    except ValueError:
        return False
    current = root_path
    for part in lexical_relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


__all__ = [
    "WORKSPACE_CODE_EXTENSIONS",
    "WORKSPACE_DOCUMENT_EXTENSIONS",
    "WORKSPACE_EXCLUDED_DIR_NAMES",
    "WORKSPACE_EXCLUDED_FILE_NAMES",
    "WORKSPACE_EXCLUDED_SECRET_SUFFIXES",
    "WORKSPACE_SUPPORTED_EXTENSIONS",
    "iter_workspace_files",
    "workspace_directory_is_excluded",
    "workspace_file_rejection_reason",
    "workspace_qwen_endpoint_is_local",
    "workspace_source_kind",
]
