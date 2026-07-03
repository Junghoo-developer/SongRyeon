# ORDER 188: R Vessel Raw Original Read Cap v0

## Status

Approved by the user on 2026-07-03 for immediate implementation.

## Trigger

After ORDER 187, R traversal now prefers summary layers before raw source material. The next safety boundary is to prevent R traversal from opening too many raw originals in a single traversal.

User requirement:

```text
원본은 최대 5회만 열람할 수 있도록 해
```

## Goal

Limit raw original material inspection during one R Vessel traversal to at most 5.

For this MVP, raw original material means:

- `RawSource`
- `RawCapsule`

Summary nodes do not count as raw original material, even if their summaries are about raw material.

## Policy

```text
R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS = 5
```

The 5th raw original inspection is allowed. If R3 asks to continue after the cap is reached, code closes traversal with:

```text
continuation_status=stop_budget_exhausted
continuation_reason_code=CODE_STATUS:r_loop_raw_original_read_cap_reached
next_target_node=return_summary
```

## Metadata Boundary

- Code may count raw original inspections.
- Code may stop traversal when the raw original read cap is reached.
- Code must not semantically judge whether raw original content was useful.
- R2 still chooses among official refs.
- R3 still judges sufficiency and desired next action until the cap blocks further traversal.

## Non-Goals

- Do not change summary-layer priority.
- Do not increase traversal defaults.
- Do not connect R route to node_1/node_2/node_3 live flow.
- Do not mutate Neo4j.
- Do not add semantic-axis traversal.
- Do not add keyword or text heuristics.

## Verification Targets

- R traversal stops after 5 raw original inspections if it would otherwise continue.
- The 6th raw source is not selected.
- Summary-layer traversal does not increment raw original read count.
- Result frame records raw original count, max cap, and cap reached status.
