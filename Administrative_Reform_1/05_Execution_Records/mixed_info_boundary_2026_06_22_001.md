# Mixed Info Boundary 2026-06-22 001

## Linked Order

- `ORDER_051_MIXED_INFO_BOUNDARY.md`

## Result

`node_2` now permits mixed information only when the mixed text has a concrete original record and evidence IDs.

Implemented boundary payload:

- `MixedInfoRef.info_id`
- `MixedInfoRef.source_data_id`
- `MixedInfoRef.field_path`
- `MixedInfoRef.info_kind`
- `MixedInfoRef.text`
- `MixedInfoRef.source_trace_ids`
- `MixedInfoRef.source_data_ids`

Initial allowed mixed information:

- `L3AchievementFrame.reason`
- `ToolChoiceFrame.reason`
- `L2QueryPlanFrame.candidates[n].purpose`

## Code Changes

- `songryeon_core/core/schemas.py`
  - Added `MixedInfoRef` validation use in `MetainfoBoundary.mixed_info`.
  - Added `ReportFrame.allowed_mixed_info_ids`.
- `songryeon_core/nodes/node_2_metainfo_boundary.py`
  - Extracts only source-backed mixed info from `Node2InputFrame.source_data_ids`.
  - Rejects source-less mixed text by omission.
- `songryeon_core/nodes/node_3_reporter.py`
  - Renders only mixed info that passed the node 2 boundary.
  - Records allowed mixed info IDs in `ReportFrame`.
- `songryeon_core/runtime/dry_run.py`
  - Passes allowed mixed info IDs into the report.
  - Exposes `mixed_info_count` in the dry-run summary.
- `main.py`
  - Prints `mixed_info_count` in the `dry-run` summary.
- `songryeon_core/runtime/smoke_test.py`
  - Verifies mixed info evidence IDs, L3 reason, tool choice reason, and L2 query plan purpose.

## Verification

- `python -m py_compile main.py songryeon_core\core\schemas.py songryeon_core\nodes\node_2_metainfo_boundary.py songryeon_core\nodes\node_3_reporter.py songryeon_core\runtime\dry_run.py songryeon_core\runtime\smoke_test.py`
- `python main.py dry-run`
- `python main.py smoke-test`

Smoke result included:

- `mixed_info_count: 3`
- `mixed_info_l3_reason: true`
- `mixed_info_tool_choice_reason: true`
- `l2_query_plan_mixed_info: true`

## Notes

This does not make mixed information absolute information. It only lets `node_3` report mixed text after `node_2` has tied it to the original data record, field path, trace IDs, and data IDs.
