# ORDER 227: R1 Minimum Traversal Budget And Hierarchy Primer v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: Vessel R / R1 budget semantics

## 배경

R1은 그래프 탐색 목표와 최대 예산을 정하지만, 현재 입력만으로는 그래프 계층의 의미를 충분히 이해하기 어렵다.
그 결과 R3가 높은 navigation layer에서 `sufficient`를 말하면, code가 최소 탐색 필요성을 구조적으로 판단하기 어렵다.

이미 terminal material 최소 1개 guard는 있었지만, 이는 고정 상수였고 R1이 질문에 맞춰 선언한 최소 예산은 아니었다.

## 목표

R1에게 그래프 계층 개념을 구조적으로 알려주고, R1이 최소 탐색 예산을 선언할 수 있게 한다.
code는 R1의 최소 예산을 절대 조건으로 검증하고, R3가 너무 빨리 `stop_sufficient`를 내도 최소 조건이 충족되지 않으면 계속 내려가게 한다.

## 변경

- R1 input payload에 `hierarchy_primer`를 추가한다.
  - CoreEgo / TimeAxis / SourceIngestBundle / SourceKindBundle / TokenBudgetSummary / SourceLeafSummaryOrRawSource의 역할을 구조적으로 설명한다.
  - 후보 ID나 summary text는 제공하지 않는다.
- R1 input payload에 `minimum_budget_contract`를 추가한다.
  - `min_traversal_depth`
  - `min_node_reads`
  - `min_terminal_material_count`
- `R1GraphGoalFrame`과 `RLoopBudgetFrame`에 최소 예산 필드를 추가한다.
- `RLoopBudgetFrame` validator가 최소값이 최대값을 넘지 않는지 검증한다.
- multi-step Vessel R traversal에서 R3가 `stop_sufficient`를 내도 다음 조건이 미달이면 `continue_deeper`로 바꾼다.
  - `used_traversal_depth < min_traversal_depth`
  - `used_node_reads < min_node_reads`
  - `terminal_material_seen_count < min_terminal_material_count`

## 하지 않는 것

- R1이 graph node나 surface/node ref를 선택하지 않는다.
- R2/R3 선택 의미 판단을 code가 대신하지 않는다.
- Neo4j 구조나 graph memory 데이터를 변경하지 않는다.
- node_1 라우팅, node_3 답변 정책, 외부 DB 정책은 변경하지 않는다.

## 완료 조건

- R1 payload에 계층 primer와 minimum budget contract가 들어간다.
- R1 frame과 budget frame에 최소 예산이 보존된다.
- R3가 premature `sufficient`를 내도 R1 최소 node read 조건이 미달이면 traversal이 계속된다.
- 기존 R2/R3/quick-smoke 기준선을 깨지 않는다.
