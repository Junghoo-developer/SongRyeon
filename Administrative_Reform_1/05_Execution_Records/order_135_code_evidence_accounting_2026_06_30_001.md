# ORDER_135 Code Evidence Accounting Implementation

Date: 2026-06-30

## Scope

ORDER_135 fixes the downstream accounting gap where `read_code_file` could succeed but L3/node_3 still reported the turn as if no original evidence had been read.

This implementation keeps document evidence and source-code evidence separate. It does not rename code reads into `read_doc`.

## Core Changes

- Added source-code evidence fields.
  - `L3AchievementFrame.read_code_file_paths`
  - `L3AchievementFrame.actual_read_code_file_count`
  - `LLoopReturnSummaryFrame.read_code_file_paths`
  - `LLoopReturnSummaryFrame.actual_read_code_file_count`
  - `Node3InputBriefFrame.actual_tool_read_code_file_paths`
  - `Node3InputBriefFrame.actual_tool_read_code_file_count`
  - `Node3InputBriefFrame.supplied_source_code_context_count`

- Updated L3 goal-match logic.
  - Successful `read_code_file` records are scanned as source-code evidence.
  - If the requested path matches a read source file path, the goal match can be `matched`.
  - The match reason is recorded as `CODE_STATUS:requested_source_code_file_read_code_file_matched`.

- Updated L1 minimum evidence guard.
  - Source-code evidence can satisfy the minimum evidence count when the L tool scope/material expects source-code evidence.
  - Document reads remain counted through `read_doc_ids`.

- Updated L return summary and node_2 handoff.
  - Return summary carries source-code read count/path.
  - route=2 handoff now distinguishes document extract counts from code extract counts.
  - `missing_l_evidence_result` is not added when successful code evidence exists.

- Updated node_3 brief and final grounding block.
  - Grounding now displays `read_doc` count and `read_code_file` count separately.
  - Source-code context count is visible separately from total supplied context.

- Updated prompts.
  - L3 prompt now treats `read_code_file_count` and `read_code_file_paths` as source/config read evidence.
  - node_3 prompt now tells the reporter not to describe `read_code_file` as `read_doc`.

## Verification

- `python -m pytest tests/test_order_133_codebase_readonly_inspection.py tests/test_order_134_l_tool_scope_budget_partition.py tests/test_order_135_code_evidence_accounting.py`
  - 10 passed

- `python -m pytest`
  - 77 passed

- `python -m compileall songryeon_core main.py`
  - passed

- `python main.py smoke-test`
  - `SMOKE_TEST_OK`

## Deliberately Not Done

- No code editing tools.
- No command execution tools.
- No AST/dependency graph analysis.
- No keyword heuristic for deciding code/document scope.
- No W/R loop, scheduler, external DB, vector DB, or long-term memory DB changes.
- No same-turn L reroute policy change.

## Remaining Risk

- Source-code context still travels through the legacy `read_documents`/`supplied_document_contexts` payload shape, although counts now distinguish it.
- Future work may split node_3 context into separate `document_contexts` and `source_code_contexts` fields if the mixed payload name keeps confusing the model or users.
