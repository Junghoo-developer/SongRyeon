# ORDER 101 Recent Raw Conversation Capsule Alignment - 2026-06-26-001

## Source Order

- `ORDER_101_RECENT_RAW_CONVERSATION_CAPSULE_ALIGNMENT_V0`

## Current Raw Conversation Entry Shape

현재 코드에서 `ZeroState.recent_raw_conversation`은 다음 스키마 필드로만 존재했다.

```text
recent_raw_conversation: list[dict[str, str]]
```

런타임에서 이 목록을 생성하거나 소비하는 기존 배선은 없었다.
이번 MVP에서는 `run_dry_turn()`에 주입 가능한 `recent_raw_conversation` 입력을 연결하고, raw entry의 최소 필드 모양을 다음처럼 정했다.

```text
turn_id=...
user_text=...
assistant_text=...
```

호환을 위해 raw text 필드는 다음 고정 alias만 원문 그대로 읽는다.

```text
user: raw_user_text, user_text, user_input, user
assistant: raw_assistant_text, assistant_text, final_response, assistant
```

`turn_id`는 `turn_id` 필드만 인정한다.
순서, 문자열 유사도, 키워드 겹침으로 `turn_id`를 추정하지 않는다.

## Implemented Scope

0 기억공급관의 `pre_route_report` memory packet에 최근 raw conversation과 `TurnStateCapsule`의 대응 좌표 item을 추가했다.

읽기 창은 코드 상수로 고정했다.

```text
RECENT_RAW_CONVERSATION_ALIGNMENT_WINDOW=8
```

이 값은 장기기억 크기가 아니라 이번 턴의 `pre_route_report` packet에 복사할 최근 raw-capsule 대응 후보 창이다.

## Alignment Rule

대응 기준은 하나뿐이다.

```text
recent_raw_conversation entry.turn_id == TurnStateCapsule.turn_id
```

대응되지 않은 raw entry는 item을 만들지 않는다.
대응되지 않은 capsule도 item을 만들지 않는다.
순서상 가까운 항목을 붙이거나 텍스트 유사도로 보정하지 않는다.

## MemoryItem Format

추가 item은 다음 형식을 따른다.

```text
item_type=recent_raw_conversation_capsule_alignment
text=COPIED_FIELDS:turn_id=...;raw_user_text_present=...;raw_assistant_text_present=...;raw_user_text_chars=...;raw_assistant_text_chars=...;capsule_trace_count=...;capsule_movement_count=...;user_input_trace_id=...;final_response_trace_id=...
source_trace_ids=[actual user_input_trace_id, actual final_response_trace_id]
source_data_ids=[]
```

`source_trace_ids`는 해당 trace ID가 capsule의 `trace_event_ids`에 실제로 있을 때만 넣는다.
없는 trace ID는 만들지 않는다.
raw text 원문은 이번 item text에 복사하지 않고, 존재 여부와 문자 수만 복사했다.

기존 `trace_evidence` item과 `previous_turn_capsule_index` item은 `pre_route_report`에 유지된다.

## Non-Scope Guard

관련성 판단/선택은 구현하지 않았다.

- `turn_id` 일치만 사용한다.
- 키워드 매칭, 문자열 겹침, 유사도 점수, 순서 기반 fallback을 추가하지 않았다.
- 새 selector, prompt, policy 문구를 추가하지 않았다.

기억 요약도 구현하지 않았다.

- raw text를 의미 요약으로 바꾸지 않았다.
- `MemoryPacketPayload.llm_semantic_summary_status`는 계속 `not_run`이다.
- node_4 승인, 장기기억 저장, 외부 DB, 벡터 DB, 그래프 DB, scheduler, W/R loop를 열지 않았다.

## Changed Files

- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/05_Execution_Records/order_101_recent_raw_conversation_capsule_alignment_2026_06_26_001.md`

## Smoke Coverage

새 smoke는 다음을 확인한다.

- recent raw conversation 9턴과 previous turn capsule 9턴을 주입하면 최근 8턴만 alignment item이 된다.
- alignment item의 `item_type`은 `recent_raw_conversation_capsule_alignment`다.
- alignment는 `turn_id`가 같은 raw conversation과 capsule만 연결한다.
- `turn_id`가 맞지 않는 raw conversation 또는 capsule은 억지 연결하지 않는다.
- 각 item은 `COPIED_FIELDS`로 시작한다.
- 각 item에는 `turn_id`, `raw_user_text_present`, `raw_assistant_text_present`, `raw_user_text_chars`, `raw_assistant_text_chars`, `capsule_trace_count`, `capsule_movement_count`, `user_input_trace_id`, `final_response_trace_id`가 있다.
- `source_trace_ids`는 실제 capsule.trace_event_ids 안에 있는 anchor trace ID만 담는다.
- `source_data_ids=[]`다.
- `llm_semantic_summary_status=not_run`이다.
- 기존 `trace_evidence` item과 `previous_turn_capsule_index` item이 유지된다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

Result: passed.

```powershell
python main.py smoke-test
```

Result: passed. `SMOKE_TEST_OK`.

Observed ORDER_101 smoke fields:

```text
recent_raw_conversation_alignment_window=8
recent_raw_conversation_alignment_count=8
recent_raw_conversation_alignment_item_type=recent_raw_conversation_capsule_alignment
recent_raw_conversation_alignment_skips_mismatch=True
recent_raw_conversation_alignment_llm_summary_status=not_run
```
