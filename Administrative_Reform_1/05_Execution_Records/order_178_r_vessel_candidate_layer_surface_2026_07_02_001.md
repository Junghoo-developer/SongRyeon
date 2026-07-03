# ORDER 178 Execution Record: R Vessel Candidate Layer Surface

## Summary

ORDER_178을 구현했다.

R1 후보 텍스트 차단 이후에도 R2가 flat 50개 후보판을 직접 받아 첫 후보에 끌리는 문제가 남아 있었다. 이번 패치는 R2 앞에 code-generated absolute candidate layer surface를 추가해, R2가 먼저 surface/table-of-contents shelf를 고른 뒤 그 안의 graph node를 고르게 했다.

## Changed Files

- `songryeon_core/core/r_loop_vessel_read_packet.py`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_176_vessel_r_one_step_traversal.py`
- `tests/test_order_177_r1_candidate_text_blindness.py`
- `tests/test_order_178_r_vessel_candidate_layer_surface.py`
- `Administrative_Reform_1/04_Orders/ORDER_178_R_VESSEL_CANDIDATE_LAYER_SURFACE_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- `RLoopVesselCandidateLayerSurfaceFrame`을 추가했다.
  - generated_by: `CODE:R_LOOP_VESSEL_CANDIDATE_LAYER_SURFACE_BUILDER`
  - info_class: `absolute`
  - semantic_judgement_status: `not_run`
- surface frame은 다음 absolute fields만 기준으로 후보를 묶는다.
  - entry candidate kind
  - summary data kind
  - summary depth
  - info class
- surface frame 자체에는 `summary_text`를 넣지 않는다.
- R2 input은 flat `summary_candidate_records`/`entry_candidate_records` 대신:
  - `candidate_layer_surface_frame`
  - `available_surface_ids`
  - `candidate_records_by_surface`
  를 받는다.
- R2 output은 이제 `selected_surface_id`와 `selected_graph_node_id`를 함께 내야 한다.
- code validator는 `selected_graph_node_id`가 selected surface 안에 없으면 schema failure로 닫는다.
- Vessel read packet은 active summaries를 flat first-N으로 자르지 않고, data-kind/depth/info-class group을 round-robin으로 담는다.

## Metadata Boundary

Code는 surface grouping과 ID membership만 확정한다. 어떤 surface 또는 candidate가 질문에 의미상 맞는지는 R2 LLM 판단으로 남겼다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py tests/test_order_178_r_vessel_candidate_layer_surface.py -q
```

결과: `19 passed in 0.24s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `121 passed in 68.27s`

```powershell
python main.py smoke-test
```

결과: `SMOKE_TEST_OK`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- R route를 기본 live route로 열지 않았다.
- multi-step R traversal을 열지 않았다.
- code가 semantic surface relevance를 판단하지 않았다.
- Neo4j schema/write shape를 바꾸지 않았다.
- night summary 생성/무효화 로직을 건드리지 않았다.

