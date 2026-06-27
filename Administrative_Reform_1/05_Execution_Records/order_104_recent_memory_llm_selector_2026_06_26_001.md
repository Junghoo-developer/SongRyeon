# ORDER_104 Recent Memory LLM Selector 실행 기록

## 작업 일시

2026-06-26

## 목표

ORDER_103의 `MemoryRelevanceCandidateFrame`을 입력으로 보고, 최근 기억 후보 중 현재 턴과 관련 있어 보이는 후보를 LLM selector가 선택한 결과를 별도 frame으로 기록한다.

이번 작업의 경계는 다음이다.

```text
0은 후보 좌표를 공급한다.
LLM selector가 관련성 판단을 한다.
code는 그 판단의 출처와 schema를 기록한다.
```

## 변경 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/memory_relevance_selector.py`
- `songryeon_core/prompts/memory_relevance_selector_v0.md`
- `songryeon_core/llm/fake.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/smoke_test.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/runtime/user_turn.py`
- `songryeon_core/core/registry.py`
- `main.py`

## 구현 내용

### 1. MemoryRelevanceSelectionFrame 추가

새 frame은 다음 DataStore record로 저장된다.

```text
data_id=memory_packet:node_1:pre_route_report:memory_relevance_selection
data_type=node_output:memory_relevance_selection_frame
schema_name=MemoryRelevanceSelectionFrame
schema_version=0.1
```

candidate frame은 기존처럼 `memory_packet:node_1:pre_route_report` payload의 `relevance_candidate_frames`에 남는다.
selection frame은 같은 memory packet을 `source_memory_packet_id`로 참조하는 별도 record다.
이미 저장된 memory packet payload를 덮어쓰지 않는다.

### 2. selector 입력 source

selector 입력에는 다음을 넣었다.

```text
current_user_input
current_user_input_trace_id
selector_target_node=node_1
source_memory_packet_id=memory_packet:node_1:pre_route_report
memory_packet 최소 view
relevance_candidate_frames
candidate_alignment_items
source_data_ids=[memory_packet:node_1:pre_route_report]
```

`candidate_alignment_items`에는 candidate가 가리키는 `recent_raw_conversation_capsule_alignment` memory item의 `COPIED_FIELDS` text, `source_memory_item_id`, `candidate_turn_id`, `source_trace_ids`만 넣었다.

이번 MVP에서는 raw user/assistant 전문을 selector 입력에 추가하지 않았다.

### 3. LLM이 판단하는 부분

후보가 있을 때 selector LLM은 다음 필드를 판단한다.

```text
selection_status=selected | none_selected
selected_candidate_turn_ids
selected_candidate_frame_ids
selection_reason
```

성공한 LLM selector 결과는 다음 출처를 반드시 가진다.

```text
judged_by=LLM:...
generated_by=LLM:...:memory_relevance_selector
llm_call_data_id=...
llm_trace_event_id=...
info_class=mixed
source_mode=source_bundle
claim_alignment=multi_source_bundle
```

`info_class=mixed`로 둔 이유는 현재 사용자 입력, memory packet, candidate frame, alignment item, capsule trace anchor가 함께 묶인 source bundle을 보고 관련성 판단을 하기 때문이다.

### 4. code가 판단하지 않는 부분

code는 관련 후보를 직접 고르지 않는다.

code가 하는 일은 다음으로 제한했다.

```text
candidate frame 존재 여부 확인
LLM payload JSON parse/schema 검증
선택된 frame_id가 입력 candidate 안에 있는지 검증
선택된 turn_id가 선택된 frame_id의 candidate_turn_id와 맞는지 검증
DataStore/TraceStore 기록
```

LLM이 schema를 통과하지 못하면 code가 대신 후보를 고르지 않는다.

### 5. 실패 정책

selector LLM parse 실패 또는 schema 실패 시 다음으로 기록한다.

```text
selection_status=failed
selected_candidate_turn_ids=[]
selected_candidate_frame_ids=[]
selection_reason=CODE_STATUS:memory_relevance_selector_failed
generated_by=CODE:MEMORY_RELEVANCE_SELECTOR_FAILURE_RECORDER
```

이 경우 `llm_call_data_id`와 `llm_trace_event_id`는 실패한 LLM call record를 가리킨다.
선택 목록은 끝까지 빈 리스트로 둔다.

candidate frame이 없으면 LLM을 호출하지 않고 다음으로 닫는다.

```text
selection_status=none_selected
selection_reason=CODE_STATUS:no_memory_relevance_candidates
llm_call_data_id=None
```

이 no-candidates frame은 관련성 의미 판단이 아니라 후보 부재라는 code status close다.

### 6. dry_run / terminal 표시

`run_dry_turn()`은 `memory_relevance_selector_adapter`를 받을 수 있다.

후보가 있고 adapter가 없으면 dry-run 검증용 `MemoryRelevanceNoneSelectedFakeLLMAdapter`를 사용한다.
후보가 없으면 adapter가 있어도 LLM을 호출하지 않는다.

runtime/terminal 출력에는 다음을 표시한다.

```text
selector status
candidate count
selected count
judged_by
llm_call_data_id
selection_reason
```

## Smoke 확인값

`python main.py smoke-test` 결과에 다음 값이 추가됐다.

```text
recent_memory_relevance_selection_selected=selected
recent_memory_relevance_selection_none=none_selected
recent_memory_relevance_selection_failed=failed
recent_memory_relevance_selection_no_candidates=none_selected
recent_memory_relevance_selection_info_class=mixed
```

기존 ORDER_103 확인값도 유지된다.

```text
recent_memory_relevance_candidate_window=8
recent_memory_relevance_candidate_count=8
recent_memory_relevance_candidate_judgement=not_run
recent_memory_relevance_candidate_skips_mismatch=true
```

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python main.py smoke-test
```

통과.

최종 상태:

```text
SMOKE_TEST_OK
```

## 비범위 유지

이번 작업에서 다음은 하지 않았다.

- 장기기억 DB 생성
- vector DB
- embedding 기반 memory search
- memory graph
- 오래된 대화 요약
- node_4 요약 승인 루프
- scheduler
- W loop
- R loop
- 관련성 heuristic fallback
- 키워드 매칭 selector
- 문자열 유사도 selector
- 선택된 memory candidate를 node_1/router 또는 node_3 final report 입력에 주입

## 남은 위험

- selector 입력에는 아직 raw user/assistant 전문이 없다. 현재는 alignment item의 존재 여부, 문자 수, trace anchor, candidate frame 좌표만 본다.
- dry-run 기본 selector는 후보가 있을 때 `none_selected` fake adapter로 검증한다. 실제 Qwen selector 품질은 별도 live 검증이 필요하다.
- selection frame은 기록만 되고 아직 라우터나 최종 보고 입력에 반영되지 않는다.
- no-candidates frame은 `info_class=absolute_status` 성격의 code status close다. LLM 관련성 판단이 실제로 실행된 selected/none_selected frame만 `info_class=mixed`로 해석해야 한다.
