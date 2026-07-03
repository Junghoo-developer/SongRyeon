# ORDER_133 Codebase Readonly Inspection MVP Implementation

Date: 2026-06-30

## Scope

ORDER_133 implemented the first code-structure reading MVP.

This is not a coding agent loop. It only gives the L loop read-only inspection tools for the local workspace:

- `list_code_files`
- `search_code`
- `read_code_file`

## Core Changes

- Added `songryeon_core/tools/code_tools.py`.
  - Lists source/config files under the workspace.
  - Searches source/config files by literal substring.
  - Reads one workspace-relative source/config file.
  - Rejects absolute paths, path traversal outside the workspace, ignored cache/venv paths, directories, missing files, and unsupported extensions.

- Extended `build_document_tool_registry()`.
  - The tool catalog now includes 7 read-only tools: existing document tools plus the 3 code inspection tools.
  - `code_root` is optional and defaults to the current working directory.

- Extended L2 query schema and prompts.
  - Added `code_file_list`, `code_search`, and `code_file_read` query modes.
  - Added `list_code_files`, `search_code`, and `read_code_file` as allowed L2 targets.
  - Prompt boundary says these are read-only inspection tools and must not propose edits, patches, file writes, tests, or command execution.

- Extended L loop execution.
  - Initial L2 code tool choices now execute the selected code tool instead of falling through to `search_docs`.
  - Revision tool attempts can also execute code inspection tools when the revision query frame selects them.

- Extended tool result distillation.
  - `list_code_files` and `search_code` are distilled into small candidate-like previews.
  - `read_code_file` is distilled into an excerpt-like preview.
  - These are copied file/line/path facts, not semantic code review.

- Extended node_3 handoff.
  - Successful `read_code_file` records are copied into node_3 supplied context as source-code text.
  - Search/list code results alone do not become raw source context.

- Protected document context packing.
  - `document_context_pack` now excludes candidates that are not readable Markdown documents instead of crashing when L3 preserved candidates include source-code paths.
  - New exclusion reason: `excluded_not_readable_markdown_document`.

## Verification

- `python -m compileall songryeon_core main.py`
  - passed

- `python -m pytest tests/test_order_133_codebase_readonly_inspection.py`
  - 4 passed

- `python -m pytest`
  - 71 passed

- `python main.py smoke-test`
  - `SMOKE_TEST_OK`
  - observed `tool_catalog_count=7`

## Deliberately Not Done

- No file editing tools.
- No patch generation or application.
- No automatic test execution as a SongRyeon runtime tool.
- No AST/dependency graph analysis.
- No W/R loop, scheduler, external DB, vector DB, or long-term memory DB changes.
- No same-turn L reroute policy change.

## Remaining Risk

- Code search is literal substring search, not semantic code understanding.
- Code context currently reuses node_3 supplied context plumbing, so future work may need a separate `source_code_contexts` field if code/document counts must be separated more strictly.
- L3 achievement language still evolved from document evidence language, so later audits should check whether code-inspection turns are described as code evidence rather than document evidence.
