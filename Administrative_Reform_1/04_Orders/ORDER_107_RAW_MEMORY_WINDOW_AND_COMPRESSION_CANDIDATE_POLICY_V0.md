# ORDER 107: Raw Memory Window And Compression Candidate Policy v0

## 상태

발주서 초안.

이 발주서는 ORDER_101~105 이후의 기억 계열 다음 MVP다.
구현 전에는 인간 결재가 필요하다.

## 배경

현재 기억 계열은 다음까지 진행되었다.

```text
ORDER_100: 최근 TurnStateCapsule index 공급
ORDER_101: 최근 raw conversation과 TurnStateCapsule을 turn_id로 대응
ORDER_103: 최근 raw-capsule alignment를 relevance candidate frame으로 보존
ORDER_104: LLM selector가 후보 중 관련 있어 보이는 기억을 선택
ORDER_105: selector 판단을 node_2/node_3 handoff까지 mixed 정보로 전달
```

이제 남은 문제는 최근 원문 기억 창이 계속 커질 때의 처리다.

철학 기준선:

- `Administrative_Reform_1/00_Philosophy/Raw_Memory_Window_And_Node5_Compression_Philosophy_2026_06_26.md`

핵심 구상:

```text
최근 원문은 최대 8턴을 기본 창으로 둔다.
최근 원문 3턴은 최소 보장한다.
9턴째가 들어와 원문 창이 넘치면 최신 5턴은 원문 창에 남긴다.
그보다 오래된 4턴은 압축 후보 좌표로 분리한다.
```

## 목표

ORDER_107의 목표는 0이 최근 raw conversation 창을 정책 기준으로 나누고, 압축이 필요한 4턴 묶음을 **의미 요약 없이** compression candidate로 기록하는 것이다.

핵심 문장:

```text
0은 오래된 4턴을 요약하지 않고, 5 기억 압축기가 나중에 읽을 압축 후보 좌표만 만든다.
```

이번 발주는 node_5 기억 압축기 구현이 아니다.
이번 발주는 node_4 기억 요약 승인 구현도 아니다.

## 정책 상수

첫 MVP 기준은 다음으로 둔다.

```text
RECENT_RAW_CONVERSATION_MAX_WINDOW = 8
RECENT_RAW_CONVERSATION_MIN_GUARANTEE = 3
RAW_MEMORY_POST_COMPRESSION_KEEP = 5
RAW_MEMORY_COMPRESSION_BATCH_SIZE = 4
```

의미:

1. 최근 원문 창은 최대 8턴을 기준으로 본다.
2. 최근 3턴 원문은 최소 보장 창이다.
3. 원문 entry가 9개가 되면 최신 5턴은 retained raw window로 둔다.
4. retained 5턴 바로 앞의 4턴은 compression candidate가 된다.

예:

```text
raw turns = 1,2,3,4,5,6,7,8
-> compression candidate 없음
-> active raw window = 1,2,3,4,5,6,7,8

raw turns = 1,2,3,4,5,6,7,8,9
-> compression candidate = 1,2,3,4
-> retained raw window = 5,6,7,8,9
```

raw turns가 9개를 초과하는 경우에는, 최신 5턴 바로 앞의 4턴을 이번 pending candidate로 잡고, 그보다 오래된 미처리 raw turn 수는 `older_unmanaged_raw_turn_count` 같은 절대 count로 노출한다.

예:

```text
raw turns = 1..13
-> pending compression candidate = 5,6,7,8
-> retained raw window = 9,10,11,12,13
-> older_unmanaged_raw_turn_count = 4
```

이 값은 숨기지 않는다.
장기적으로는 이전 candidate가 node_5/node_4를 거쳐 처리되었는지 추적해야 한다.

## 구현 범위

### 1. Raw memory window policy helper

0 기억공급관 근처에 raw memory window를 계산하는 helper를 둔다.

후보 함수명:

```text
build_raw_memory_window_policy_frame(...)
build_recent_raw_conversation_compression_candidate(...)
```

이 helper는 다음을 판단하지 않는다.

- 현재 입력과 과거 턴의 관련성
- 과거 턴의 의미
- 사용자의 감정/의도/장기 목표
- 압축 요약 내용

이 helper가 하는 일은 다음뿐이다.

- raw conversation entry 수를 센다.
- 최신 retained raw turn id를 고른다.
- 압축 후보 turn id 묶음을 고른다.
- 정책 상수와 count를 기록한다.

### 2. Compression candidate frame 추가

새 schema를 추가한다.

후보 이름:

```text
RawMemoryCompressionCandidateFrame
```

후보 필드:

```text
frame_id
turn_id
policy_id
raw_conversation_count
max_raw_window
min_raw_guarantee
post_compression_keep
compression_batch_size
candidate_status
candidate_turn_ids
candidate_raw_entry_count
retained_raw_turn_ids
retained_raw_entry_count
older_unmanaged_raw_turn_count
source_memory_item_ids
source_trace_ids
source_data_ids
generated_by
info_class
semantic_judgement_status
node5_compression_status
node4_approval_status
```

기본 값:

```text
generated_by=CODE:RAW_MEMORY_WINDOW_POLICY
info_class=absolute_policy_decision
semantic_judgement_status=not_run
node5_compression_status=not_run
node4_approval_status=not_run
```

candidate가 없을 때:

```text
candidate_status=not_needed
candidate_turn_ids=[]
candidate_raw_entry_count=0
```

candidate가 있을 때:

```text
candidate_status=pending_node5_compression
candidate_turn_ids=[...4개...]
candidate_raw_entry_count=4
```

### 3. Memory packet에 candidate 좌표 연결

`pre_route_report` memory packet에 다음 중 하나를 넣는다.

선호:

```text
compression_candidate_frames=[RawMemoryCompressionCandidateFrame]
```

최소 대안:

```text
memory_items[].item_type=raw_memory_compression_candidate_index
```

단, frame 방식이 더 낫다.
이미 `MemoryRelevanceCandidateFrame`이 frame으로 들어가 있으므로 같은 패턴을 따른다.

### 4. 원문 삭제 금지

이번 ORDER_107에서는 raw conversation 원본을 파괴적으로 삭제하지 않는다.

이유:

- node_5 압축기가 아직 없다.
- node_4 요약 승인이 아직 없다.
- 압축 후보가 active compressed memory가 되기 전까지 원문을 잃으면 안 된다.

따라서 이번 MVP의 "최신 5턴 유지"는 다음 의미다.

```text
0이 다음 노드에 active recent raw window로 공급할 turn 범위
```

다음 의미가 아니다.

```text
ZeroState.recent_raw_conversation에서 오래된 원문을 즉시 삭제
```

실제 삭제/보관 교체 정책은 node_5와 node_4 승인 구조가 생긴 뒤 별도 발주에서 다룬다.

### 5. 기존 ORDER_101~105 유지

기존 동작은 깨지면 안 된다.

유지 대상:

- `previous_turn_capsule_index`
- `recent_raw_conversation_capsule_alignment`
- `MemoryRelevanceCandidateFrame`
- `MemoryRelevanceSelectionFrame`
- node_2 handoff의 memory selection 요약
- node_3 brief의 memory selection material

ORDER_107은 압축 후보 좌표를 추가하는 작업이지, relevance selector를 대체하는 작업이 아니다.

## 메타정보 분류

이번 발주에서 code가 쓰는 것은 절대정보다.

절대정보:

- raw conversation count
- retained turn ids
- candidate turn ids
- policy 상수
- source trace ids
- source memory item ids
- node5/node4 status가 아직 `not_run`이라는 사실

이번 발주에서 만들지 않는 것:

- 4턴 묶음의 의미 요약
- 왜 그 기억이 중요한지
- 현재 입력과 candidate의 관련성
- 사용자 감정/의도/장기 목표

미래 node_5가 만들 압축 요약은 mixed 정보로 취급한다.
하지만 ORDER_107에서는 그 mixed 요약을 생성하지 않는다.

## 비범위

이번 발주에서 하지 말 것:

```text
node_5 기억 압축기 구현
node_4 기억 요약 승인 구현
압축 요약 생성
압축 요약을 active memory로 승격
raw conversation 원본 삭제
장기기억 DB
vector DB
memory graph
embedding search
scheduler/background compression
W loop
R loop
관련성 heuristic fallback
키워드/문자열 유사도 기반 candidate 선택
```

## 감사/수정 후보 파일

```text
songryeon_core/core/schemas.py
songryeon_core/nodes/node_0_memory_supplier.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/user_turn.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
```

## Smoke-test 요구

### 1. raw count 8 no candidate smoke

fixture:

- raw conversation 8턴
- capsule 8턴

검증:

```text
raw_conversation_count=8
candidate_status=not_needed
candidate_turn_ids=[]
retained_raw_turn_ids=8개
node5_compression_status=not_run
node4_approval_status=not_run
```

### 2. raw count 9 creates candidate smoke

fixture:

- raw conversation 9턴
- capsule 9턴

검증:

```text
raw_conversation_count=9
candidate_status=pending_node5_compression
candidate_turn_ids=[turn_001, turn_002, turn_003, turn_004]
candidate_raw_entry_count=4
retained_raw_turn_ids=[turn_005, turn_006, turn_007, turn_008, turn_009]
retained_raw_entry_count=5
older_unmanaged_raw_turn_count=0
semantic_judgement_status=not_run
```

### 3. raw count 13 exposes older unmanaged smoke

fixture:

- raw conversation 13턴

검증:

```text
candidate_turn_ids=[turn_005, turn_006, turn_007, turn_008]
retained_raw_turn_ids=[turn_009, turn_010, turn_011, turn_012, turn_013]
older_unmanaged_raw_turn_count=4
```

### 4. no semantic compression smoke

검증:

```text
candidate frame에 natural-language summary가 없다.
node5_compression_status=not_run
node4_approval_status=not_run
info_class=absolute_policy_decision
generated_by=CODE:RAW_MEMORY_WINDOW_POLICY
```

### 5. existing memory pipeline still works smoke

검증:

```text
recent_raw_conversation_alignment_count 기존 smoke 유지
recent_memory_relevance_candidate_count 기존 smoke 유지
recent_memory_relevance_selection_* 기존 smoke 유지
memory_selection_handoff_* 기존 smoke 유지
```

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

가능하면 다음 수동 확인도 수행한다.

```powershell
python main.py fake-turn "최근 기억 창 상태 확인" --live-trace
```

완료 보고에는 반드시 다음을 적는다.

- raw memory window policy 상수를 어디에 정의했는지
- raw count 8/9/13 smoke 결과
- compression candidate frame id와 DataStore 저장 위치
- retained raw turn ids와 candidate turn ids가 어떻게 계산되는지
- raw 원본을 삭제하지 않았음을 어떻게 보장했는지
- 0이 의미 요약을 만들지 않았음을 어떻게 보장했는지
- 기존 ORDER_101~105 smoke가 깨지지 않았는지
- compileall / smoke-test 결과

## 다음 발주 후보

ORDER_107 이후에야 다음을 논의한다.

```text
ORDER_108_NODE5_MEMORY_COMPRESSOR_V0
ORDER_109_NODE4_MEMORY_SUMMARY_GATE_V0
```

ORDER_108은 pending compression candidate를 실제 요약으로 바꾸는 LLM node_5 발주다.

ORDER_109는 node_5가 만든 요약을 node_4가 검사하고, 통과한 것만 active memory 후보로 승격하는 발주다.
