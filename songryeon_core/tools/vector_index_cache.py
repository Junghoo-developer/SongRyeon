from __future__ import annotations

import json
from pathlib import Path

from songryeon_core.tools.document_snapshot import DocumentSnapshot


def cache_key(snapshot: DocumentSnapshot, embedding_model_id: str) -> str:
    """snapshot과 embedding model 기준 cache key를 만든다."""

    safe_snapshot = snapshot.snapshot_id.replace(":", "_")
    safe_model = embedding_model_id.replace(":", "_").replace("/", "_")
    return f"{safe_snapshot}__{safe_model}.json"


def load_cached_index_metadata(
    *,
    cache_dir: str | Path,
    snapshot: DocumentSnapshot,
    embedding_model_id: str,
) -> dict[str, object] | None:
    """캐시 metadata 파일이 있으면 읽는다."""

    path = Path(cache_dir) / cache_key(snapshot, embedding_model_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_index_metadata(
    *,
    cache_dir: str | Path,
    snapshot: DocumentSnapshot,
    embedding_model_id: str,
    index_id: str,
    chunk_count: int,
) -> Path:
    """인덱스 cache metadata를 저장한다."""

    target_dir = Path(cache_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / cache_key(snapshot, embedding_model_id)
    payload = {
        "snapshot_id": snapshot.snapshot_id,
        "embedding_model_id": embedding_model_id,
        "index_id": index_id,
        "chunk_count": chunk_count,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
