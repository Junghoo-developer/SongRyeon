# ORDER 157 SongRyeon Core Source Ingest Manifest - Execution Record 2026-07-01 001

## Scope

Implemented a manifest-based source ingest runner for SongRyeon Core internal documents and source code files.

This order applies the ORDER 155~156 graph source ingest foundation to the project itself without semantic file classification.

## Approved Policy Applied

- Internal document/code raw text snapshots are stored.
- `tests/**/*.py` is included as `source_code_file`.
- Glob manifest is allowed only as explicit policy, not semantic guessing.
- Missing explicit paths fail.
- Missing glob matches are not treated as deletion detection in this MVP.

## Manifest Policy

```text
internal_document:
  explicit:
    - AGENTS.md
    - README.md
  globs:
    - Administrative_Reform_1/**/*.md

source_code_file:
  explicit:
    - main.py
  globs:
    - songryeon_core/**/*.py
    - tests/**/*.py
```

`external_project_file` is not auto-ingested in this order.

## Code Changes

- Added `songryeon_core/core/songryeon_source_manifest.py`.
- Added optional text snapshot support to `record_graph_source_kind_ingest()`.
- Added text snapshot DataRecord type:
  - `graph_source:file_text_snapshot`
- Text snapshot payloads use:
  - `info_class=absolute_copied_source`
  - `semantic_judgement_status=not_run`
- Added ORDER 157 pytest coverage.
- Added the ORDER 157 test to `fast-test --profile graph`.
- Added the new manifest module to the import baseline.

## Current Repository Manifest Check

Manual manifest resolution against the current repository root:

```text
internal_document: 364
source_code_file: 135
```

This was a manifest resolution check only, not a full current-repo source text ingest export.

## Verification

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_order_156_graph_source_observation_time_and_core_link.py tests/test_order_157_songryeon_core_source_manifest.py tests/test_import_baseline.py -q
# 17 passed

python main.py fast-test --profile graph
# FAST_TEST_OK
# pytest:graph: 36 passed

python -m pytest
# 167 passed in 584.42s

python main.py smoke-test
# SMOKE_TEST_OK
```

## Not Opened

- Neo4j/Vessel connection
- semantic axis
- night-government summary worker
- automatic semantic file selection
- external project file auto-discovery
- R LLM selector over source ingest bundles
- node_3 answer injection
