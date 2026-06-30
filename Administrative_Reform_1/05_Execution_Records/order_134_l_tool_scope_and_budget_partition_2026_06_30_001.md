# ORDER_134 L Tool Scope And Budget Partition Implementation

Date: 2026-06-30

## Scope

ORDER_134 adds an explicit L tool-scope stage before L2 query planning.

This was implemented after ORDER_133 added read-only code inspection tools, but live testing showed that L2 could still keep using document search only. The fix is not a keyword heuristic. L now records an explicit scope frame first, then code filters the tool catalog and builds a budget partition from that recorded scope.

## Core Changes

- Added `LToolScopeFrame`.
  - `tool_scope_mode` is constrained to `document_only`, `code_only`, `document_and_code`, `runtime_trace_only`, or `mixed_evidence`.
  - `allowed_tool_groups` is constrained to explicit tool groups.
  - LLM success is recorded as `info_class=mixed` and `semantic_judgement_status=ran`.
  - Missing/failed LLM scope planning is recorded as `CODE:FALLBACK`, `info_class=absolute_status`, and `semantic_judgement_status=failed`.

- Added `LToolBudgetPartitionFrame`.
  - Code builds document/code budget slices from the approved L budget and the recorded scope.
  - Code does not decide semantic relevance from user keywords.
  - The budget partition is an absolute policy decision derived from explicit frame values.

- Added `songryeon_core/nodes/l_tool_scope.py`.
  - Runs the scope planner.
  - Records fallback status honestly.
  - Filters the tool catalog by allowed tool groups.
  - Builds the budget partition frame.

- Added `songryeon_core/prompts/l_tool_scope_planner_v0.md`.
  - Asks the LLM to choose the evidence/tool world before L2 selects a specific tool.
  - Distinguishes document tools, code inspection tools, and future runtime record tools.

- Updated L2 query planning.
  - `run_l2_query_planner()` and `run_l2_revision_query_planner()` now receive `l_tool_scope`, `budget_partition`, and a filtered tool catalog.
  - L2 candidates outside the filtered allowed tools fail schema validation.
  - Revision L2 retains compatibility with ORDER_122 by allowing default `read_doc` when no explicit tool catalog is supplied.

- Updated L loop wiring.
  - The L loop now runs scope planning after L1 and before L2.
  - The L loop passes the filtered catalog and budget partition to initial and revision L2 planning.
  - Fallback L2 tool selection respects the filtered catalog.

- Updated runtime output.
  - Terminal output now displays L tool scope and L budget partition records.

- Updated ORDER_133 code inspection tests.
  - Code-inspection behavior now uses an explicit `code_only` scope adapter.
  - This preserves the ORDER_134 rule that code tools are opened by a recorded scope, not by hidden keyword matching.

## Verification

- `python -m compileall songryeon_core main.py`
  - passed

- `python -m pytest tests/test_order_122_l_revision_read_doc_path.py tests/test_order_134_l_tool_scope_budget_partition.py`
  - 9 passed

- `python -m pytest`
  - 76 passed

- `python main.py smoke-test`
  - `SMOKE_TEST_OK`
  - observed `tool_catalog_count=7`

## Deliberately Not Done

- No user-keyword routing heuristic.
- No code editing tools.
- No automatic test execution as a SongRyeon runtime tool.
- No runtime trace tool implementation for `runtime_record_tools`.
- No W/R loop, scheduler, external DB, vector DB, or long-term memory DB changes.
- No same-turn L reroute policy change.

## Remaining Risk

- `runtime_trace_only` is reserved by schema, but no runtime-record tool exists yet.
- Live Qwen behavior still depends on whether the L scope planner chooses `code_only` or `document_and_code` when the user asks for source inspection.
- The scope frame opens the correct tool world structurally; it does not guarantee the model will choose the best exact file or query inside that world.
