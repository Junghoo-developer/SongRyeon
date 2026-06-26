# l loop continuation controller 2026-06-24 001

## Status

Implemented and smoke-tested.

This record covers ORDER 089 step 2: controller decision function.

It does not yet rewire the graph back to L2.

## Why This Boundary Matters

If the runtime records `continue` but does not actually execute L2 again, the trace becomes deceptive.

Therefore this step adds the controller decision/recording function and smoke-tests it in isolation.

The live L loop is not yet changed to take the continuation branch.

## Implemented Module

Added:

```text
songryeon_core/loops/l_loop_continuation.py
```

Main function:

```text
record_l_loop_continuation_decision(...)
```

Responsibilities:

- Read `L3:achievement_frame`
- Read `L2:query_frame`
- Read the latest `tool_use_budget`
- Compute remaining budget counts
- Preserve read and unread candidate document IDs
- Write `LLoopContinuationFrame`

## Decision Rules

The controller uses structured fields only.

It reads:

- `achievement_status`
- `goal_match_status`
- `semantic_goal_match_status`
- latest tool budget counts
- current attempt index
- maximum attempts
- unread candidate document IDs

It does not interpret:

- L3 natural-language reason
- L3 feedback text
- document title meaning
- user input keywords

## Smoke Cases

Smoke-test now checks two cases.

Case 1:

```text
L3 achieved
-> stop_achieved
-> next_target_node = loop_return_summary
```

Case 2:

```text
L3 partial
remaining budget exists
unread candidate exists
-> continue
-> next_target_node = L2
```

Smoke output includes:

```text
l_loop_continuation_stop = stop_achieved
l_loop_continuation_continue = continue
```

## Verification

Commands:

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

Result:

```text
SMOKE_TEST_OK
```

## Not Implemented Yet

- Calling the continuation controller from the live `run_l_loop` path
- `l3_continuation_summary_for_L2`
- L2 revision query plan
- Tool re-execution after continuation
- L3 second judgement after continuation
- Runtime view for continuation branch

