# ORDER 171 Execution Record: Night Token Budget Layer Summary

## Summary

Implemented `night-summarize-token-layer`.

This command reads existing active source leaf summary graph nodes, builds a code-generated budget queue, records one token-budget summary bundle graph node, and asks the LLM to summarize that one bundle.

## Key Changes

- Added order:
  - `Administrative_Reform_1/04_Orders/ORDER_171_NIGHT_TOKEN_BUDGET_LAYER_SUMMARY_V0.md`
- Added prompt:
  - `songryeon_core/prompts/night_summarize_token_budget_bundle_v0.md`
- Added worker:
  - `songryeon_core/nodes/night_summarize_token_budget_bundle.py`
- Added runtime CLI backend:
  - `songryeon_core/runtime/night_token_budget_layer_summary.py`
- Added CLI command:
  - `python main.py night-summarize-token-layer`
- Added test:
  - `tests/test_order_171_night_token_budget_layer_summary.py`
- Added graph fast-test coverage:
  - `songryeon_core/runtime/fast_test.py`

## Design Notes

- v0 budget unit is explicitly `characters`, not hidden tokenizer output.
- The queue is code-generated absolute information.
- The bundle node is `graph_memory:node:token_budget_summary_bundle`.
- The bundle node contains source leaf summary nodes through `CONTAINS` edges.
- The successful upper summary is `info_class=mixed`.
- The original leaf summary nodes are not edited or deleted.
- One execution processes at most one bundle.
- Optional Neo4j write remains explicit through `--write-vessel`.

## Verification

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest tests/test_order_171_night_token_budget_layer_summary.py -q
# 3 passed

python -m pytest tests/test_order_169_night_changed_source_summary_cli.py tests/test_order_170_night_changed_source_one_at_a_time.py tests/test_order_171_night_token_budget_layer_summary.py -q
# 10 passed

python main.py fast-test --profile graph
# FAST_TEST_OK, 94 passed
```

## Not Done

- No exact tokenizer adapter.
- No semantic axis.
- No R loop live route.
- No recursive all-layer summarization.
- No automatic failed-bundle retry policy.
