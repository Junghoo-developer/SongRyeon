from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from songryeon_core.tools.workspace_policy import (
    WORKSPACE_DOCUMENT_EXTENSIONS,
    iter_workspace_files,
    workspace_file_rejection_reason,
)


@dataclass
class DocumentRecord:
    """읽기 전용 문서 하나의 절대정보."""

    doc_id: str
    path: str
    suffix: str
    exists: bool
    size_bytes: int


@dataclass
class DocumentChunk:
    """문서 검색용으로 나눈 chunk 하나."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int


def list_markdown_docs(root: str | Path) -> list[DocumentRecord]:
    """root 아래의 허용된 Markdown/텍스트 문서를 doc_id 기준으로 목록화한다."""

    safe_root = _resolve_root(root)
    records: list[DocumentRecord] = []
    for path in iter_workspace_files(
        root=safe_root,
        allowed_extensions=WORKSPACE_DOCUMENT_EXTENSIONS,
    ):
        relative = path.relative_to(safe_root).as_posix()
        stat = path.stat()
        records.append(
            DocumentRecord(
                doc_id=relative,
                path=str(path),
                suffix=path.suffix,
                exists=True,
                size_bytes=stat.st_size,
            )
        )
    return records


def read_markdown_doc(root: str | Path, doc_id: str) -> str:
    """root 아래의 doc_id Markdown/텍스트 문서를 UTF-8로 읽는다."""

    safe_root = _resolve_root(root)
    path = _resolve_doc_path(safe_root, doc_id)
    return path.read_text(encoding="utf-8-sig", errors="replace")


def chunk_markdown_docs(
    root: str | Path,
    *,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[DocumentChunk]:
    """허용된 Markdown/텍스트 문서를 단순 문자 길이 기준으로 chunk로 나눈다."""

    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be >= 0")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be smaller than max_chars")

    chunks: list[DocumentChunk] = []
    for doc in list_markdown_docs(root):
        text = read_markdown_doc(root, doc.doc_id)
        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk_text = text[start:end]
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc.doc_id}#chunk_{chunk_index:04d}",
                    doc_id=doc.doc_id,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    char_start=start,
                    char_end=end,
                )
            )
            if end == len(text):
                break
            start = end - overlap_chars
            chunk_index += 1
    return chunks


def _resolve_root(root: str | Path) -> Path:
    """문서 루트를 절대 경로로 바꾸고 존재 여부를 확인한다."""

    safe_root = Path(root).resolve()
    if not safe_root.exists():
        raise FileNotFoundError(f"document root does not exist: {safe_root}")
    if not safe_root.is_dir():
        raise NotADirectoryError(f"document root is not a directory: {safe_root}")
    return safe_root


def _resolve_doc_path(root: Path, doc_id: str) -> Path:
    """doc_id가 root 밖으로 빠져나가지 못하게 경로를 검증한다."""

    if not doc_id:
        raise ValueError("doc_id must not be empty")
    path = root / doc_id
    reason = workspace_file_rejection_reason(
        root=root,
        path=path,
        allowed_extensions=WORKSPACE_DOCUMENT_EXTENSIONS,
    )
    if reason == "path_outside_workspace_rejected":
        raise ValueError(f"doc_id escapes document root: {doc_id}")
    if reason == "not_found":
        raise FileNotFoundError(f"document does not exist: {doc_id}")
    if reason == "not_file":
        raise FileNotFoundError(f"document is not a file: {doc_id}")
    if reason is not None:
        raise ValueError(f"document rejected by workspace policy ({reason}): {doc_id}")
    return path.resolve()
