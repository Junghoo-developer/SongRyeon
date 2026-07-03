# ORDER 198: R Vessel Node0 Return Packet v0

## Status

Prepared on 2026-07-03 as the fifth implementation step after ORDER 195.

This order depends on ORDER 194 and ORDER 195. ORDER 196 and ORDER 197 improve its traceability but are not strict prerequisites.

## Trigger

ORDER 193 lets node_2/node_3 read the latest Vessel R traverse result.

But this skips one conceptual step:

```text
R ends
0 receives/organizes R result
then downstream nodes consume it
```

The current path is closer to:

```text
R result exists in DataStore
node_2 finds it
```

That is usable, but it does not yet honor the intended role of node_0 as memory supplier/recovery manager.

## Goal

Create a node_0 return packet after Vessel R traversal ends.

Elementary explanation:

```text
R comes back from the graph.
0 takes R's notebook, labels it, and hands the labeled result downstream.
```

## Scope

Add a frame such as:

```text
RLoopVesselReturnPacketFrame
```

Suggested fields:

```text
packet_id
turn_id
target="node_1_or_node_2"
mode="vessel_r_return_packet"
return_status
source_start_handoff_packet_id
source_activity_ledger_frame_id
source_traverse_result_frame_id
source_return_summary_frame_id
source_read_packet_id
r_loop_task_status
traverse_status
failure_stage
failure_type
failure_reason
selected_graph_node_count
inspected_graph_node_count
summary_material_count
raw_original_material_count
node3_material_ready
node3_material_source_data_ids
generated_by
info_class
semantic_judgement_status
source_trace_ids
source_data_ids
schema_name
schema_version
```

## Integration

After `run_r_loop_vessel_traverse(...)` and `record_r_loop_vessel_activity_ledger(...)`, call:

```text
record_r_loop_vessel_return_packet(...)
```

Then update `node_2_handoff` so ORDER 193 material builder prefers:

```text
RLoopVesselReturnPacketFrame
```

over raw "latest traverse result" when present.

Fallback to latest traverse result may remain for compatibility, but terminal output should reveal which source was used.

## Rules

- The return packet is absolute metadata.
- It does not write the final answer.
- It does not summarize graph memory.
- It does not hide failed/partial R traversal.
- It should make failed/partial/sufficient states obvious to node_2/node_3/node_4.

## Non-Goals

- Do not implement final answer demo route. That is ORDER 199.
- Do not enable default route=R.
- Do not add new graph traversal strategy.
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

1. Successful traversal creates return packet with `return_status=available`.
2. Failed traversal creates return packet with failure fields and `node3_material_ready=false`.
3. node_2 handoff uses return packet source when present.
4. ORDER 193 direct traversal fallback still works when return packet is absent.
5. node_3 brief exposes return packet source IDs without raw internal ID leakage.

## Done Criteria

There is a clear R end boundary:

```text
R traversal result
-> R activity ledger
-> node_0 return packet
-> node_2 handoff
-> node_3 material
```

No normal chat route is opened yet.
