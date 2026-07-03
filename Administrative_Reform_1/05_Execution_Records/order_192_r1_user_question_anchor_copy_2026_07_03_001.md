# ORDER 192 Execution Record: R1 User Question Anchor Copy

## Date

2026-07-03

## Scope

Implemented explicit code-supplied user question anchor copying for R1 Vessel traversal.

## Trigger

Before this patch, a Korean live R traversal failed at R1:

```text
status: R_LOOP_VESSEL_TRAVERSE_NOT_PASSED
failure_stage: R1
failure_type: schema_failed
failure_reason: R1 graph_search_goal must preserve a user question anchor
```

A manual pre-patch test with an explicit `anchor_source_token_path` string succeeded, proving that R1/R2/R3 traversal could work when the anchor guard was satisfied. The fragile part was the text-token anchor check, not the graph traversal path itself.

## Changed Files

- `songryeon_core/core/schema_parts/r_loop.py`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r1_vessel_goal_setter_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_176_vessel_r_one_step_traversal.py`
- `tests/test_order_177_r1_candidate_text_blindness.py`
- `tests/test_order_178_r_vessel_candidate_layer_surface.py`
- `tests/test_order_179_r2_vessel_selection_id_disambiguation.py`
- `tests/test_order_181_r2_official_selection_ref_map.py`
- `tests/test_order_182_r_core_ego_start_surface.py`
- `tests/test_order_183_r_vessel_hierarchical_child_surface.py`
- `tests/test_order_185_r_terminal_material_guard.py`
- `tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py`
- `tests/test_order_191_r2_branch_role_surface_stability.py`
- `tests/test_order_192_r1_user_question_anchor_copy.py`
- `Administrative_Reform_1/04_Orders/ORDER_192_R1_USER_QUESTION_ANCHOR_COPY_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`
- `Administrative_Reform_1/05_Execution_Records/order_192_r1_user_question_anchor_copy_2026_07_03_001.md`

## Implementation Notes

R1 input payload now includes:

```json
{
  "user_question_anchor": {
    "anchor_id": "r1_user_question_anchor:<sha256-prefix>",
    "source_field": "user_question",
    "copy_required": true
  }
}
```

R1 output now includes:

```json
{
  "user_question_anchor_id": "r1_user_question_anchor:<sha256-prefix>"
}
```

`R1GraphGoalFrame` preserves `user_question_anchor_id`.

R1 validation now checks exact copied anchor identity:

```text
payload.user_question_anchor_id == expected user question anchor
```

The previous live R1 text-token guard `_shares_user_question_anchor(...)` is no longer used for R1 payload validation.

## Metadata Boundary

Code does:

- generate a deterministic anchor ID from the user question
- give that anchor ID to R1
- require R1 to copy the anchor ID exactly
- reject missing or invented anchor IDs

Code does not:

- judge whether R1's graph goal is semantically correct
- parse Korean meaning with keyword heuristics
- rewrite R1's graph goal
- create a code fallback goal pretending to be R1's judgment

The copied anchor is absolute linkage. R1's graph goal remains LLM-generated mixed/semantic material.

## Verification

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_192_r1_user_question_anchor_copy.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_191_r2_branch_role_surface_stability.py
python -m pytest -q tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py tests/test_order_181_r2_official_selection_ref_map.py tests/test_order_182_r_core_ego_start_surface.py tests/test_order_183_r_vessel_hierarchical_child_surface.py tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_187_r_vessel_summary_layer_before_raw.py tests/test_order_188_r_vessel_raw_original_cap.py tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py tests/test_order_191_r2_branch_role_surface_stability.py tests/test_order_192_r1_user_question_anchor_copy.py
python main.py fast-test --profile graph
python -m pytest
python main.py smoke-test
git diff --check
```

Observed results:

```text
compileall: passed
focused ORDER 192 / related tests: 9 passed
R traversal related tests: 37 passed
graph fast-test: FAST_TEST_OK, 148 passed
full pytest: 279 passed
smoke-test: SMOKE_TEST_OK
git diff --check: passed
```

Live Qwen Vessel traversal after implementation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.env.vessel.local.ps1
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘. 과거 대화 기억 가지가 아니라 코드/문서 소스 가지를 우선 보고, 시간축에서 시작해서 어떤 묶음을 거쳐 내려가는지 말해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

Observed:

```text
status: R_LOOP_VESSEL_TRAVERSE_OK
traverse_status: completed
step_count: 4
final_sufficiency_status: sufficient
r_loop_task_status: sufficient

step 1: graph:axis:time
step 2: graph:source_ingest_time_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest
step 3: graph:source_kind_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest:internal_document
step 4: graph:summary:token_budget_bundle:08a835f99e68e01e:night_token_budget_layer_active
```

This confirms that the same Korean live test no longer fails at R1 due to the anchor guard.

## Remaining Risk

R1 anchor copy only proves source linkage. It does not prove that R1's natural-language goal is semantically ideal.

R traversal can now reach token-budget summary material more reliably, but the next quality bottleneck is still how R3 decides whether a summary is sufficient or whether it should descend further.
