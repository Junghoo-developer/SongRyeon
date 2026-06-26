from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.tools.document_loader import list_markdown_docs, read_markdown_doc
from songryeon_core.tools.document_memory_index import (
    build_document_memory_index,
    item_by_doc_id,
    save_document_memory_index,
)
from songryeon_core.tools.document_snapshot import build_document_snapshot
from songryeon_core.tools.embedding_store import EmbeddingIndex
from songryeon_core.tools.vector_index_cache import load_cached_index_metadata, save_index_metadata


DOCUMENT_MEMORY_INDEX_CACHE_DIR = Path(".songryeon_core_cache/document_memory_indexes")


def list_docs(*, root: str | Path) -> list[dict[str, object]]:
    """읽기 가능한 Markdown 문서 목록을 돌려준다."""

    memory_index = _build_and_cache_document_memory_index(root)
    index_items = item_by_doc_id(memory_index)
    docs: list[dict[str, object]] = []
    for record in list_markdown_docs(root):
        payload = asdict(record)
        item = index_items.get(record.doc_id)
        if item is not None:
            payload.update(_document_memory_payload(memory_index_id=memory_index.index_id, item=item))
        docs.append(payload)
    return docs


def read_doc(*, root: str | Path, doc_id: str) -> dict[str, object]:
    """특정 Markdown 문서의 원문을 돌려준다."""

    memory_index = _build_and_cache_document_memory_index(root)
    item = item_by_doc_id(memory_index).get(doc_id)
    text = read_markdown_doc(root, doc_id)
    payload = {
        "doc_id": doc_id,
        "text": text,
        "char_count": len(text),
    }
    if item is not None:
        payload.update(_document_memory_payload(memory_index_id=memory_index.index_id, item=item))
    return payload


def read_artifact(*, root: str | Path, artifact_ref: str) -> dict[str, object]:
    """Read one Markdown artifact by an explicit file/path reference.

    This tool is intentionally strict. It does not perform semantic search; it
    only resolves visible artifact references such as a doc_id, file name, or
    file stem against the document memory index.
    """

    memory_index = _build_and_cache_document_memory_index(root)
    index_items = item_by_doc_id(memory_index)
    normalized_ref = _normalize_artifact_ref(artifact_ref)
    candidates = _artifact_candidates(
        root=root,
        normalized_ref=normalized_ref,
        memory_index_id=memory_index.index_id,
        index_items=index_items,
    )

    payload: dict[str, object] = {
        "artifact_ref": artifact_ref,
        "normalized_ref": normalized_ref,
        "match_status": "not_found",
        "match_type": None,
        "candidate_count": len(candidates),
        "selected_doc_id": None,
        "doc_id": None,
        "text": "",
        "char_count": 0,
        "candidates": candidates,
        "document_memory_index_id": memory_index.index_id,
        "snapshot_id": memory_index.snapshot_id,
        "document_count": memory_index.total_docs,
    }
    if not normalized_ref:
        payload["match_status"] = "invalid_ref"
        return payload
    if not candidates:
        return payload

    best_rank = min(_ARTIFACT_MATCH_RANK.get(str(item["match_type"]), 99) for item in candidates)
    best_candidates = [
        item
        for item in candidates
        if _ARTIFACT_MATCH_RANK.get(str(item["match_type"]), 99) == best_rank
    ]
    if len(best_candidates) != 1:
        payload["match_status"] = "ambiguous"
        payload["candidate_count"] = len(best_candidates)
        payload["candidates"] = best_candidates
        return payload

    selected = best_candidates[0]
    doc_id = str(selected["doc_id"])
    text = read_markdown_doc(root, doc_id)
    payload.update(
        {
            "match_status": "unique",
            "match_type": selected["match_type"],
            "candidate_count": 1,
            "selected_doc_id": doc_id,
            "doc_id": doc_id,
            "text": text,
            "char_count": len(text),
            "candidates": best_candidates,
        }
    )
    item = index_items.get(doc_id)
    if item is not None:
        payload.update(_document_memory_payload(memory_index_id=memory_index.index_id, item=item))
    return payload


def search_docs(
    *,
    root: str | Path,
    query: str,
    top_k: int = 5,
) -> dict[str, object]:
    """문서 chunk 임베딩을 만들고 query와 가까운 chunk를 찾는다."""

    memory_index = _build_and_cache_document_memory_index(root)
    index_items = item_by_doc_id(memory_index)
    snapshot = build_document_snapshot(root)
    index = EmbeddingIndex.build(str(root))
    cache_dir = Path(".songryeon_core_cache/vector_indexes")
    cached = load_cached_index_metadata(
        cache_dir=cache_dir,
        snapshot=snapshot,
        embedding_model_id=index.model.model_id,
    )
    cache_status = "hit" if cached is not None else "miss"
    if cached is None:
        save_index_metadata(
            cache_dir=cache_dir,
            snapshot=snapshot,
            embedding_model_id=index.model.model_id,
            index_id=index.index_id,
            chunk_count=len(index.embedded_chunks),
        )
    results = index.search(query, top_k=top_k)
    result_payloads: list[dict[str, object]] = []
    for result in results:
        payload = asdict(result)
        item = index_items.get(result.doc_id)
        if item is not None:
            payload.update(_document_memory_payload(memory_index_id=memory_index.index_id, item=item))
        result_payloads.append(payload)
    return {
        "query": query,
        "top_k": top_k,
        "index_id": index.index_id,
        "document_memory_index_id": memory_index.index_id,
        "embedding_model_id": index.model.model_id,
        "snapshot_id": snapshot.snapshot_id,
        "document_count": memory_index.total_docs,
        "chunk_count": memory_index.total_chunks,
        "document_kind_counts": _count_field(memory_index.items, "document_kind"),
        "source_role_counts": _count_field(memory_index.items, "source_role"),
        "cache_status": cache_status,
        "result_count": len(results),
        "results": result_payloads,
    }


def _build_and_cache_document_memory_index(root: str | Path):
    """문서 메모리 인덱스를 만들고 cache metadata로 남긴다."""

    frame = build_document_memory_index(root)
    save_document_memory_index(cache_dir=DOCUMENT_MEMORY_INDEX_CACHE_DIR, frame=frame)
    return frame


def _document_memory_payload(*, memory_index_id: str, item) -> dict[str, object]:
    """도구 결과에 붙일 문서 메모리 메타정보를 만든다."""

    return {
        "document_memory_index_id": memory_index_id,
        "snapshot_id": item.snapshot_id,
        "content_hash": item.content_hash,
        "chunk_count": item.chunk_count,
        "document_kind": item.document_kind,
        "source_role": item.source_role,
    }


def _count_field(items: list[object], field_name: str) -> dict[str, int]:
    """문서 종류나 source role의 개수를 세어 도구 결과 요약에 넣는다."""

    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, field_name)
        counts[value] = counts.get(value, 0) + 1
    return counts


_ARTIFACT_MATCH_RANK = {
    "doc_id_exact": 1,
    "doc_id_without_suffix_exact": 2,
    "path_suffix_exact": 3,
    "filename_exact": 4,
    "filename_stem_exact": 5,
}


def _artifact_candidates(
    *,
    root: str | Path,
    normalized_ref: str,
    memory_index_id: str,
    index_items: dict[str, object],
) -> list[dict[str, object]]:
    if not normalized_ref:
        return []

    candidates: list[dict[str, object]] = []
    for record in list_markdown_docs(root):
        match_type = _artifact_match_type(normalized_ref, record.doc_id)
        if match_type is None:
            continue
        payload: dict[str, object] = {
            "doc_id": record.doc_id,
            "path": record.path,
            "match_type": match_type,
            "suffix": record.suffix,
            "size_bytes": record.size_bytes,
        }
        item = index_items.get(record.doc_id)
        if item is not None:
            payload.update(_document_memory_payload(memory_index_id=memory_index_id, item=item))
        candidates.append(payload)

    candidates.sort(
        key=lambda item: (
            _ARTIFACT_MATCH_RANK.get(str(item["match_type"]), 99),
            str(item["doc_id"]),
        )
    )
    return candidates


def _artifact_match_type(normalized_ref: str, doc_id: str) -> str | None:
    normalized_doc = _normalize_artifact_ref(doc_id)
    normalized_doc_no_suffix = _strip_md_suffix(normalized_doc)
    normalized_ref_no_suffix = _strip_md_suffix(normalized_ref)
    filename = normalized_doc.rsplit("/", 1)[-1]
    filename_no_suffix = _strip_md_suffix(filename)

    if normalized_ref == normalized_doc:
        return "doc_id_exact"
    if normalized_ref_no_suffix == normalized_doc_no_suffix:
        return "doc_id_without_suffix_exact"
    if "/" in normalized_ref and (
        normalized_doc.endswith(normalized_ref)
        or normalized_doc_no_suffix.endswith(normalized_ref_no_suffix)
    ):
        return "path_suffix_exact"
    if normalized_ref == filename:
        return "filename_exact"
    if normalized_ref_no_suffix == filename_no_suffix:
        return "filename_stem_exact"
    return None


def _normalize_artifact_ref(value: str) -> str:
    normalized = str(value or "").strip().strip("`'\"").replace("\\", "/")
    normalized = normalized.strip().strip("/")
    normalized = normalized.removeprefix("Administrative_Reform_1/")
    return normalized.lower()


def _strip_md_suffix(value: str) -> str:
    return value[:-3] if value.endswith(".md") else value
