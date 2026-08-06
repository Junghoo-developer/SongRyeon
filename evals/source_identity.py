"""평가 대상 SUT source tree의 결정론적 식별값을 계산한다.

특정 실험의 protocol이나 채점 로직에 의존하지 않고, 평가 실행 전에
동일한 source 집합을 사용하고 있는지 확인할 때 공통으로 사용한다.
"""

import hashlib
import json

from .runner import PROJECT_DIRECTORY, _portable_text_sha256


REQUIRED_SUT_PYTHON_ROOTS = (
    "agent_tools",
    "demo",
    "knowledge",
    "llm",
    "memory",
    "nodes",
    "prompts",
    "runtime",
)
REQUIRED_SUT_FILES = (
    "evals/__init__.py",
    "evals/evaluator.py",
    "evals/live_capture.py",
    "evals/runner.py",
    "evals/schema.py",
    "evals/source_identity.py",
    "evals/summary.py",
    "evals/variants.py",
)


def _resolve_inside(root, relative_path, label):
    root = root.resolve(strict=True)
    path = (root / relative_path).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label}이 허용 폴더 밖을 가리킵니다.") from error
    return path


def _system_source_entries(roots, files):
    entries = {}
    project_root = PROJECT_DIRECTORY.resolve(strict=True)
    for relative_root in roots:
        root = _resolve_inside(project_root, relative_root, "SUT root")
        if not root.is_dir():
            raise ValueError("SUT root는 폴더여야 합니다.")
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(project_root).as_posix()
            entries[relative] = _portable_text_sha256(path)

    for relative_file in files:
        path = _resolve_inside(project_root, relative_file, "SUT file")
        if not path.is_file():
            raise ValueError("SUT file은 파일이어야 합니다.")
        relative = path.relative_to(project_root).as_posix()
        entries[relative] = _portable_text_sha256(path)

    return [
        {"path": path, "sha256": entries[path]}
        for path in sorted(entries)
    ]


def _tree_sha256(entries):
    payload = json.dumps(
        entries,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def current_system_source_identity():
    """동결 대상 SUT source의 현재 파일 수와 tree SHA-256을 반환한다."""

    entries = _system_source_entries(
        REQUIRED_SUT_PYTHON_ROOTS,
        REQUIRED_SUT_FILES,
    )
    return {
        "include_python_roots": list(REQUIRED_SUT_PYTHON_ROOTS),
        "include_files": list(REQUIRED_SUT_FILES),
        "file_count": len(entries),
        "tree_sha256": _tree_sha256(entries),
    }


__all__ = [
    "REQUIRED_SUT_FILES",
    "REQUIRED_SUT_PYTHON_ROOTS",
    "current_system_source_identity",
]
