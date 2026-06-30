# ORDER_134_L_TOOL_SCOPE_AND_BUDGET_PARTITION_V0

## Goal

Make the L loop decide its evidence/tool scope before L2 chooses individual tools.

This order exists because ORDER_133 added read-only code inspection tools, but a live test showed that L2 kept using document search only. The fix must not be keyword heuristics such as "if user says code, use code tools." Instead, the L loop must first record an explicit tool-scope contract, then allocate budgets by allowed tool group, and only then allow L2 to choose tools inside that contract.

## Problem

Current L2 receives a flat tool catalog and is asked to choose a target tool directly. In mixed requests such as "read ORDER_133 and actual source code," L2 may keep selecting `search_docs` even though code tools exist.

That is not a tool implementation failure. It is a missing planning layer:

- L1 describes the evidence goal.
- L2 chooses one tool/query.
- But no frame says which evidence worlds are open this turn.
- No frame divides budget between document tools and code inspection tools.
- Therefore L2 can over-focus on one tool family.

## Required MVP

Add a small L tool scope stage after L1 and before L2 query planning.

### New frame

Create `LToolScopeFrame` with at least:

- `frame_id`
- `turn_id`
- `tool_scope_mode`
  - `document_only`
  - `code_only`
  - `document_and_code`
  - `runtime_trace_only`
  - `mixed_evidence`
- `allowed_tool_groups`
  - `document_tools`
  - `code_inspection_tools`
  - `runtime_record_tools`
- `required_materials`
  - `order_document`
  - `source_code_file`
  - `code_search_result`
  - `runtime_trace`
  - `execution_record`
  - `project_document`
- `scope_reason`
- `scope_reason_info_class`
- `generated_by`
- `info_class`
- `semantic_judgement_status`
- `source_trace_ids`
- `source_data_ids`

### Responsibility boundary

- LLM chooses the scope.
- Code validates enum values and allowed tool groups.
- Code must not decide from user keywords which tool group is semantically needed.
- If the scope LLM fails or is absent, code may use a compatibility fallback, but it must label it as `CODE:FALLBACK`, `semantic_judgement_status=failed`, and must not pretend it is a semantic decision.

### Tool catalog filtering

After `LToolScopeFrame` is recorded:

- L2 receives only tools allowed by the selected tool groups.
- `document_tools` allow existing document tools.
- `code_inspection_tools` allow `list_code_files`, `search_code`, `read_code_file`.
- `runtime_record_tools` is reserved for later and should not add new tools in this MVP.

### Budget partition

Add a code-built budget partition record from the approved L budget and the tool scope:

- `document_tool_call_budget`
- `document_query_budget`
- `document_read_budget`
- `code_tool_call_budget`
- `code_query_budget`
- `code_read_budget`

For this MVP, simple explicit partition policy is acceptable:

- `document_only`: all approved budget to document group.
- `code_only`: all approved budget to code group.
- `document_and_code`: reserve at least 1 code query/read/tool call when possible, and at least 1 document query/read/tool call when possible.
- `mixed_evidence`: split conservatively between document and code when both groups are allowed.
- `runtime_trace_only`: no new external/document/code tools beyond existing runtime records in this MVP.

This partition is a policy decision derived from the explicit scope frame, not hidden semantic classification.

### L2 contract

L2 query planner input must include:

- `l_tool_scope`
- `budget_partition`
- filtered `available_tools`

The prompt must say:

- choose tools only from the supplied `available_tools`;
- if both `order_document` and `source_code_file` are required, create candidates that cover both document and code tools when available;
- do not claim a tool ran before it actually runs.

## Tests

Required verification:

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`

Add pytest coverage:

- scope LLM can select `document_and_code` and the frame validates.
- allowed tool catalog is filtered to document + code inspection tools.
- L2 planner receives filtered tools and scope payload.
- L2 candidate outside the allowed scope is rejected or filtered.
- budget partition for `document_and_code` reserves nonzero document and code budgets when global budget allows.
- fallback scope is explicit `CODE:FALLBACK` with failed semantic status.

## Out Of Scope

- No keyword heuristics.
- No code editing tools.
- No patch generation/application.
- No automatic test-running tool inside SongRyeon runtime.
- No W/R loop.
- No scheduler.
- No external DB/vector DB/long-term memory DB.
- No same-turn L reroute policy change.
- No runtime trace tool implementation yet.

## Completion Report Must Include

- where `LToolScopeFrame` is created;
- how tool groups map to allowed tools;
- how budget partition is recorded;
- what L2 receives;
- what happens on scope LLM failure;
- compileall / pytest / smoke-test results.
