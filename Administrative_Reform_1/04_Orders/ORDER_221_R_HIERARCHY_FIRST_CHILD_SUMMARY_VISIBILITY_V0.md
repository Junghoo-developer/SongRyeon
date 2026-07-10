# ORDER 221: R Hierarchy-First Child Summary Visibility v0

## Status

Implemented on 2026-07-08.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_221_r_hierarchy_first_child_summary_visibility_2026_07_08_001.md`

## Goal

Let R2 and R3 see lower-node summary material when the graph already presents a
clean child summary layer.

This order does not cap or trim child summaries. If a child layer is not clean,
code reports the layer status instead of pretending that a sampled subset is
enough.

## Background

ORDER 220 found that R traversal can structurally descend, but R2 and R3 mostly
received child structure counts rather than child summary substance.

The user rejected arbitrary caps:

- Do not solve overloaded prompts by hiding part of the child layer.
- If the child layer is too messy, the graph needs more hierarchy.
- R traversal should consume clean graph layers, not randomly sampled prompt
  fragments.

## Implementation

### R2 candidate cards

R2 candidate cards now include:

- `child_summary_layer_status`
- `child_summary_layer_data_kind`
- `child_summary_layer_summary_depths`
- `child_summary_layer_record_count`
- `child_summary_layer_records`

When all child candidates are summary nodes with one shared `data_kind`, code
marks the layer as `clean_summary_layer` and exposes the full child summary
layer previews.

When child records are mixed or not a summary layer, code does not expose a
partial child summary list.

### R3 inspection payload

R3 receives the same clean child summary layer under
`hierarchy_child_summary_layer`.

R3 may use this to decide whether a deeper traversal is promising, but must not
claim it inspected raw/original material unless that raw node is actually
selected and supplied by code.

### Prompt boundary

R2/R3 prompts now distinguish:

- structural child counts;
- clean child summary layer previews;
- raw/original material.

Clean child summary previews are summary-level navigation evidence, not raw
source evidence.

## Rules

- No arbitrary count cap.
- No candidate trimming.
- No raw original dump.
- No route policy change.
- No Neo4j schema rewrite.
- No R1/R2/R3 role rewrite.
- No L loop changes.

## Completion Checks

- R2 sees clean child summary layer previews for source-kind -> token summary
  traversal.
- R3 sees the same clean child summary layer for the selected source-kind node.
- R2 still does not receive full `summary_text`.
- Existing R2 candidate card tests remain valid after the policy update.
- `python -m compileall songryeon_core main.py`
- focused pytest for ORDER 217 and ORDER 221
