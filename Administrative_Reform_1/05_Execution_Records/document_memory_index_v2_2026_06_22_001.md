# Document Memory Index v2 2026-06-22 001

## Linked Order

- `ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md`

## Result

Readable Markdown documents are now indexed as document memory, not just searched as anonymous text chunks.

Each indexed document records:

- `doc_id`
- `path`
- `content_hash`
- `snapshot_id`
- `chunk_count`
- `document_kind`
- `source_role`
- `size_bytes`
- `suffix`

## Document Kinds

The first version classifies internal documents by administrative folder:

- `philosophy`
- `maintenance_system`
- `constitution`
- `constitution_map`
- `function_map`
- `development_map`
- `map`
- `order`
- `tmp_order`
- `execution_record`
- `runtime_artifact`
- `root_index`
- `unknown`

## Source Roles

The index separates original documents from derived or administrative documents:

- `original`
- `derived_summary`
- `generated_order`
- `execution_artifact`
- `index`
- `unknown`

## Code Changes

- `songryeon_core/core/schemas.py`
  - Added `DocumentMemoryIndexFrame` and `DocumentMemoryIndexItem`.
  - Added optional document memory metadata to distilled tool items and L3 preserved candidates.
- `songryeon_core/tools/document_memory_index.py`
  - Builds, validates, classifies, and caches document memory indexes.
- `songryeon_core/tools/document_tools.py`
  - `list_docs`, `read_doc`, and `search_docs` now attach document memory metadata.
  - `search_docs` returns `document_memory_index_id`, document/source role counts, and per-result document metadata.
- `songryeon_core/tools/tool_result_distiller.py`
  - Preserves document memory metadata while compressing `search_docs` and `read_doc` outputs.
- `songryeon_core/nodes/l3_result_keeper.py`
  - Carries document memory metadata into `L3PreservedSearchCandidate`.
- `songryeon_core/runtime/smoke_test.py`
  - Verifies search/list/read metadata, cache persistence, and L3 metadata survival.

## Verification

- `python -m py_compile songryeon_core\core\schemas.py songryeon_core\tools\document_memory_index.py songryeon_core\tools\document_tools.py songryeon_core\tools\tool_result_distiller.py songryeon_core\nodes\l3_result_keeper.py songryeon_core\runtime\smoke_test.py`
- `python main.py search-docs "L3AchievementFrame" --top-k 1`
- `python main.py smoke-test`

Smoke result included:

- `document_memory_index_docs: 119`
- `document_memory_index_has_order: true`
- `document_memory_index_l3_metadata: true`

## Notes

This still does not make the agent a universal file reader. It improves the Markdown internal-document memory layer so L and later 0 can reason over what kind of document they are reading.
