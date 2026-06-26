# Runtime Explanation Fields 2026-06-22 001

## Goal

Expose the internal runtime decisions that the user should see during `qwen-turn --pretty` and `qwen-chat`.

## Result

The pretty runtime view now shows:

- node 0 memory compression packets
  - target
  - mode
  - trace evidence count
  - compression summary
- node 1 routing decisions
  - selected route
  - next node 0 mode
  - route reason
- L1 goal setting
  - macro goal
  - macro goal reason
  - micro goal
  - micro goal reason
- L3 goal achievement
  - overall achievement status
  - controller decision
  - macro achievement status and reason
  - micro achievement status and reason

## Code Changes

- `songryeon_core/core/schemas.py`
  - Added `route_reason`.
  - Added `compression_summary`.
  - Added L1 macro/micro goal reason fields.
  - Added L3 macro/micro achievement status and reason fields.
- `songryeon_core/nodes/node_0_memory_supplier.py`
  - Records a rule-based compression summary for each memory packet.
- `songryeon_core/nodes/node_1_router.py`
  - Records routing reasons.
- `songryeon_core/nodes/l1_goal_setter.py`
  - Records macro/micro goal reasons.
- `songryeon_core/nodes/l3_result_keeper.py`
  - Records macro/micro achievement status and reasons.
- `songryeon_core/runtime/terminal_view.py`
  - Renders the new fields in `[runtime]`.
- `songryeon_core/runtime/smoke_test.py`
  - Verifies that the explanation fields are preserved.

## Verification

- `python -m py_compile main.py songryeon_core\core\schemas.py songryeon_core\nodes\node_0_memory_supplier.py songryeon_core\nodes\node_1_router.py songryeon_core\nodes\l1_goal_setter.py songryeon_core\nodes\l3_result_keeper.py songryeon_core\runtime\terminal_view.py songryeon_core\runtime\smoke_test.py`
- `python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 120 --pretty`
- `python main.py smoke-test`

Smoke result:

- `status: SMOKE_TEST_OK`

## Current Interpretation

These fields are still mostly rule-based. They show what the structure did and why the structure made that move. They are not yet full LLM self-reflection.
