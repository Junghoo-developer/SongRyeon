from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.tools.document_loader import list_markdown_docs


@dataclass
class DocumentSnapshotItem:
    """문서 하나의 변경 감지용 metadata."""

    doc_id: str
    size_bytes: int
    content_hash: str


@dataclass
class DocumentSnapshot:
    """문서 루트 전체의 snapshot."""

    snapshot_id: str
    root: str
    items: list[DocumentSnapshotItem]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_document_snapshot(root: str | Path) -> DocumentSnapshot:
    """Markdown 문서들의 content hash로 snapshot_id를 만든다."""

    root_path = Path(root).resolve()
    items: list[DocumentSnapshotItem] = []
    digest = hashlib.sha256()
    for record in list_markdown_docs(root_path):
        path = Path(record.path)
        content = path.read_bytes()
        content_hash = hashlib.sha256(content).hexdigest()
        items.append(
            DocumentSnapshotItem(
                doc_id=record.doc_id,
                size_bytes=record.size_bytes,
                content_hash=content_hash,
            )
        )
        digest.update(record.doc_id.encode("utf-8"))
        digest.update(content_hash.encode("utf-8"))
    return DocumentSnapshot(
        snapshot_id=f"snapshot:{digest.hexdigest()[:16]}",
        root=str(root_path),
        items=items,
    )
