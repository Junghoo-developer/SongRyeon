# ORDER 197: R Vessel Node0 Continuation Checkpoint Packet v0

## Status

Implemented on 2026-07-03 as the fourth implementation step after ORDER 196.

This order depends on ORDER 194 and ORDER 195. It may be implemented before ORDER 196 if needed, but ORDER 196 should still link its resulting ledger later.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_197_r_vessel_node0_continuation_checkpoint_implementation_2026_07_03_001.md`

## Trigger

L loop has a stronger memory discipline because intermediate results can be passed forward as explicit packets/frames.

Vessel R multi-step traversal currently loops internally:

```text
R2 selects
R3 inspects
continuation decides
next candidate surface is built
R2 selects again
```

This works, but node_0 does not yet create a stable checkpoint packet between steps.

## Goal

After each R continuation decision, node_0 should record a checkpoint packet that copies the current R traversal state for the next step.

Elementary explanation:

```text
R says, "I need to go deeper."
0 writes down what R has already seen and what it may see next.
Then R continues from that written checkpoint.
```

## Scope

Add a frame such as:

```text
RLoopVesselContinuationCheckpointPacketFrame
```

Suggested fields:

```text
packet_id
turn_id
step_index
target="R_LOOP"
mode="vessel_r_continuation_checkpoint"
source_start_handoff_packet_id
source_read_packet_id
source_candidate_surface_frame_id
source_r2_selection_frame_id
source_r3_inspection_frame_id
source_continuation_frame_id
selected_graph_node_ids_so_far
inspected_graph_node_ids_so_far
next_candidate_graph_node_ids
next_candidate_count
remaining_node_reads
remaining_traversal_depth
terminal_material_seen_count
raw_original_material_seen_count
raw_original_read_cap_reached
continuation_status
next_target_node
generated_by
info_class
semantic_judgement_status
source_trace_ids
source_data_ids
schema_name
schema_version
```

## Runtime Integration

In `run_r_loop_vessel_traverse(...)`, after recording the continuation frame and before the next step, record the checkpoint packet when:

```text
continuation_status == continue_deeper
```

If the loop stops, do not create a fake "next" checkpoint.

The next candidate surface may reference the checkpoint packet as a source.

## Rules

- node_0 checkpoint copies absolute state only.
- node_0 does not pick the next graph node.
- R2 still chooses among allowed candidates.
- No semantic summary is generated.
- Checkpoints must be included in the Vessel R activity ledger once ORDER 195 is present.

## Non-Goals

- Do not add automatic branch switching logic.
- Do not add relevance ranking.
- Do not change R2/R3 prompt semantics beyond accepting checkpoint metadata.
- Do not enable live route=R.
- Do not create final answer route.

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

Focused tests:

1. Multi-step traversal with `continue_deeper` creates one checkpoint per continuation step.
2. Checkpoint selected/inspected IDs match records so far.
3. Checkpoint next candidates match the next candidate surface.
4. Checkpoint is code-generated absolute information.
5. Stop conditions create no fake checkpoint.

## Done Criteria

The runtime can show:

```text
R Vessel checkpoints: count=N / latest_step=K / next_candidates=M
```

and a later node can reconstruct R's intermediate state without guessing.
