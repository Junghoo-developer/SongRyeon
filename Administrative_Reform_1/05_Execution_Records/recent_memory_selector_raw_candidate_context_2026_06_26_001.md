# Recent memory selector raw candidate context execution record

## 배경

qwen-chat 4턴 실행 사례에서 세션 기억 카운트는 존재했지만 최근 기억 selector가 `none_selected`를 냈다.

확인된 흐름:

```text
recent_raw_conversation=3
previous_turn_capsules=3
memory_relevance_selection=none_selected
selected_recent_memory_context copied=0
node_3 selected_memory_contexts=0
```

3턴 원문에는 암구호 `"청성"`이 있었지만, 4턴 selector 입력에는 후보별 실제 raw user/assistant text가 없었다.

기존 selector 입력:

- `relevance_candidate_frames`
- `candidate_alignment_items`

기존 alignment item은 원문 존재 여부와 글자 수만 담았다.
따라서 selector prompt의 "raw conversation text가 명시되어 있지 않으면 사용하지 말라"는 규칙상, Qwen이 `none_selected`를 낸 것은 규칙 위반이 아니라 입력 부족에 가까웠다.

## 변경

`songryeon_core/nodes/memory_relevance_selector.py`

- selector 입력에 `candidate_raw_conversation_items`를 추가했다.
- 후보 frame의 `candidate_turn_id`와 `ZeroState.recent_raw_conversation.turn_id`가 정확히 일치할 때만 raw user/assistant text를 복사한다.
- 관련성 선택은 code가 하지 않는다.
- code는 원문 복사와 truncation 여부 기록만 한다.

추가 입력 record:

```text
data_type=node_input:memory_relevance_selector_input
```

이 record에는 selector가 실제로 본 후보 raw text 복사본이 저장된다.

`songryeon_core/runtime/dry_run.py`

- `run_recent_memory_relevance_selector()` 호출에 `zero_state.recent_raw_conversation`을 전달한다.

`songryeon_core/prompts/memory_relevance_selector_v0.md`

- `candidate_raw_conversation_items`를 읽도록 지시를 보강했다.
- 이전/최근 턴 발화 회상 질문에서는 raw user/assistant text를 primary evidence로 쓰라고 명시했다.

`songryeon_core/runtime/smoke_test.py`

- 3번째 이전 턴 raw user text에 `"청성"`이 있는 fixture를 추가했다.
- smoke-only adapter가 `candidate_raw_conversation_items` 안의 `"청성"`을 보고 해당 candidate를 selected로 반환한다.
- selected recent memory context가 `"청성"` 원문을 복사하는지 확인한다.

## 검증

```text
python -m compileall .\songryeon_core .\main.py
```

통과.

```text
python .\main.py smoke-test
```

통과.

확인값:

```text
status=SMOKE_TEST_OK
recent_memory_relevance_selection_raw_text_selected=selected
recent_memory_relevance_selector_input_has_raw_text=True
```

## 남은 위험

실제 Qwen selector가 어떤 candidate를 고를지는 여전히 LLM mixed 판단이다.
이번 패치는 Qwen에게 판단 근거 raw text를 제공하는 것이며, code fallback으로 관련성을 고르지 않는다.
