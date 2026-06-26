# ORDER 101: Recent Raw Conversation Capsule Alignment v0

## 상태

구현 및 검증 완료.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_101_recent_raw_conversation_capsule_alignment_2026_06_26_001.md`

이 발주서는 ORDER_100 다음 단계로, 장기기억 DB를 만들기 전에 최근 원문 대화와 `TurnStateCapsule` 좌표를 안전하게 대응시키는 MVP다.

## 목표

최근 8턴 raw conversation과 `TurnStateCapsule`을 `turn_id` 기준으로 대응시켜, `pre_route_report` memory packet에 `COPIED_FIELDS` alignment item으로 공급한다.

이번 발주의 핵심은 다음이다.

```text
최근 원문 대화가 어느 TurnStateCapsule과 대응되는지 0이 좌표표로 넘긴다.
0은 관련성 선택자나 기억 요약자가 아니다.
```

## 현재 코드 사실

- `ZeroState.recent_raw_conversation` 구조가 있다.
- `ZeroState.previous_turn_capsules` 구조가 있다.
- `TurnStateCapsule`은 `turn_id`, `trace_event_ids`, `node_movements`, `user_input_trace_id`, `final_response_trace_id`를 가진다.
- ORDER_100에서 0은 최근 3턴 capsule index를 `previous_turn_capsule_index` item으로 `pre_route_report` packet에 넣기 시작했다.
- `MemoryItem`은 `item_type`, `text`, `source_trace_ids`, `source_data_ids`를 가진다.
- `record_memory_packet()`은 외부에서 만든 `memory_items`를 받을 수 있다.

구현자는 먼저 현재 `recent_raw_conversation` entry의 실제 모양을 감사한다.
필요하면 이번 MVP 안에서 최소한의 정규화 함수를 두되, raw text를 의미 요약으로 바꾸지 않는다.

## 문제

ORDER_100은 이전 턴 capsule 좌표를 넘기지만, 최근 원문 대화와 capsule이 어느 턴에서 서로 대응되는지는 아직 memory packet에서 선명하지 않다.

나중에 LLM selector가 관련 capsule을 고르려면, 먼저 다음 절대 좌표가 안정되어야 한다.

```text
최근 원문 대화 turn
그 turn의 capsule
그 capsule의 user input trace
그 capsule의 final response trace
```

이 대응표 없이 바로 관련성 판단이나 기억 요약으로 가면, 0이 의미 판단을 만든 것처럼 보일 위험이 있다.

## 구현 범위

### 1. Read Window

최근 raw conversation alignment window는 8턴으로 둔다.

```text
RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW=8
```

이 값은 장기기억 크기가 아니다.
이번 턴의 `pre_route_report` packet에 넣을 최근 원문-capsule 대응 후보 창이다.

### 2. Alignment 기준

원칙 기준은 `turn_id`다.

```text
recent_raw_conversation entry.turn_id == TurnStateCapsule.turn_id
```

현재 raw conversation entry에 `turn_id`가 없다면 구현자는 다음 중 더 작은 쪽을 택한다.

```text
1. raw conversation entry에 turn_id를 넣는 최소 배선
2. 이미 존재하는 trace/capsule 생성 시점에서 turn_id를 보존하는 최소 정규화
```

단, 순서 추정이나 문자열 유사도 같은 휴리스틱으로 대응시키지 않는다.

### 3. MemoryItem 형식

대응된 각 최근 턴에 대해 다음 item을 만든다.

```text
item_type=recent_raw_conversation_capsule_alignment
text=COPIED_FIELDS:turn_id=...;raw_user_text_present=...;raw_assistant_text_present=...;raw_user_text_chars=...;raw_assistant_text_chars=...;capsule_trace_count=...;capsule_movement_count=...;user_input_trace_id=...;final_response_trace_id=...
source_trace_ids=[실제로 capsule 안에 존재하는 user_input_trace_id, final_response_trace_id]
source_data_ids=[]
```

필요하면 raw text 원문 자체를 별도 field로 복사할 수 있다.
그 경우에도 `COPIED_FIELDS`로 표시하고, 요약문처럼 바꾸지 않는다.

예:

```text
raw_user_text=...
raw_assistant_text=...
```

다만 smoke-test에서는 최소한 text 존재 여부와 문자 수, trace anchor 대응을 먼저 검증한다.

### 4. 기존 ORDER_100 item 유지

기존 `trace_evidence` item과 `previous_turn_capsule_index` item은 유지한다.

ORDER_101은 alignment item을 추가하는 작업이지 ORDER_100 item을 대체하는 작업이 아니다.

## 이번 발주의 비범위

관련성 판단/선택 로직은 이번 ORDER_101에서 구현하지 않는다.

이 제한은 ORDER_101의 구현 범위를 좁히기 위한 일시적 경계다.
송련이 장기적으로 관련성 판단을 하면 안 된다는 뜻이 아니다.

따라서 prompt, schema, runtime policy에 다음 같은 영구 규칙을 추가하지 않는다.

```text
너는 이전 턴과 현재 입력의 관련성을 판단하지 마라.
송련은 최근 턴 관련성 판단을 하지 않는다.
```

향후 별도 발주에서 LLM selector가 최근 턴 alignment를 보고 관련 capsule을 선택할 수 있다.
그때 선택 이유는 상대정보 또는 혼합정보로 기록하고, source ids를 붙인다.

## 기억 요약 비범위

기억 요약은 이번 발주의 비범위다.

기억 요약은 단순히 0에 함수 하나를 추가하는 문제가 아니다.
요약 주체, source id, 정보 등급, node_4 승인, 반려 경로, 저장 위치, 최근 원문 window와 오래된 요약 window의 배치 정책을 함께 정해야 한다.

따라서 다음 작업은 이번 발주에서 하지 않는다.

```text
이전 턴 의미 요약
요약 후보 생성
node_4 요약 승인
승인된 요약 저장
최근 원문 + 오래된 요약 계층 배치
episode/project 계층 capsule
```

이 작업들은 충분히 숙고한 뒤 별도 발주에서 다룬다.

## 금지

- 관련성 선택을 구현하지 않는다.
- 키워드 매칭, 문자열 겹침, 유사도 점수 같은 휴리스틱 선택을 넣지 않는다.
- 원문 대화를 요약하지 않는다.
- 사용자 의도, 감정, 목표를 0이 추론하지 않는다.
- 외부 DB를 만들지 않는다.
- 벡터 DB를 만들지 않는다.
- 장기기억 그래프를 만들지 않는다.
- scheduler를 열지 않는다.
- W/R loop를 열지 않는다.
- 없는 trace ID나 turn_id를 지어내지 않는다.

## 감사/수정 후보 파일

```text
songryeon_core/core/schemas.py
songryeon_core/nodes/node_0_memory_supplier.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/user_turn.py
songryeon_core/runtime/smoke_test.py
songryeon_core/state/zero_state.py
songryeon_core/state/capsule_persistence.py
```

## Smoke-test 요구

가능하면 다음 검사를 추가한다.

```text
1. recent_raw_conversation 9턴과 previous_turn_capsules 9턴을 주입하면 최근 8턴만 alignment item이 된다.

2. alignment item의 item_type은 recent_raw_conversation_capsule_alignment다.

3. alignment는 turn_id가 같은 raw conversation과 capsule만 연결한다.

4. turn_id가 맞지 않는 raw conversation 또는 capsule은 휴리스틱으로 억지 연결하지 않는다.

5. 각 item은 COPIED_FIELDS로 시작한다.

6. 각 item에는 turn_id, raw_user_text_present, raw_assistant_text_present, raw_user_text_chars, raw_assistant_text_chars, capsule_trace_count, capsule_movement_count, user_input_trace_id, final_response_trace_id가 있다.

7. source_trace_ids는 실제 capsule.trace_event_ids 안에 있는 anchor trace ID만 담는다.

8. source_data_ids는 []다.

9. llm_semantic_summary_status=not_run 이다.

10. 기존 trace_evidence item과 previous_turn_capsule_index item이 유지된다.
```

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- `recent_raw_conversation` entry의 실제 현재 모양.
- raw conversation과 capsule을 어떤 절대 기준으로 대응시켰는지.
- 대응되지 않은 raw/capsule이 있을 때 어떻게 처리했는지.
- alignment item의 정확한 `COPIED_FIELDS` 형식.
- 관련성 판단/선택을 이번 발주에서 구현하지 않았음을 어떻게 보장했는지.
- 기억 요약을 이번 발주에서 열지 않았음을 어떻게 보장했는지.
- compileall / smoke-test 결과.

## 다음 발주 후보

ORDER_101 이후에 검토할 수 있는 후보는 다음이다.

```text
RECENT_CAPSULE_LLM_SELECTOR_V0
```

이 후보는 최근 턴 alignment를 보고 LLM이 관련 capsule을 선택하는 작업이다.
선택 이유는 상대정보 또는 혼합정보로 기록하고, source turn/trace/data/memory item ids를 붙인다.

단, 이 selector 후보는 ORDER_101 완료 뒤 별도 결재와 새 번호를 받아야 한다.
ORDER_102 번호는 이후 `Relative Info Direct-Field Smoke v0`에 사용되었으므로, 이 selector 후보는 후속 번호로 재발주한다.
