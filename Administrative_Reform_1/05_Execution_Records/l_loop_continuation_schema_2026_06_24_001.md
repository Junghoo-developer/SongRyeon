# l loop continuation schema 2026-06-24 001

## Status

Implemented and smoke-tested.

This record covers only ORDER 089 step 1: schema preparation.

No graph rewiring was implemented in this step.

## Implemented Schemas

Added to `songryeon_core/core/schemas.py`:

- `LLoopContinuationFrame`
- `validate_l_loop_continuation_frame`
- `L2RevisionInputFrame`
- `validate_l2_revision_input_frame`

## LLoopContinuationFrame

Purpose:

```text
L3 이후 L루프 controller가 계속 검색할지, 멈출지 기록한다.
```

Important fields:

- `attempt_index`
- `max_attempts`
- `continuation_status`
- `continuation_reason_code`
- `source_l3_achievement_id`
- `source_l2_query_frame_id`
- `previous_query_text`
- `read_doc_ids`
- `unread_candidate_doc_ids`
- `tool_budget_status`
- `next_target_node`

Important rule:

```text
continuation_reason_code must start with CODE_STATUS:
```

This prevents an LLM-written natural-language reason from pretending to be a code condition.

## L2RevisionInputFrame

Purpose:

```text
L3 목표 미달 이후 L2가 재검색 계획을 세울 때 필요한 재료를 받는다.
```

Important fields:

- `attempt_index`
- `max_attempts`
- `macro_goal`
- `micro_goal`
- `previous_query_text`
- `previous_tool_name`
- `read_document_names`
- `unread_candidate_summaries`
- `l3_goal_status`
- `l3_goal_match_status`
- `l3_semantic_goal_match_status`
- `l3_feedback_text`
- `remaining_tool_calls`
- `remaining_query_attempts`
- `remaining_read_doc_calls`

Important rule:

```text
l3_feedback_text is mixed information for L2's next judgement.
The controller must not interpret this free text to decide whether to continue.
```

## Verification

Commands:

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

Additional schema-only validation created sample frames and called:

```text
validate_l2_revision_input_frame(...)
validate_l_loop_continuation_frame(...)
```

Result:

```text
SCHEMA_CONTINUATION_OK
SMOKE_TEST_OK
```

## Not Implemented Yet

- L3 이후 continuation decision
- `l3_continuation_summary_for_L2` memory packet
- L2 `revision_query_plan`
- tool re-execution loop
- runtime continuation display
- continuation smoke-test cases

