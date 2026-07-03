# ORDER 182: R CoreEgo Start Selection Surface v0

## Status

Approved by the user on 2026-07-02 for immediate small implementation.

## Trigger

Live R one-step tests no longer failed on invented IDs after ORDER_181, but R2 still received too many deep candidates too early.

Observed shape:

- `entry_candidate_count=3`
- `summary_candidate_count=50`
- R2 could reason over source leaf summaries and token layer summaries in the first step.

This contradicted the intended traversal model:

```text
CoreEgo -> Time Axis -> Time Bundle / Source Ingest Bundle -> lower graph nodes
```

R2 should not start by seeing many leaf summaries. R2 should first choose the next graph entry point from CoreEgo's direct entry layer, and R3 should inspect that selected node.

## Goal

Make the first R one-step selection surface CoreEgo-started:

- R2 first view is entry/root candidates only.
- If the read packet contains a `TimeAxis` entry candidate, prefer that as the first CoreEgo direct child surface.
- If no `TimeAxis` entry exists, fall back to existing entry bundle candidates.
- Summary candidates remain in the read packet for later use, but are not exposed in the first R2 selection payload.

## Metadata Boundary

The first-step surface is absolute information:

- code groups existing read-packet entries;
- code does not semantically choose the best candidate;
- R2 still performs the semantic selection among the visible official refs.

## Non-Goals

- Do not introduce R2a/R2b or A/B style selection.
- Do not open full multi-step R traversal yet.
- Do not delete summary candidates from the read packet.
- Do not weaken R2 ref validation.
- Do not change node_1 routing, node_3 answer generation, W/R scheduler policy, or external DB schema beyond read packet visibility.

## Verification Targets

- R2 payload hides `summary_text`, `summary_node_id`, and summary data kinds in the first view.
- R2 payload keeps official `surface_ref` / `node_ref` selection.
- TimeAxis candidates are recognized as `time_axis`.
- If TimeAxis is present, first surface exposes TimeAxis only.
- If TimeAxis is absent, entry bundles remain available as fallback.
