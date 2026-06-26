# Live L Loop Continuation 2026-06-24 001

## Goal

Wire the previously isolated L-loop continuation pieces into the live `run_l_loop` graph.

The target path is:

```text
L3 partial
-> L continuation decision
-> node_0 l3_continuation_summary_for_L2
-> L2 revision input
-> L2 revision query planner
-> revision tool attempt
-> L3 revision recheck
-> second L continuation decision
```

## Changes

- `songryeon_core/loops/l_loop.py`
  - Added live continuation wiring after the first L3 judgement.
  - Added attempt-scoped revision output tracking.
  - Added `final_continuation_status` and `final_continuation_data_id` to `LLoopResult`.
  - The live continuation path runs only when an L2 query planner adapter exists.

- `songryeon_core/nodes/l2_revision_input.py`
  - Fixed revision input construction so it reads the L2/L3 source IDs from the continuation frame.
  - This prevents later revision attempts from accidentally reading only the first `L2:query_frame` and `L3:achievement_frame`.

- `songryeon_core/runtime/dry_run.py`
  - Passes `zero_state` into `run_l_loop`.
  - Exposes continuation counts and final continuation status in runtime results.

- `songryeon_core/runtime/user_turn.py` and `main.py`
  - Expose continuation summary values in turn JSON.

- `songryeon_core/runtime/terminal_view.py`
  - Shows `L continuation`, `L2 revision query`, and `L3 revision recheck` blocks in pretty runtime output.

- `songryeon_core/runtime/smoke_test.py`
  - Added live continuation smoke coverage.

## Metainfo Boundary

- The continuation controller reads structured L3/L2 frame IDs and tool budget counts.
- It does not interpret free-form L3 reasons.
- L3 revision recheck remains `CODE:OPERATION_CHECK` with `llm_semantic_judgement_status=not_run`.
- The old tool controller `final_control_decision` and the new continuation controller `final_continuation_status` are separate fields.

## Verified

Commands:

```powershell
python -m compileall songryeon_core
python main.py smoke-test
```

Smoke signal:

```text
SMOKE_TEST_OK
live_l_loop_continuation_count = 2
live_l_loop_revision_query_count = 1
live_l_loop_final_continuation = stop_budget_exhausted
```

## Remaining Work

- Decide how a revision attempt should create a new controller success/failure frame.
- Decide qwen-turn/qwen-chat operating budgets. The current default budget is intentionally small:

```text
max_tool_calls = 2
max_read_doc_calls = 1
```

For visible continuation tests, use larger values such as:

```powershell
python main.py qwen-turn "..." --timeout 120 --max-tool-calls 4 --max-read-doc-calls 2 --pretty
```
