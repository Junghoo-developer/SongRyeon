# ORDER 191 Execution Record: R2 Source Ingest Branch Selection Stability

## Date

2026-07-03

## Scope

Implemented structural branch role labels for R2 Vessel candidate surfaces.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_191_r2_branch_role_surface_stability.py`
- `Administrative_Reform_1/04_Orders/ORDER_191_R2_SOURCE_INGEST_BRANCH_SELECTION_STABILITY_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`
- `Administrative_Reform_1/05_Execution_Records/order_191_r2_source_ingest_branch_selection_stability_2026_07_03_001.md`

## Implementation Notes

Added structural `branch_role` labels:

```text
graph_axis
source_material_ingest
source_material_leaf
summary_memory
conversation_time_memory
unknown_graph_branch
```

Branch roles are attached to:

- candidate layer surface records
- R2 visible surface records
- R2 visible candidate records

Structural surface order now keeps source-material ingest surfaces before conversation time memory surfaces. This helps R2 see the source/code/document path before plain time-bundle paths.

## Metadata Boundary

This patch is structural labeling, not semantic routing.

Code does:

- map explicit graph node kinds to structural branch roles
- expose those roles to R2
- sort surfaces by branch role

Code does not:

- decide that a branch is relevant to the user question
- force source-ingest selection
- hide TimeBundle candidates
- add keyword heuristics

R2 still chooses one official surface ref and one official node ref as an LLM judgment.

## Verification

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest -q tests/test_order_191_r2_branch_role_surface_stability.py tests/test_order_183_r_vessel_hierarchical_child_surface.py tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_187_r_vessel_summary_layer_before_raw.py tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py
python main.py fast-test --profile graph
python main.py smoke-test
git diff --check
```

Observed results:

```text
compileall: passed
focused/related R tests: 11 passed
graph fast-test: FAST_TEST_OK, 144 passed
smoke-test: SMOKE_TEST_OK
git diff --check: passed
```

Manual fake traversal with Vessel env configured:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.env.vessel.local.ps1
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode fake --format text
```

Observed path:

```text
step 1: graph:axis:time
step 2: graph:source_ingest_time_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest
step 3: graph:source_kind_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest:internal_document
step 4: graph:summary:token_budget_bundle:05689be7afe978fc:night_token_budget_layer_active_layer_03
```

This confirms the deterministic traversal can prefer the source/material branch before plain conversation time memory for the tested source-summary/token-summary question.

Live Qwen traversal was attempted with the same source-summary/token-summary style question, but the local model call did not complete inside the 180 second runtime timeout / 240 second shell window. This is recorded as a live-adapter availability/performance limit, not as a schema or validator failure.

## Remaining Risk

Branch comparison remains unimplemented. ORDER 191 improves first branch choice, but it does not yet make R traverse multiple branches before returning.
