# ORDER 149 R Graph Traversal Candidate Surface Implementation

Date: 2026-07-01

## Summary

Implemented ORDER_149 as a narrow R graph traversal candidate surface.

The new frame gives future R2 traversal a code-generated candidate board without letting code rank semantic relevance.

## Code Changes

- `songryeon_core/core/schema_parts/r_loop.py`
  - Added `RGraphTraversalCandidateSurfaceFrame`.
  - Added `validate_r_graph_traversal_candidate_surface_frame`.
  - Added `R_GRAPH_TRAVERSAL_CANDIDATE_SURFACE_GENERATOR`.
  - Added allowed candidate relations: `child`, `next`, `previous`.

- `songryeon_core/core/schemas.py`
  - Re-exported the new frame and validator through the compatibility layer.

- `songryeon_core/core/schema_parts/__init__.py`
  - Re-exported the new frame and validator through the split-schema package.

- `songryeon_core/loops/r_loop_dry_run.py`
  - Builds candidate surface after R3 inspection.
  - Copies only code-checkable graph coordinates:
    - `R3.child_node_ids` -> `child_candidate_node_ids`
    - outgoing `NEXT` edge targets -> `next_candidate_node_ids`
    - incoming `NEXT` edge sources -> `previous_candidate_node_ids`
  - Records the frame as `node_output:R_graph_traversal_candidate_surface_frame`.
  - Feeds candidate surface ids into `RLoopReturnSummaryFrame` and `TurnGraphAccessLedgerFrame`.

- `songryeon_core/runtime/dry_run.py`
  - Added result keys for candidate surface id/count and next/previous counts.

- `songryeon_core/runtime/terminal_view.py`
  - Added `R graph traversal candidates` runtime display.

- `tests/test_order_149_r_graph_traversal_candidate_surface.py`
  - Added child candidate and NEXT/previous candidate tests.

## Guardrails Preserved

- R2 selection behavior was not changed.
- No multi-step R traversal was opened.
- No R LLM traversal was added.
- No live R route expansion was added.
- No external DB / Neo4j connection was opened.
- No semantic ranking or relevance judgement was added.
- Candidate surface is code-generated absolute information:
  - `generated_by=CODE:R_GRAPH_TRAVERSAL_CANDIDATE_SURFACE`
  - `info_class=absolute`
  - `semantic_judgement_status=not_run`

## Verification

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Pytest result:

```text
133 passed in 484.63s
```

Smoke result:

```text
SMOKE_TEST_OK
```

## Remaining Risk

The candidate surface is now recorded, but R2 does not yet consume it for multi-step traversal. The next candidate order should decide how R2 receives this surface and how budgeted traversal repeats without opening live R route broadly.
