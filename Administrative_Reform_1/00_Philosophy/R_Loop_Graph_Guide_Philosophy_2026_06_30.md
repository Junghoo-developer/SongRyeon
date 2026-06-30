# R Loop Graph Guide Philosophy 2026-06-30

**계층**: 00 철학
**상태**: 미승격 설계 철학
**권한**: 실행 권한 없음. 향후 유지 체계, 지도, 발주서로 승격 심사한다.

## 1. 배경

R루프를 지금 구상하는 이유는, 심야정부의 첫 MVP 목표가 "완성된 장기기억"이 아니라 R루프의 그래프 DB 길찾기 안내이기 때문이다.

본점의 CoreEgo 구상은 모든 송련 노드가 봐야 할 최소 정보를 생성하고 배분하는 더 큰 목표를 가졌다.

SongRyeon Core에서는 그 큰 목표를 뒤로 미룬다.

현재 MVP 감각은 더 좁다.

```text
CoreEgo는 우선 R루프가 그래프 DB에서 길을 잃지 않게 하는 안내 정보를 만든다.
```

## 2. L루프에서 배운 패턴

L루프의 성능이 좋아진 이유는 "그냥 검색을 더 시켰기 때문"이 아니다.

L루프는 다음 장부를 갖게 되면서 강해졌다.

```text
목표
예산
검색 후보
읽은 문서
안 읽은 후보
남은 예산
성공/부분성공/실패 판단
다음에 할 수 있는 행동
```

현재 L루프의 큰 흐름은 다음과 같다.

```text
L1: 목표와 필요 근거, 예산 요구 설정
-> L2: 검색어/도구/읽을 대상 선택
-> tool 실행
-> L3: 목표 달성 여부와 근거 충분성 판단
-> continuation controller:
     충분하면 stop
     부족하고 예산 남으면 L2 revision
     예산 없으면 partial/fail로 닫음
-> 0이 L return summary를 만들어 다음 노드에 전달
```

R루프도 이 패턴을 그대로 가져가되, 검색 대상이 문서가 아니라 그래프 DB가 된다.

## 3. R루프의 기본 목표

R루프는 범용 대화 루프가 아니다.

R루프는 다음 역할을 위한 미래 루프다.

```text
CoreEgo
정체성
장기 기억
그래프 DB 탐색
심야정부가 만든 기억 계층 읽기
```

초기 R루프의 목표는 다음 하나로 좁힌다.

```text
CoreEgo에 직속 연결된 그래프 노드들에서 시작해,
사용자 질문에 필요한 정보 농도까지 안전하게 내려간다.
```

## 4. R1, R2, R3 역할 구상

### R1: Graph Goal And Budget Planner

R1은 0이 공급한 CoreEgo guide와 현재 사용자 질문을 보고 그래프 탐색 목표를 세운다.

R1이 정해야 할 것:

```text
graph_search_goal
required_information_granularity
allowed_summary_depth
max_traversal_depth
max_branch_switches
max_node_reads
max_context_tokens
stop_condition
```

R1은 다음 질문에 답해야 한다.

```text
이번 질문은 원문에 가까운 정보가 필요한가?
낮은 농도의 summary로 충분한가?
높은 농도의 mixed summary도 쓸 수 있는가?
몇 계층까지 파도 되는가?
예산을 어디까지 쓸 것인가?
```

R1의 목표/예산 판단은 LLM 판단이면 상대/혼합정보다.

코드는 예산 숫자와 schema만 검증한다.

### R2: Graph Entry Or Child Selector

R2는 R1의 목표를 보고 탐색할 그래프 노드 하나를 고른다.

초기 MVP에서는 CoreEgo 직속 시간축 노드 중 하나를 고르는 역할이 중심이다.

나중에 deeper 탐색 중에는 선택된 상위 노드의 하위 노드 목록을 보고 하나를 고른다.

R2가 고르는 것:

```text
selected_graph_node_id
selection_scope
selection_reason
expected_information_granularity
expected_source_kind
```

R2의 선택 이유는 의미 판단이다.

따라서 code fallback이 "이 노드가 의미상 맞다"고 대신 판단하면 안 된다.

### R3: Graph Node Inspector And Sufficiency Judge

R3는 R2가 고른 그래프 노드를 검사한다.

R3가 봐야 할 것:

```text
선택된 노드가 raw leaf인가?
bundle인가?
summary인가?
summary라면 depth가 몇인가?
하위 노드가 있는가?
현재 정보 농도로 답할 수 있는가?
더 아래로 내려가야 하는가?
애초에 다른 가지를 골라야 하는가?
```

R3는 두 문제를 구분해야 한다.

```text
농도 문제:
같은 가지는 맞지만 정보가 너무 압축되어 있다.
-> 더 아래로 판다.

가지 문제:
애초에 선택한 그래프 노드가 목표와 맞지 않는다.
-> 다른 entry 또는 sibling branch로 돌아간다.
```

이 구분이 없으면 R루프는 같은 곳만 계속 파거나, 조금 부족하다는 이유로 엉뚱한 곳으로 튈 수 있다.

## 5. 정보 농도

사용자 표현의 "농도"는 R루프에서 중요한 개념이다.

정식 후보 용어:

```text
information_granularity
evidence_density
summary_depth
```

초기 감각:

```text
낮은 농도
-> 원문에 가까움
-> 구체적
-> 토큰을 많이 먹음

중간 농도
-> 한 묶음 요약
-> 적당히 압축됨

높은 농도
-> 요약의 요약
-> 빠르지만 세부 근거 약함
```

사용자가 구체적인 것을 물으면 R루프는 낮은 농도 정보나 원본 데이터를 향해 내려가야 한다.

사용자가 큰 흐름, 방향, 전략을 물으면 더 높은 농도의 mixed summary에서 멈출 수 있다.

R3의 핵심 질문:

```text
지금 농도의 정보로 사용자 질문에 답해도 되는가?
```

## 6. R Continuation Controller

R3 이후에는 controller가 반복 여부를 결정한다.

controller는 의미 판단을 새로 하지 않는다.

controller가 보는 것은 구조화된 R3 결과와 예산 숫자다.

후보 상태:

```text
stop_sufficient
continue_deeper
continue_switch_branch
stop_budget_exhausted
stop_no_actionable_path
stop_failed_final
```

의미:

- `stop_sufficient`: 현재 노드/요약 농도로 충분하다.
- `continue_deeper`: 같은 가지는 맞지만 더 낮은 농도 정보가 필요하다.
- `continue_switch_branch`: 현재 가지가 목표와 맞지 않아 다른 entry 또는 sibling을 봐야 한다.
- `stop_budget_exhausted`: 더 볼 수 있지만 예산이 없다.
- `stop_no_actionable_path`: 하위 노드도 없고 다른 선택지도 없다.
- `stop_failed_final`: 반복 한계에 닿았다.

## 7. 0의 역할

R루프에서도 0은 중요하다.

L루프에서 0이 잘하는 일은 "의미 판단"이 아니라 다음이다.

```text
루프가 만든 trace/data 좌표를 다음 노드가 잃어버리지 않게 봉투에 담는다.
```

R루프에서도 0은 다음을 해야 한다.

- R루프 시작 전에 CoreEgo guide packet을 공급한다.
- R1/R2/R3/controller가 만든 frame ID를 보존한다.
- 읽은 graph node 목록을 보존한다.
- 선택하지 않은 후보 목록도 필요하면 보존한다.
- R return summary를 만들어 1 또는 downstream node가 이해할 수 있게 한다.

0은 그래프 의미 판단을 대신하지 않는다.

0은 좌표, trace, source, budget, status를 잃지 않게 전달한다.

## 8. RLoopGraphGuidePacket

심야정부/CoreEgo 측에서 R루프에 줄 첫 안내 정보는 `RLoopGraphGuidePacket`으로 볼 수 있다.

역할:

```text
R루프가 그래프 DB를 탐색할 때 어디서 시작하고,
어떤 종류의 노드를 조심하고,
어떤 depth의 요약을 어떻게 볼지 알려주는 안내판.
```

후보 필드:

```text
graph_snapshot_id
target_consumer = R_LOOP
available_entry_nodes
node_kind_counts
data_kind_counts
summary_depth_range
source_leaf_count_range
high_value_entry_node_ids
risky_or_unreviewed_node_ids
recommended_traversal_hints
forbidden_shortcuts
source_graph_node_ids
generated_by
info_class
semantic_judgement_status
```

주의:

- `available_entry_nodes`, count, depth range는 code가 확정 가능한 절대정보다.
- `recommended_traversal_hints`는 의미 판단이므로 LLM이 만들어야 한다.
- guide packet은 최종 진실이 아니라 탐색 안내다.

## 9. 초기 CoreEgo MVP 범위

본점의 CoreEgo 전체 목표는 아직 열지 않는다.

아직 하지 않는 것:

- 모든 노드에 공통 최소 정보 배분
- 장기 자아 요약
- 전역 세계관 생성
- 자동 행동 계획
- 의미축 CoreEgo 직속 연결

이번 철학이 가리키는 초기 MVP:

```text
심야정부가 그래프 DB를 정리한다.
CoreEgoGuideWorker가 시간축 graph snapshot을 본다.
RLoopGraphGuidePacket을 만든다.
R루프는 그 guide를 보고 그래프 탐색을 시작한다.
```

## 10. R루프와 L루프의 대응

```text
L1: 문서 검색 목표/예산
R1: 그래프 탐색 목표/예산

L2: 검색어/도구/문서 후보 선택
R2: CoreEgo entry 또는 하위 graph node 선택

L3: 검색 결과와 읽은 문서가 목표에 충분한지 판단
R3: 선택 노드의 정보 농도와 하위 구조가 목표에 충분한지 판단

L continuation: 더 검색/읽기 또는 멈춤
R continuation: 더 깊게/다른 가지/멈춤

L return summary: 0이 다음 노드에 전달
R return summary: 0이 1 또는 downstream에 전달
```

## 11. 지금 당장 하지 않는 것

이 문서는 발주서가 아니다.

지금 당장 하지 않는다.

- R루프 구현
- 그래프 DB 연결
- CoreEgo full implementation
- 의미축 graph hierarchy
- R1/R2/R3 prompt 작성
- 자동 graph traversal
- 0의 graph memory packet 구현

먼저 이 철학을 기준으로 R루프 프레임/상태기계 설계 감사를 해야 한다.

## 12. 임시 결론

R루프는 L루프의 검색 반복 구조를 그래프 탐색 반복 구조로 바꾸는 것이다.

L루프가 다음을 한다면:

```text
검색 후보 -> 문서 읽기 -> 충분성 판단 -> 더 검색/읽기
```

R루프는 다음을 한다.

```text
CoreEgo entry 후보 -> graph node 열람 -> 농도/충분성 판단 -> 더 깊게/다른 가지
```

R루프의 첫 성공 조건은 똑똑한 대답이 아니다.

첫 성공 조건은 다음이다.

```text
R1이 목표와 예산을 정한다.
R2가 후보를 하나 고른다.
R3가 농도 문제와 가지 문제를 구분한다.
controller가 예산 안에서 반복 여부를 결정한다.
0이 모든 trace/data 좌표를 잃지 않고 다음 노드에 전달한다.
```

