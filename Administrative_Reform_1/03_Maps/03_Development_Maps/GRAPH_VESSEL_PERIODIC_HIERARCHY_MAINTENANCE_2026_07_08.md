# Graph Vessel Periodic Hierarchy Maintenance Note

Date: 2026-07-08

## Purpose

This note records the next design direction after ORDER 221.

The Vessel graph should remain sustainable by periodically building cleaner
summary layers. R traversal should not survive by arbitrary prompt caps. It
should survive because each layer is small and meaningful enough to inspect as a
whole.

Before implementing graph maintenance, read:

- `Administrative_Reform_1/00_Philosophy/Graph_DB_Management_Risk_Philosophy_2026_07_09.md`

## Core Principle

If R2 or R3 cannot reasonably inspect a child layer, do not hide part of that
layer. Build a better intermediate graph layer.

In simple words:

- Bad fix: show only a few children and pretend that was the layer.
- Good fix: create another summary layer so the next visible layer is clean.

## Periodic Maintenance Loop Candidate

The future maintenance loop can run after source ingest, after long chat
sessions, or on manual command.

1. Observe changed or newly added graph leaves.
2. Keep raw/original graph nodes immutable where possible.
3. Invalidate old summaries when source lineage changes.
4. Find child layers that are structurally mixed or hard for R traversal.
5. Create intermediate summary layers by data kind, source kind, time bundle, or
   existing summary depth.
6. Mark the new layer with summary depth, source leaf count, source summary
   count, generated_by, info_class, and source ids.
7. Expose only clean layers to R2/R3 as child summary layers.

## Suggested Future Statuses

- `clean_summary_layer`: children are summary nodes of one data kind.
- `non_summary_navigation_layer`: children are normal graph navigation nodes.
- `needs_more_hierarchy`: children are summaries but the layer is structurally
  mixed.
- `raw_layer_requires_explicit_read`: children are raw/original material and
  should remain behind raw read policy.

## Not Implemented Yet

- No automatic periodic scheduler.
- No background Neo4j maintenance worker.
- No automatic layer rebuild after every run.
- No semantic axis.
- No deletion of old nodes.

## Recommended Next Order

The next order should audit existing Vessel graph layers and report where
`needs_more_hierarchy` would appear before adding automatic layer creation.
