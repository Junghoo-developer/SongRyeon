# ORDER 156 Graph Source Observation Time And CoreEgo Link - Execution Record 2026-07-01 001

## Scope

Implemented observation-time metadata and CoreEgo time-axis linkage for source-kind separated graph ingest.

This makes raw source graph nodes represent a specific filesystem observation, not a timeless claim about the current file.

## Changes

- Added graph node kind:
  - `source_ingest_time_bundle`
- Added optional observation fields to `GraphMemoryNodeFrame`:
  - `observed_at`
  - `ingested_at`
  - `source_last_modified_at`
  - `exists_at_ingest`
  - `content_sha1`
- Required those fields for `raw_source` graph nodes.
- Required `observed_at` and `ingested_at` for `source_kind_bundle` and `source_ingest_time_bundle` nodes.
- Updated `record_graph_source_kind_ingest()` to require existing CoreEgo root/time-axis graph records.
- Added graph path:

```text
graph:core_ego:root
  -> graph:axis:time
    -> graph:source_ingest_time_bundle:{batch_id}
      -> graph:source_kind_bundle:{batch_id}:{source_kind}
        -> graph:raw_source:{source_kind}:{observation_digest}
```

- Added source-ingest graph snapshot and RLoop guide packet records for the source ingest surface.
- Added observation time into source file data IDs, so the same file/content observed at different times becomes distinct raw source snapshot coordinates.
- Added ORDER 156 pytest coverage and included it in `fast-test --profile graph`.

## Absolute Information Boundary

Code writes only observation coordinates:

- source kind
- normalized path
- path name
- suffix
- exists-at-ingest flag
- char count
- source last modified timestamp
- observed/ingested timestamp
- content SHA-1
- graph/data IDs
- CoreEgo time-axis graph edges
- source ingest snapshot/guide packet coordinates

Code does not write summaries, semantic topics, importance scores, relevance judgments, or current-truth claims about future file state.

## Verification

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_order_156_graph_source_observation_time_and_core_link.py tests/test_import_baseline.py -q
# 12 passed

python main.py fast-test --profile graph
# FAST_TEST_OK
# pytest:graph: 31 passed

python -m pytest
# 162 passed in 582.76s

python main.py smoke-test
# SMOKE_TEST_OK
```

## Not Opened

- Neo4j/Vessel connection
- night-government summary worker
- semantic axis
- R LLM selector over source ingest bundles
- automatic source path discovery
- node_3 answer injection
