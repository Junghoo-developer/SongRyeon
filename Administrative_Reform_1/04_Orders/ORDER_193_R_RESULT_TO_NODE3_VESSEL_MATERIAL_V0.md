# ORDER 193: R Result To Node3 Vessel Material v0

## Status

Prepared on 2026-07-03 as the next narrow MVP after the Vessel graph memory and R traversal baseline was merged to `main`.

Do not implement this order until the user explicitly approves implementation.

## Trigger

SongRyeon Core can now:

- write graph memory into a local Neo4j Vessel
- inspect the CoreEgo/TimeAxis/TimeBundle/source/summary graph
- run experimental R1/R2/R3 Vessel traversal from the CLI

However, the normal answer route still does not safely use R traversal output as final-answer material.

The current R path can find graph memory, but node_3 does not yet receive a structured, source-labeled R material packet in the same careful style used for L-loop document material.

## Goal

Create a read-only handoff path from completed R traversal results to node_3 input brief material.

In elementary terms:

```text
R loop finds something in Vessel.
Code wraps that result in a labeled evidence packet.
node_3 can use that packet as material.
node_3 must not pretend the packet is a normal document read or a code fact it did not receive.
```

## Proposed Scope

1. Add a narrow R material frame.

Suggested frame name:

```text
Node3VesselRMaterial
```

Suggested fields:

```text
r_loop_result_id
r_loop_task_status
traversal_path_count
selected_graph_node_ids
inspected_graph_node_ids
summary_material_count
raw_original_material_count
material_items
generated_by
info_class
semantic_judgement_status
source_data_ids
source_trace_ids
```

2. Populate the frame from an existing successful `vessel-r-traverse` result.

Code may copy:

- selected graph node IDs
- inspected graph node IDs
- summary snippets already produced by Vessel/R traversal
- raw original material count
- R1/R2/R3 status fields

Code must not:

- invent semantic relevance
- summarize graph material itself
- silently convert R traversal into L document evidence
- hide R traversal failure as normal answer material

3. Add the material to `Node3InputBriefFrame`.

The brief should preserve:

```text
vessel_r_material_status
vessel_r_material_count
vessel_r_material_source_data_ids
```

If R traversal failed or did not run, node_3 should see that explicitly.

4. Update node_3 prompt boundary.

node_3 may use R material as graph-memory material.

node_3 must not call it:

- `read_doc` evidence
- current-turn source-code read evidence
- direct user memory unless the material item says so

5. Keep node_4 guard direction.

node_4 should be able to reject an answer that claims:

```text
R traversal succeeded
```

when the R material status says:

```text
failed
not_run
partial
```

## Non-Goals

- Do not turn on route=R in normal qwen-chat by default.
- Do not build a full R loop answer route.
- Do not write new graph nodes.
- Do not change Neo4j schema labels or relationship names.
- Do not increase raw original read cap.
- Do not add heuristics for relevance.
- Do not weaken node_4.
- Do not merge R material into L document material.

## Test Plan

Run:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Add focused tests:

1. Successful R traversal result creates a `Node3VesselRMaterial` frame.
2. Failed R traversal result creates no fake successful material and preserves failure status.
3. node_3 input brief receives R material status/count/source IDs.
4. R material is labeled as graph/Vessel material, not `read_doc` material.
5. node_4 rejects an answer that claims R traversal success when R material says failed/not_run.
6. Existing L-loop document material tests remain unchanged.

## Expected Result

After this order, SongRyeon can say:

```text
I found graph memory through R traversal, and here is exactly what node_3 received from that traversal.
```

without pretending the normal live answer route is already fully R-powered.
