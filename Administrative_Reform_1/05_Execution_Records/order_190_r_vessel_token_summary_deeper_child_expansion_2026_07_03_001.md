# ORDER 190 Execution Record: R Vessel Token Summary Deeper Child Expansion

## Date

2026-07-03

## Scope

Implemented lower-summary expansion for token-budget summary traversal in the R Vessel loop.

## Changed Files

- `songryeon_core/core/r_loop_vessel_read_packet.py`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/r_loop_vessel_read_packet.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py`
- `Administrative_Reform_1/04_Orders/ORDER_190_R_VESSEL_TOKEN_SUMMARY_DEEPER_CHILD_EXPANSION_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## Implementation Notes

- Added `R_LOOP_VESSEL_SUMMARY_CHILD_EXPANSION_V0`.
- R read packet now keeps:
  - `base_summary_candidate_count`
  - `summary_child_expanded_count`
  - `summary_child_expanded_node_ids`
  - `summary_child_expansion_truncated`
- Summary candidate balancing now prefers higher-level token summaries before lower source leaf summaries.
- Multi-step R traversal default budget changed:

```text
R_TRAVERSE_MAX_TRAVERSAL_DEPTH: 4 -> 6
R_TRAVERSE_MAX_NODE_READS: 4 -> 6
```

- Token-budget summary child traversal now exposes `graph:summary:*` children first.
- Token-budget summary traversal no longer falls through to unreadable token bundle IDs when no summary child record is available.
- ORDER 188 raw original cap remains unchanged:

```text
R_TRAVERSE_MAX_RAW_ORIGINAL_MATERIAL_READS = 5
```

## Metadata Boundary

This patch is code-generated absolute structure handling.

Code does:

- count and copy active summary records by source ID
- sort summary layers by explicit structural policy
- stop exposing unresolved bundle IDs as readable material

Code does not:

- decide semantic relevance of a summary child
- summarize content
- write graph nodes
- route user turns to R

R2/R3 still perform LLM selection and sufficiency judgment.

## Verification

Passed:

```text
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py
python -m pytest -q tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_186_r_vessel_exact_child_expansion.py tests/test_order_187_r_vessel_summary_layer_before_raw.py tests/test_order_188_r_vessel_raw_original_cap.py
python main.py fast-test --profile graph
python main.py smoke-test
git diff --check
```

Observed:

```text
ORDER 190 focused tests: 2 passed
ORDER 175/184-188 related tests: 15 passed
graph fast-test: FAST_TEST_OK, 142 passed
smoke-test: SMOKE_TEST_OK
diff check: clean
```

## Live Vessel Checks

### Read Packet

```text
python main.py vessel-r-read-packet --database neo4j --limit 50 --format text
```

Observed:

```text
status=R_LOOP_VESSEL_READ_PACKET_OK
entry_candidate_count=100
base_entry_candidate_count=50
exact_child_expanded_entry_count=50
exact_child_expansion_truncated=True
summary_candidate_count=100
base_summary_candidate_count=50
summary_child_expanded_count=50
summary_child_expansion_truncated=True
total_summary_scanned_count=598
summary_count_by_data_kind={'source_leaf_summary': 68, 'token_budget_bundle_summary': 32}
summary_count_by_depth={'1': 68, '2': 26, '3': 6}
```

Interpretation:

- Summary-child expansion is active in the live Neo4j read packet.
- The packet now carries additional lower summary records needed for deeper traversal.

### Qwen Normal Traversal

```text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Observed:

```text
status=R_LOOP_VESSEL_TRAVERSE_OK
step_count=4
final_graph_node_id=graph:summary:token_budget_bundle:08a835f99e68e01e:night_token_budget_layer_active
final_sufficiency_status=sufficient
final_continuation_status=stop_sufficient
r_loop_task_status=sufficient
raw_original_material_seen_count=0
raw_original_read_cap_reached=False
```

Interpretation:

- The previous ORDER 189 partial/budget-exhausted behavior did not repeat for this normal traversal.
- Qwen accepted the token summary as sufficient and stopped honestly.

### Qwen Forced-Deeper Probe

```text
python main.py vessel-r-traverse "송련 Core 그래프에서 token summary가 충분해 보여도 그 아래 lower summary child가 실제로 있는지 한 단계 더 내려가서 확인해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Observed:

```text
status=R_LOOP_VESSEL_TRAVERSE_OK
step_count=2
final_graph_node_id=graph:time_bundle:night_changed_sources_2026_07_02T14_02_36_242082:core
final_sufficiency_status=insufficient
final_continuation_status=stop_no_actionable_path
r_loop_task_status=partial
raw_original_material_seen_count=0
raw_original_read_cap_reached=False
```

Interpretation:

- Qwen chose the time-bundle branch instead of the source-ingest/source-kind branch.
- This is not a raw-original overread problem.
- This identifies the next bottleneck: branch choice stability when the user asks for a specific graph path.

## Remaining Risk

Branch comparison is still not implemented. If the user asks for code-vs-document comparison, R can descend one branch more safely, but it still does not yet guarantee multi-branch traversal before returning.

## Recommended Next MVP

```text
ORDER_191_R2_SOURCE_INGEST_BRANCH_SELECTION_STABILITY_V0
```

Goal:

- When the user asks about source summaries, token summaries, source kinds, or code/document separation, the R2 selection surface should keep source-ingest/source-kind branches distinguishable from old conversation time bundles.
- Do not use keyword heuristics.
- Prefer a structural surface policy: source-ingest/source-kind branch surfaces should be explicit and selectable as graph branches, while plain conversation `TimeBundle` should not accidentally intercept source-ingest questions.
