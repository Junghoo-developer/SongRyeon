# ORDER_135_CODE_EVIDENCE_ACCOUNTING_AND_L3_SUCCESS_BOUNDARY_V0

## Goal

Fix the boundary where `read_code_file` succeeds but downstream accounting still treats the turn as failed because it only counts `read_doc`.

ORDER_133 opened read-only code inspection tools. ORDER_134 made L choose a tool scope before L2 tool selection. A live test then showed the next bottleneck:

- L tool scope selected `code_only`.
- L2 selected `read_code_file`.
- The source file was available to node_3 as context.
- But L3 and downstream count fields still centered on `read_doc`, so the run was described as if no original evidence had been read.

This order separates document evidence from source-code evidence without turning code into a hidden semantic judge.

## Required MVP

### L3 Accounting

Add source-code evidence fields to `L3AchievementFrame`:

- `read_code_file_paths`
- `actual_read_code_file_count`

L3 should still keep `read_doc_ids` for document reads. It must not rename source-code evidence into document evidence.

### Goal Match Boundary

If the requested exact artifact/source path matches a successful `read_code_file` path, L3 may mark the specific file match as `matched`.

This is a path/record match, not semantic code understanding.

### L1 Minimum Evidence Guard

The minimum read requirement must not be checked only against `read_doc` when the tool scope/material is source-code evidence.

For source-code turns, successful `read_code_file` records count as source evidence for the minimum evidence guard.

### Return Summary And Node_3 Brief

Carry source-code counts downstream:

- `LLoopReturnSummaryFrame.actual_read_code_file_count`
- `LLoopReturnSummaryFrame.read_code_file_paths`
- `Node3InputBriefFrame.actual_tool_read_code_file_count`
- `Node3InputBriefFrame.actual_tool_read_code_file_paths`
- `Node3InputBriefFrame.supplied_source_code_context_count`

The node_3 grounding block should show document reads and source-code reads separately.

### Prompt/Runtime Boundary

Update node_3 prompt/runtime wording so:

- `read_doc` means document tool reads only.
- `read_code_file` means source-code file reads only.
- supplied source-code context can be used as copied source text.
- source-code context must not be called a document search result.

## Non-Goals

- No code editing tools.
- No command execution tools.
- No AST/dependency graph analysis.
- No keyword heuristic that decides code/document scope.
- No W/R loop, scheduler, external DB, vector DB, or long-term memory DB changes.
- No same-turn L reroute policy change.

## Verification

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`

Add focused tests proving:

- Successful `read_code_file` is counted separately from `read_doc`.
- L3 can mark an exact requested source file as matched when the read path matches.
- L loop return summary carries source-code evidence counts.
- node_3 grounding block shows code reads separately from document reads.
