# ORDER 219: Document Search Runtime Embedding Index Cache v0

## Status

Implemented on 2026-07-08.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_219_document_search_runtime_embedding_index_cache_2026_07_08_001.md`

## Goal

Reduce repeated document search cost during full smoke and live runtime by
reusing in-process document search indexes when the document snapshot has not
changed.

## Background

ORDER 218 found that the full smoke baseline is expensive partly because
`search_docs()` repeatedly scans hundreds of Markdown files, chunks them, and
builds hash embeddings.

The existing vector cache records metadata, but `EmbeddingIndex.build(...)`
still runs before cache metadata is checked. That means `cache_status=hit` did
not necessarily mean the expensive in-memory index build was avoided.

## Scope

- Add a process-local document memory index cache keyed by:
  - resolved document root
  - snapshot id
  - chunking parameters
- Add a process-local embedding index cache keyed by:
  - resolved document root
  - snapshot id
  - embedding model id
  - chunking parameters
- Reuse the cached `EmbeddingIndex` for later `search_docs()` calls in the same
  Python process.
- Reuse the cached document memory index for later `list_docs()`, `read_doc()`,
  `read_artifact()`, and `search_docs()` calls in the same Python process.
- Expose `document_memory_runtime_cache_status=hit|miss` in `search_docs()`
  results.
- Expose `runtime_index_cache_status=hit|miss` in `search_docs()` results.
- Keep the existing `cache_status=hit|miss` field for compatibility.

## Rules

- Code only caches absolute computation artifacts.
- Do not change ranking semantics.
- Do not introduce LLM judgment.
- Do not weaken document memory metadata.
- Do not change L/R routing behavior.
- Do not add persistent vector storage in this order.

## Non-Goals

- No disk-persisted vector payload cache.
- No new embedding model.
- No semantic reranker.
- No vector DB.
- No Neo4j changes.

## Completion Checks

- Repeated `search_docs()` on the same snapshot reports runtime cache hit.
- Cache miss returns a normal result and preserves metadata.
- Snapshot change creates a new runtime cache miss.
- Document memory smoke remains valid.
- `python -m compileall songryeon_core main.py`
- focused pytest for ORDER 219
- document memory smoke case remains valid
