# Answer basis mode philosophy and learning record

## 목적

오늘 qwen-chat 기억력 테스트에서 확인한 문제의식을 구현하지 않고 철학 문서로 보존했다.

추가 문서:

```text
Administrative_Reform_1/00_Philosophy/Answer_Basis_Mode_And_Evidence_Role_Philosophy_2026_06_26.md
```

## 오늘 확인한 것

### 1. 최근 기억 전달은 작동한다

qwen-chat 2턴 사례에서 다음 흐름이 확인되었다.

```text
recent_raw_conversation=1
previous_turn_capsules=1
memory_relevance_selection=selected
selected_recent_memory_context copied=1
node_3 selected_memory_contexts=1
```

즉 최근 기억 raw 원문은 selector와 node_3까지 전달된다.

### 2. 문제는 기억 부재가 아니라 answer basis 혼동이다

node_3는 선택된 최근 기억 원문에서 `"전진"`을 볼 수 있었다.
하지만 L루프가 돌고 읽은 문서가 있으면 문서 근거를 과하게 의식한다.

결과적으로 다음처럼 답변이 흐를 수 있다.

```text
선택된 최근 기억에는 전진이 있다.
하지만 문서에는 전진이 없다.
```

사용자 의도가 "최근 대화 원문을 기억하느냐"일 때 문서는 주근거가 아니다.
이 경우 주근거는 selected recent memory context다.

### 3. 다음 MVP 후보는 node_2 answer basis mode다

다음 MVP 후보:

```text
ORDER_111_NODE2_ANSWER_BASIS_MODE_FOR_NODE3_V0
```

핵심 아이디어:

```text
node_2가 node_3에게 이번 답변의 주근거 버킷을 지정한다.
```

후보 필드:

```text
answer_basis_mode
primary_evidence_bucket
secondary_evidence_buckets
document_evidence_role
recent_memory_evidence_role
current_user_utterance_role
```

주의:

code가 `"암구호"`, `"방금"`, `"문서"` 같은 단어로 mode를 정하면 안 된다.
그것은 숨은 휴리스틱이다.

## 오늘의 학습 결론

송련의 기억 문제는 단순히 "기억을 많이 넣기"로 풀리지 않는다.

중요한 것은 다음 순서다.

1. raw 원문과 capsule을 정확히 대응시킨다.
2. selector가 raw 원문을 볼 수 있게 한다.
3. selected context를 node_3에 복사한다.
4. node_3가 어떤 근거를 주근거로 답해야 하는지 node_2가 지정한다.
5. node_4가 그 basis mode를 어겼는지 검사한다.

현재는 1~3이 작동한다.
다음 병목은 4다.

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
qwen_chat_loop_after_store_raw_count=2
node4_recent_memory_guard_no_word_heuristic=True
```

## 다음 행동 후보

바로 구현하지 않는다.

다음 개발 전에는 먼저 `ORDER_112_NODE2_ANSWER_BASIS_MODE_FOR_NODE3_V0` 발주서를 작성하고, 다음 질문을 좁힌다.

1. answer basis mode를 node_2 LLM이 판단할지, 별도 작은 판단 노드로 분리할지.
2. current user utterance를 답변 근거로 승격하는 schema가 필요한지.
3. node_4가 basis mode 위반을 어떻게 검수할지.
