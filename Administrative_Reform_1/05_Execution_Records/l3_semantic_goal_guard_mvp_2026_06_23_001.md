# L3 Semantic Goal Guard MVP 2026-06-23 001

## Purpose

Add an L3 judgement layer that checks whether the read/search evidence fits the user's actual goal.

This MVP deliberately does not add identity presets, keyword routing rules, or document-name heuristics.

## Design Rule

Code must not decide semantic relevance by itself.

The code may:

1. pass the user query, L1 goals, search candidates, and read document previews to L3;
2. validate the L3 JSON schema;
3. record the L3 semantic judgement;
4. downgrade `achieved` when the LLM explicitly reports `semantic_goal_match_status` as `partial` or `missing`.

The code must not:

1. hardcode phrases such as identity/self-introduction queries;
2. map user intent to preferred documents with keyword presets;
3. invent semantic mismatch reasons without an LLM judgement.

## Implementation

1. Added L3 schema fields:
   - `semantic_goal_match_status`
   - `semantic_goal_match_reason`

2. Added valid semantic match statuses:
   - `matched`
   - `partial`
   - `missing`
   - `not_run`

3. Added L3 prompt rules:
   - use only supplied user query, L1 goals, candidate previews, and read document previews;
   - do not use keyword presets, identity presets, hidden project knowledge, or hardcoded routing assumptions;
   - if semantic fit is `partial` or `missing`, do not return `achievement_status: achieved`.

4. Added read document previews to L3 LLM input.

5. Added a code safety policy:
   - if L3 LLM reports `semantic_goal_match_status=partial`, downgrade `achieved` to `partial`;
   - if L3 LLM reports `semantic_goal_match_status=missing`, downgrade to `failed`;
   - mark this intervention with `+CODE:SEMANTIC_GOAL_GUARD`.

6. Added runtime output:
   - `L3 semantic goal match: ...`
   - semantic reason line

## Verification

Commands:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

Smoke result included:

- `l3_semantic_goal_match_status`: `partial`
- `l3_semantic_goal_achievement_status`: `partial`

This confirms the code did not rely on a keyword heuristic. The fake LLM supplied the semantic mismatch judgement, and code only applied the downgrade policy.

## Remaining Limit

This does not yet make L3 retry L2 or change the search query.

It only prevents an LLM semantic mismatch judgement from being reported as a full `achieved` L-loop result.
