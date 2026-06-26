# Runtime Honesty Patch 2026-06-22 001

## Goal

Expose which runtime text was produced by Qwen, which text was produced by code, which text came from tools, and which LLM judgement has not run yet.

## Problem

The previous pretty runtime view showed code-generated rule explanations as if they were node judgement. That made it difficult to tell whether L1, L3, node 0, and node 1 were real LLM nodes or rule-based scaffolds.

## Result

The terminal view now labels runtime output with explicit provenance:

- `CODE:RULE_STUB`
- `CODE:POLICY_STUB`
- `RULE_STUB`
- `CODE:OPERATION_CHECK`
- `CODE/RENDERER`
- `TOOL_RESULT`
- `TOOL_RESULT:DOCUMENT_EXTRACT`
- `LLM:qwen3:14b`

The view also explicitly prints:

- `LLM_SUMMARY=not_run`
- `LLM_ROUTER=not_run`
- `LLM_GOAL=not_run`
- `LLM_SEMANTIC=not_run`
- `LLM_REPORTER=not_run`

## Important Behavioral Fix

`force_l_route` no longer works by adding hidden text such as `내부 문서 검색` into the router input.

Instead, node 1 receives `force_l_route=True` as an explicit policy flag and records:

```text
route_source=CODE:POLICY_STUB
```

This prevents policy injection from looking like user keyword detection.

## Code Changes

- `songryeon_core/core/schemas.py`
  - Added generation/provenance fields to memory packets, routing decisions, L1 goals, and L3 achievement frames.
- `songryeon_core/nodes/node_0_memory_supplier.py`
  - Marks node 0 memory packets as `CODE:RULE_STUB`.
- `songryeon_core/nodes/node_1_router.py`
  - Marks keyword routing as `CODE:RULE_STUB`.
  - Marks forced L routing as `CODE:POLICY_STUB`.
- `songryeon_core/runtime/dry_run.py`
  - Passes `force_l_route` as a policy flag instead of modifying user input.
- `songryeon_core/nodes/l1_goal_setter.py`
  - Marks L1 goal generation as `RULE_STUB`.
- `songryeon_core/nodes/l3_result_keeper.py`
  - Marks L3 achievement as `CODE:OPERATION_CHECK`.
- `songryeon_core/runtime/terminal_view.py`
  - Renders provenance labels and `not_run` LLM judgement statuses.
- `songryeon_core/runtime/smoke_test.py`
  - Verifies honesty/provenance fields.

## Verification

- `python -m py_compile main.py songryeon_core\core\schemas.py songryeon_core\core\registry.py songryeon_core\runtime\dry_run.py songryeon_core\nodes\node_0_memory_supplier.py songryeon_core\nodes\node_1_router.py songryeon_core\nodes\l1_goal_setter.py songryeon_core\nodes\l3_result_keeper.py songryeon_core\runtime\terminal_view.py songryeon_core\runtime\smoke_test.py`
- `python main.py qwen-turn "너는 누구니?" --timeout 120 --pretty --force-l`
- `python main.py smoke-test`

Smoke result:

- `status: SMOKE_TEST_OK`

## Current Interpretation

At this stage, only L2 query planning is a Qwen LLM node.

Node 0, node 1, L1, L3, and the final answer renderer are still code/rule scaffolds unless the runtime view says otherwise.
