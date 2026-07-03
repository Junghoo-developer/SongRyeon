# ORDER 194: R Vessel Node0 Start Handoff Packet v0

## Status

Prepared on 2026-07-03 as the first implementation step after ORDER 193.

Implemented on 2026-07-03 in
`Administrative_Reform_1/05_Execution_Records/order_194_r_vessel_node0_start_handoff_implementation_2026_07_03_001.md`.

## Trigger

ORDER 193 lets node_3 receive already-recorded Vessel R traversal material.

However, the current Vessel R CLI path still starts mostly like this:

```text
runtime reads Neo4j Vessel packet
-> R1/R2/R3 traverses
```

That is useful, but it is not yet the same as:

```text
node_0 supplies R with memory/graph coordinates
-> R loop starts from that supply packet
```

The older dry-run R route has `RLoopMemoryHandoffPacketFrame`, but the newer Vessel-backed R traversal needs a clearer start packet that includes the actual Vessel read packet and graph memory guide boundary.

## Goal

Make R traversal start from a node_0 supplied handoff packet.

Elementary explanation:

```text
Before R starts searching Vessel, 0 prepares the map and hands it to R.
R must be able to say, "I started from this 0-supplied packet."
```

## Scope

Add a narrow start handoff frame for Vessel-backed R traversal.

Suggested frame name:

```text
RLoopVesselStartHandoffPacketFrame
```

Suggested fields:

```text
packet_id
turn_id
target="R_LOOP"
mode="vessel_r_start_handoff"
packet_status
source_vessel_read_packet_id
source_graph_guide_packet_id
source_graph_snapshot_id
entry_candidate_count
summary_candidate_count
available_entry_node_ids
summary_count_by_data_kind
summary_count_by_depth
recent_turn_capsule_count
recent_raw_conversation_count
generated_by
info_class
semantic_judgement_status
source_trace_ids
source_data_ids
schema_name
schema_version
```

Code may copy:

- `RLoopVesselReadPacketFrame` status and counts
- graph guide packet ID if present
- previous turn capsule/raw conversation counts if supplied in the current runtime
- source trace/data IDs

Code must not:

- choose a relevant graph node
- summarize graph memory
- claim R traversal success
- convert the packet into L document evidence

## Runtime Integration

Add a helper such as:

```text
record_r_loop_vessel_start_handoff_packet(...)
```

The helper should:

1. Validate the Vessel read packet.
2. Copy only absolute metadata into the handoff frame.
3. Record a `TraceEvent` with `actor=node_0`, `event_type=memory_packet`.
4. Store the frame in DataStore.
5. Pass this packet ID into `run_r_loop_vessel_traverse(...)`.

The initial CLI may still build the read packet before node_0 records the handoff, but the traversal input should reference the node_0 handoff trace/data IDs.

## Non-Goals

- Do not enable default `route=R` in normal chat.
- Do not create R activity ledger yet. That is ORDER 195.
- Do not link to TurnStateCapsule yet. That is ORDER 196.
- Do not add mid-loop checkpoints. That is ORDER 197.
- Do not create final answer demo route. That is ORDER 199.
- Do not add semantic relevance heuristics.
- Do not weaken node_4.

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

Focused tests:

1. A passed Vessel read packet creates an available node_0 start handoff packet.
2. A failed/empty read packet creates a non-success handoff without fake candidates.
3. The handoff frame is `generated_by=CODE:*`, `info_class=absolute`, `semantic_judgement_status=not_run`.
4. R traversal receives the handoff packet trace/data IDs in its source IDs.
5. Existing `vessel-r-traverse` output still works.

## Done Criteria

- Runtime output can show:

```text
node_0 Vessel R start handoff: status=available / read_packet=... / entries=N / summaries=N
```

- R result/source IDs can be traced back to the node_0 start packet.
- No R answer route is opened yet.
