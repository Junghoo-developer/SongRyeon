from __future__ import annotations

from songryeon_core.tools.document_memory_index import load_document_memory_index
from songryeon_core.tools.document_tools import list_docs, read_doc


def check_document_memory_index(
    records: dict[str, object],
    search_result: dict[str, object],
) -> dict[str, object]:
    """문서 검색 도구가 문서 메모리 인덱스 metadata를 보존하는지 확인한다."""

    index_id = search_result.get("document_memory_index_id")
    snapshot_id = search_result.get("snapshot_id")
    if not isinstance(index_id, str) or not index_id.startswith("document_memory_index:"):
        raise AssertionError("search_docs did not return document_memory_index_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("snapshot:"):
        raise AssertionError("search_docs did not return snapshot_id")

    document_count = search_result.get("document_count")
    chunk_count = search_result.get("chunk_count")
    if not isinstance(document_count, int) or document_count < 1:
        raise AssertionError("document memory index document_count is invalid")
    if not isinstance(chunk_count, int) or chunk_count < document_count:
        raise AssertionError("document memory index chunk_count is invalid")

    kind_counts = search_result.get("document_kind_counts")
    role_counts = search_result.get("source_role_counts")
    if not isinstance(kind_counts, dict) or "order" not in kind_counts:
        raise AssertionError("document memory index did not classify order documents")
    if not isinstance(role_counts, dict) or "generated_order" not in role_counts:
        raise AssertionError("document memory index did not classify generated orders")

    results = search_result.get("results")
    if not isinstance(results, list) or not results:
        raise AssertionError("search_docs results are missing")
    first_result = results[0]
    if not isinstance(first_result, dict):
        raise AssertionError("search_docs result item must be a dict")
    for field_name in (
        "document_memory_index_id",
        "content_hash",
        "chunk_count",
        "document_kind",
        "source_role",
    ):
        if not first_result.get(field_name):
            raise AssertionError(f"search_docs result misses {field_name}")

    listed_docs = list_docs(root="Administrative_Reform_1")
    order_doc = next(
        (
            item
            for item in listed_docs
            if item.get("doc_id") == "04_Orders/ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md"
        ),
        None,
    )
    if not isinstance(order_doc, dict):
        raise AssertionError("list_docs did not include ORDER_061")
    if order_doc.get("document_kind") != "order":
        raise AssertionError("list_docs did not classify ORDER_061 as order")
    if order_doc.get("source_role") != "generated_order":
        raise AssertionError("list_docs did not classify ORDER_061 as generated_order")

    read_payload = read_doc(
        root="Administrative_Reform_1",
        doc_id="04_Orders/ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md",
    )
    if read_payload.get("document_kind") != "order":
        raise AssertionError("read_doc did not preserve document_kind")
    if not read_payload.get("content_hash"):
        raise AssertionError("read_doc did not preserve content_hash")

    cached = load_document_memory_index(
        cache_dir=".songryeon_core_cache/document_memory_indexes",
        snapshot_id=snapshot_id,
    )
    if cached is None:
        raise AssertionError("document memory index cache was not saved")

    preserved = records["L3:preserved_info_frame"]
    if not isinstance(preserved, dict):
        raise AssertionError("L3 preserved payload must be a dict")
    candidates = preserved.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AssertionError("L3 candidates are missing")
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise AssertionError("L3 candidate must be a dict")
    l3_metadata = bool(
        first_candidate.get("document_kind")
        and first_candidate.get("source_role")
        and first_candidate.get("document_memory_index_id")
        and first_candidate.get("snapshot_id")
    )
    if not l3_metadata:
        raise AssertionError("L3 candidate did not preserve document memory metadata")

    return {
        "document_count": document_count,
        "has_order": True,
        "l3_metadata": True,
    }
