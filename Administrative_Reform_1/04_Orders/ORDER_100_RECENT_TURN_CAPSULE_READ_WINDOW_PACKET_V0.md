# ORDER 100: Recent Turn Capsule Read Window Packet v0

## 상태

구현 및 검증 완료.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_100_recent_turn_capsule_read_window_2026_06_25_001.md`

## 목표

장기기억 DB를 만들기 전에, 0 기억공급관이 최근 N턴 `TurnStateCapsule`을 읽고 그 좌표를 `memory_packet`에 안전하게 넣는 최소 MVP다.

이번 발주는 장기기억 구현이 아니다.
0이 이전 턴의 의미를 요약하거나 해석하지 않고, 다음 노드가 원본 trace를 다시 찾아갈 수 있는 색인 좌표만 공급한다.

## 현재 코드 사실

- `TraceStore`는 실제 사건 로그 원본이다.
- `DataStore`는 사건이 만든 payload 원본 저장소다.
- `TurnStateCapsule`은 한 턴의 trace/event/movement를 다시 찾기 위한 색인 카드다.
- `ZeroState.previous_turn_capsules` 구조는 이미 있다.
- 기존 `supply_memory()`는 주로 현재 턴 trace를 공급했다.
- `memory_packet`은 다음 노드에게 주는 출처 달린 근거 봉투다.
- `record_memory_packet()`은 이미 `MemoryItem` 목록을 받을 수 있다.

## 문제

현재 0 기억공급은 안전하지만 약하다.
trace 좌표는 남지만, 다음 노드나 LLM이 바로 확인할 수 있는 구조화 memory item이 부족하다.

하지만 바로 “이전 기억 회상”이나 장기 DB로 가면 0이 의미 판단을 생성하는 것처럼 보일 위험이 있다.
따라서 첫 MVP는 이전 턴 의미 요약이 아니라 capsule index 공급까지만 한다.

## 구현 범위

### 1. Read Window

최근 capsule read window는 3턴으로 고정한다.

```text
RECENT_TURN_CAPSULE_READ_WINDOW=3
```

`ZeroState.previous_turn_capsules`의 최근 3개만 읽는다.

### 2. 적용 mode

첫 적용 대상은 `pre_route_report` memory packet이다.

다른 mode로 확장하지 않는다.

### 3. MemoryItem 형식

각 capsule에 대해 다음 item을 만든다.

```text
item_type=previous_turn_capsule_index
text=COPIED_FIELDS:turn_id=...;trace_count=...;movement_count=...;user_input_trace_id=...;final_response_trace_id=...
source_trace_ids=[실제로 존재하는 user_input_trace_id, final_response_trace_id]
source_data_ids=[]
```

`source_trace_ids`에는 해당 trace ID가 capsule의 `trace_event_ids`에 실제로 있을 때만 넣는다.
없는 trace ID를 지어내지 않는다.

### 4. 기존 item 유지

기존 `trace_evidence` memory item은 유지한다.

## 금지

- 이전 턴 내용을 요약하지 않는다.
- 사용자 의도, 감정, 목표 같은 의미 판단을 하지 않는다.
- 원본 trace/data를 삭제하거나 변형하지 않는다.
- 외부 DB를 만들지 않는다.
- 벡터 DB를 만들지 않는다.
- 장기기억 그래프를 만들지 않는다.
- scheduler를 열지 않는다.
- W/R loop를 열지 않는다.
- 없는 trace ID를 지어내지 않는다.

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

smoke-test는 최소한 다음을 확인한다.

```text
recent_capsule_read_window=3
recent_capsules_read_count=3
memory_packet.memory_items includes previous_turn_capsule_index
previous_turn_capsule_index only copies turn_id, trace_count, movement_count, user_input_trace_id, final_response_trace_id
source_trace_ids use only actual capsule trace IDs
source_data_ids=[]
llm_semantic_summary_status=not_run
existing trace_evidence item remains
```

## 다음 발주 후보

이번 발주는 이전 턴 의미 요약을 하지 않는다.

다음 발주에서 검토할 수 있는 것은 다음 정도다.

```text
recent capsule index를 node_1 또는 node_3가 어떻게 읽는지
이전 턴 원문 trace/data를 실제로 재조회하는 도구 경계
LLM이 이전 턴을 요약할 경우 generated_by/info_class/source ids 표시 방식
```
