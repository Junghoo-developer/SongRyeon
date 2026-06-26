from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.schemas import (
    DocumentMemoryIndexFrame,
    DocumentMemoryIndexItem,
    validate_document_memory_index_frame,
)
from songryeon_core.tools.document_loader import chunk_markdown_docs, list_markdown_docs
from songryeon_core.tools.document_snapshot import build_document_snapshot


def build_document_memory_index(
    root: str | Path,
    *,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> DocumentMemoryIndexFrame:
    """Build a metadata index for every readable Markdown document."""

    root_path = Path(root).resolve()
    snapshot = build_document_snapshot(root_path)
    hash_by_doc_id = {
        item.doc_id: item.content_hash
        for item in snapshot.items
    }
    chunk_counts = Counter(
        chunk.doc_id
        for chunk in chunk_markdown_docs(
            root_path,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
    )

    items: list[DocumentMemoryIndexItem] = []
    for record in list_markdown_docs(root_path):
        items.append(
            DocumentMemoryIndexItem(
                doc_id=record.doc_id,
                path=record.path,
                content_hash=hash_by_doc_id[record.doc_id],
                snapshot_id=snapshot.snapshot_id,
                chunk_count=chunk_counts[record.doc_id],
                document_kind=classify_document_kind(record.doc_id),
                source_role=classify_source_role(record.doc_id),
                size_bytes=record.size_bytes,
                suffix=record.suffix,
            )
        )

    frame = DocumentMemoryIndexFrame(
        index_id=document_memory_index_id(snapshot.snapshot_id),
        root=str(root_path),
        snapshot_id=snapshot.snapshot_id,
        total_docs=len(items),
        total_chunks=sum(item.chunk_count for item in items),
        items=items,
    )
    validate_document_memory_index_frame(frame)
    return frame


def document_memory_index_id(snapshot_id: str) -> str:
    """Return the stable index ID for a document snapshot."""

    return f"document_memory_index:{snapshot_id}"


def save_document_memory_index(
    *,
    cache_dir: str | Path,
    frame: DocumentMemoryIndexFrame,
) -> Path:
    """Persist the document memory index payload as cache metadata."""

    target_dir = Path(cache_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / _cache_file_name(frame.snapshot_id)
    path.write_text(json.dumps(asdict(frame), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_document_memory_index(
    *,
    cache_dir: str | Path,
    snapshot_id: str,
) -> dict[str, object] | None:
    """Load cached document memory index metadata if it exists."""

    path = Path(cache_dir) / _cache_file_name(snapshot_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("document memory index cache payload must be a dict")
    return payload


def classify_document_kind(doc_id: str) -> str:
    """Classify a readable document by its administrative folder path."""

    normalized = doc_id.replace("\\", "/")
    if normalized == "README.md":
        return "root_index"
    if normalized.startswith("00_Philosophy/"):
        return "philosophy"
    if normalized.startswith("01_Maintenance_System/"):
        return "maintenance_system"
    if normalized.startswith("02_Constitutions/"):
        return "constitution"
    if normalized.startswith("03_Maps/01_Constitution_Maps/"):
        return "constitution_map"
    if normalized.startswith("03_Maps/02_Function_Maps/"):
        return "function_map"
    if normalized.startswith("03_Maps/03_Development_Maps/"):
        return "development_map"
    if normalized.startswith("03_Maps/"):
        return "map"
    if normalized.startswith("04_Orders/TMP_"):
        return "tmp_order"
    if normalized.startswith("04_Orders/"):
        return "order"
    if normalized.startswith("05_Execution_Records/runtime_runs/"):
        return "runtime_artifact"
    if normalized.startswith("05_Execution_Records/"):
        return "execution_record"
    return "unknown"


def classify_source_role(doc_id: str) -> str:
    """Separate original documents from summaries, generated orders, and artifacts."""

    normalized = doc_id.replace("\\", "/")
    lowered_name = Path(normalized).name.lower()
    lowered = normalized.lower()
    if lowered_name == "readme.md":
        return "index"
    if any(token in lowered for token in ("summary", "report", "reflection", "capsule")):
        return "derived_summary"
    if normalized.startswith("04_Orders/"):
        return "generated_order"
    if normalized.startswith("05_Execution_Records/"):
        return "execution_artifact"
    if normalized.startswith("00_Philosophy/") or normalized.startswith("01_Maintenance_System/"):
        return "original"
    if normalized.startswith("02_Constitutions/") or normalized.startswith("03_Maps/"):
        return "original"
    return "unknown"


def item_by_doc_id(frame: DocumentMemoryIndexFrame) -> dict[str, DocumentMemoryIndexItem]:
    """Return a quick lookup table for index items."""

    return {item.doc_id: item for item in frame.items}


def _cache_file_name(snapshot_id: str) -> str:
    safe_snapshot_id = snapshot_id.replace(":", "_").replace("/", "_")
    return f"{safe_snapshot_id}.json"
