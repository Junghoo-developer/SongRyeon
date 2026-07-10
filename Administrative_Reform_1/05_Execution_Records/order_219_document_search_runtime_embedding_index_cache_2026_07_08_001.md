# ORDER 219 Execution Record: Document Search Runtime Embedding Index Cache

## Date

2026-07-08

## Summary

Added process-local runtime caches for the document search path.

The previous vector cache stored metadata, but `search_docs()` still rebuilt
the in-memory embedding index before checking metadata. This order separates
metadata cache status from actual runtime index reuse.

## Changes

- Added runtime document memory index cache in `songryeon_core/tools/document_tools.py`.
- Added runtime embedding index cache in `songryeon_core/tools/document_tools.py`.
- Added `clear_runtime_document_search_caches()` for tests and diagnostics.
- Kept `cache_status` for compatibility.
- Added `metadata_cache_status`.
- Added `document_memory_runtime_cache_status`.
- Added `runtime_index_cache_status`.
- Added `tests/test_order_219_document_search_runtime_cache.py`.
- Added `Administrative_Reform_1/04_Orders/ORDER_219_DOCUMENT_SEARCH_RUNTIME_EMBEDDING_INDEX_CACHE_V0.md`.
- Updated `Administrative_Reform_1/04_Orders/README.md`.

## Timing Probe

Command shape:

```powershell
python - << equivalent inline probe calling search_docs three times
```

Measured result on `Administrative_Reform_1`:

- first call: about 4.528s, `document_memory_runtime_cache_status=miss`, `runtime_index_cache_status=miss`
- second call: about 0.255s, `document_memory_runtime_cache_status=hit`, `runtime_index_cache_status=hit`
- third call: about 0.246s, `document_memory_runtime_cache_status=hit`, `runtime_index_cache_status=hit`

Earlier probe before document-memory runtime cache:

- first call: about 4.494s
- second call: about 0.798s
- third call: about 0.880s

## Smoke Timing

`tests/smoke/test_document_memory.py` before ORDER 219 follow-up was observed
around 15-18 seconds. After runtime document search caching:

- `python -m pytest tests/smoke/test_document_memory.py -m smoke -q --durations=5`: 1 passed in 6.63s
- slowest call: about 6.48s

## Verification

- `python -m compileall songryeon_core main.py`: passed
- `python -m pytest tests/test_order_219_document_search_runtime_cache.py -q`: 3 passed
- `python -m pytest tests/smoke/test_document_memory.py -m smoke -q --durations=5`: 1 passed
- `python -m pytest tests/test_order_218_test_routine_stratification.py tests/test_order_219_document_search_runtime_cache.py tests/smoke/test_document_memory.py -m "smoke or not smoke" -q --durations=10`: 7 passed
- `python main.py quick-smoke`: passed
- `python main.py fast-test --profile core`: passed

## Not Run

Full smoke was not run in this order. ORDER 218 intentionally separated full
smoke from normal development checks, and ORDER 219 only changed document
search cache behavior.

## Remaining Risk

The first document search in a new Python process still scans files and builds
the index. This order optimizes repeated searches inside the same process. A
future order can add disk-persisted vector payload caching if the first-call
cost becomes the next bottleneck.
