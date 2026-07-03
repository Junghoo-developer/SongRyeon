# ORDER_141 CoreEgo Guide Worker LLM Hints Implementation

Date: 2026-06-30

## Scope

Implemented ORDER_141 as a narrow LLM hint layer over the code-generated `RLoopGraphGuidePacketFrame`.

## Changed Files

- `songryeon_core/core/schema_parts/graph_memory.py`
  - Added `CoreEgoGuideWorkerHintFrame`.
  - Added validator for available entry IDs, source graph node IDs, source bundle metadata, and failure frames.
- `songryeon_core/core/schema_parts/__init__.py`
  - Re-exported the new frame and validator.
- `songryeon_core/core/schemas.py`
  - Preserved compatibility import surface for the new frame and validator.
- `songryeon_core/nodes/core_ego_guide_worker.py`
  - Added `run_core_ego_guide_worker_hint`.
  - Records input, LLM call, and hint frame in TraceStore/DataStore.
  - Does not make code fallback recommendations on LLM failure.
- `songryeon_core/prompts/core_ego_guide_worker_v0.md`
  - Added JSON-only traversal hint prompt.
- `tests/test_order_141_core_ego_guide_worker_hints.py`
  - Added success, schema failure, parse failure, direct validator, and separation tests.

## Metainfo Boundary

- `RLoopGraphGuidePacketFrame` remains code-generated absolute information.
- `CoreEgoGuideWorkerHintFrame` is LLM-generated mixed information because it interprets a graph guide source bundle.
- Failed hint frames preserve failure state with empty recommendations.
- Code does not choose a replacement graph entry when the LLM output fails.

## Explicit Non-Goals

- Did not open R route.
- Did not execute R1/R2/R3.
- Did not connect Neo4j or any external DB.
- Did not create semantic axis hierarchy.
- Did not inject the hint into node_1/node_3 user-facing answer flow.

## Verification

Focused verification passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_141_core_ego_guide_worker_hints.py -q
```

Graph/R focused bundle passed:

```powershell
python -m pytest tests/test_order_139_graph_memory_foundation.py tests/test_order_140_r_loop_frame_state_machine.py tests/test_order_141_core_ego_guide_worker_hints.py tests/test_order_142_graph_memory_store_boundary.py -q
```

Full verification passed:

```powershell
python -m pytest
python main.py smoke-test
git diff --check
```

Result:

- `python -m pytest`: `101 passed`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: passed
