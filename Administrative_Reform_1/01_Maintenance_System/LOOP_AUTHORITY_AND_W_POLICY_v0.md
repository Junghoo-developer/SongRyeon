# Loop Authority And W Policy v0

## Status

This document is a maintenance-system rule.

It records the current owner view before W-loop implementation. Future loop, node, prompt, schema, and runtime work should follow this policy unless a newer maintenance-system document replaces it.

## Owner Thesis

W-loop should not exist because the agent wants more thinking for every turn.

W-loop exists because some turns are dangerous to blur.

A turn is dangerous to blur when a vague answer would damage later L/R/2/3 operation, pollute loop authority definitions, or make future document/search behavior harder to recover.

If there is no such danger, the system should not overthink. It should route through the simplest safe path.

## Loop Roles

### 0: Memory Supplier

0 supplies bounded memory and trace context.

0 may:

- compress current turn trace for the next target,
- provide recent context and source references,
- report missing context,
- build condition-specific packets for a selected target.

0 must not:

- decide final routing,
- call tools,
- judge source truth,
- write final answers,
- silently turn code status into semantic judgement.

### 1: Router And Decision Owner

1 owns current-turn routing.

1 may:

- choose `2`, `L`, future `W`, future `R`, ask-user, or rescue-like paths,
- read reports from 0 and loops,
- decide whether route=2 is ready.

1 must not:

- write final user-facing answers,
- pretend a loop recommendation is final authority,
- send uncertain structural turns directly to final speech without a reason.

### L: Document And Evidence Loop

L is the internal document and evidence loop.

L may:

- set lookup goals,
- plan document search,
- call allowed document tools through the tool layer,
- preserve search/read results,
- report evidence status to 1.

L must not:

- write final answers,
- own identity/CoreEgo truth by default,
- decide final routing after its report,
- treat a search hit as truth.

### W: Problem Triage Loop

W is a problem triage and loop-economy loop.

W is used when 1 finds the turn too ambiguous for direct route=2, but the need for L or R is not yet clear.

W answers the operational question:

```text
Is this turn safe to blur, or would blurring it damage later loop operation?
If there is a problem, can the current structure solve it, or is stop/ask/hold better?
So what should 1 do next?
```

W may:

- judge problem/no-problem/unclear for the current turn,
- estimate blur risk and loop damage risk,
- estimate whether the current structure can solve the problem,
- recommend a next route to 1,
- recommend give-up, ask-user, or hold-for-definition when further looping is wasteful.

W must not:

- call tools,
- search documents,
- read graph DB,
- decide final routing,
- write final answers,
- assert factual truth,
- replace 1's judgement,
- loop indefinitely.

### R: Identity And CoreEgo Candidate Loop

R is not ready for MVP implementation.

Current owner view:

- R should not be a generic non-tool conversation loop.
- Simple non-tool conversation should usually go `1 -> 2 -> 3`.
- R is a future candidate for identity, self-description, CoreEgo, and night-government knowledge graph reading.

Until R is implemented, identity questions may be handled by L or safe uncertainty, but the system must not pretend it has a stable CoreEgo graph path.

### 2: Boundary And Brief Builder

2 prepares reportable material before final speech.

2 may:

- separate internal ledger from user-facing brief,
- build node_3 input brief,
- preserve provenance internally,
- mark insufficiency.

2 must not:

- make unsupported semantic truth claims,
- expose internal IDs to node_3,
- replace 3's final expression,
- bypass node_4 when node_4 is enabled.

### 3: Final Speaker

3 renders final user-facing text from an allowed brief or contract.

3 may:

- phrase the answer naturally,
- choose concise structure,
- explain uncertainty within the allowed material.

3 must not:

- call tools,
- create new facts,
- expose internal node names, IDs, schemas, or workflow labels unless the user is in an explicit developer/runtime explanation mode and the brief allows it,
- claim memory/search/tool access happened unless the brief says so.

### 4: Gatekeeper

4 checks the final answer against what 3 actually received.

4 may:

- mark pass,
- mark needs_revision,
- list unsupported claims,
- list contradictions,
- recommend remand.

4 must not:

- write the replacement answer as if it were 3,
- call tools,
- expand evidence beyond the brief,
- silently allow a needs_revision answer to be treated as final success.

## W1 Required Fields

W1 should produce a structured frame with at least these fields:

```text
problem_status:
  no_problem | problem_detected | unclear

blur_risk:
  low | medium | high

loop_damage_risk:
  none | possible | high

solvability:
  solvable_with_current_structure
  needs_more_info
  needs_new_loop_or_tool
  not_worth_solving_now
  unsolvable_in_current_turn

give_up_recommended:
  true | false

give_up_reason:
  short reason when give_up_recommended is true

so_what:
  one sentence explaining what 1 should do with this diagnosis

recommended_next_route:
  2 | L | R | ask_user | hold_for_definition | stop_safe_failure | W_retry

instruction_for_1:
  compact instruction for the routing owner

instruction_for_next_node:
  compact instruction for the recommended next node, if any
```

## W1 Routing Meaning

`recommended_next_route` is advisory, not binding.

1 remains the final routing authority.

Recommended route meanings:

- `2`: no meaningful problem; direct final-report path is safe.
- `L`: the problem can be solved by internal document/evidence lookup.
- `R`: the problem appears to require future identity/CoreEgo graph lookup. If R is not implemented, 1 should usually hold or answer with uncertainty.
- `ask_user`: one clarifying question is cheaper and safer than another loop.
- `hold_for_definition`: preserve as design material; do not code yet.
- `stop_safe_failure`: current turn should end with a safe limitation/failure answer.
- `W_retry`: only allowed once when W lacked enough trace context and 0 can supply more context without new tools.

## Give-Up Rule

Give-up is not failure.

Give-up is correct when:

- current structure cannot solve the problem,
- additional loops would likely repeat the same uncertainty,
- the missing capability is a future loop/tool,
- the turn is not worth expanding,
- a safe limitation answer is more honest than pretend progress.

When W1 recommends give-up, it must include `give_up_reason` and a non-looping next action.

## Loop Economy Rule

W must reduce pointless loops.

W is failing if it increases loops without improving route clarity.

Default W retry limit:

```text
max_w_retries_per_turn: 1
```

If W returns `unclear` twice in the same turn, 1 should not call W again. It should choose `ask_user`, `hold_for_definition`, or `stop_safe_failure`.

## Coding Implication

Before W is implemented, any W-related code must preserve these boundaries:

- W reports to 1.
- W does not route by itself.
- W does not call tools.
- W does not create final answer text.
- W output is mixed information when produced by LLM.
- W status fields are schema-controlled labels.
