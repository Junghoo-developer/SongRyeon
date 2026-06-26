# read_artifact exact reference tool 2026-06-23 001

## Status

Implemented and smoke-tested.

## Problem

`search_docs` is a semantic search tool. When the user asks for an explicit artifact such as `CODE_STRUCTURE_MAP_v1`, semantic ranking can prefer an index document like `README.md` because that document mentions the artifact name.

That behavior is valid for semantic search, but it is wrong for explicit artifact reading.

## Decision

Do not make `search_docs` more complicated.

Add `read_artifact` as a separate read-only tool:

- `search_docs`: semantic search for described content.
- `read_artifact`: exact artifact reference resolver for document names, file names, file stems, paths, and order IDs.

## Implementation Notes

- `document_tools.read_artifact` resolves explicit references against the document memory index.
- L2 may now choose `search_docs` or `read_artifact`.
- `read_artifact` uses `query_mode=exact_artifact_ref`.
- L controller executes `read_artifact` directly when L2 selected it.
- `read_artifact` results remain `tool_result:read_artifact`, not disguised as `read_doc`.
- Node2/Node3/L3 treat `read_artifact` as a document extract source.
- Runtime output displays `TOOL:read_artifact` and `selection_method=read_artifact_payload`.

## Verification

Commands:

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

Result:

```text
SMOKE_TEST_OK
read_artifact_doc_id = 03_Maps/02_Function_Maps/CODE_STRUCTURE_MAP_v1.md
read_artifact_l_loop_tool = read_artifact
```

## Design Boundary

This is not an L3 retry loop.

It fixes the earlier layer first: tool responsibility and tool selection. L3 continuation should be designed after exact artifact reading and semantic search are clearly separated.
