# ORDER 179 Execution Record: R2 Vessel Selection ID Disambiguation

## Summary

ORDER_179를 구현했다.

ORDER_178 live Qwen test에서 R2가 schema failure로 닫혔다. 실패 원인은 `selected_graph_node_id`가 `available_graph_node_ids` 안에 없다는 것이었다. 이는 R2가 선택해야 하는 summary/entry candidate ID와 설명용 target/source ID를 혼동했을 가능성이 높다.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_179_r2_vessel_selection_id_disambiguation.py`
- `Administrative_Reform_1/04_Orders/ORDER_179_R2_VESSEL_SELECTION_ID_DISAMBIGUATION_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- R2 candidate records now expose `graph_node_id` as the direct selectable ID.
- R2 candidate records no longer expose:
  - `target_graph_node_id`
  - `source_graph_node_ids`
  - `summary_node_id`
  - `candidate_node_id`
- R2 prompt now says to copy `selected_graph_node_id` from candidate record `graph_node_id`.
- R2 prompt now explicitly says not to use target/source/data IDs as selected graph node IDs.
- Failed R2 schema validation now stores and renders `failure_payload_summary`:
  - selected surface ID
  - selected graph node ID
  - whether selected surface ID was allowed
  - whether selected graph node ID was globally allowed
  - whether selected graph node ID belonged to the selected surface

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py -q
```

결과: `15 passed in 0.22s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `123 passed in 62.29s`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- R2 validator를 약화하지 않았다.
- invalid selected graph node ID를 허용하지 않았다.
- code가 semantic fallback candidate를 고르지 않았다.
- R2a/R2b two-stage selector는 아직 열지 않았다.
- multi-step R traversal은 열지 않았다.

