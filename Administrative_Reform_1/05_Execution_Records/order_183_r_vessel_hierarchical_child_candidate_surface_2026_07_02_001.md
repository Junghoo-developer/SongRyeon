# ORDER 183 Execution Record: R Vessel Hierarchical Child Candidate Surface

## Summary

ORDER_183을 구현했다.

ORDER_182로 R2 첫 화면은 CoreEgo entry layer만 보게 되었지만, 선택한 노드 아래의 다음 계층 후보를 구조화해서 남기는 장부가 Vessel one-step에는 없었다. 이번 패치는 선택된 Vessel graph node의 direct child candidates를 code가 복사하고, 기존 R loop schema인 `RGraphTraversalCandidateSurfaceFrame`으로 기록하게 만든다.

## Changed Files

- `songryeon_core/core/r_loop_vessel_read_packet.py`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r3_vessel_inspector_v0.md`
- `songryeon_core/runtime/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_183_r_vessel_hierarchical_child_surface.py`
- `Administrative_Reform_1/04_Orders/ORDER_183_R_VESSEL_HIERARCHICAL_CHILD_CANDIDATE_SURFACE_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- R Vessel read packet entry candidates now preserve:
  - `source_graph_node_ids`
  - `parent_graph_node_ids`
- Neo4j read query can include:
  - `TimeAxis`
  - `TimeBundle`
  - `SourceIngestBundle`
  - `SourceKindBundle`
  - `RawSource`
  - `token_budget_summary_bundle`
- When R2 selects a node, code derives `hierarchy_child_node_ids` and `hierarchy_child_candidate_records`.
- R3 input now includes:
  - `hierarchy_child_candidate_records`
  - `hierarchy_child_candidate_count`
  - `hierarchy_read_policy`
- After R3, code records `RGraphTraversalCandidateSurfaceFrame` with child candidate IDs.
- Runtime text output shows `hierarchy_child_candidate_count` and up to 20 child node IDs.

## Metadata Boundary

The hierarchy child candidate surface is absolute information. Code copies graph IDs and relationships from read packet records and graph payloads. It does not choose which child is semantically best.

R3 may judge whether the selected node is sufficient or whether deeper traversal is needed. That remains LLM-generated mixed information.

## Verification

```powershell
python -m pytest tests/test_order_183_r_vessel_hierarchical_child_surface.py -q
```

결과: `3 passed in 0.13s`

```powershell
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py tests/test_order_180_r2_prompt_example_id_removal.py tests/test_order_181_r2_official_selection_ref_map.py tests/test_order_182_r_core_ego_start_surface.py tests/test_order_183_r_vessel_hierarchical_child_surface.py -q
```

결과: `29 passed in 0.36s`

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `131 passed in 54.65s`

## Non-goals Preserved

- Full automatic multi-step R traversal은 열지 않았다.
- R2a/R2b 또는 A/B 선택 구조는 만들지 않았다.
- Code가 semantic child choice를 대신하지 않았다.
- R2 official ref validation은 약화하지 않았다.
- node_3 최종 답변 연결은 열지 않았다.
