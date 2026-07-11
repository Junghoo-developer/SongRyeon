# ORDER 228: R Continuation Work Order And Actionable Child Selection v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: Vessel R / R2 continuation stability

## 배경

ORDER 226으로 R2는 공식 선택표를 받게 되었고, ORDER 227로 R1은 최소 탐색 예산을 정할 수 있게 되었다.
하지만 R3가 `deeper`를 권고하고 code가 다음 후보 surface를 만들었더라도, 다음 R2가 `none_selected`를 내며 탐색이 `stop_no_actionable_path`로 닫힐 수 있다.

이 경우 문제는 후보가 없는 것이 아니라, R2가 “지금은 멈춰도 되는 상황인지, 반드시 다음 후보를 R3에게 넘겨야 하는 상황인지”를 충분히 구조적으로 받지 못하는 데 있다.

## 목표

R3가 `deeper`를 냈고 현재 후보가 존재하면, 다음 R2에게 code-built `continuation_work_order`를 제공한다.
이 작업지시서는 R2가 멈추지 말고 공식 선택표에서 하나를 골라 R3에게 넘겨야 하는 상황을 절대정보로 알려준다.

## 변경

- R2 input payload에 `continuation_work_order`를 추가한다.
  - `work_order_status`
  - `previous_r3_recommended_next_action`
  - `previous_continuation_status`
  - `candidate_count`
  - `stop_allowed`
  - `none_selected_allowed`
  - `reason_code`
  - `next_selection_task`
- `previous_r_step_memory_packet` 기준으로 R3가 `deeper`를 권고했고 현재 후보가 있으면 `none_selected_allowed=false`로 둔다.
- R2 validator는 `none_selected_allowed=false`인데 R2가 `none_selected`를 내면 schema 실패로 막는다.
- R2 schema repair payload에도 `continuation_work_order`를 보존한다.
- official selection table candidate row에 현재 후보 surface에서 선택 가능한 후보임을 표시하는 구조 필드를 추가한다.
- R2 prompt에 continuation work order 사용 규칙을 추가한다.

## 하지 않는 것

- code가 어떤 후보가 의미적으로 맞는지 대신 선택하지 않는다.
- R3의 판단 권한을 R2로 합치지 않는다.
- Neo4j graph 구조, graph summary, node_3 답변 정책은 변경하지 않는다.
- R route live gate나 node_1 routing 정책은 변경하지 않는다.

## 완료 조건

- R3 `deeper` 이후 다음 R2 payload에 `continuation_work_order`가 들어간다.
- 후보가 있는데 work order가 `none_selected_allowed=false`이면 R2의 `none_selected`는 schema 실패가 된다.
- schema repair가 official table을 보고 valid candidate 선택으로 복구할 수 있다.
- 기존 R1/R2/R3 smoke와 quick-smoke를 깨지 않는다.
