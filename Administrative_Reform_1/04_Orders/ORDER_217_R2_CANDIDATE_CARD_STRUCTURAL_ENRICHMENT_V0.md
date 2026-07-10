# ORDER 217: R2 Candidate Card Structural Enrichment v0

## Status

Implemented on 2026-07-08.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_217_r2_candidate_card_structural_enrichment_2026_07_08_001.md`

## Goal

Make Vessel R2 selection more stable by enriching each visible candidate card
with code-copied structural facts about its next graph layer.

## Background

ORDER 216 made R traversal safer by preserving per-step memory and keeping
child candidates preview-only. Live testing showed that R2 can still fail to
choose a next node after inspecting `TimeAxis`.

The failure is not mainly an LLM prompt problem. R2 receives official candidate
refs, but the candidate card does not yet clearly say what kind of structure is
below each candidate.

## Scope

Add absolute, code-generated structural fields to R2 candidate cards:

- child candidate count
- child candidate kind counts
- child branch role counts
- child data kind counts
- child summary depth values
- whether child candidates include summary material
- whether child candidates include token-budget summaries
- whether child candidates include source-leaf summaries
- whether child candidates include raw/original material

## Rules

- Do not expose full child summary text in R2.
- Do not expose raw/original text in R2.
- Do not expose hidden graph IDs as selectable output.
- Keep `node_ref` and `surface_ref` as the only selectable identifiers.
- Code supplies structure facts only.
- R2 still performs the semantic choice.
- R3 still performs sufficiency/granularity/branch status judgment.

## Non-Goals

- Do not add code fallback relevance selection.
- Do not regenerate Neo4j summaries.
- Do not change R traversal budgets.
- Do not implement full branch switching.
- Do not weaken R2/R3 schema validators.

## Completion Checks

- R2 payload candidate cards include child structure facts.
- The enrichment contains no `summary_text`.
- A source ingest candidate can show that source kind children exist.
- A source kind candidate can show that token summary children exist.
- `python -m compileall songryeon_core main.py`
- focused pytest for ORDER 217
- related R-loop pytest
- `python main.py smoke-test`
