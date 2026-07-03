# ORDER 187: R Vessel Summary Layer Before Raw v0

## Status

Approved by the user on 2026-07-03 for immediate implementation.

## Trigger

After ORDER 186, live R traversal successfully descended:

```text
TimeAxis -> SourceIngestBundle -> SourceKindBundle -> RawSource
```

This proved the graph path was visible, but it also showed that R could jump from a source-kind bundle directly into raw source material even when active summary-layer material already existed.

## Goal

Make R traversal prefer existing summary-layer material before raw source material under a `SourceKindBundle`.

Target behavior:

```text
SourceKindBundle
-> token_budget_bundle_summary, if it structurally covers that source kind's raw children
-> source_leaf_summary, if token layer is absent
-> RawSource, only if no active summary-layer child exists
```

## Policy

This is a structural source-bundle policy, not semantic ranking.

Code may:

- read the exact raw child IDs under a `SourceKindBundle`
- inspect active summary candidate source IDs
- expose summaries that explicitly include those raw child IDs in their `source_data_ids`, `source_graph_node_ids`, or `target_graph_node_id`
- prefer token-budget bundle summaries over leaf summaries when both are structurally available

Code must not:

- judge which summary is semantically best
- infer relevance from text
- use keyword matching or vector similarity
- hide raw source forever

## Metadata Boundary

- `SourceKindBundle` and `RawSource` links are absolute graph structure.
- `SummaryGraphNode` text remains LLM-generated relative/mixed information.
- Code only chooses which layer to expose first based on explicit source IDs.
- R2 still chooses from official refs.
- R3 still decides sufficiency and whether to continue.

## Non-Goals

- Do not connect R route to the normal node_1/node_2/node_3 live flow.
- Do not mutate Neo4j.
- Do not create semantic-axis traversal.
- Do not summarize new material.
- Do not add hidden heuristics.

## Verification Targets

- If a token-budget summary covers raw source children under a source kind, traversal selects the token summary before raw.
- If token layer is absent but source-leaf summary exists, traversal selects the leaf summary before raw.
- Raw remains available as fallback when no summary layer is present.
- Existing R hierarchy and traversal tests remain green.
