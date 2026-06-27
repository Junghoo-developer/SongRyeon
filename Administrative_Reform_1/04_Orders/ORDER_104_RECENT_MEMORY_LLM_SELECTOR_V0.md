# ORDER 104: Recent Memory LLM Selector v0

## 상태

발주서 초안.

이 발주서는 ORDER_100~103 이후 다음 개발자를 위한 좁은 MVP 지시서다.
장기기억 DB를 만드는 발주가 아니다.

## 배경

최근 기억 공급 계열은 다음 단계까지 왔다.

- ORDER_100: 최근 3턴 `TurnStateCapsule`을 `previous_turn_capsule_index` memory item으로 공급했다.
- ORDER_101: 최근 8턴 raw conversation과 capsule을 `turn_id` 기준으로 대응해 `recent_raw_conversation_capsule_alignment` item으로 공급했다.
- ORDER_102: `relative_info` / `mixed_info` 직접 field 기준 smoke를 추가했다.
- ORDER_103: 최근 8턴 alignment를 `MemoryRelevanceCandidateFrame`으로 보존했다.

ORDER_103의 candidate frame은 아직 판단 결과가 아니다.

현재 상태:

```text
judgement_status=not_run
judged_by=None
relevance_label=None
relevance_reason=None
info_class=None
```

즉 0 기억공급관은 아직 관련성 판단을 하지 않는다.
0은 후보 좌표만 공급한다.

## 목표

ORDER_104의 목표는 최근 memory relevance candidate frame을 보고, LLM selector가 현재 턴과 관련 있어 보이는 과거 턴 후보를 선택하게 하는 최소 MVP다.

핵심 문장:

```text
0은 후보 좌표를 공급한다.
LLM selector가 관련성 판단을 한다.
code는 그 판단의 출처와 schema를 기록한다.
```

이번 발주의 핵심은 기억을 똑똑하게 만드는 것이 아니라, 기억 관련성 판단이 시작되는 지점을 정직하게 표시하는 것이다.

## 핵심 원칙

1. 0은 여전히 관련성 판단자가 아니다.
2. code는 관련성 판단을 하지 않는다.
3. LLM selector가 관련성 판단을 한다.
4. selector 판단은 절대정보가 아니다.
5. 판단 결과는 `generated_by`, `judged_by`, `llm_call_data_id`, `llm_trace_event_id`, `source_trace_ids`, `source_data_ids`, `source_memory_item_ids`로 출처를 드러낸다.
6. 휴리스틱 fallback을 넣지 않는다.
7. selector 실패 시 code가 몰래 대신 고르지 않는다.

## 메타정보 분류

이번 selector의 관련성 판단은 기본적으로 `mixed_info`에 가깝다.

이유:

```text
현재 사용자 입력
과거 raw conversation alignment
capsule trace anchor
MemoryRelevanceCandidateFrame
```

이 여러 source bundle을 함께 보고 "관련 있어 보인다"를 판단하기 때문이다.

따라서 기본 분류는 다음으로 둔다.

```text
info_class=mixed
source_mode=source_bundle
claim_alignment=multi_source_bundle
```

만약 구현 중 특정 하나의 record/field에 직접 대응하는 판단이 정말로 필요하면 `relative_info`를 검토할 수 있다.
하지만 code가 자동으로 분류를 몰래 바꾸지 말고, 명시적 schema/policy로만 둔다.

## 구현 후보 schema

새 frame 후보:

```text
MemoryRelevanceSelectionFrame
```

필드 후보:

```text
frame_id
turn_id
selector_target_node
current_user_input_trace_id
source_memory_packet_id
candidate_frame_ids
selected_candidate_turn_ids
selected_candidate_frame_ids
selection_status
selection_reason
judged_by
generated_by
llm_call_data_id
llm_trace_event_id
source_trace_ids
source_data_ids
source_memory_item_ids
info_class
source_mode
claim_alignment
schema_name
schema_version
```

허용 상태 후보:

```text
selection_status=selected | none_selected | failed
```

주의:

- `selection_reason`은 LLM 의미 판단이다.
- `selected_candidate_turn_ids`도 LLM 판단 결과다.
- code가 "관련 있는 후보"를 직접 고르면 안 된다.

## selector 입력

LLM selector 입력에는 최소한 다음을 포함한다.

```text
current user input
memory_packet:node_1:pre_route_report
relevance_candidate_frames
각 candidate의 source_memory_item_id
각 candidate의 candidate_turn_id
각 candidate의 source_trace_ids
가능하면 recent_raw_conversation_capsule_alignment item의 COPIED_FIELDS text
```

처음 MVP에서는 raw text 전문을 넣지 않고, ORDER_101 alignment item의 존재 여부/문자 수/trace anchor만 넣어도 된다.

단, 관련성 판단에 원문 일부가 필요하다고 판단되면 바로 구현하지 말고 먼저 보고하라.
그 경우 다음 중 어느 방식이 안전한지 설계 판단이 필요하다.

```text
1. raw_user_text / raw_assistant_text를 memory item에 COPIED_FIELDS로 추가
2. raw text를 별도 DataStore record로 저장하고 source_data_id로 참조
3. selector 입력에서만 임시로 raw text를 제공하되 저장 경계를 별도 기록
```

## 구현 방향

1. ORDER_103 코드와 schema를 읽는다.
2. `MemoryRelevanceCandidateFrame`이 어디에 저장되는지 확인한다.
3. `MemoryRelevanceSelectionFrame` schema를 추가한다.
4. LLM selector prompt를 추가한다.
5. fake adapter smoke부터 만든다.
6. dry_run에서는 실제 Qwen이 아니라 fake LLM selector로 최소 검증할 수 있게 한다.
7. selector 결과를 DataStore에 저장한다.
8. terminal/runtime 출력에 selector 실행 여부, 후보 수, 선택 수를 표시한다.
9. selector 실패 시 code fallback으로 후보를 고르지 않는다.

## selector 실패 정책

LLM selector가 실패하면 다음처럼 기록한다.

```text
selection_status=failed
selected_candidate_turn_ids=[]
selected_candidate_frame_ids=[]
selection_reason=CODE_STATUS:memory_relevance_selector_failed
```

이 실패 reason은 code status다.
실패 시 code가 대신 관련 후보를 고르지 않는다.

candidate frame이 없으면 LLM selector를 호출하지 않고 code status로 닫아도 된다.

```text
selection_status=none_selected
selection_reason=CODE_STATUS:no_memory_relevance_candidates
llm_call_data_id=None
```

이 경우 code가 "관련 후보 없음"이라고 판단하는 것이 아니라, "판단할 후보가 없음"이라는 절대 상태를 기록하는 것이다.

## 비범위

이번 발주에서 하지 말 것:

```text
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
현재 턴 답변 품질 개선을 위한 임의 memory injection
```

## smoke-test 요구

### 1. selected smoke

fixture:

- 현재 사용자 입력이 과거 turn 하나와 명확히 관련된 상황
- fake LLM selector가 candidate 1개를 선택

검증:

```text
selection_status=selected
selected_candidate_turn_ids length >= 1
selected_candidate_frame_ids length >= 1
judged_by is LLM
generated_by indicates LLM selector
llm_call_data_id exists
info_class=mixed
source_mode=source_bundle
claim_alignment=multi_source_bundle
source_memory_item_ids not empty
```

### 2. none_selected smoke

fake LLM selector가 아무 후보도 선택하지 않는 상황.

검증:

```text
selection_status=none_selected
selected_candidate_turn_ids=[]
selected_candidate_frame_ids=[]
judged_by is LLM
```

### 3. failed smoke

selector LLM parse 실패 또는 schema 실패 상황.

검증:

```text
selection_status=failed
selected_candidate_turn_ids=[]
selected_candidate_frame_ids=[]
selection_reason=CODE_STATUS:memory_relevance_selector_failed
code fallback selection does not happen
```

### 4. no candidates smoke

candidate frame이 없으면 LLM selector를 호출하지 않고 code status로 닫는다.

검증:

```text
selection_status=none_selected
selection_reason=CODE_STATUS:no_memory_relevance_candidates
llm_call_data_id=None
```

## 완료 조건

다음 명령을 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 반드시 다음을 적는다.

- selector frame이 어디에 저장되는지
- selector 입력 source가 무엇인지
- LLM이 판단하는 부분이 무엇인지
- code가 판단하지 않는 부분이 무엇인지
- selector 실패 시 fallback이 없음을 어떻게 보장했는지
- info_class를 왜 mixed로 두었는지
- smoke-test 결과
- 남은 위험

## 다음 단계 후보

ORDER_104 이후에야 다음을 논의할 수 있다.

```text
선택된 memory candidate를 node_1/router 입력에 어떻게 반영할지
선택된 memory candidate를 node_3 final report 입력에 어떻게 반영할지
관련성 판단을 node_4가 검토해야 하는지
최근 원문 window와 오래된 요약 memory를 어떻게 계층화할지
```

이 후보들은 ORDER_104의 비범위다.
