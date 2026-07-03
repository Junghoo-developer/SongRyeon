# ORDER_136_CURRENT_CAPABILITY_BASELINE_AND_LIVE_TEST_PACK_V0

## Goal

Freeze the current SongRyeon Core capability baseline before the next feature expansion.

The project has recently added recent-memory supply, L loop continuation, node_2 answer-basis mode, L3 summaries, document material accounting, read-only code inspection, L tool scope, budget partitioning, and source-code evidence accounting. This is now powerful enough that the next risk is not a missing feature but losing track of what the system can actually do.

ORDER_136 documents the current baseline and defines a small live test pack that can be reused before future MVP work.

## Problem

SongRyeon Core now has many safety and evidence-accounting layers:

- node_0 memory supply
- node_1 routing
- L loop document/code evidence collection
- L3 achievement judgement
- node_2 metainfo boundary and answer-basis mode
- node_3 code-supplied grounding block
- node_4 gatekeeper
- runtime/terminal renderer
- pytest and smoke-test baseline

Without a baseline map, future work may accidentally:

- retest the wrong capability,
- confuse document reads with code reads,
- treat a live qwen answer as proof when the runtime signals say otherwise,
- reopen W/R/scheduler/long-term DB work too early,
- or keep adding features before the current system is understandable to humans and external reviewers.

## Required Documentation

Create a capability baseline document under:

`Administrative_Reform_1/03_Maps/03_Development_Maps/`

The document must include:

- current verified capability groups,
- what is deliberately not supported yet,
- live test prompts,
- expected runtime signals for each prompt,
- known weak spots,
- next sustainable work candidates.

## Live Test Pack Requirements

The live test pack should cover:

1. recent conversation memory,
2. internal document search/read,
3. explicit source-code file read,
4. mixed document + code inspection,
5. answer-basis mode behavior,
6. count honesty,
7. failure honesty.

The test pack is manual for now. It should not pretend to be a deterministic CI suite.

## Non-Goals

- No new runtime feature.
- No W loop.
- No R loop.
- No scheduler.
- No external DB/vector DB/long-term memory DB.
- No code editing agent tools.
- No new heuristic classifier.
- No hidden keyword routing policy.

## Completion Conditions

- ORDER_136 file is added.
- Capability baseline/live test pack document is added.
- `04_Orders/README.md` is updated.
- `03_Development_Maps/README.md` is updated.
- Execution record is added.

## Verification

Documentation-only change.

Recommended check:

```powershell
git diff --check
```
