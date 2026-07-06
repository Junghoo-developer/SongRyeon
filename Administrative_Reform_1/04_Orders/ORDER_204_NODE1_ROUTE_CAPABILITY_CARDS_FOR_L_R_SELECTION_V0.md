# ORDER_204_NODE1_ROUTE_CAPABILITY_CARDS_FOR_L_R_SELECTION_V0

## Status

Accepted for immediate implementation.

## Goal

Strengthen node_1's explanation of the difference between the L loop and the Vessel R loop so that, when the Vessel R route is explicitly enabled, node_1 can choose between `L`, `R`, and `2` by comparing evidence surfaces instead of treating every project-memory question as document search.

## Background

Recent live tests showed two facts:

- `--force-vessel-r-route` successfully runs the Vessel R path and returns graph material to node_3.
- `--enable-vessel-r-route` alone still lets node_1 choose `L` for a question asking whether graph memory traversal is more suitable than document search.

This means the R path exists, but node_1's view of the route choices is still too weak. The current prompt describes R as an experimental graph route, while L is described broadly as internal document / long-term memory search. This makes the L route look safer even when the user is asking about already-ingested Vessel graph memory.

## Scope

Add code-supplied route capability cards to node_1's LLM input.

The cards must explain:

- `L`: use when the requested evidence must be found in source documents, code files, artifacts, or unread project material.
- `R`: use only when R is present in `allowed_routes`, and the requested evidence surface is already-ingested Vessel / Neo4j graph memory, graph structure, summary layers, CoreEgo time-axis traversal, or a comparison of graph traversal vs document search.
- `2`: use when existing supplied memory/context is enough and no loop is needed.

## Non-Goals

- Do not add hidden keyword routing.
- Do not make code semantically decide that a user question is R-suitable.
- Do not force R unless `--force-vessel-r-route` is explicitly used.
- Do not change R1/R2/R3 traversal behavior.
- Do not change L loop search/read policy.
- Do not add W loop, scheduler, external DB changes, or automatic learning-loop changes.

## Implementation Plan

1. Add `route_capability_cards` to node_1 LLM input payload.
2. Keep `allowed_routes` as the hard source of truth.
3. Make the R card appear only when the experimental Vessel R route is enabled.
4. Update `node_1_router_v0.md` so node_1 compares the requested evidence surface before choosing a route.
5. Add tests that verify:
   - node_1 receives concrete L/R/2 capability cards when R is enabled.
   - the R card is absent when R is disabled.
   - R remains an LLM-selected route under the explicit R gate, not a code fallback.

## Completion Conditions

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_204_node1_route_capability_cards.py -q`
- Relevant R route tests still pass.
- `python main.py smoke-test`

## Expected Human Decision After This

If ORDER_204 passes and live testing shows node_1 can naturally select R for graph-memory questions, SongRyeon Core should pause broad feature expansion and transition to a human-centered learning loop. The next work should prioritize:

- explaining the implemented system to the user,
- reducing dependence on Codex,
- auditing route behavior slowly,
- and turning the project routine toward user learning, not raw development speed.
