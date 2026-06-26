# W Loop Pre-Coding Plan 2026-06-22 001

## Status

This is an execution record and pre-coding checklist.

It does not replace the official orders. It summarizes the minimum coding order needed after `ORDER_080` to `ORDER_085`.

## Current Decision

The next coding target is not R loop.

The next coding target is:

```text
1. node_4 remand blocking
2. W1 schema
3. W1 LLM node and prompt
4. W runtime wiring
5. W smoke/runtime view
```

Reason:

- The current system can already detect some final-answer problems through node_4.
- But if node_4 says `needs_revision`, the bad answer can still be printed.
- This breaks runtime honesty before W is even useful.
- After that, W can be added as a problem-triage loop without stealing route authority from node_1.

## Source Documents

- `01_Maintenance_System/LOOP_AUTHORITY_AND_W_POLICY_v0.md`
- `04_Orders/ORDER_080_W_LOOP_AUTHORITY_POLICY.md`
- `04_Orders/ORDER_081_W1_PROBLEM_TRIAGE_SCHEMA.md`
- `04_Orders/ORDER_082_W1_LLM_NODE_AND_PROMPT.md`
- `04_Orders/ORDER_083_W_LOOP_RUNTIME_WIRING.md`
- `04_Orders/ORDER_084_NODE4_REMAND_BLOCKING.md`
- `04_Orders/ORDER_085_W_LOOP_SMOKE_AND_RUNTIME_VIEW.md`

## Implementation Step 1: Node4 Remand Blocking

Order:

- `ORDER_084_NODE4_REMAND_BLOCKING.md`

Target files to inspect first:

- `songryeon_core/runtime/user_turn.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/nodes/node_4_gatekeeper.py`
- `songryeon_core/core/schemas.py`

Coding goal:

- If node_4 gate status is `pass`, print the normal final answer.
- If node_4 gate status is `needs_revision` or `failed`, do not print node_3's rejected answer as final.
- Print a safe blocking answer instead.
- Keep the rejected answer in runtime artifacts for debugging.

Important boundary:

- Code may enforce the gate status.
- Code must not pretend to rewrite the semantic answer.
- Automatic rewrite loop is deferred.

Expected smoke:

```text
fake node_3 answer exposes internal IDs
node_4 gatekeeper -> needs_revision
final user answer -> safe blocking answer
runtime artifact -> rejected answer preserved
```

## Implementation Step 2: W1 Schema

Order:

- `ORDER_081_W1_PROBLEM_TRIAGE_SCHEMA.md`

Target file:

- `songryeon_core/core/schemas.py`

Add:

- `W1ProblemTriageFrame`
- enum validation for status/risk/route fields
- validation for `give_up_recommended`
- validation for `W_retry` usage at runtime level if schema alone cannot know retry count

Required fields:

```text
frame_id
turn_id
user_question
problem_status
blur_risk
loop_damage_risk
problem_type
solvability
give_up_recommended
give_up_reason
so_what
recommended_next_route
instruction_for_1
instruction_for_next_node
confidence
source_trace_ids
source_data_ids
schema_name
schema_version
```

Information classification:

- Code-created IDs, schema names, versions, trace IDs, data IDs are absolute information.
- W1 judgement fields are relative or mixed information when produced by LLM.
- Code fallback must use explicit `CODE_STATUS` language when LLM judgement is unavailable.

## Implementation Step 3: W1 LLM Node And Prompt

Order:

- `ORDER_082_W1_LLM_NODE_AND_PROMPT.md`

Target files to add:

- `songryeon_core/nodes/w1_problem_triage.py`
- `songryeon_core/prompts/w1_problem_triage_v0.md`

Target files to inspect:

- `songryeon_core/llm/node_executor.py`
- `songryeon_core/nodes/llm_node_1_router.py`
- `songryeon_core/nodes/l1_goal_setter.py`
- `songryeon_core/nodes/l3_result_keeper.py`

W1 must:

- call Qwen through the same LLM node executor pattern,
- output only a schema frame,
- explain `so_what` clearly,
- recommend a next route without executing it,
- recommend give-up/hold/ask when looping is wasteful.

W1 must not:

- call tools,
- search docs,
- open future R graph,
- write final user-facing answer,
- decide final route.

Fallback:

```text
problem_status: unclear
blur_risk: medium
loop_damage_risk: possible
solvability: needs_more_info
give_up_recommended: false
so_what: CODE_STATUS:w1_llm_unavailable
recommended_next_route: ask_user
```

## Implementation Step 4: Runtime Wiring

Order:

- `ORDER_083_W_LOOP_RUNTIME_WIRING.md`

Target files to inspect:

- `songryeon_core/runtime/user_turn.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/nodes/node_1_router.py`
- `songryeon_core/nodes/llm_node_1_router.py`
- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/nodes/llm_node_0_memory_supplier.py`
- `songryeon_core/loops/l_loop.py`

Target route shape:

```text
user -> 0(pre_route_report) -> 1(route=W)
1 -> 0(targeted_memory_supply_for_W)
0 -> W1(problem_triage)
W1 -> 0(loop_return_summary_for_1)
0 -> 1(route=2/L/R/ask_user/hold/stop)
```

Implementation rules:

- Add `W` as a route candidate for node_1.
- W1 recommendation is advisory.
- node_1 must write the actual post-W route.
- W must never jump directly to node_2 or node_3.
- W retry is maximum once per turn.

## Implementation Step 5: Runtime View And Smoke

Order:

- `ORDER_085_W_LOOP_SMOKE_AND_RUNTIME_VIEW.md`

Target files:

- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/runtime/smoke_test.py`
- `main.py`

Pretty runtime should show:

```text
- W1 problem triage:
  - problem_status:
  - blur_risk:
  - loop_damage_risk:
  - solvability:
  - give_up_recommended:
  - so_what:
  - recommended_next_route:
  - LLM/source:
```

Smoke cases:

- `안녕?` should not get overcomplicated.
- `R루프를 모든 비도구 대화 루프로 만들까?` should trigger structural-risk W behavior.
- `문서 메모리 인덱스가 무엇을 읽는지 알려줘` should still work through L.
- `너는 누구니?` should not pretend stable R/CoreEgo exists.
- fake W retry should stop after maximum one retry.
- fake node_4 remand should block final answer.

## Do Not Code Yet Without Checking

Before implementation, inspect current code paths for:

- where node_4 gate status is stored,
- where final answer is selected,
- whether terminal pretty view reads report text or answer text directly,
- how LLM node executor records source/adapter status,
- how route records are named in trace/data store.

## Human-Learning Notes

The key learning point for the next coding turn:

```text
Schema first does not mean code gets to make meaning.
Schema means the LLM must put its meaning into a shape that code can validate, store, route around, and display honestly.
```

For W:

```text
LLM writes the judgement.
Code validates the judgement shape.
Code enforces authority boundaries.
Node_1 owns final routing.
Node_4 owns final-answer rejection.
```
