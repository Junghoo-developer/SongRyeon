# ORDER 182 Execution Record: R CoreEgo Start Selection Surface

## Summary

ORDER_182를 구현했다.

ORDER_181로 R2의 공식 ref 선택 문제는 해결됐지만, live R one-step에서 R2가 여전히 첫 단계부터 source leaf summary와 token layer summary 후보를 넓게 보고 있었다. 이는 사용자가 의도한 `CoreEgo -> Time Axis -> Bundle -> Leaf/Summary` 하향 탐색과 맞지 않았다.

이번 패치는 첫 R2 선택 화면을 CoreEgo 시작 entry 후보로 제한했다.

## Changed Files

- `songryeon_core/core/r_loop_vessel_read_packet.py`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_176_vessel_r_one_step_traversal.py`
- `tests/test_order_177_r1_candidate_text_blindness.py`
- `tests/test_order_178_r_vessel_candidate_layer_surface.py`
- `tests/test_order_179_r2_vessel_selection_id_disambiguation.py`
- `tests/test_order_181_r2_official_selection_ref_map.py`
- `tests/test_order_182_r_core_ego_start_surface.py`
- `Administrative_Reform_1/04_Orders/ORDER_182_R_CORE_EGO_START_SELECTION_SURFACE_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- R read packet now recognizes `TimeAxis` entry rows as `candidate_kind=time_axis`.
- Neo4j entry read query includes the `TimeAxis` row before TimeBundle/SourceIngestBundle rows.
- First R2 candidate surface now uses CoreEgo-start entry candidates only.
- If a TimeAxis candidate exists, the first R2 surface exposes TimeAxis only.
- If no TimeAxis candidate exists, first R2 surface falls back to existing entry bundle candidates.
- Summary candidates remain in the read packet, but first R2 payload does not expose `summary_text`, `summary_node_id`, `source_leaf_summary`, or `token_budget_bundle_summary`.
- R2 still selects official refs only; code maps refs to graph IDs after validation.

## Metadata Boundary

The first-step surface is code-generated absolute information. It does not decide which graph branch is semantically best. R2 still performs semantic selection over visible official refs.

## Verification

```powershell
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py tests/test_order_179_r2_vessel_selection_id_disambiguation.py tests/test_order_180_r2_prompt_example_id_removal.py tests/test_order_181_r2_official_selection_ref_map.py tests/test_order_182_r_core_ego_start_surface.py -q
```

결과: `26 passed in 0.35s`

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `128 passed in 60.09s`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- R2a/R2b 또는 A/B 선택 구조를 만들지 않았다.
- full multi-step R traversal은 열지 않았다.
- summary 후보를 read packet에서 삭제하지 않았다.
- R2 validator를 약화하지 않았다.
- node_1 routing, node_3 answer, W/R scheduler, 외부 DB write schema는 바꾸지 않았다.
