# Release Notes

## 2026-07-03: Vessel Graph Memory And R Traversal Baseline

This is the first public baseline where SongRyeon Core can show a local graph-memory path end to end.

Merged PR:

- [PR #2: Integrate Vessel graph memory and R traversal baseline](https://github.com/Junghoo-developer/SongRyeon/pull/2)

Main commit:

- `8fe05aa Merge Vessel graph memory and R traversal baseline`

## What Is New

- Graph memory foundation:
  - `CoreEgo`
  - `Time Axis`
  - `Time Bundle`
  - raw capsules, source ingest bundles, source kind bundles, raw sources, and summary nodes
- Local Neo4j Vessel adapter:
  - write plan boundary
  - first write command
  - readback verification
  - inspect command
- Source ingest and night summary pipeline:
  - changed source leaf summaries
  - token-budget summary layers
  - checkpointed long-run support
  - summary invalidation/source lineage groundwork
- Experimental Vessel-backed R traversal:
  - R1 goal setting
  - R2 graph node selection
  - R3 inspection/sufficiency
  - multi-step traversal
  - summary-before-raw traversal
  - raw original read cap
  - user-question anchor copy guard
- Development gates:
  - full pytest baseline
  - smoke-test GitHub Actions
  - graph-focused fast-test profile

## Verified Before Merge

```text
python -m pytest -> 279 passed
python main.py smoke-test -> SMOKE_TEST_OK
python main.py fast-test --profile graph -> FAST_TEST_OK
git diff --check -> passed
```

After merge to `main`, GitHub Actions `smoke-test` completed successfully.

## What This Is Not Yet

- Not a production assistant.
- Not a hosted cloud service.
- Not a fully automatic long-term memory system.
- Not yet a normal live-chat route that automatically uses R traversal in final answers.
- Not yet a polished external developer SDK.

## Next Development Target

The next narrow MVP is `ORDER_193_R_RESULT_TO_NODE3_VESSEL_MATERIAL_V0`.

Goal:

```text
Let R traversal results become explicit read-only material for node_3,
without pretending that graph traversal is already part of the normal answer route.
```
