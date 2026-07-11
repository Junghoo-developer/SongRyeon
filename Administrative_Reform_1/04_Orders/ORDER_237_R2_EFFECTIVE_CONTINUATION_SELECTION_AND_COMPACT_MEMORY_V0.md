# ORDER 237: R2 Effective Continuation Selection And Compact Memory v0

## 상태

- Status: implemented and regression verified; follow-up completed through ORDER_242
- Date: 2026-07-10
- Scope: R2 continuation work order / previous step memory LLM view

## 배경

ORDER 236 완전 통합 재시험에서 첫 R3는 TimeAxis 자식 3개를 보면서도 `stop`을 반환했다. code의 terminal-material guard는 실제 continuation을 `continue_deeper`로 교정했다. 그러나 다음 R2 work order는 `continuation=continue_deeper`와 `R3 action=deeper`가 동시에 있어야 선택을 요구했으므로, 교정된 continuation인데도 `none_selected`를 허용했다.

두 번째 R2 input은 full previous step provenance 때문에 약 51,455자까지 커졌다.

## 목표

- R2 work order가 원래 R3 신호가 아니라 최종 code-recorded continuation 상태를 따른다.
- 실제 continuation이 `continue_deeper|continue_switch_branch`이고 후보가 있으면 R2는 하나를 선택한다.
- R2에 전달하는 previous step memory도 compact view를 사용한다.

## 구현 경계

- code는 continuation enum과 candidate count만 검사한다.
- code는 후보 의미를 판단하거나 특정 축을 선택하지 않는다.
- 후보 선택은 official selection table 안에서 R2가 수행한다.
- full step-memory provenance는 DataStore에 유지한다.
- LLM input에서는 직전 선택, R3 신호, 최종 continuation, 남은 예산 count만 보낸다.

## 하지 않는 것

- TimeAxis를 하드코딩하지 않는다.
- R3의 의미 판단을 code가 성공으로 바꾸지 않는다.
- trace/data records를 삭제하지 않는다.
- 키워드나 축 이름 휴리스틱을 추가하지 않는다.

## 완료 조건

- R3 action이 stop이어도 effective continuation이 continue이고 후보가 있으면 `none_selected_allowed=false`다.
- 후보가 없으면 none_selected를 허용한다.
- R2 previous memory LLM view에는 full source trace/data ID 목록이 없다.
- 관련 pytest와 quick-smoke가 통과한다.
- 완전 통합 qwen-turn에서 R이 RawSource까지 이어지고 node_3에 실제 R material이 전달된다.
