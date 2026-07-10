# order_215_r_traverse_path_duplicate_preservation_2026_07_08_001

## 작업 범위

ORDER_215 R Traverse Path Duplicate Preservation을 구현한다.

## 구현 내용

- R traversal path field에서는 중복 graph node id를 제거하지 않는다.
- provenance/source id field에서는 기존 중복 제거를 유지한다.
- 같은 graph node를 두 번 밟는 path도 result frame validator가 통과하도록 테스트한다.
- `RLoopReturnSummaryFrame`은 기존 schema대로 중복 제거를 유지한다.

## 검증

```powershell
python -m pytest tests\test_order_214_r3_schema_repair_once.py tests\test_order_215_r_traverse_path_duplicate_preservation.py -q
python -m pytest tests\test_order_176_vessel_r_one_step_traversal.py tests\test_order_181_r2_official_selection_ref_map.py tests\test_order_184_r_vessel_multi_step_traversal.py tests\test_order_191_r2_branch_role_surface_stability.py tests\test_order_201_r2_granularity_and_vessel_r_display.py tests\test_order_213_r2_schema_repair_once.py tests\test_order_214_r3_schema_repair_once.py tests\test_order_215_r_traverse_path_duplicate_preservation.py -q
python -m compileall songryeon_core main.py
python main.py smoke-test
```

결과:

- ORDER_214/215 좁은 테스트: 3 passed
- 관련 R loop 테스트 묶음: 19 passed
- 저장소 기본 compileall 통과
- smoke-test 통과: `SMOKE_TEST_OK`

## live 확인

다음 live R traverse를 재실행했다.

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘. 과거 대화 기억 가지가 아니라 코드/문서 소스 가지를 우선 보고, 시간축에서 시작해서 어떤 묶음을 거쳐 내려가는지 말해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

결과:

```text
status: R_LOOP_VESSEL_TRAVERSE_OK
traverse_status: completed
read_packet_status: passed
step_count: 4
final_graph_node_id: graph:summary:token_budget_bundle:b8bc3046747646a3:night_token_budget_layer_active
final_sufficiency_status: insufficient
final_continuation_status: stop_no_actionable_path
r_loop_task_status: partial
terminal_material_seen_count: 1
```

관찰:

- 이전 `R3 current_information_granularity is invalid` 실패는 재발하지 않았다.
- 이전 `selected path mismatch` 코드 예외도 재발하지 않았다.
- R traversal은 4단계까지 내려가 token budget summary node를 확인했다.
- 최종 상태는 `partial`이다. 이는 R3가 충분하다고 판단하지 않았고 더 내려갈 actionable path가 없어 닫힌 상태다.
