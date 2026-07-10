# ORDER 220 Execution Record: R Traverse Continuation Surface Audit

Date: 2026-07-08

## Summary

Audited the Vessel R traversal continuation path without changing runtime code.

The current implementation already has a structural descent path:

- first candidate surface from CoreEgo/time-axis entry records;
- R2 selects one official surface/node ref;
- R3 inspects the selected record and child candidate records;
- `decide_r_loop_continuation(...)` returns `continue_deeper` when R3 asks for
  lower granularity and child nodes exist;
- code builds the next candidate surface from the graph traversal surface.

The remaining live weakness is not simply "R cannot go down." The weakness is
that R2/R3 currently see child structure and child candidate cards, but not
enough child summary substance to choose confidently in all live cases.

## Files Audited

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/core/r_loop_state_machine.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/prompts/r3_vessel_inspector_v0.md`
- `tests/test_order_184_r_vessel_multi_step_traversal.py`
- `tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py`
- `tests/test_order_191_r2_branch_role_surface_stability.py`
- `tests/test_order_217_r2_candidate_card_enrichment.py`

## Key Findings

### Structural descent exists

`r_loop_vessel_one_step.py` records R2/R3 frames, builds a graph traversal
surface, asks the state machine whether to continue, and creates a next
candidate layer surface from child candidates when continuation is
`continue_deeper`.

### Stop/failure modes differ

The current runtime should distinguish at least these cases:

- R3 did not recommend deeper traversal.
- R3 recommended deeper traversal, but no child candidates existed.
- R3 recommended deeper traversal, next surface existed, but R2 returned
  `none_selected`.
- R2 or R3 produced invalid copy-contract/schema output.

These are different bugs or limitations and should not be collapsed into one
"R failed" label.

### R2/R3 child visibility is intentionally shallow

R2 sees child counts/kinds/branch roles as map signs.

R3 sees hierarchy child candidate records as preview-only navigation cards.

This preserves safety, but it means R2/R3 may know lower material exists without
seeing enough lower summary content to choose naturally.

### User direction is compatible with the architecture

The user's direction is to let R2/R3 see not only the selected node but also
lower-node summaries when the hierarchy is already sufficiently layered.

This should be implemented as a hierarchy-first visibility feature, not as raw
child dumping and not as arbitrary prompt-time candidate trimming. If a child
layer is structurally mixed, the correct fix is more graph hierarchy.

## Verification

Command:

```powershell
python -m pytest tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py tests/test_order_191_r2_branch_role_surface_stability.py tests/test_order_217_r2_candidate_card_enrichment.py -q
```

Result:

```text
9 passed in 0.30s
```

## No Code Changes

This order changed only documentation and execution records.

No runtime behavior, prompt, schema, Neo4j adapter, R route policy, raw original
cap, or L loop behavior was changed.

## Recommended Next Step

Prepare `ORDER_221` for hierarchy-first child-summary visibility:

- expose the next clean child-summary layer to R2/R3;
- if that layer is structurally mixed, report `needs_more_hierarchy` instead of
  silently trimming candidates;
- preserve official refs and copy contracts;
- keep raw originals behind the existing raw read cap;
- add runtime diagnostics for selected-node-only vs child-layer-summary-driven
  decisions.
