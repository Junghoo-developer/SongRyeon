# ORDER 227 실행 기록: R1 Minimum Traversal Budget And Hierarchy Primer

## 일시

- 2026-07-10

## 목적

R1이 그래프 계층 개념을 모른 채 최대 예산만 보는 상태를 줄이고, R3의 premature `sufficient`를 code가 R1 최소 예산 기준으로 막을 수 있게 했다.

## 구현 요약

- `songryeon_core/core/schema_parts/r_loop.py`
  - `R1GraphGoalFrame`에 `min_traversal_depth`, `min_node_reads`, `min_terminal_material_count` 추가.
  - `RLoopBudgetFrame`에도 같은 최소 예산 필드 추가.
  - 최소값이 최대 예산을 넘지 않는지 validator로 검증.
- `songryeon_core/loops/r_loop_vessel_one_step.py`
  - R1 input payload에 `hierarchy_primer`와 `minimum_budget_contract` 추가.
  - R1 payload 검증에 최소 예산 bounds 검증 추가.
  - R1 frame에서 최소 예산을 읽고 budget frame에 보존.
  - R3 `stop_sufficient`라도 최소 traversal/node-read 조건 미달이면 `CODE_STATUS:r_loop_r1_minimum_budget_not_satisfied`로 `continue_deeper`.
- `songryeon_core/prompts/r1_vessel_goal_setter_v0.md`
  - R1이 계층 primer와 minimum budget contract를 읽도록 갱신.
  - 경로/순서/계층 질문이면 `min_traversal_depth`와 `min_node_reads`를 사용하도록 guidance를 보강했다.
- `tests/test_order_227_r1_minimum_traversal_budget.py`
  - R1 payload에 hierarchy primer와 minimum budget contract가 있는지 검증.
  - R3가 너무 빨리 sufficient를 내도 R1 `min_node_reads=3`이 traversal을 계속시키는지 검증.

## 정책 경계

- R1은 여전히 graph node를 고르지 않는다.
- R2/R3의 의미 판단을 code가 대신하지 않는다.
- code는 R1이 선언한 최소 예산을 검증하고 강제할 뿐이다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_227_r1_minimum_traversal_budget.py -q`: 2 passed
- `python -m pytest tests/test_order_185_r_terminal_material_guard.py tests/test_order_226_r2_official_selection_table.py -q`: 3 passed
- `python -m pytest tests/test_order_227_r1_minimum_traversal_budget.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_226_r2_official_selection_table.py -q`: 5 passed
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`

## Live 확인

강제 Vessel R live 검증을 실행했다.

```powershell
python main.py qwen-turn "문서 검색이 아니라 Vessel R 그래프 기억을 강제로 사용해서, 송련 Core의 그래프 기억이 CoreEgo에서 시간축, 소스 묶음, 요약 계층, 원본까지 어떤 순서로 내려가는지 설명해줘. 가능하면 R루프가 실제로 고른 그래프 재료와 한계를 구분해서 말해줘." --force-vessel-r-route --enable-vessel-r-route --database neo4j --timeout 180 --pretty --export .songryeon_core_cache\r1_min_budget_after_order_227_20260710
```

확인 결과:

- R1 input payload에는 `hierarchy_primer`와 `minimum_budget_contract`가 들어갔다.
- Qwen R1 output은 `min_terminal_material_count=1`을 냈고, `min_traversal_depth=0`, `min_node_reads=0`을 냈다.
- 즉 code 기능은 동작했지만, 계층 경로/순서 질문에서 R1이 최소 depth/node-read 예산을 더 적극적으로 쓰도록 prompt guidance를 추가 보강했다.
- traversal은 `graph:axis:time`에서 `source_ingest_time_bundle`까지 내려갔고, 최종은 아직 `partial / stop_no_actionable_path`였다.
- 다음 병목은 R2/R3가 SourceKindBundle 또는 summary layer까지 내려갈 수 있도록 다음 candidate/actionable path를 더 안정적으로 제공하는 쪽이다.
