from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    """root 아래의 Markdown 문서를 doc_id 기준으로 목록화한다."""

    safe_root = _resolve_root(root)
    records: list[DocumentRecord] = []
    for path in sorted(safe_root.rglob("*.md")):
        if not path.is_file():
            continue
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
    """root 아래의 doc_id 문서를 UTF-8 텍스트로 읽는다."""

    safe_root = _resolve_root(root)
    path = _resolve_doc_path(safe_root, doc_id)
    return path.read_text(encoding="utf-8")


def chunk_markdown_docs(
    root: str | Path,
    *,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[DocumentChunk]:
    """Markdown 문서들을 단순 문자 길이 기준으로 chunk로 나눈다."""

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
    path = (root / doc_id).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"doc_id escapes document root: {doc_id}")
    if not path.exists():
        raise FileNotFoundError(f"document does not exist: {doc_id}")
    if not path.is_file():
        raise FileNotFoundError(f"document is not a file: {doc_id}")
    if path.suffix.lower() != ".md":
        raise ValueError(f"document is not markdown: {doc_id}")
    return path
