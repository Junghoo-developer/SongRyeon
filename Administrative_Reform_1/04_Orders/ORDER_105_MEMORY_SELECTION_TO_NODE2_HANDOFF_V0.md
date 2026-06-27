# ORDER 105: Memory Selection to Node2 Handoff v0

## 상태

발주서 초안.

이 발주서는 ORDER_104 이후 다음 개발자를 위한 좁은 MVP 지시서다.
장기기억 DB, 요약, 자동 회상 답변을 여는 발주가 아니다.

## 배경

ORDER_100~104의 기억 계열은 다음 흐름을 만든다.

```text
ORDER_100: 최근 TurnStateCapsule index 공급
ORDER_101: 최근 raw conversation과 capsule을 turn_id로 대응
ORDER_103: 대응된 최근 턴을 MemoryRelevanceCandidateFrame 후보로 보존
ORDER_104: LLM selector가 후보 중 관련 있어 보이는 과거 턴을 선택
```

ORDER_104의 핵심 결과는 `MemoryRelevanceSelectionFrame`이다.

이 frame은 다음을 담는다.

```text
selection_status
selected_candidate_turn_ids
selected_candidate_frame_ids
selection_reason
judged_by
generated_by
llm_call_data_id
llm_trace_event_id
source_trace_ids
source_data_ids
source_memory_item_ids
info_class=mixed
source_mode=source_bundle
claim_alignment=multi_source_bundle
```

하지만 ORDER_104가 완료되어도, 이 selection result가 node_2와 node_3에게 충분히 선명하게 전달되지 않으면 다음 위험이 생긴다.

```text
기억 선택 판단이 있었는데 node_2 boundary가 분류하지 못한다.
node_3가 선택된 과거 턴을 근거 없는 기억처럼 사용할 수 있다.
selection_reason이 code 사실처럼 보일 수 있다.
selected_candidate_turn_ids가 절대정보처럼 오해될 수 있다.
```

## 목표

ORDER_105의 목표는 `MemoryRelevanceSelectionFrame`을 route=2 handoff와 node_3 input brief에 정직하게 전달하는 것이다.

핵심 문장:

```text
LLM selector가 고른 기억 선택 결과를 2와 3이 출처 달린 mixed 판단으로 볼 수 있게 한다.
```

이번 발주는 기억을 실제 답변에 적극 사용하게 만드는 작업이 아니다.
먼저 handoff/brief의 정직성을 고정한다.

## 핵심 원칙

1. 0은 관련성 선택자가 아니다.
2. ORDER_104 selector 결과는 LLM 판단이다.
3. selection result는 code fact가 아니라 mixed 판단으로 전달한다.
4. node_2는 selection result의 출처와 정보 등급을 보존해야 한다.
5. node_3는 선택된 memory를 사용할 수 있더라도, 그것이 LLM selector 판단임을 잃으면 안 된다.
6. 선택된 과거 턴의 원문 내용을 요약하거나 재작성하지 않는다.
7. 장기기억 DB, vector DB, memory graph는 열지 않는다.

## 구현 범위

### 1. Node2InputFrame source_data_ids 보강 확인

현재 `Node2InputFrame.source_data_ids`에 다음이 포함되는지 확인한다.

```text
memory_packet:node_1:pre_route_report
memory_relevance_selection_frame
memory_packet:node_2:final_trace_for_2
turn_outcome
route ids
```

없다면 최소 수정으로 포함한다.

### 2. Node2HandoffFrame memory selection summary 추가

`Node2HandoffFrame` 또는 route2 handoff payload에 다음 절대 count/status 필드를 추가하는 것을 검토한다.

후보 필드:

```text
memory_relevance_selection_frame_id
memory_relevance_selection_status
memory_relevance_candidate_count
memory_relevance_selected_count
memory_relevance_info_class
memory_relevance_generated_by
memory_relevance_llm_call_data_id
```

주의:

- 여기서 selection_reason을 code가 해석하지 않는다.
- count/status/id/source만 handoff에서 명시한다.

### 3. node_2 metainfo boundary에 selection reason 보존

`MemoryRelevanceSelectionFrame.selection_reason`은 LLM 의미 판단이다.

기본 분류:

```text
info_class=mixed
source_mode=source_bundle
claim_alignment=multi_source_bundle
```

node_2 boundary가 이 selection reason을 allowed mixed info로 볼 수 있게 한다.

다만 code가 selection_reason의 의미를 새로 판단하지 않는다.
원래 selector frame에 있는 라벨과 source ids를 보존하는 방식으로만 처리한다.

### 4. Node3InputBriefFrame에 memory selection material 추가

node_3 input brief에 선택된 memory result를 짧게 전달한다.

후보 구조:

```text
selected_memory_count
memory_selection_status
memory_selection_reason
memory_selection_info_class
selected_candidate_turn_ids
source_memory_item_ids
source_data_id
```

또는 기존 `allowed_claims`에 mixed claim으로 넣어도 된다.

중요:

- node_3에게 "이 과거 턴이 실제로 관련 있다"고 code 사실처럼 주지 않는다.
- "LLM selector가 관련 후보로 선택했다"는 판단으로 전달한다.
- raw internal ID를 최종 사용자 답변에 직접 노출하지 않도록 기존 renderer 규칙을 유지한다.

### 5. terminal/runtime 출력

runtime 출력에서 memory selection handoff 상태를 사람이 볼 수 있게 한다.

예시:

```text
memory_relevance_selection: status=selected / candidates=8 / selected=1 / generated_by=LLM:...
```

## 비범위

이번 발주에서 하지 말 것:

```text
선택된 과거 대화를 자동으로 최종 답변에 강제 삽입
선택된 과거 대화 원문 요약
장기기억 DB 생성
vector DB
embedding 기반 memory search
memory graph
오래된 대화 요약
node_4 요약 승인 루프
scheduler
W loop
R loop
관련성 heuristic fallback
키워드 매칭 selector
문자열 유사도 selector
```

## smoke-test 요구

### 1. handoff includes selection frame smoke

fixture:

- fake LLM selector가 candidate 1개를 선택

검증:

```text
Node2InputFrame.source_data_ids includes memory relevance selection frame id
Node2HandoffFrame.source_data_ids includes memory relevance selection frame id
memory_relevance_selection_status=selected
memory_relevance_selected_count=1
memory_relevance_info_class=mixed
```

### 2. boundary preserves memory selection as mixed smoke

검증:

```text
MetainfoBoundary.mixed_info includes memory relevance selection reason
source_data_id == memory relevance selection frame id
source_mode=source_bundle
claim_alignment=multi_source_bundle
info_kind=memory_relevance_selection_reason
```

### 3. node3 brief receives memory selection material smoke

검증:

```text
Node3InputBriefFrame includes selected memory material
selected_candidate_turn_ids length == selected count
memory_selection_info_class=mixed
memory_selection_status=selected
```

### 4. none_selected/failed safety smoke

검증:

```text
selection_status=none_selected이면 selected memory material count=0
selection_status=failed이면 selected memory material count=0
node_3 brief가 failed selector를 선택된 기억처럼 전달하지 않음
```

### 5. no raw id leakage smoke

최종 fallback report 또는 terminal/final renderer에서 raw internal ID가 사용자 답변 본문에 노출되지 않는지 확인한다.

단, terminal/runtime debug 출력에는 source id가 나와도 된다.

## 완료 조건

다음 명령을 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 반드시 다음을 적는다.

- selection frame id가 Node2InputFrame / Node2HandoffFrame에 어떻게 포함되는지
- node_2 boundary가 selection reason을 어떻게 mixed info로 보존하는지
- node_3 brief가 memory selection material을 어떻게 받는지
- none_selected/failed일 때 선택된 기억으로 오해되지 않음을 어떻게 보장했는지
- terminal/runtime 출력에서 무엇을 보여주는지
- smoke-test 결과
- 남은 위험

## 다음 단계 후보

ORDER_105 이후에야 다음을 논의할 수 있다.

```text
선택된 memory material을 node_3 본문 생성에 어떻게 제한적으로 사용할지
선택된 과거 턴 원문을 안전하게 재조회하는 도구/record 경계
node_4가 memory selection claim을 검증하거나 반려하는 정책
최근 원문 window와 오래된 요약 memory의 계층 배치
```

이 후보들은 ORDER_105의 비범위다.
