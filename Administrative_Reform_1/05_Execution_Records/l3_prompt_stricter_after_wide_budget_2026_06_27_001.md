# L3 prompt stricter after wide budget - 2026-06-27

## Context

The L loop default budget was widened for document trace testing:

- tool calls: 18
- query attempts: 8
- search top-k: 12
- read_doc calls: 10

After that change, L3 still needed clearer judgement guidance so it would not mark a broad or multi-ORDER request as achieved merely because a small old minimum of documents had been read.

## Change

Updated `songryeon_core/prompts/l3_result_keeper_v0.md`.

Added prompt rules that tell L3:

- do not treat two read documents as automatically sufficient for broad requests;
- compare explicit ORDER/document identifiers in the user query against `read_doc_ids` and `read_document_previews`;
- treat README/map/digest/summary documents as partial overview evidence, not a substitute for reading each named source document;
- return `partial` when only some requested identifiers are visibly covered or coverage cannot be verified;
- return `achieved` only when the read documents are sufficient for node 3 to answer the user's actual requested scope.

## Boundary

This is prompt guidance only.

No new code heuristic was added.
No router, L loop graph, node_3 renderer, memory system, W/R loop, scheduler, or external DB behavior was changed.

Absolute counts still come from code/data frames.
The stricter coverage judgement remains L3's LLM semantic judgement.

## Verification

Passed:

- `python -m compileall songryeon_core main.py`
- `python main.py smoke-test`

Smoke result:

- `SMOKE_TEST_OK`
