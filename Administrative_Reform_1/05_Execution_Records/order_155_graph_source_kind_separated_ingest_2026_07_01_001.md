# ORDER 155 Graph Source Kind Separated Ingest - Execution Record 2026-07-01 001

## Scope

Implemented the first graph source ingest foundation for non-conversation materials.

This order keeps source kinds separated before any later night-government summary or R traversal work.

Initial source kinds:

- `internal_document`
- `source_code_file`
- `external_project_file`

Conversation turns still use the existing `raw_capsule` graph path.

## Changes

- Added `songryeon_core/core/graph_source_ingest.py`.
- Added graph node kinds:
  - `raw_source`
  - `source_kind_bundle`
- Added validation for raw source leaves and source-kind bundle child counts.
- Added source-kind-separated ingest tests in `tests/test_order_155_graph_source_kind_ingest.py`.
- Added the new module to the import baseline.
- Added the ORDER 155 test to `fast-test --profile graph`.
- Documented the order in `Administrative_Reform_1/04_Orders/ORDER_155_GRAPH_SOURCE_KIND_SEPARATED_INGEST_FOUNDATION_V0.md`.

## Data Boundary

The code writes only absolute source coordinates:

- source kind
- normalized path
- file name
- suffix
- exists flag
- char count
- content SHA-1
- deterministic source file data ID
- deterministic raw source graph node ID
- source-kind bundle node ID
- `CONTAINS` edge ID

The code does not write:

- semantic topic
- summary
- importance score
- relevance judgment
- meaning cluster

## Verification

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_import_baseline.py -q
# 7 passed

python main.py fast-test --profile graph
# FAST_TEST_OK
# pytest:graph: 26 passed
```

## Not Opened

- Neo4j/Vessel connection
- night-government summary worker
- semantic axis
- R LLM selector over these bundles
- node_3 answer injection
- conversation ingest replacement
