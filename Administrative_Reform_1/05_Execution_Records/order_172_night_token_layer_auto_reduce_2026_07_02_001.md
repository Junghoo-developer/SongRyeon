# ORDER 172 Execution Record: Night Token Layer Auto Reduce

## Summary

Implemented automatic token-layer reduction for `night-summarize-token-layer`.

The command can now process more than one bundle in a bounded run and continue building higher summary layers until the current layer fits the target context budget, reaches `max_steps`, or reaches `max_layer_depth`.

## Key Changes

- Added order:
  - `Administrative_Reform_1/04_Orders/ORDER_172_NIGHT_TOKEN_LAYER_AUTO_REDUCE_UNTIL_CONTEXT_BUDGET_V0.md`
- Updated CLI:
  - `--until-context-budget`
  - `--target-context-chars`
  - `--max-layer-depth`
  - `--max-steps`
- Extended runtime:
  - `songryeon_core/runtime/night_token_budget_layer_summary.py`
- Added tests:
  - `tests/test_order_172_night_token_layer_auto_reduce.py`
- Added graph fast-test coverage:
  - `songryeon_core/runtime/fast_test.py`

## Behavior

- Default one-bundle-at-a-time behavior remains unchanged.
- Auto mode first completes any incomplete layer queue.
- Once a layer is complete, code sums that layer's successful summary text character counts.
- If the layer total is within `target_context_chars`, auto mode stops.
- If the layer is still too large and depth allows, code creates the next layer queue.
- Each step still processes only one bundle and saves after the step.
- v0 budget unit remains explicit `characters`, not hidden tokenizer output.

## Verification

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest tests/test_order_172_night_token_layer_auto_reduce.py -q
# 3 passed

python -m pytest tests/test_order_171_night_token_budget_layer_summary.py tests/test_order_172_night_token_layer_auto_reduce.py -q
# 6 passed

python main.py fast-test --profile graph
# FAST_TEST_OK, 97 passed
```

## Not Done

- No exact tokenizer adapter.
- No semantic axis.
- No R loop live route.
- No failed-bundle retry policy.
- No deletion or overwrite of existing summary nodes.
