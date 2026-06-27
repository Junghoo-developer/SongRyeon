# ORDER 108-110 Memory Context Order Drafts 2026-06-26 001

## 요청

사용자가 다른 채팅방의 ORDER_107 구현을 기다리는 동안, 그 다음 기억 맥락 발주서를 모두 작성해 달라고 요청했다.

## 작성한 발주서

### ORDER_108

파일:

- `Administrative_Reform_1/04_Orders/ORDER_108_QWEN_CHAT_SESSION_ZERO_STATE_CONTINUITY_V0.md`

목표:

```text
qwen-chat 세션 안에서 recent_raw_conversation과 previous_turn_capsules를 다음 턴 ZeroState로 이어준다.
```

### ORDER_109

파일:

- `Administrative_Reform_1/04_Orders/ORDER_109_SELECTED_RECENT_MEMORY_CONTEXT_TO_NODE3_BRIEF_V0.md`

목표:

```text
selector가 고른 최근 기억의 raw user/assistant text를 code가 요약 없이 복사해 node_3 brief에 넣는다.
```

### ORDER_110

파일:

- `Administrative_Reform_1/04_Orders/ORDER_110_NODE4_RECENT_MEMORY_UTTERANCE_GUARD_V0.md`

목표:

```text
node_3가 이전 대화를 말할 때 node_4가 selected recent memory context 범위를 벗어난 발화를 반려한다.
```

## 의도한 구현 순서

```text
ORDER_107
-> ORDER_108 qwen-chat 세션 ZeroState 연결
-> ORDER_109 선택된 최근 원문을 node_3 brief에 복사
-> ORDER_110 node_4 최근 기억 발화 검수
-> 이후 node_5 기억 압축기와 node_4 요약 승인
```

## 주의

이번 작업은 문서 작성만 수행했다.

코드 변경, compileall, smoke-test는 수행하지 않았다.
