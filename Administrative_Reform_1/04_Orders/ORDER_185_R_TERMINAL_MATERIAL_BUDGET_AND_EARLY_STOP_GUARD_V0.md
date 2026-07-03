# ORDER 185: R Terminal Material Budget And Early Stop Guard v0

## Status

Approved by the user on 2026-07-03 for immediate implementation.

## Trigger

Live `vessel-r-traverse` Qwen test returned:

```text
step_count: 1
final_graph_node_id: graph:axis:time
final_sufficiency_status: sufficient
final_continuation_status: stop_sufficient
```

The runtime completed structurally, but R3 treated `Time Axis` as sufficient even though no terminal material had been inspected.

## Goal

Prevent R Vessel traversal from stopping as sufficient before it has inspected at least one terminal material node.

For this MVP, terminal material means a graph candidate that directly carries usable material for downstream answer/evidence work:

- raw source node
- raw capsule node
- active summary node with summary text

Axis and bundle nodes are traversal scaffolding, not terminal material.

## Policy

Initial code policy:

```text
min_terminal_material_reads = 1
```

If all of the following are true:

- R3 says `sufficient` or recommends `stop`
- terminal material seen count is still below the policy minimum
- the inspected node has code-supplied child candidates
- traversal budget still allows another node read

then code must not accept `stop_sufficient`.

Instead, the continuation frame should stay within the existing schema and use:

```text
continuation_status=continue_deeper
continuation_reason_code=CODE_STATUS:r_loop_terminal_material_not_seen
next_target_node=R2
```

## Metadata Boundary

- Code may count whether a selected record is terminal material.
- Code may enforce the minimum terminal material count.
- Code must not decide whether the selected material semantically answers the user.
- R2 still chooses among supplied official refs.
- R3 still judges sufficiency/granularity/branch choice.
- The guard only blocks a structurally premature stop.

## Non-Goals

- Do not connect R route to node_1 yet.
- Do not connect R result to node_0 or node_3 yet.
- Do not mutate Neo4j.
- Do not create semantic-axis traversal.
- Do not make R1 truly decide budgets yet.
- Do not add hidden text/keyword heuristics.

## Verification Targets

- If R3 marks `graph:axis:time` sufficient while child candidates exist and no terminal material has been seen, traversal continues.
- Traversal can still stop after inspecting one terminal summary.
- Result frame records terminal material counts and early-stop guard trigger count.
- Existing ORDER_184 traversal path tests still pass.
