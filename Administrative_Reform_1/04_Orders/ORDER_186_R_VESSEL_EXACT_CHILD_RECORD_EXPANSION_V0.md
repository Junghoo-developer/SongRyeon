# ORDER 186: R Vessel Exact Child Record Expansion v0

## Status

Approved by the user on 2026-07-03 for immediate implementation.

## Trigger

Live `vessel-r-traverse` reached:

```text
step 1: graph:axis:time
step 2: graph:source_ingest_time_bundle:...
final_continuation_status=stop_no_actionable_path
terminal_material_seen_count=0
```

Audit showed that Neo4j already had the intended structure:

```text
SourceIngestBundle -> SourceKindBundle -> RawSource -> SummaryGraphNode / TokenBudgetSummaryBundle
```

But the R Vessel read packet only used the first bounded entry rows. In the observed packet order, `SourceKindBundle` records appeared after many raw source rows, so the source ingest node had child IDs that were real in Neo4j but absent from the packet candidate map.

## Goal

When an already visible entry candidate has exact child graph node IDs, include those child records in the same R Vessel read packet even if they appear outside the base row limit.

This is a structural record expansion, not semantic ranking.

## Policy

- Keep the base entry row limit.
- Add exact child records only when their IDs are already present in the graph record itself or in `parent_graph_node_ids`.
- Follow exact child links for a small bounded depth:

```text
R_LOOP_VESSEL_EXACT_CHILD_EXPANSION_MAX_DEPTH = 2
```

- Use the same numeric `limit` as the maximum additional expansion budget.
- Record the expansion facts in `RLoopVesselReadPacketFrame`:
  - `exact_child_expansion_policy_id`
  - `base_entry_candidate_count`
  - `exact_child_expanded_entry_count`
  - `exact_child_expanded_node_ids`
  - `exact_child_expansion_truncated`

## Metadata Boundary

- Code may follow exact graph IDs and count what it added.
- Code may not decide which child is semantically more relevant.
- R2 still chooses from official refs.
- R3 still judges sufficiency and whether to go deeper.
- This order does not add keyword matching, vector similarity, or hidden ranking.

## Non-Goals

- Do not increase default R route scope by simply dumping all graph records into R2.
- Do not connect R route to normal node_1/node_2/node_3 flow.
- Do not mutate Neo4j.
- Do not create semantic-axis traversal.
- Do not change R1 budget policy.
- Do not add hidden text heuristics.

## Verification Targets

- A `SourceKindBundle` outside the base packet limit is included when a visible `SourceIngestBundle` points to it by exact child ID.
- The packet records base count and exact child expansion count.
- Multi-step traversal can descend through the expanded child record to terminal summary material.
- Existing R Vessel read/traverse tests remain green.
