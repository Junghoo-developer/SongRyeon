# ORDER 189 Execution Record: R Traverse Live Audit

## Date

2026-07-03

## Scope

Created the ORDER 189 audit order and prepared live/manual R Vessel traversal checks.

## Changed Files

- `Administrative_Reform_1/04_Orders/ORDER_189_R_TRAVERSE_LIVE_AUDIT_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`
- `Administrative_Reform_1/05_Execution_Records/order_189_r_traverse_live_audit_2026_07_03_001.md`

## Audit Intent

This audit checks whether R Vessel traversal is ready for the next integration step.

The audit focuses on:

- CoreEgo/time-axis start
- hierarchical descent
- summary-before-raw behavior
- raw original cap visibility
- partial/failure stop honesty
- whether the next MVP should be integration, prompt repair, or traversal structure repair

## Verification Log

### Baseline

```text
python -m compileall songryeon_core main.py
```

Result:

```text
passed
```

### Vessel Readback

```text
python main.py vessel-readback --database neo4j
```

Result:

```text
status=VESSEL_READBACK_OK
readback_status=passed
vessel_record_count=4611
vessel_relationship_count=1747
core_ego_count=1
time_axis_count=1
time_bundle_count=2
raw_capsule_count=2
```

### Fake Traversal: Structure Walk

```text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조를 CoreEgo에서 시작해서 한 단계씩 내려가며 설명 가능한 만큼만 탐색해줘" --database neo4j --llm-mode fake --format text
```

Result:

```text
status=R_LOOP_VESSEL_TRAVERSE_OK
step_count=4
final_graph_node_id=graph:summary:token_budget_bundle:08a835f99e68e01e:night_token_budget_layer_active
final_sufficiency_status=sufficient
final_continuation_status=stop_sufficient
r_loop_task_status=sufficient
terminal_material_seen_count=1
raw_original_material_seen_count=0
max_raw_original_material_count=5
raw_original_read_cap_reached=False
```

Observed path:

```text
graph:axis:time
-> graph:source_ingest_time_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest
-> graph:source_kind_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest:internal_document
-> graph:summary:token_budget_bundle:08a835f99e68e01e:night_token_budget_layer_active
```

Interpretation:

- CoreEgo/time-axis start path is working.
- Summary-before-raw is working.
- Fake adapter stops after one terminal summary.
- Raw originals were not opened.

### Qwen Traversal: Summary Layer Link

```text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Result:

```text
status=R_LOOP_VESSEL_TRAVERSE_OK
step_count=4
final_graph_node_id=graph:summary:token_budget_bundle:08a835f99e68e01e:night_token_budget_layer_active
final_sufficiency_status=insufficient
final_continuation_status=stop_budget_exhausted
r_loop_task_status=partial
terminal_material_seen_count=1
raw_original_material_seen_count=0
max_raw_original_material_count=5
raw_original_read_cap_reached=False
```

Observed:

- Qwen descended through the same high-level hierarchy.
- Qwen wanted to continue beyond the token-budget summary.
- Traversal stopped because the current traversal budget ended, not because raw cap was reached.
- Raw originals were not opened.

### Qwen Traversal: Code/Document Separation

```text
python main.py vessel-r-traverse "송련 Core 그래프 기억에서 코드 파일과 내부 문서가 서로 어떻게 분리되어 저장됐는지 계층적으로 확인해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Result:

```text
status=R_LOOP_VESSEL_TRAVERSE_OK
step_count=4
final_graph_node_id=graph:summary:token_budget_bundle:a5f9e552fe7ff1cf:night_token_budget_layer_active_layer_03
final_sufficiency_status=insufficient
final_continuation_status=stop_budget_exhausted
r_loop_task_status=partial
terminal_material_seen_count=1
raw_original_material_seen_count=0
max_raw_original_material_count=5
raw_original_read_cap_reached=False
```

Observed:

- Qwen again followed the hierarchy instead of seeing every leaf summary at once.
- Qwen selected `internal_document` source kind in this run.
- Qwen did not yet inspect both code and internal-document branches in one traversal.
- The bottleneck is traversal budget/deeper branch handling, not raw-original overread.

## Audit Conclusion

Current R traversal is healthy enough to keep developing, but not ready to be wired into normal user-facing answers yet.

What works:

- Neo4j Vessel readback passes.
- CoreEgo/time-axis entry path exists.
- R traversal starts high and descends.
- Summary-before-raw behavior is visible.
- Raw original read count stays at 0 in these tests.
- Raw original cap is visible in runtime output.

Current bottleneck:

- Qwen reaches a token-budget summary and often wants to continue deeper.
- The traversal currently stops partial when traversal budget ends.
- For questions that require comparing branches, R traversal needs a structured next step before node_3 integration.

## Recommended Next MVP

Do not connect R traversal to node_3 yet.

Recommended next order:

```text
ORDER_190_R_TRAVERSE_DEEPER_FROM_TOKEN_SUMMARY_OR_BRANCH_COMPARE_V0
```

Goal:

- When R3 says a token-budget summary is insufficient and wants `deeper`, expose the exact children under that summary or the appropriate lower summary/leaf layer.
- For branch comparison questions, preserve enough information for R2 to switch from one source-kind branch to another without pretending one branch answered the whole question.

## Initial Expected Next MVP

If live traversal passes at least fake traversal and one Qwen traversal, the next likely MVP is:

```text
R traversal result -> node_3 brief material packet
```

If live traversal fails because R2/R3 cannot choose valid child nodes, the next MVP should stay inside R traversal and repair the candidate surface before any node_3 integration.
