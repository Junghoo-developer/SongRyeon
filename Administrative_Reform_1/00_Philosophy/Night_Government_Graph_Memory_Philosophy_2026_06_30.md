# Night Government Graph Memory Philosophy 2026-06-30

**계층**: 00 철학
**상태**: 미승격 설계 철학
**권한**: 실행 권한 없음. 향후 유지 체계, 지도, 발주서로 승격 심사한다.

## 1. 배경

외부 채팅방에서 구현된 심야정부 MVP는 제거되었다.

제거 이유는 단순히 코드 품질 문제가 아니라, 송련 Core가 이미 가진 기억 기반과 맞지 않았기 때문이다.

송련 Core에는 이미 다음 기반이 있다.

```text
TraceStore
DataStore
TurnStateCapsule
ZeroState
MemoryPacket
```

따라서 심야정부는 별도 `MemoryRecord` 저장소를 새로 발명하기보다, 기존 trace/capsule/data 좌표를 그래프 DB에 올리고 그 위에 출처가 분명한 상대/혼합정보를 쌓는 방향이어야 한다.

## 2. 핵심 원칙

심야정부의 첫 목표는 "기억을 새로 상상해서 쓰는 것"이 아니다.

첫 목표는 다음과 같다.

```text
기존 trace/capsule/data를 잃지 않고
그래프 DB에 절대정보 좌표로 정리하고
그 위에 LLM 요약을 출처 달린 상대/혼합정보로 연결한다.
```

즉 심야정부는 원본 기억을 대체하지 않는다.

심야정부는 원본 기억을 그래프 구조로 재배치하고, 요약 노드를 별도로 붙인다.

## 3. 용어 구분

앞으로 "노드"라는 말을 두 의미로 섞지 않는다.

```text
GraphNode
-> 그래프 DB에 저장되는 데이터 객체

NightWorker
-> 심야정부에서 실행되는 LLM 작업자
```

예:

- `RawCapsuleGraphNode`: 한 턴 캡슐 또는 그 안의 원본 좌표를 나타내는 그래프 노드.
- `RawBundleGraphNode`: 여러 raw leaf를 토큰 예산 안에서 묶은 그래프 노드.
- `SummaryGraphNode`: LLM이 만든 요약/판단 그래프 노드.
- `CoreEgoGuideWorker`: R루프 안내 정보를 생성하는 LLM 호출 작업자.

그래프 DB의 노드와 LLM 실행 노드를 혼동하면, 저장 구조와 실행 책임이 흐려진다.

## 4. Raw Leaf와 Raw Bundle

최하위 원본 단위는 raw leaf로 본다.

예:

- 한 턴의 `TurnStateCapsule`
- 특정 trace/data record 묶음
- 내부 문서 원문
- 코드 파일 원문

raw leaf는 절대정보에 가깝다.

코드가 확인할 수 있는 것은 다음이다.

- 존재 여부
- `turn_id`
- `trace_id`
- `data_id`
- 파일 경로
- 문자 수
- 생성 시각
- 원본 종류

raw leaf 여러 개를 묶은 `RawBundleGraphNode`도 의미 요약이 아니다.

`RawBundleGraphNode`는 다음과 같은 절대정보적 묶음 좌표다.

```text
이 raw leaf 묶음이 있다.
이 묶음은 이 source id 목록에 기대고 있다.
이 묶음은 이 시간 범위에 속한다.
이 묶음은 이 토큰 예산 안에서 구성되었다.
```

## 5. 원문 절단 금지

토큰 예산 때문에 계층을 나눌 때 원문을 중간에서 자르지 않는다.

기본 규칙:

```text
원문을 자르지 않는다.
토큰 예산을 넘으면 leaf 단위로 bundle을 나눈다.
예산에 걸치는 마지막 leaf는 빼거나 다음 bundle로 넘긴다.
```

최하단 bundle worker는 임시 요약을 보지 않는다.

최하단 `NightWorker`는 가능한 한 raw leaf 원문들을 직접 본다.

이유:

1. 첫 요약 이전의 정보 손실을 줄인다.
2. 요약의 요약 오류가 초반부터 전파되는 것을 막는다.
3. 첫 LLM 산출물이 어떤 원문 source bundle을 직접 봤는지 분명히 남길 수 있다.

## 6. 요약은 원본 속성이 아니라 별도 노드다

LLM이 만든 요약을 raw node의 속성으로 바로 박지 않는다.

더 안전한 구조는 다음이다.

```text
RawGraphNode
<- SUMMARY_OF
SummaryGraphNode
```

원본 노드는 절대정보 좌표로 깨끗하게 남긴다.

요약 노드는 별도 graph node로 만들고, 다음 필드를 가진다.

```text
info_class
generated_by
semantic_judgement_status
source_graph_node_ids
source_trace_ids
source_data_ids
source_bundle_kind
review_status
```

이 구조는 나중에 요약이 틀렸을 때 원본을 오염시키지 않고 요약 노드만 폐기하거나 재생성할 수 있게 한다.

## 7. 상대정보와 혼합정보 분류

심야정부의 LLM 산출물은 다음 기준으로 분류한다.

```text
원문 leaf 1개를 직접 보고 만든 요약/판단
-> relative

원문 leaf 여러 개를 직접 보고 만든 요약/판단
-> mixed

여러 summary node를 보고 만든 상위 요약/판단
-> mixed

대화, 내부 문서, 코드처럼 서로 다른 data kind가 섞인 source bundle
-> mixed
```

따라서 현실적으로 한 턴만 처리하는 특수 상황이 아니라면, 첫 `NightWorker` 산출물도 대부분 `mixed`일 가능성이 높다.

중요한 점:

```text
mixed는 출처가 흐린 정보가 아니다.
mixed는 여러 절대정보 묶음에 근거했다는 사실을 드러내는 정보다.
```

혼합정보는 반드시 source bundle을 가진다.

## 8. 요약 계층 계산

심야정부의 summary node에는 계층 계산 필드가 필요하다.

필수 후보:

```text
summary_depth
source_depth_min
source_depth_max
source_leaf_count
source_summary_count
source_bundle_kind
```

계산 원칙:

```text
raw leaf node:
depth = 0

raw leaf를 직접 보고 만든 첫 summary:
summary_depth = 1

summary node들을 보고 만든 상위 summary:
summary_depth = max(source_depths) + 1
```

`source_leaf_count`는 위로 올라가도 누적한다.

예:

```text
대화 원문 8턴 -> depth 1 mixed summary
대화 원문 8턴 -> depth 1 mixed summary
두 summary를 다시 묶음 -> depth 2 mixed summary
```

이때 depth 2 summary는 다음을 기록한다.

```text
summary_depth = 2
source_leaf_count = 16
source_summary_count = 2
source_depth_min = 1
source_depth_max = 1
```

이 인프라가 있어야 나중에 R루프가 다음을 구분할 수 있다.

- 원문에 가까운 기억인가?
- 요약의 요약인가?
- 몇 단계 압축됐나?
- 너무 추상화된 기억인가?
- R1이 직접 쓰기에는 위험한 고압축 정보인가?

## 9. CoreEgo 연결: 초기에는 시간축만

초기 CoreEgo 직속 그래프 연결은 시간축만 사용한다.

이유:

- 시간, 턴, trace, data 좌표는 코드가 비교적 안정적으로 확정할 수 있다.
- 의미 분류는 LLM의 상대/혼합 판단이므로 처음부터 CoreEgo 직속 구조로 쓰면 위험하다.
- 먼저 시간축으로 작고 정직하게 시작해야 한다.

초기 구조:

```text
CoreEgo
  -> TimeAxis
      -> TimeBundle_2026_06_30_session_001
          -> RawCapsule_turn_0001
          -> RawCapsule_turn_0002
          -> Summary_time_bundle_001
```

의미축은 나중에 R1의 부담이 실제로 커졌을 때 도입한다.

도입 조건 후보:

- R1 context가 시간축 guide만으로 자주 초과된다.
- R루프가 시간축에서 반복적으로 탐색 실패한다.
- 사용자 질문이 시간보다 주제 기준 검색을 요구하는 비율이 높아진다.
- graph node 수가 많아져 CoreEgo 직속 시간축만으로는 entry selection 비용이 커진다.

## 10. 장기 의미축 구상

장기적으로는 다음 구조를 병행할 수 있다.

```text
CoreEgo
  -> TimeAxis
      -> TimeBundle_...
  -> SemanticAxis
      -> Topic_최근기억시스템
      -> Topic_L루프검색구조
      -> Topic_메타정보정책
```

의미축 도입 후 R1은 기본적으로 의미축을 우선 열람하고, 필요할 때 시간축으로 역추적할 수 있다.

다만 의미축은 코드가 몰래 만들면 안 된다.

의미 분류 필수 필드 후보:

```text
topic_label
topic_assignment_generated_by
topic_assignment_info_class
topic_source_graph_node_ids
topic_confidence
topic_review_status
```

의미축은 강력하지만 위험하다.

따라서 초기 MVP에서는 열지 않는다.

## 11. 지금 당장 하지 않는 것

이 문서는 구현 발주서가 아니다.

지금 당장 하지 않는다.

- 그래프 DB 연결
- 의미축 CoreEgo 연결
- R루프 구현
- 자동 장기기억 승격
- 4 승인 없는 summary 사용
- 외부 DB record를 기존 capsule과 별도로 새로 발명하기
- 모든 노드에 CoreEgo 최소정보 배분하기

## 12. 임시 결론

심야정부는 기억 요약기가 아니라 그래프 기억 정리기여야 한다.

첫 MVP의 정신은 다음이다.

```text
TurnStateCapsule/TraceStore/DataStore를 source로 삼는다.
raw graph node는 절대정보 좌표로 만든다.
summary는 별도 node로 만들고 source edge를 단다.
첫 LLM worker는 원문 leaf bundle을 직접 본다.
대부분의 첫 summary는 mixed다.
summary depth를 계산한다.
CoreEgo 직속 연결은 처음에는 시간축만 쓴다.
의미축은 R1 부담이 실제로 관측된 뒤 연다.
```

