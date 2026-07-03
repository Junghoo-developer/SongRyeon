# ORDER 195: R Vessel Activity Ledger v0

## Status

Prepared on 2026-07-03 as the second implementation step after ORDER 194.

This order depends on ORDER 194.

## Trigger

Vessel R traversal already records many frames:

```text
R1 goal
candidate layer surface
R2 surface/node selection
R3 inspection
graph traversal candidate surface
budget
continuation
return summary
traverse result
```

But these frames are not yet gathered into one activity ledger equivalent to the L loop activity ledger.

Without a ledger, later systems must rediscover all R frames by scanning DataStore. That is fragile.

## Goal

Create a single absolute ledger that says what the Vessel R loop did in this turn.

Elementary explanation:

```text
R walked through the graph.
The activity ledger is the notebook listing every door R looked at.
```

## Scope

Add a frame such as:

```text
RLoopVesselActivityLedgerFrame
```

Suggested fields:

```text
frame_id
turn_id
source_start_handoff_packet_id
source_read_packet_id
traverse_result_frame_id
r1_goal_frame_id
candidate_layer_surface_frame_ids
surface_selection_frame_ids
r2_selection_frame_ids
r3_inspection_frame_ids
graph_traversal_candidate_surface_frame_ids
budget_frame_ids
continuation_frame_ids
return_summary_frame_id
selected_graph_node_ids
inspected_graph_node_ids
candidate_graph_node_ids
terminal_material_seen_count
raw_original_material_seen_count
r_loop_task_status
final_continuation_status
failure_stage
failure_type
failure_reason
generated_by
info_class
semantic_judgement_status
source_trace_ids
source_data_ids
schema_name
schema_version
```

The ledger should be built from a completed or failed `RLoopVesselTraverseRun`.

## Rules

- The ledger is absolute information.
- It only records what frames and graph node IDs existed.
- It does not decide which graph node was important.
- It does not summarize R output.
- It preserves failures as failures.
- If traversal fails at R1/R2/R3, the ledger should still record frames created before failure.

## Runtime Integration

Preferred helper:

```text
record_r_loop_vessel_activity_ledger(...)
```

It should be called after `run_r_loop_vessel_traverse(...)` returns.

The resulting DataStore record data type should be explicit, for example:

```text
r_loop:vessel_activity_ledger_frame
```

Do not reuse the older dry-run `graph_memory:turn_access_ledger_frame` type unless the schema is intentionally generalized.

## Non-Goals

- Do not connect the ledger to raw capsule yet. That is ORDER 196.
- Do not create node_0 mid-loop checkpoints. That is ORDER 197.
- Do not create final answer route. That is ORDER 199.
- Do not write new Neo4j nodes by default.
- Do not add summary/relevance heuristics.

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

Focused tests:

1. Successful Vessel R traversal creates one activity ledger.
2. Ledger selected/inspected IDs match the traverse result.
3. Ledger includes R1/R2/R3/continuation/result frame IDs.
4. Failed traversal creates a failed ledger with failure fields.
5. Ledger is absolute/code-generated/not semantic.

## Done Criteria

Runtime or test output can report:

```text
R Vessel activity ledger: status=sufficient|partial|failed / steps=N / selected=N / inspected=N
```

The ledger is enough for later graph backup without re-running R traversal.
