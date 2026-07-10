# ORDER 220: R Traverse Continuation Surface Audit v0

## Status

Audit completed on 2026-07-08.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_220_r_traverse_continuation_surface_audit_2026_07_08_001.md`

## Goal

Audit whether the Vessel R traversal loop can continue from a selected graph
node to lower hierarchy candidates, and identify why live R traversal can still
stop or fail even when lower graph nodes appear to exist.

This order does not implement a new child-summary visibility feature. It only
records the current structure and the next safe implementation boundary.

## Background

Recent live tests showed that R traversal can start from the graph memory entry
surface and move down to source/token summary layers, but it can also stop with
`stop_no_actionable_path`, `none_selected`, or schema repair failures.

The user direction is:

- R2 and R3 should eventually see lower-node summary material through a clean
  graph hierarchy, not through arbitrary prompt-time caps.
- R2 and R3 should not be limited to the currently selected node if the graph
  hierarchy already contains safe child summaries.
- The system still must not dump raw originals or uncontrolled child material
  into the LLM prompt.

## Current Code Facts

- R traversal already builds a first candidate surface from CoreEgo entry
  records.
- When R3 recommends `continue_deeper`, code creates the next candidate surface
  from `RGraphTraversalCandidateSurfaceFrame.candidate_graph_node_ids`.
- The next surface groups lower candidates by structural fields such as
  candidate kind, data kind, branch role, and summary depth.
- R2 is required to copy an official surface ref and node ref from the current
  candidate surface.
- R3 receives the selected record and code-copied child candidate records.
- Current child candidate records are treated as preview/navigation cards, not
  as fully inspected child summary material.

## Audit Findings

### 1. Structural descent path exists

Focused tests confirm that fake traversal can descend through the graph memory
hierarchy and token-summary child layers.

Verified cases:

- CoreEgo/time-axis traversal can move through multiple steps.
- Source ingest branch surfaces are ordered ahead of conversation memory for
  source/code/document questions.
- Token-budget summary nodes can expose lower summary children.
- Candidate cards expose structural child counts and kinds without exposing raw
  summary text to R2.

### 2. Live failure can happen after a valid next surface exists

The loop has a valid code path for this sequence:

1. R2 selects a current node.
2. R3 inspects it.
3. R3 recommends deeper traversal.
4. Code builds a next candidate surface.
5. The next R2 call must select one official candidate from that new surface.

If step 5 returns `none_selected`, or if copied refs fail schema validation, the
traversal closes as partial or failed. This is different from "there was no
child path."

### 3. R2/R3 currently see child structure, not child summary substance

R2 prompt explicitly says child structure fields are map signs and do not grant
access to child text.

R3 prompt says child candidate records are preview-only navigation cards unless
code supplies them as the selected candidate in a later step.

This is safe, but it explains the user's concern: R2/R3 may know that lower
summary nodes exist without seeing enough lower-summary content to choose
comfortably.

### 4. The next implementation should be hierarchy-first child-summary visibility

The next safe feature is not "show a small capped sample of children." If the
child layer is structurally mixed instead of being a clean summary layer, that
means the graph hierarchy is not layered enough yet.

- expose the next hierarchy layer's official child refs and summaries;
- if that layer is structurally mixed, create or use an intermediate summary
  layer before R traversal rather than silently trimming candidates;
- keep raw originals behind the raw read cap;
- preserve source ids in frames, but hide raw internal ids from LLM-facing copy
  contracts;
- record whether R2/R3 used selected-node material or child-layer summary
  material.

## Non-Goals

- No R route policy change.
- No R2/R3 role rewrite.
- No Neo4j schema rewrite.
- No raw original cap increase.
- No automatic branch-switch implementation.
- No broad child summary dump.
- No L loop changes.

## Recommended Next Order

`ORDER_221` should implement hierarchy-first R child-summary visibility.

Suggested target:

- R2 receives current candidate cards plus the next clean child-summary layer.
- R3 receives the selected node plus the next clean child-summary layer.
- If the child-summary layer is structurally mixed, code should report
  `needs_more_hierarchy` rather than trimming or sampling the list.
- R3 may say "the selected node alone is insufficient, but the child summaries
  indicate a useful deeper path."
- R3 must not claim it inspected raw original material unless that raw node was
  actually selected and supplied.
- Runtime should show whether stop/continue was driven by:
  - selected node material,
  - child summary layer material,
  - missing/insufficient hierarchy,
  - no child path,
  - R2 `none_selected`,
  - schema failure.

## Completion Checks

- Focused R traversal tests remain green.
- Audit execution record identifies exact continuation decision points.
- No runtime behavior is changed by this order.
