# ORDER 221 Execution Record: R Hierarchy-First Child Summary Visibility

Date: 2026-07-08

## Summary

Implemented hierarchy-first child summary visibility for Vessel R traversal.

R2 and R3 can now receive clean lower summary layers when code can verify that
the child candidates form one summary layer. The implementation does not trim
candidate lists and does not introduce arbitrary prompt-time caps.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/prompts/r3_vessel_inspector_v0.md`
- `tests/test_order_217_r2_candidate_card_enrichment.py`
- `tests/test_order_221_r_child_summary_layer_visibility.py`
- `Administrative_Reform_1/04_Orders/ORDER_221_R_HIERARCHY_FIRST_CHILD_SUMMARY_VISIBILITY_V0.md`
- `Administrative_Reform_1/03_Maps/03_Development_Maps/GRAPH_VESSEL_PERIODIC_HIERARCHY_MAINTENANCE_2026_07_08.md`

## Code Behavior

R2 candidate cards now expose child summary layer fields:

- `child_summary_layer_status`
- `child_summary_layer_data_kind`
- `child_summary_layer_summary_depths`
- `child_summary_layer_record_count`
- `child_summary_layer_records`

R3 receives the corresponding `hierarchy_child_summary_layer`.

The helper returns:

- `clean_summary_layer` when every child is a summary node with one shared
  `data_kind`;
- `non_summary_navigation_layer` when children are not a summary layer;
- `needs_more_hierarchy` when summary children are structurally mixed;
- `no_child_candidates` when there are no children.

## Verification

Commands:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_217_r2_candidate_card_enrichment.py tests/test_order_221_r_child_summary_layer_visibility.py -q
python -m pytest tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py tests/test_order_191_r2_branch_role_surface_stability.py tests/test_order_217_r2_candidate_card_enrichment.py tests/test_order_221_r_child_summary_layer_visibility.py -q
python main.py quick-smoke
git diff --check
```

Results:

```text
compileall passed
5 passed in 0.22s
11 passed in 0.36s
QUICK_SMOKE_OK
git diff --check passed
```

## Not Changed

- No R route policy change.
- No raw original cap change.
- No Neo4j schema rewrite.
- No prompt-time child candidate cap.
- No L loop change.

## Next Thought

Periodic hierarchy maintenance should become a separate order. The system should
audit graph layers, detect mixed or messy child layers, and build intermediate
summary layers instead of hiding candidates from R2/R3.
