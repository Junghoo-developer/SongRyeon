# ORDER 153 Graph Memory Integrity And R Experimental Source Recording - Execution Record

Date: 2026-07-01

## Goal

Before opening a real external graph DB, make graph-memory references auditable and remove the dangling source refs found in the experimental R route.

## Implemented

### R experimental graph source recording

The experimental R route now records graph source records before the R handoff is created.

Recorded source ids include batch-specific graph records such as:

- `graph:snapshot:turn_dry_001:r_route_experimental`
- `rloop:graph_guide:graph:snapshot:turn_dry_001:r_route_experimental`
- `graph:time_bundle:turn_dry_001:r_route_experimental`

Shared graph ids that can collide with the final turn graph payload are intentionally not re-recorded in that early branch:

- `graph:core_ego:root`
- `graph:axis:time`
- `graph:edge:contains:graph:core_ego:root:graph:axis:time`

Those shared ids are still recorded by the normal final turn graph-memory build.

### Read-only integrity audit helper

Added `songryeon_core/core/graph_memory_integrity.py`.

The helper checks:

- graph/rloop-prefixed `source_data_ids`
- `graph_memory:edge:*` `from_node_id`
- `graph_memory:edge:*` `to_node_id`

It reports missing references but does not auto-repair them.

## Tests Added

Added `tests/test_order_153_graph_memory_integrity.py`.

Covered cases:

- default dry turn graph-memory integrity passes
- R experimental route records graph source ids and integrity passes
- missing graph/rloop `source_data_ids` are reported
- missing graph edge endpoints are reported

## Verification

Commands passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_153_graph_memory_integrity.py -q
python -m pytest tests/test_order_146_r_route_experimental_gate.py tests/test_order_147_r_result_to_node3_brief.py tests/test_order_153_graph_memory_integrity.py -q
python -m pytest -q
python main.py smoke-test
```

Observed results:

```text
ORDER_153 pytest: 4 passed
R route focused pytest: 14 passed
full pytest: 147 passed in 873.18s
smoke-test: SMOKE_TEST_OK
```

## Not Opened

This order did not open:

- Neo4j/Vessel connection
- graph DB export execution
- semantic graph axis
- R LLM selector
- live R route expansion
- R traversal over `HAS_ACTIVITY_LEDGER`
- node_3 answer injection changes

## Remaining Risk

`R1/R2/R3` dry-run frames still use code-generated wiring decisions in a dry-run skeleton. Before live R traversal is expanded, their metainfo class should be reviewed separately so code-policy wiring does not look like LLM semantic judgment.
