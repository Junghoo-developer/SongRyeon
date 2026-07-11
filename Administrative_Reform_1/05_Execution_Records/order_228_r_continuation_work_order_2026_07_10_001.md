# ORDER 228 실행 기록: R continuation work order and actionable child selection

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: Vessel R loop continuation stability

## 변경 요약

R3가 `deeper`를 권고하고 다음 후보 surface가 실제로 존재하는 경우, 다음 R2 input payload에 code-built `continuation_work_order`를 추가했다.

이 work order는 후보를 의미적으로 고르지 않는다. 대신 이전 R3 신호와 현재 후보 개수를 기준으로 다음 R2가 `none_selected`로 닫아도 되는 상황인지, 반드시 official selection table에서 후보 하나를 골라 R3에게 넘겨야 하는 상황인지 알려주는 절대정보 계약이다.

## 코드 변경

- `songryeon_core/loops/r_loop_vessel_one_step.py`
  - R2 payload에 `continuation_work_order` 추가
  - 첫 단계와 continuation 단계를 구분
  - 이전 R3가 `deeper`를 냈고 후보가 있으면 `none_selected_allowed=false`
  - R2 validator가 input contract payload를 함께 보고 금지된 `none_selected`를 schema 실패로 차단
  - R2 schema repair table에 `continuation_work_order` 보존
  - official selection table candidate row에 현재 후보 row임을 드러내는 구조 필드 추가
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
  - continuation work order 사용 규칙 추가
  - `none_selected_allowed=false`일 때 `none_selected` 금지 명시
- `tests/test_order_228_r_continuation_work_order.py`
  - 두 번째 R2가 continuation work order를 받는지 검증
  - 금지된 `none_selected`가 schema 실패 후 official table 선택으로 repair되는지 검증

## 확인한 것

- 첫 R2는 기존처럼 official table을 보고 선택할 수 있다.
- R3가 `deeper`를 낸 뒤 다음 R2는 `continuation_work_order`를 받는다.
- 후보가 있는데 work order가 `none_selected_allowed=false`이면 R2의 `none_selected`는 schema 실패가 된다.
- schema repair는 work order와 official table을 유지한 채 valid candidate 선택으로 복구할 수 있다.

## 하지 않은 것

- code가 의미적으로 어떤 그래프 노드가 좋은지 선택하지 않았다.
- R3 판단을 R2로 합치지 않았다.
- Neo4j 구조, source summary 계층, node_1 라우팅 정책, node_3 답변 정책은 바꾸지 않았다.
- R루프를 현장 qwen-turn에 더 깊게 자동 통합하지 않았다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_228_r_continuation_work_order.py -q
```

결과: `2 passed`.

```powershell
python -m pytest tests/test_order_226_r2_official_selection_table.py tests/test_order_227_r1_minimum_traversal_budget.py tests/test_order_185_r_terminal_material_guard.py tests/test_order_213_r2_schema_repair_once.py -q
```

결과: `7 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

## 남은 위험

이번 패치는 R2가 continuation 상황에서 멈추지 않도록 구조적으로 막는 것이다.
R루프가 live Qwen 실행에서 항상 좋은 가지를 고른다는 의미는 아니다.
다음 병목은 live R traverse에서 work order, official selection table, hierarchy child candidates가 실제로 어떤 선택 경로를 만드는지 확인하는 것이다.
