# All LLM Nodes Activation 2026-06-22 001

## Linked Orders

- `ORDER_069_NODE1_LLM_ROUTER.md`
- `ORDER_070_L1_LLM_GOAL_SETTER.md`
- `ORDER_071_L3_LLM_RESULT_KEEPER.md`
- `ORDER_072_NODE2_LLM_METAINFO_BOUNDARY_V2.md`
- `ORDER_073_NODE3_LLM_REPORTER.md`
- `ORDER_074_NODE4_GATEKEEPER_AND_RETURN_LOOP.md`
- `ORDER_075_METAINFO_GOVERNANCE_E2E_SMOKE.md`

## Result

The runtime now supports LLM calls across the MVP node chain:

- node_1 router
- L1 goal setter
- L2 query planner
- L3 achievement judgement
- node_2 boundary review
- node_3 reporter
- node_4 gatekeeper

Code still owns absolute operational facts such as IDs, trace existence, tool calls, document extracts, and schema validation.
LLM-generated reasons and reports are marked as mixed/relative judgement candidates with source trace/data IDs.

## Runtime Visibility

`--pretty` now exposes the important intermediate processing records:

- node_1 route source and reason status
- L1 macro/micro goals and LLM reasons
- L2 query plan
- tool results and copied document extract source
- L3 achievement judgement and LLM reasons
- node_2 boundary review
- node_3 report generation source
- node_4 gatekeeper status

## Validation

Commands run:

```powershell
python main.py smoke-test
python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --pretty
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 180 --pretty
python main.py qwen-turn "너는 누구니?" --timeout 180 --pretty
```

Observed result:

- `smoke-test` passed.
- Qwen document-memory question used node_1, L1, L2, L3, node_2, node_3, node_4 LLM calls.
- Qwen identity question now routes to L because identity/self-description must be grounded in internal documents.
- node_4 returned `pass` after receiving mixed info and document extracts as checkable grounding material.

## Remaining Limits

- node_4 currently records `pass`, `needs_revision`, or `failed`; it does not yet re-run a correction loop.
- node_0 memory compression remains code/rule based.
- L loop tool choice/controller are still code policy, not LLM tool-use planning.
