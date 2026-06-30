# order_140_r_loop_frame_state_machine_2026_06_30_001

## 1. 작업 요약

ORDER_140 후보 발주를 사용자 승인에 따라 frame-only state machine 구현으로 승격했다.

이번 작업은 R루프를 실제 route로 열지 않는다.

구현 범위는 R1/R2/R3/controller/return summary frame schema와 deterministic continuation decision helper, 그리고 pytest다.

## 2. 핵심 변경

- `songryeon_core/core/schema_parts/r_loop.py`
  - `R1GraphGoalFrame`
  - `RLoopBudgetFrame`
  - `R2GraphNodeSelectionFrame`
  - `R3GraphInspectionFrame`
  - `RLoopContinuationFrame`
  - `RLoopReturnSummaryFrame`
  - 각 validator 추가
- `songryeon_core/core/r_loop_state_machine.py`
  - R3 구조화 상태와 budget 숫자만 보고 continuation status를 결정하는 helper 추가
- `songryeon_core/core/schemas.py`, `schema_parts/__init__.py`
  - 기존 import 호환 surface에 R loop frame 연결
- `tests/test_order_140_r_loop_frame_state_machine.py`
  - 허용 graph node id 검증, deeper/switch 분리, budget exhausted, not_run 경계 테스트 추가

## 3. 금지선

- node_1 route=R 연결 없음.
- qwen-turn/qwen-chat에서 R루프 실행 없음.
- R1/R2/R3 LLM prompt 없음.
- 외부 graph DB 연결 없음.
- 의미축 CoreEgo 연결 없음.
- node_3 final answer에 R 결과 주입 없음.
- code가 graph node 선택 이유나 inspection reason을 의미적으로 작성하지 않음.

## 4. 검증

다음 명령을 실행했다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_140_r_loop_frame_state_machine.py
python -m pytest tests/test_order_139_graph_memory_foundation.py tests/test_order_140_r_loop_frame_state_machine.py
python -m pytest
python main.py smoke-test
git diff --check
```

결과:

- `compileall`: 통과
- ORDER_140 단독 pytest: `6 passed`
- ORDER_139+140 묶음 pytest: `12 passed`
- 전체 pytest: `89 passed`
- smoke-test: `SMOKE_TEST_OK`
- `git diff --check`: 통과

## 5. 확인된 경계

- R2 selection은 허용된 graph node id만 통과한다.
- 허용 목록 밖 graph node id는 validator가 거부한다.
- R3는 raw capsule, time bundle, summary node kind를 구조적으로 구분한다.
- `continue_deeper`와 `continue_switch_branch`는 다른 continuation status로 남는다.
- 예산 소진 시 `stop_budget_exhausted`로 닫힌다.
- schema-only/fake frame의 semantic judgement는 `not_run`으로 유지된다.
