# ORDER 148 Graph NEXT And Turn Access Ledger Implementation

Date: 2026-07-01

## Summary

Implemented ORDER_148 as a narrow graph-memory provenance step.

This change adds:

- time-adjacent `NEXT` edges between deduped raw capsule graph nodes
- `TurnGraphAccessLedgerFrame` for per-turn graph access coordinates
- R skeleton DataStore recording for graph access ledger frames
- runtime display for graph access ledger counts

## Code Changes

- `songryeon_core/core/schema_parts/graph_memory.py`
  - Added `NEXT` to `GRAPH_MEMORY_EDGE_KINDS`.
  - Added `TurnGraphAccessLedgerFrame`.
  - Added `validate_turn_graph_access_ledger_frame`.
  - Added `GRAPH_ACCESS_LEDGER_CODE_GENERATOR=CODE:GRAPH_ACCESS_LEDGER`.

- `songryeon_core/core/schemas.py`
  - Re-exported the new schema and validator through the compatibility layer.

- `songryeon_core/core/schema_parts/__init__.py`
  - Re-exported the new schema and validator through the split-schema package.

- `songryeon_core/core/graph_memory.py`
  - `build_graph_memory_snapshot_from_capsules()` now creates `NEXT` edges between adjacent deduped raw capsule nodes.

- `songryeon_core/loops/r_loop_dry_run.py`
  - `run_r_loop_dry_run_skeleton()` now builds and records a `TurnGraphAccessLedgerFrame`.
  - The ledger copies R2/R3 graph coordinates:
    - R2 available nodes -> `candidate_graph_node_ids`
    - R2 selected node -> `selected_graph_node_ids`
    - R3 inspected node -> `inspected_graph_node_ids`
    - R3 child nodes -> additional `candidate_graph_node_ids`

- `songryeon_core/runtime/dry_run.py`
  - Added result keys for R dry-run / experimental access ledger ids and counts.

- `songryeon_core/runtime/terminal_view.py`
  - Added `R graph access ledger` runtime display block.

- `tests/test_order_148_graph_next_and_access_ledger.py`
  - Added NEXT edge and access ledger tests.

## Guardrails Preserved

- No external DB / Neo4j connection was opened.
- No semantic axis was created.
- No R LLM traversal was added.
- No live R route policy expansion was added.
- No graph summary or memory summary was generated.
- `TurnGraphAccessLedgerFrame` is code-generated absolute information:
  - `generated_by=CODE:GRAPH_ACCESS_LEDGER`
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
131 passed in 516.56s
```

Smoke result:

```text
SMOKE_TEST_OK
```

## Remaining Risk

The ledger records R skeleton graph coordinates, but live R traversal is still gated and limited. Future work should decide how external graph DB reads map to `read_graph_node_ids` and how final answers mark `used_as_answer_source_graph_node_ids`.
