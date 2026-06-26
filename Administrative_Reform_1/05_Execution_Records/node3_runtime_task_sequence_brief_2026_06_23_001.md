# node3 runtime task sequence brief 2026-06-23 001

## Status

Implemented and smoke-tested.

## Problem

The runtime view showed Task Ledger v0, but node_3 did not receive that runtime sequence as answer material.

When the user asked which nodes were recorded as tasks in order, node_3 searched internal documents and answered that the documents did not contain such a record.

That answer was grounded, but it failed the user's actual request.

## Decision

Do not add keyword heuristics.

Instead, always pass a current runtime task sequence into the node_3 input brief.

## Implementation Summary

Changed schema:

- Added `Node3BriefRuntimeTask`
- Added `runtime_tasks` to `Node3InputBriefFrame`

Changed node_2 handoff:

- `record_node3_input_brief` now accepts current `runtime_movements`
- Converts them into a sanitized task sequence
- Does not expose raw trace IDs, data IDs, or task IDs to node_3

Changed node_3 payload:

- Added `available_runtime_task_count`
- Added `runtime_task_sequence`
- Added a note that this is captured before node_3 report generation

Changed prompts:

- node_3 may answer from document extracts, allowed claims, and runtime task sequence
- node_4 treats runtime task sequence as valid grounding material
- raw internal tracking IDs remain blocked

Changed runtime view:

- `node_3 input brief` now displays `runtime_tasks=N`

Changed smoke-test:

- Verifies node_3 brief includes runtime tasks
- Verifies raw internal IDs do not leak into each runtime task item

## Verification

Commands:

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
python main.py fake-turn "방금 턴에서 어떤 노드들이 어떤 순서로 task로 기록됐는지 설명해줘" --pretty --force-l
python main.py qwen-turn "방금 턴에서 어떤 노드들이 어떤 순서로 task로 기록됐는지 설명해줘" --timeout 120 --include-report
```

Observed result:

```text
node_3 input brief: ready / documents=1 / claims=3 / runtime_tasks=11
Qwen report described the current node/task order from the supplied runtime sequence.
node_4 gatekeeper passed.
```

## Boundary

This is not a scheduler.

This does not use a keyword heuristic.

This only gives node_3 an honest, sanitized snapshot of current-turn execution order before report generation.

