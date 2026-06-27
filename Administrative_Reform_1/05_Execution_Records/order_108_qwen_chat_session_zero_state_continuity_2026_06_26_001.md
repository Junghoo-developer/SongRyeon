# ORDER_108 qwen-chat session ZeroState continuity execution record

## 대상

- `Administrative_Reform_1/04_Orders/ORDER_108_QWEN_CHAT_SESSION_ZERO_STATE_CONTINUITY_V0.md`

## 구현 상태

구현됨.

## 핵심 변경

`main.py`

- `qwen-chat`이 턴마다 `turn_chat_0001`, `turn_chat_0002` 형식의 turn id를 사용한다.
- 같은 qwen-chat 세션 안에서 이전 턴 raw conversation과 `TurnStateCapsule`을 다음 턴의 `ZeroState` 입력으로 넘긴다.

`songryeon_core/runtime/chat_session.py`

- `ChatSessionMemory` 추가.
- `current_chat_turn_id()` 추가.
- `attach_chat_session_snapshot()` 추가.
- `store_chat_turn_result()` 추가.
- `turn_capsule_from_result()` 추가.

`songryeon_core/runtime/user_turn.py`

- `run_qwen_user_turn()` / `run_fake_user_turn()`이 외부 `turn_id`, `previous_turn_capsules`, `recent_raw_conversation`을 받을 수 있다.

`songryeon_core/runtime/dry_run.py`

- `run_dry_turn()`이 외부 `turn_id`, `previous_turn_capsules`, `recent_raw_conversation`을 받아 0 memory supply에 연결한다.

## Smoke 기준선

`python main.py smoke-test`에서 다음 확인값을 본다.

```text
qwen_chat_continuity_external_turn_id=turn_test_0002
qwen_chat_continuity_two_turn_alignment=1
qwen_chat_continuity_stateless_default=true
qwen_chat_continuity_no_semantic_memory=true
qwen_chat_loop_snapshot_raw_count=1
qwen_chat_loop_after_store_raw_count=2
qwen_chat_loop_after_store_capsule_count=2
```

## 범위 밖

- 장기기억 DB
- 기억 요약
- node_5 compression 실행
- node_4 기억 요약 승인
- 외부 DB/벡터 DB/그래프 DB
