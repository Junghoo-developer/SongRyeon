# ORDER 108: Qwen Chat Session ZeroState Continuity v0

## 상태

구현됨.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_108_qwen_chat_session_zero_state_continuity_2026_06_26_001.md`

현재 코드 기준:

- `main.py`의 `qwen-chat`은 세션 안 raw conversation과 `TurnStateCapsule`을 다음 턴의 `ZeroState`로 다시 주입한다.
- `songryeon_core/runtime/chat_session.py`가 qwen-chat 세션 상태 저장/스냅샷 생성을 담당한다.
- `run_qwen_user_turn()` / `run_fake_user_turn()` / `run_dry_turn()`은 외부 `turn_id`, `previous_turn_capsules`, `recent_raw_conversation`을 받을 수 있다.
- `python main.py smoke-test`의 `qwen_chat_continuity_*`, `qwen_chat_loop_*` 확인값으로 기준선이 검증된다.

아래 본문은 구현 전 발주 내용이며, 현재는 구현 기준선 설명으로 보존한다.

## 배경

현재 `qwen-turn`은 단일 턴 실행에 가깝다.

`qwen-chat`은 여러 입력을 반복해서 받지만, 현재 구조에서는 각 입력마다 `run_qwen_user_turn()`을 새로 호출한다.
따라서 "아까 말한 것" 같은 직전 대화 참조가 약하다.

이미 다음 구조는 있다.

```text
ZeroState.recent_raw_conversation
ZeroState.previous_turn_capsules
TurnStateCapsule
ORDER_101 raw conversation-capsule alignment
ORDER_103 MemoryRelevanceCandidateFrame
ORDER_104 MemoryRelevanceSelectionFrame
ORDER_105 memory selection handoff
ORDER_107 raw memory compression candidate policy
```

하지만 qwen-chat 세션이 이 구조를 다음 턴에 다시 주입하지 않으면, 0은 실제 이전 턴 기억을 읽을 수 없다.

## 목표

`qwen-chat` 세션 안에서 이전 턴의 raw conversation과 TurnStateCapsule을 이어서 다음 턴의 `ZeroState`로 공급한다.

핵심 문장:

```text
qwen-chat은 같은 세션 안에서 이전 턴 raw/capsule을 다음 턴의 0에게 다시 넘긴다.
```

이번 발주는 선택된 기억 내용을 node_3가 말하게 만드는 작업이 아니다.
이번 발주는 node_5 압축기나 node_4 기억 요약 승인도 아니다.

## 구현 범위

### 1. run_dry_turn 외부 turn_id 주입

현재 기본 턴 ID가 고정되어 있으면 여러 턴 세션에서 trace/capsule 구분이 약해진다.

`run_dry_turn()`에 선택적 `turn_id` 인자를 추가한다.

기본값:

```text
turn_id=None
```

동작:

```text
turn_id is None -> 기존 DEFAULT_TURN_ID 사용
turn_id is not None -> 호출자가 준 turn_id 사용
```

기존 `dry-run`, `fake-turn`, `qwen-turn` 단발 실행은 깨지면 안 된다.

### 2. run_qwen_user_turn / run_fake_user_turn에 ZeroState 입력 추가

다음 optional 인자를 추가한다.

```text
turn_id: str | None = None
previous_turn_capsules: list[TurnStateCapsule] | None = None
recent_raw_conversation: list[dict[str, str]] | None = None
```

이 인자는 그대로 `run_dry_turn()`에 전달한다.

주의:

- 단발 `qwen-turn` 기본값은 여전히 stateless다.
- 명시적으로 넘긴 경우에만 이전 기억을 본다.

### 3. result에 capsule 반환 또는 capsule payload 보존

qwen-chat이 다음 턴에 capsule을 이어주려면, 현재 턴 끝에서 만든 `TurnStateCapsule`을 꺼낼 수 있어야 한다.

방법 후보:

```text
result["turn_capsule"] = asdict(capsule)
```

또는 더 명시적으로:

```text
result["zero_state_after_turn"] = {
  "previous_turn_capsules": [...],
  "recent_raw_conversation": [...]
}
```

권장:

```text
result["turn_capsule"] = asdict(capsule)
```

이유:

- qwen-chat 세션이 자신의 세션 상태를 관리하기 쉽다.
- run_dry_turn 내부 ZeroState 전체를 외부에 그대로 노출하지 않아도 된다.

### 4. qwen-chat 세션 상태 추가

`main.py`의 `_run_qwen_chat()` 안에서 세션 상태를 둔다.

후보:

```text
session_recent_raw_conversation: list[dict[str, str]] = []
session_previous_turn_capsules: list[TurnStateCapsule] = []
```

매 턴 실행 전:

```text
run_qwen_user_turn(
  turn_id=f"turn_chat_{turn_index:04d}",
  recent_raw_conversation=session_recent_raw_conversation,
  previous_turn_capsules=session_previous_turn_capsules,
  ...
)
```

매 턴 실행 후:

```text
session_recent_raw_conversation.append({
  "turn_id": current_turn_id,
  "user_text": user_input,
  "assistant_text": final_answer_text,
})
session_previous_turn_capsules.append(TurnStateCapsule(**result["turn_capsule"]))
```

raw conversation window는 ORDER_107 정책을 기준으로 보되, 이번 발주에서는 파괴적으로 삭제하지 않는다.

### 5. 최종 답변 원문 기준

`assistant_text`에는 node_4를 통과한 최종 사용자-facing answer를 넣는다.

주의:

- runtime debug 전체를 넣지 않는다.
- raw internal ID 목록을 넣지 않는다.
- node_4가 `needs_revision` 또는 `failed`이면 safe blocking answer를 넣는다.

가능하면 `render_chat_answer(result, user_input=...)`를 재사용한다.

### 6. terminal/runtime 표시

qwen-chat pretty output 또는 summary에 세션 기억 상태를 표시한다.

예시:

```text
session_memory:
- recent_raw_conversation=1
- previous_turn_capsules=1
- current_turn_id=turn_chat_0002
```

runtime view에서 다음도 보이면 좋다.

```text
0 기억 공급:
previous_turn_capsule_index N개
recent_raw_conversation_capsule_alignment N개
recent_memory_relevance_candidate N개
```

## 메타정보 분류

코드가 확정하는 것:

- 세션에 raw conversation entry가 몇 개 있는지
- 각 entry의 `turn_id`
- 각 entry의 user/assistant text 존재 여부
- 각 capsule의 trace id와 movement count
- 다음 턴에 어떤 `ZeroState`가 전달되었는지

이것은 절대정보다.

코드가 하지 않는 것:

- 이전 턴이 현재 입력과 관련 있는지 판단
- 이전 답변을 요약
- 사용자 의도/감정/목표 해석

관련성 판단은 ORDER_104 selector가 담당한다.

## 비범위

이번 발주에서 하지 말 것:

```text
선택된 기억 내용을 node_3 답변 본문에 삽입
node_5 기억 압축기 구현
node_4 기억 요약 승인 구현
장기기억 DB
vector DB
memory graph
raw 원문 삭제
scheduler/background memory
관련성 heuristic fallback
```

## 감사/수정 후보 파일

```text
main.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/user_turn.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
songryeon_core/core/schemas.py
```

## Smoke-test 요구

### 1. run_dry_turn accepts external zero state smoke

fixture:

- previous_turn_capsules 1개
- recent_raw_conversation 1개
- turn_id=`turn_test_0002`

검증:

```text
result.turn_id == turn_test_0002
recent_capsules_read_count == 1
recent_raw_conversation_alignment_count == 1
recent_memory_relevance_candidate_count == 1
turn_capsule.turn_id == turn_test_0002
```

### 2. qwen-chat style two turn session smoke

fake adapter로 qwen-chat 세션 흐름을 함수 단위로 재현한다.

1턴:

```text
user_input="내 테스트 암호는 파란노트야."
```

2턴:

```text
user_input="방금 내가 말한 테스트 암호 관련 기억 후보가 있나?"
```

검증:

```text
2턴 result.previous_turn_capsule_index count >= 1
2턴 result.recent_raw_conversation_alignment_count >= 1
2턴 result.recent_memory_relevance_candidate_count >= 1
2턴 turn_id != 1턴 turn_id
```

### 3. stateless qwen-turn remains stateless smoke

단발 `qwen-turn` 또는 `run_qwen_user_turn()` 기본 호출은 이전 턴을 자동으로 가지면 안 된다.

검증:

```text
previous_turn_capsule_index count == 0
recent_raw_conversation_alignment_count == 0
```

### 4. no semantic memory creation smoke

검증:

```text
llm_semantic_summary_status=not_run
0은 raw text를 요약하지 않음
selector 외 관련성 판단 없음
```

## 수동 확인 시나리오

ORDER_108만 구현된 상태에서는 아직 node_3가 이전 턴 내용을 답변에 적극 사용하지 않을 수 있다.

그래도 다음은 확인 가능해야 한다.

```powershell
python main.py qwen-chat --live-trace
```

1턴:

```text
내 테스트 암호는 파란노트야.
```

2턴:

```text
방금 내가 말한 테스트 암호 관련 기억 후보가 있나?
```

기대:

```text
0이 previous_turn_capsule_index와 recent_raw_conversation_capsule_alignment를 만든다.
memory relevance candidate가 생성된다.
selector가 실행될 수 있다.
```

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- qwen-chat 세션 상태를 어디서 유지하는지
- run_dry_turn/user_turn 인자 변경 내용
- turn_id가 어떻게 고유해졌는지
- raw conversation과 capsule이 다음 턴에 어떻게 다시 들어가는지
- 단발 qwen-turn 기본 동작이 stateless로 유지되는지
- smoke-test 결과

## 다음 발주

ORDER_108 이후 다음은 ORDER_109다.

ORDER_109는 selector가 고른 최근 원문 내용을 node_3 brief에 제한적으로 복사하여, 최종 답변에서 실제 대화 맥락을 말할 수 있게 하는 발주다.
