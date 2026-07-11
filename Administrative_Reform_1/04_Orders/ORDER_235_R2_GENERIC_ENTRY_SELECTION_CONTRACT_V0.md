# ORDER 235: R2 Generic Entry Selection Contract v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: R2 first-step work order / schema repair reuse / future multi-axis compatibility

## 배경

ORDER 234 최종 Qwen live 재검증에서 R2가 첫 단계의 유일한 TimeAxis 후보를 두 번 `none_selected`로 닫았다. 기존 continuation 단계는 후보가 있고 R3가 deeper를 요청하면 `none_selected_allowed=false`와 schema repair를 사용하지만, 첫 단계는 후보가 있어도 항상 `none_selected_allowed=true`였다.

## 목표

- R 탐색이 시작됐고 code가 entry 후보를 하나 이상 공급했다면 R2가 그중 하나를 선택하게 한다.
- TimeAxis 이름이나 후보 수 1개를 하드코딩하지 않는다.
- 미래에 MeaningAxis, WorkAxis 등 여러 진입 축이 생기면 R2가 R1 목표에 따라 하나를 의미적으로 선택하게 한다.

## 구현 경계

- code는 `candidate_count > 0`이라는 절대정보만 보고 선택 필요 여부를 정한다.
- code는 어떤 entry가 적합한지 판단하지 않는다.
- 후보가 여러 개면 R2가 official selection table 안에서 하나를 고른다.
- 잘못된 `none_selected`는 기존 R2 schema repair 1회 경로를 재사용한다.
- 후보가 0개일 때만 `none_selected`를 허용한다.

## 하지 않는 것

- TimeAxis를 강제 선택하지 않는다.
- 특정 axis 이름 목록을 validator에 넣지 않는다.
- 키워드·질문 유형 휴리스틱을 추가하지 않는다.
- R1/R3, 그래프 계층, 예산을 변경하지 않는다.
- code가 의미 선택 fallback을 만들지 않는다.

## 완료 조건

- 첫 단계 후보가 있으면 `none_selected_allowed=false`다.
- 첫 단계 후보가 없으면 `none_selected_allowed=true`다.
- 후보가 여러 개여도 특정 axis 이름을 강제하지 않는다.
- first-step `none_selected`가 schema_failed 후 기존 1회 repair로 공식 후보 선택으로 복구된다.
- compileall, 관련 pytest, quick-smoke가 통과한다.
