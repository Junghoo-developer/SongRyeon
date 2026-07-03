# ORDER 181 Execution Record: R2 Official Selection Ref Map

## Summary

ORDER_181을 구현했다.

ORDER_180 이후 live Qwen test에서 R2가 긴 runtime ID 대신 `surface_003`, `node_073` 같은 짧은 label을 임의 생성했다. 이는 LLM이 긴 graph ID를 직접 복사하는 구조가 취약하다는 신호였다.

이번 패치는 code가 공식 선택 ref를 제공하고, R2는 ref만 선택하게 만들었다.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_176_vessel_r_one_step_traversal.py`
- `tests/test_order_177_r1_candidate_text_blindness.py`
- `tests/test_order_178_r_vessel_candidate_layer_surface.py`
- `tests/test_order_179_r2_vessel_selection_id_disambiguation.py`
- `tests/test_order_180_r2_prompt_example_id_removal.py`
- `tests/test_order_181_r2_official_selection_ref_map.py`
- `Administrative_Reform_1/04_Orders/ORDER_181_R2_OFFICIAL_SELECTION_REF_MAP_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- R2 input now exposes official short refs:
  - `available_surface_refs`
  - `candidate_layer_surface_ref_records`
  - `candidate_records_by_surface_ref`
- R2 output now uses:
  - `selected_surface_ref`
  - `selected_node_ref`
- Actual graph IDs are hidden from R2 candidate records.
- Code maps official refs back to actual `surface_id` and `graph_node_id`.
- Existing R2/R3 frames still store actual graph IDs after validation.
- Arbitrary invented refs still fail validation.

## Metadata Boundary

The ref map is code-generated absolute information. It does not rank surfaces or candidates semantically. R2 still makes the semantic selection; code only validates official ref membership and translates refs to actual IDs.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py tests/test_order_180_r2_prompt_example_id_removal.py tests/test_order_181_r2_official_selection_ref_map.py -q
```

결과: `18 passed in 0.32s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `126 passed in 50.51s`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- Arbitrary `surface_003`/`node_073` style invented refs are not accepted unless code supplied them.
- R2 validator was not weakened.
- Code does not choose a semantic fallback.
- R2a/R2b and multi-step R traversal remain unopened.
- Neo4j data/write shape was not changed.

