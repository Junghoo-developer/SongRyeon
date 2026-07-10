# ORDER 216: R Loop Hierarchy Visibility And Step Memory v0

## Status

Implemented on 2026-07-08.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_216_r_loop_hierarchy_visibility_and_step_memory_2026_07_08_001.md`

## Goal

Make Vessel R traversal behave like a layered graph search loop instead of a
wide summary-card picker.

The R loop must move from broad, low-density graph material toward narrower,
higher-density material while preserving what each step saw and why the next
step is allowed.

## Background

Current Vessel graph memory already has layered material:

- CoreEgo
- TimeAxis
- source ingest bundle
- source kind bundle
- token budget bundle summaries
- source leaf summaries
- raw source nodes

However, the R loop visibility policy is still too implicit. R2 and R3 can see
candidate records, but the runtime does not yet preserve a clear per-step
memory packet explaining:

- what R2 selected
- what R3 inspected
- what child candidates R3 could see
- whether R3 asked for lower granularity, raw material, or a branch change
- which candidates are promoted to the next R2 surface
- how much traversal/raw-read budget remains

Without this, R3-only visibility can disappear before node_2/node_3 receive
the final material, and future branch switching can lose context.

## Scope

Implement a narrow runtime MVP:

1. Add a code-generated R step memory packet for Vessel R traversal.
2. Record one packet per completed R2/R3 step.
3. Include previous R step memory in the next R2 input.
4. Include current/previous R step visibility policy in the R3 input.
5. Preserve child candidate IDs that R3 could see.
6. Preserve the candidate IDs promoted to the next R2 surface when R3 requests
   deeper traversal.
7. Keep raw original read cap behavior intact.

## Roles

- R1 chooses the graph search goal and budget.
- R2 chooses the next graph node from official runtime refs.
- R3 inspects the selected node and sends status signals.
- node_0 records step memory and carries absolute traversal state forward.

R3 does not directly select the next node.

## Visibility Rule

The currently selected node may expose its inspected material.

Child candidates should be exposed as candidate cards:

- candidate ID/ref
- display name
- kind
- summary depth
- source leaf count
- source summary count
- short preview when present

Child candidate full summary/raw content must not be bulk-exposed merely
because it is under the selected node. It becomes inspected material only when
R2 selects it in a later step.

## Original Material Rule

R traversal may reach raw source/raw capsule material when needed.

The raw original cap remains active. The code counts raw original material
reads and blocks over-cap traversal. R3 may recommend lower granularity, but
R2 selects the next node and code enforces the budget.

## Non-Goals

- Do not regenerate Neo4j summaries.
- Do not rewrite existing Vessel graph data.
- Do not add semantic-axis CoreEgo routing.
- Do not implement full branch-switch traversal in this order.
- Do not weaken R2/R3 schema validators.
- Do not let code perform semantic relevance judgment.
- Do not expose graph IDs in user-facing final answers.

## Completion Checks

- R traversal records an R step memory packet per inspected step.
- R2 input receives previous step memory when it exists.
- R3 input receives safe child candidate visibility metadata.
- R3 child candidate IDs are preserved in step memory.
- Deeper traversal records promoted candidate IDs for the next R2 surface.
- Raw original read cap still applies.
- `python -m compileall songryeon_core main.py`
- focused pytest for ORDER 216
- `python main.py smoke-test`
