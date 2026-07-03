# ORDER 190: R Vessel Token Summary Deeper Child Expansion v0

## Status

Approved by the user on 2026-07-03 for immediate implementation.

## Trigger

ORDER 189 live audit showed that R traversal now starts high and reaches token-budget summary material, but Qwen often wants to continue deeper after inspecting a token summary.

Observed bottleneck:

```text
CoreEgo -> Time Axis -> Source Ingest Bundle -> Source Kind Bundle -> Token Summary
```

At the token summary step, R traversal stopped as partial because the default traversal budget ended and the lower summary children were not reliably available as readable candidate records.

## Goal

Let R traversal continue from a token-budget summary into its lower summary children when R3 asks for `deeper`.

This is still a read-only traversal improvement. It does not connect R traversal to normal qwen-chat answers.

## Key Rules

- Token summary children must be copied from code-visible source IDs.
- Code may follow `graph:summary:*` source IDs and copy matching active summary records.
- Code must not semantically decide which child is relevant.
- R2 still chooses among official refs.
- R3 still judges whether the selected node is sufficient.
- Raw originals remain capped by ORDER 188.

## Implementation Requirements

1. Expand R read packet summary candidates.
   - Keep the original balanced summary candidate window.
   - Add active summary records referenced by selected summary candidates' `source_graph_node_ids` or `source_data_ids`.
   - Limit summary child expansion by explicit policy.

2. Prefer higher summary layers first.
   - Token-budget summaries should be visible before source leaf summaries in the base summary window.
   - Among summaries, higher `summary_depth` is a higher-level summary and should be considered first.

3. Token summary child surface.
   - When the selected node is a `token_budget_bundle_summary`, its next child candidate surface should prefer `graph:summary:*` children.
   - Do not expose unresolved token bundle IDs as first-choice material when readable summary children exist.
   - If a token summary has no summary children, do not fall through to unreadable bundle IDs as if they were useful material.

4. Traversal budget.
   - Increase default multi-step R traversal depth/node-read budget from 4 to 6.
   - This allows:

```text
Time Axis
-> Source Ingest Bundle
-> Source Kind Bundle
-> Token Summary
-> Lower Token Summary / Source Leaf Summary
```

5. Runtime visibility.
   - R read packet output should show base summary candidate count and summary child expansion count.

## Non-Goals

- Do not route normal user turns to R by default.
- Do not connect R result to node_3 yet.
- Do not add semantic-axis traversal.
- Do not add branch comparison logic beyond exposing lower child surfaces.
- Do not increase raw original read cap.
- Do not write new graph nodes.
- Do not add keyword heuristics.

## Verification Targets

- A token summary that references a lower summary record has that child summary copied into the R read packet.
- R traversal can continue from parent token summary to lower token summary.
- Token summary traversal does not count as raw original material.
- Existing R traversal tests still pass.
- `fast-test --profile graph` still passes.

