# ORDER 191: R2 Source Ingest Branch Selection Stability v0

## Status

Approved by the user on 2026-07-03 for immediate implementation.

## Trigger

ORDER 190 opened lower summary traversal under token-budget summary nodes. Live probing then showed a different bottleneck:

```text
R2 sometimes selects a plain TimeBundle branch when the user is asking about source/token summary structure.
```

This is not a raw-original overread issue. It is a branch-signage issue at the graph traversal surface.

## Goal

Make the R2 candidate surface distinguish structural branch roles so that source/code/document graph questions can select the source-ingest path more reliably.

This order must not make code choose semantic relevance. Code only labels graph branches by explicit structural node kind.

## Structural Branch Roles

R candidate surfaces may expose:

```text
graph_axis
source_material_ingest
source_material_leaf
summary_memory
conversation_time_memory
unknown_graph_branch
```

Meaning:

- `graph_axis`: top-level graph axis entry.
- `source_material_ingest`: source ingest / source kind branch for code, internal documents, and source material.
- `source_material_leaf`: raw source or low-level source material.
- `summary_memory`: existing summary graph node material.
- `conversation_time_memory`: conversation/time bundle branch.
- `unknown_graph_branch`: structurally unclassified graph branch.

## Implementation Requirements

1. Add `branch_role` to candidate layer surface records.
2. Add `branch_role` to R2 visible surface records.
3. Add `branch_role` to R2 visible candidate records.
4. Sort child surfaces structurally:
   - source ingest/source kind branch before conversation time bundle branch
   - summary layers before generic/unknown lower material
   - conversation time memory after source material branches
5. Update R2 prompt:
   - `branch_role` is a code-supplied structural label.
   - R2 still performs semantic choice.
   - If the goal is about source summaries, token summaries, source kinds, code files, internal documents, or graph ingest structure, R2 should prefer a compatible source/material branch when present.
   - If the goal is about past conversation turns or time memory, R2 should prefer conversation/time memory when present.

## Metadata Boundary

Code may:

- classify graph node kind into a structural `branch_role`
- sort surfaces by structural role
- expose branch roles to R2

Code must not:

- decide that a branch is semantically relevant to the user's question
- force R2 to select source ingest
- use keyword fallback or hidden heuristics
- hide available time-bundle branches

R2 choice remains LLM-generated mixed/semantic judgment.

## Non-Goals

- Do not connect R traversal to normal qwen-chat route.
- Do not connect R result to node_3.
- Do not add branch comparison traversal.
- Do not add semantic-axis traversal.
- Do not increase raw original cap.
- Do not write graph nodes.
- Do not add keyword heuristics.

## Verification Targets

- TimeAxis child surface exposes both `source_material_ingest` and `conversation_time_memory`.
- R2 payload carries branch roles on both surface records and candidate records.
- The structurally ordered surface presents source ingest before time bundle.
- Existing R traversal tests still pass.
- Live Qwen source/token-summary traversal should be less likely to enter TimeBundle accidentally.

