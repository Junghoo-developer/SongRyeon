# ORDER 192: R1 User Question Anchor Copy v0

## Status

Prepared on 2026-07-03 as the next R traversal stability order.

Implementation should proceed after confirming the live test failure pattern remains:

```text
failure_stage: R1
failure_type: schema_failed
failure_reason: R1 graph_search_goal must preserve a user question anchor
```

## Trigger

After ORDER 191, R2 branch signage became more stable, but a live Vessel R traversal failed before R2:

```text
status: R_LOOP_VESSEL_TRAVERSE_NOT_PASSED
failure_stage: R1
failure_type: schema_failed
failure_reason: R1 graph_search_goal must preserve a user question anchor
```

This means the graph traversal did not fail because R2 chose the wrong branch. It failed because R1's generated goal did not satisfy the current user-question-anchor validator.

## Problem

The current R1 validator asks whether `graph_search_goal` preserves a user-question anchor.

That guard is valuable because R1 must not drift away from the user's request. However, the current implementation can fail on Korean questions because the validator extracts simple normalized anchor tokens from the user question and then checks whether the generated English/Korean goal contains one of those tokens.

This creates a fragile boundary:

- The user question may be Korean.
- R1 may paraphrase the goal naturally in Korean.
- The validator may expect an English/ASCII token such as `source` or `token`.
- R1 can be semantically aligned but still fail schema validation.

## Goal

Replace fragile goal-text anchor matching with explicit code-supplied anchor copying.

R1 should receive an official user-question anchor from code and copy it into its output frame. The validator should then check the copied anchor exactly.

This keeps the anti-drift guard while avoiding Korean/English token mismatch.

## Implementation Requirements

1. Add a code-generated user question anchor to the R1 input payload.

Suggested payload fields:

```json
{
  "user_question_anchor": {
    "anchor_id": "r1_user_question_anchor:<short_hash>",
    "source_field": "user_question",
    "copy_required": true
  }
}
```

2. Extend the R1 output contract.

Suggested output field:

```json
{
  "user_question_anchor_id": "r1_user_question_anchor:<short_hash>"
}
```

3. Update `R1GraphGoalFrame` if needed.

The frame should preserve the copied anchor as absolute linkage:

```text
user_question_anchor_id
```

This field is not a semantic judgment. It is a code-supplied ID copied by the LLM and validated by code.

4. Update R1 prompt.

R1 must be told:

- Copy `user_question_anchor.anchor_id` exactly into `user_question_anchor_id`.
- Do not translate it.
- Do not invent it.
- Keep `graph_search_goal` human-readable.
- The goal may be Korean.

5. Update R1 validator.

Preferred rule:

```text
payload.user_question_anchor_id == input.user_question_anchor.anchor_id
```

The existing `_shares_user_question_anchor(...)` text-token guard should be removed from the R1 live path or demoted to a legacy/internal helper only if tests still need it.

6. Preserve metadata boundary.

Code may:

- generate the anchor ID from the user question
- require exact anchor copy
- record validation failure if the anchor is missing or wrong

Code must not:

- judge semantic relevance of the R1 goal
- parse Korean meaning with keyword heuristics
- silently rewrite R1's goal
- create a code fallback graph goal pretending to be LLM judgment

## Non-Goals

- Do not change R2 selection policy.
- Do not change R3 sufficiency policy.
- Do not add keyword heuristics.
- Do not connect R traversal to normal qwen-chat route.
- Do not write new graph memory nodes.
- Do not increase raw original read cap.
- Do not change Vessel read packet candidate budgets.

## Test Plan

Run:

```powershell
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_192_r1_user_question_anchor_copy.py
python main.py fast-test --profile graph
```

Add tests:

1. R1 input payload includes `user_question_anchor.anchor_id`.
2. R1 output with matching `user_question_anchor_id` passes even when `graph_search_goal` is Korean and does not copy English/ASCII words from the user question.
3. R1 output with missing anchor fails schema validation.
4. R1 output with invented/wrong anchor fails schema validation.
5. Existing ORDER 177 R1 candidate text blindness remains true.
6. Existing ORDER 191 R2 branch role tests remain true.

Manual live test after implementation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.env.vessel.local.ps1
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘. 과거 대화 기억 가지가 아니라 코드/문서 소스 가지를 우선 보고, 시간축에서 시작해서 어떤 묶음을 거쳐 내려가는지 말해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

Expected:

- The run should no longer fail at `failure_stage=R1` due to anchor preservation.
- If it fails later, the later failure should be recorded separately.

## Expected Result

R1 keeps a hard source link to the user's question without depending on fragile Korean/English token matching.

In elementary terms:

```text
Before:
R1 had to repeat a magic word from the user's sentence.

After:
Code gives R1 a numbered ticket.
R1 copies the ticket.
Code checks the ticket.
```

