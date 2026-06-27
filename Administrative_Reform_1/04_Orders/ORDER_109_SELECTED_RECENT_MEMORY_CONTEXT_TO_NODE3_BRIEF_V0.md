# ORDER 109: Selected Recent Memory Context To Node3 Brief v0

## 상태

구현됨.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_109_selected_recent_memory_context_to_node3_brief_2026_06_26_001.md`

현재 코드 기준:

- `songryeon_core/nodes/node_2_handoff.py`가 selector가 고른 최근 기억 후보의 raw conversation을 요약 없이 복사해 `SelectedRecentMemoryContextFrame`으로 저장한다.
- `Node3InputBriefFrame.selected_recent_memory_contexts`가 node_3 brief에 선택된 원문 context를 전달한다.
- node_3 LLM은 전달된 raw user/assistant text 범위 안에서만 이전 대화 내용을 말할 수 있다.
- `python main.py smoke-test`의 `selected_recent_memory_context_*`, `memory_selection_node3_selected_count`, `qwen_chat_loop_*` 확인값으로 기준선이 검증된다.

아래 본문은 구현 전 발주 내용이며, 현재는 구현 기준선 설명으로 보존한다.

## 배경

ORDER_104는 LLM selector가 최근 기억 후보 중 관련 있어 보이는 후보를 선택하게 한다.
ORDER_105는 그 selection result를 node_2와 node_3에게 mixed 판단으로 전달한다.
ORDER_108은 qwen-chat 세션에서 실제 이전 턴 raw/capsule을 다음 턴으로 이어준다.

그러나 여기까지 와도 node_3는 아직 선택된 과거 턴의 실제 대화 내용을 충분히 받지 못할 수 있다.

즉 현재 구조는 다음까지 가능하다.

```text
이전 턴 후보가 있다.
LLM selector가 어떤 후보를 골랐다.
그 선택 판단의 source와 info_class를 보존했다.
```

아직 부족한 것:

```text
선택된 과거 턴의 사용자 입력/최종 응답 원문을 node_3가 안전하게 본다.
node_3가 그 원문 범위 안에서 "아까 네가 말한 것"을 답한다.
```

## 목표

selector가 고른 최근 memory candidate의 raw conversation 원문을 code가 복사해서 node_3 input brief에 넣는다.

핵심 문장:

```text
code는 선택된 과거 턴 원문을 요약하지 않고 복사만 하며, node_3는 그 복사본 범위 안에서 답한다.
```

## 구현 범위

### 1. SelectedRecentMemoryContextFrame 추가

새 schema를 추가한다.

후보 이름:

```text
SelectedRecentMemoryContextFrame
```

후보 필드:

```text
frame_id
turn_id
selection_frame_id
selection_status
selected_turn_count
items
generated_by
info_class
semantic_judgement_status
source_data_ids
source_trace_ids
```

`items` 후보 구조:

```text
SelectedRecentMemoryContextItem
```

필드:

```text
item_id
source_turn_id
source_candidate_frame_id
source_memory_item_id
raw_user_text
raw_assistant_text
raw_user_text_chars
raw_assistant_text_chars
raw_user_text_truncated
raw_assistant_text_truncated
copied_from
selection_reason_source_data_id
selection_info_class
source_trace_ids
source_data_ids
```

기본 메타정보:

```text
generated_by=CODE:SELECTED_RECENT_MEMORY_CONTEXT_BUILDER
info_class=absolute_copied_context
semantic_judgement_status=not_run
```

주의:

- raw text 복사는 절대정보다.
- 이 raw text가 현재 입력과 관련 있다는 판단은 selector의 mixed 정보다.
- frame은 둘을 섞어 의미 요약으로 만들지 않는다.

### 2. source 기준

선택된 candidate는 다음 순서로 원문 source를 찾는다.

```text
MemoryRelevanceSelectionFrame.selected_candidate_frame_ids
-> MemoryRelevanceCandidateFrame.source_memory_item_id
-> recent_raw_conversation_capsule_alignment item
-> ZeroState.recent_raw_conversation turn_id
```

단, 문자열 유사도 fallback은 금지한다.

허용 기준:

```text
selected_candidate_turn_ids 또는 candidate_frame.candidate_turn_id
== raw_conversation entry.turn_id
```

일치하지 않으면 해당 item은 만들지 않는다.
그리고 누락 count를 절대정보로 기록한다.

### 3. 원문 길이 제한과 truncation 표시

node_3 brief가 너무 커지지 않도록 per item 길이 제한을 둔다.

후보 상수:

```text
SELECTED_MEMORY_RAW_USER_TEXT_MAX_CHARS = 800
SELECTED_MEMORY_RAW_ASSISTANT_TEXT_MAX_CHARS = 1200
SELECTED_MEMORY_MAX_ITEMS = 3
```

code가 할 수 있는 일:

- 원문 복사
- 길이 제한
- `truncated=true|false` 표시
- `copied_from` 표시

code가 하면 안 되는 일:

- 원문 요약
- 원문 의미 해석
- 관련성 이유 새로 쓰기

### 4. node_2 handoff 연결

`Node2HandoffFrame` 또는 node_2 input source에 `SelectedRecentMemoryContextFrame` id를 포함한다.

후보 필드:

```text
selected_recent_memory_context_frame_id
selected_recent_memory_context_count
selected_recent_memory_context_generated_by
selected_recent_memory_context_info_class
```

### 5. Node3InputBriefFrame에 selected memory context 추가

`Node3InputBriefFrame`에 다음 구조를 추가한다.

후보:

```text
selected_recent_memory_contexts: list[Node3SelectedRecentMemoryContext]
```

brief에 넣을 내용:

```text
source_turn_id
raw_user_text
raw_assistant_text
truncated flags
selection_status
selection_info_class
selection_reason
selection_reason_generated_by
```

주의:

- node_3 prompt에 "이것은 selector가 고른 이전 턴 복사본이다"라고 명시한다.
- node_3가 원문에 없는 과거 발화를 만들어내면 안 된다고 명시한다.
- raw internal id를 최종 사용자 답변에 직접 노출하지 않게 한다.

### 6. node_3 prompt 보강

`node_3_reporter_v0.md`에 다음 경계를 추가한다.

요지:

```text
선택된 최근 기억 context가 제공되면, 그 안의 raw_user_text/raw_assistant_text 범위에서만 이전 대화를 언급한다.
관련성 판단은 selector의 mixed 판단이며 code fact가 아니다.
truncated=true인 원문은 전체 대화라고 단정하지 않는다.
source id, frame id, internal id를 사용자에게 노출하지 않는다.
```

### 7. terminal/runtime 표시

runtime view에 다음을 표시한다.

예시:

```text
selected_recent_memory_context:
- status=selected / copied=1 / missing=0 / generated_by=CODE:...
```

본문 원문 전체는 runtime debug에도 과하게 뿌리지 않는다.
짧은 char count와 turn count 중심으로 표시한다.

## 메타정보 분류

절대정보:

- selected item count
- selected turn id
- raw text copied from ZeroState entry
- char count
- truncation 여부
- source trace/data id

혼합정보:

- selector가 "이 기억이 관련 있다"고 판단한 이유
- node_3가 현재 입력과 과거 원문을 함께 보고 쓰는 최종 답변

코드는 의미 판단을 새로 만들지 않는다.

## 비범위

이번 발주에서 하지 말 것:

```text
node_5 기억 압축기 구현
오래된 4턴 요약
node_4 기억 요약 승인
장기기억 DB
vector DB
memory graph
raw memory 삭제
선택되지 않은 과거 턴 원문을 node_3에 대량 주입
관련성 heuristic fallback
```

## 감사/수정 후보 파일

```text
songryeon_core/core/schemas.py
songryeon_core/nodes/node_2_handoff.py
songryeon_core/nodes/node_2_metainfo_boundary.py
songryeon_core/prompts/node_3_reporter_v0.md
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
```

## Smoke-test 요구

### 1. selected context copied smoke

fixture:

- recent_raw_conversation 2턴
- candidate frame 2개
- selector가 1개 선택

검증:

```text
SelectedRecentMemoryContextFrame.selected_turn_count=1
items length=1
raw_user_text가 원문과 일치
raw_assistant_text가 원문과 일치
generated_by=CODE:SELECTED_RECENT_MEMORY_CONTEXT_BUILDER
semantic_judgement_status=not_run
```

### 2. no selected means no copied context smoke

selection_status가 `none_selected` 또는 `failed`이면:

```text
selected_turn_count=0
items=[]
node_3 brief selected_recent_memory_contexts=[]
```

### 3. missing raw source smoke

selector가 고른 turn_id가 raw conversation에 없으면:

```text
context item 생성하지 않음
missing_selected_memory_context_count > 0
code fallback으로 비슷한 문자열을 찾지 않음
```

### 4. truncation smoke

긴 raw text를 넣는다.

검증:

```text
raw_user_text_chars는 원본 길이
raw_user_text_truncated=true
brief text는 max chars 이하
copied_from 존재
```

### 5. node3 can answer selected memory smoke

fake adapter 또는 prompt fixture로 다음을 검증한다.

입력:

```text
이전 턴 user_text="내 테스트 암호는 파란노트야."
현재 입력="방금 내가 말한 테스트 암호가 뭐였지?"
```

기대:

```text
node_3 brief에 "파란노트"가 selected_recent_memory_context로 들어감
final answer가 node_4 통과
raw internal id가 사용자 답변에 노출되지 않음
```

## 수동 확인 시나리오

```powershell
python main.py qwen-chat --live-trace
```

1턴:

```text
내 테스트 암호는 파란노트야.
```

2턴:

```text
방금 내가 말한 테스트 암호가 뭐였지?
```

기대:

```text
0이 이전 턴 raw/capsule을 공급한다.
selector가 이전 턴을 선택한다.
node_3 brief가 selected recent memory context를 받는다.
node_3가 "파란노트"를 말할 수 있다.
node_4가 통과 또는 근거 부족 반려를 낸다.
```

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- selected recent memory context frame을 어디서 만드는지
- raw text source와 copied_from 기준
- truncation 정책
- none_selected/failed/missing source 처리
- node_3 brief에 어떤 필드가 들어가는지
- node_4 gate 결과
- smoke-test 결과

## 다음 발주

ORDER_109 이후 다음은 ORDER_110이다.

ORDER_110은 node_3가 이전 대화를 말할 수 있게 된 뒤, node_4가 그 발화를 검수하는 guard를 강화하는 발주다.
