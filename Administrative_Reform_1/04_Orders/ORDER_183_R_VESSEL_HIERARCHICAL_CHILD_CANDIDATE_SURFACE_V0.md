# ORDER 183: R Vessel Hierarchical Child Candidate Surface v0

## Status

Approved by the user on 2026-07-02 for immediate implementation.

## Trigger

After ORDER_182, R2 no longer sees 50 leaf summaries at the first CoreEgo step. However, the actual R Vessel read flow still needs a hierarchy-aware next layer:

```text
CoreEgo -> TimeAxis -> SourceIngestBundle -> SourceKindBundle -> RawSource / Summary
```

The graph already contains lower-level source and summary nodes, but the one-step Vessel R flow did not yet expose the selected node's direct children as a structured downstream candidate surface.

## Goal

Add a minimal hierarchy read path:

- Read packet records enough metadata to infer child candidates from graph node payloads and edges.
- When R2 selects a node, code builds direct child candidate records for that selected node.
- R3 receives those child candidates as context.
- After R3, code records an `RGraphTraversalCandidateSurfaceFrame` using the existing R loop schema.
- The candidate surface is absolute information and can be used by a later full multi-step R traversal.

## Intended Reading Order

This order does not make R2 recursively loop yet. It prepares the exact next-layer surface:

```text
R2 selects current node
R3 inspects current node + child candidates
code records child candidate surface
continuation can truthfully say whether deeper traversal is possible
```

## Metadata Boundary

- Code may copy graph IDs, child IDs, node kinds, counts, and display names.
- Code must not decide which child is semantically best.
- R2/R3 semantic decisions remain LLM-generated mixed information.
- The child candidate surface is code-generated absolute information.

## Non-Goals

- Do not open full automatic multi-step R traversal yet.
- Do not introduce R2a/R2b or A/B selection formats.
- Do not delete or rewrite graph nodes.
- Do not weaken R2 official ref validation.
- Do not make code choose a semantic child candidate.
- Do not connect R loop output to node_3 final answer yet.

## Verification Targets

- TimeAxis selection exposes time/source ingest bundles as child candidates.
- SourceIngestBundle can expose SourceKindBundle children when present in the read packet.
- Token budget summary bundle can expose its source summary children through `source_graph_node_ids`.
- R3 child IDs are copied from code-built hierarchy records, not invented by the LLM.
- The existing `RGraphTraversalCandidateSurfaceFrame` validator is used.
