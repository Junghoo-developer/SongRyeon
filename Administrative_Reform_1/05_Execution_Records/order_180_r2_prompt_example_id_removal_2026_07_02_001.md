# ORDER 180 Execution Record: R2 Prompt Example ID Removal

## Summary

ORDER_180을 구현했다.

ORDER_179 이후 live Qwen test에서 R2가 prompt sample에 있던 `graph:summary:source_leaf:example`을 그대로 `selected_graph_node_id`로 출력했다. 이는 runtime 후보 선택 실패라기보다 prompt example ID leakage였다.

## Changed Files

- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_180_r2_prompt_example_id_removal.py`
- `Administrative_Reform_1/04_Orders/ORDER_180_R2_PROMPT_EXAMPLE_ID_REMOVAL_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- R2 prompt에서 concrete fake graph ID가 들어간 JSON code block을 제거했다.
- R2 prompt는 이제 output key contract만 설명한다.
- R2 prompt는 `selected_graph_node_id`를 runtime candidate record의 `graph_node_id`에서 복사하라고 말한다.
- R2 prompt는 selectable ID가 runtime input payload에만 있다고 명시한다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py tests/test_order_180_r2_prompt_example_id_removal.py -q
```

결과: `16 passed in 0.23s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `124 passed in 50.91s`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- R2 validator를 약화하지 않았다.
- code semantic fallback selection을 만들지 않았다.
- R2a/R2b two-stage selector는 아직 열지 않았다.
- Neo4j data/write shape를 바꾸지 않았다.

