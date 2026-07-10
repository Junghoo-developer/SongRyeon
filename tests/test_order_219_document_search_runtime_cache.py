from __future__ import annotations

from songryeon_core.tools.document_tools import (
    clear_runtime_document_search_caches,
    search_docs,
)


def test_search_docs_reuses_runtime_embedding_index_for_same_snapshot(tmp_path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "alpha.md").write_text("alpha beta gamma", encoding="utf-8")
    (root / "beta.md").write_text("beta gamma delta", encoding="utf-8")
    clear_runtime_document_search_caches()

    first = search_docs(root=root, query="alpha", top_k=1)
    second = search_docs(root=root, query="alpha", top_k=1)

    assert first["document_memory_runtime_cache_status"] == "miss"
    assert second["document_memory_runtime_cache_status"] == "hit"
    assert first["runtime_index_cache_status"] == "miss"
    assert second["runtime_index_cache_status"] == "hit"
    assert first["index_id"] == second["index_id"]
    assert first["snapshot_id"] == second["snapshot_id"]
    assert second["result_count"] == 1


def test_search_docs_runtime_cache_misses_after_snapshot_change(tmp_path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    target = root / "alpha.md"
    target.write_text("alpha beta gamma", encoding="utf-8")
    clear_runtime_document_search_caches()

    first = search_docs(root=root, query="alpha", top_k=1)
    target.write_text("alpha beta gamma changed", encoding="utf-8")
    second = search_docs(root=root, query="alpha", top_k=1)

    assert first["document_memory_runtime_cache_status"] == "miss"
    assert second["document_memory_runtime_cache_status"] == "miss"
    assert first["runtime_index_cache_status"] == "miss"
    assert second["runtime_index_cache_status"] == "miss"
    assert first["snapshot_id"] != second["snapshot_id"]


def test_search_docs_preserves_legacy_cache_status_field(tmp_path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "alpha.md").write_text("alpha beta gamma", encoding="utf-8")
    clear_runtime_document_search_caches()

    result = search_docs(root=root, query="alpha", top_k=1)

    assert result["cache_status"] in {"hit", "miss"}
    assert result["metadata_cache_status"] == result["cache_status"]
    assert result["document_memory_runtime_cache_status"] in {"hit", "miss"}
    assert result["runtime_index_cache_status"] in {"hit", "miss"}
