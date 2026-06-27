# Answer Basis Mode And Evidence Role Philosophy

## 상태

미승격 철학 메모.

이 문서는 다음 MVP 후보를 위한 문제의식 기록이다.
즉시 구현 명령이 아니다.

## 배경

최근 qwen-chat 기억력 테스트에서 다음 현상이 확인되었다.

1. 최근 대화 기억은 실제로 공급되었다.
2. memory relevance selector는 이전 턴 raw 원문을 선택했다.
3. selected recent memory context도 node_3 brief에 들어갔다.
4. 그런데 node_3 최종 답변은 여전히 문서 근거가 없다는 말을 과하게 덧붙였다.

즉 문제는 "기억이 안 된다"가 아니었다.
문제는 node_3가 어떤 근거를 주근거로 삼아야 하는지 명확히 안내받지 못한 데 있었다.

## 핵심 문제

현재 구조에서는 L루프가 돌고 읽은 문서가 있으면 node_3가 문서 기반 답변 모드로 끌려가기 쉽다.

하지만 모든 질문이 문서 기반 답변을 요구하는 것은 아니다.

예:

```text
내가 방금 말한 암구호가 뭐였지?
```

이 질문의 주근거는 내부 문서가 아니다.
주근거는 선택된 최근 대화 원문이다.

따라서 문서가 있더라도 그 문서는 보조 근거이거나 아예 불필요할 수 있다.

## 초등학생용 비유

사용자는 "내가 아까 쪽지에 뭐라고 썼는지 말해봐"라고 물었다.

송련은 쪽지를 찾아서 "전진"이라고 읽었다.
그런데 동시에 교과서도 펼쳐 보고, 교과서에 "전진"이 없다고 조심스럽게 말했다.

이때 답은 교과서가 아니라 쪽지에서 나와야 한다.

## 필요한 개념

다음 MVP에서는 node_2가 node_3에게 답변 기준을 더 분명히 알려주는 구조를 검토한다.

후보 이름:

```text
answer_basis_mode
```

후보 값 예시:

```text
document_primary
selected_recent_memory_primary
runtime_task_sequence_primary
current_user_utterance_primary
mixed_basis
insufficient_basis
```

보조 필드 후보:

```text
primary_evidence_bucket
secondary_evidence_buckets
document_evidence_role
recent_memory_evidence_role
current_user_utterance_role
```

예:

```text
answer_basis_mode=selected_recent_memory_primary
primary_evidence_bucket=selected_recent_memory_contexts
secondary_evidence_buckets=[runtime_task_sequence]
document_evidence_role=not_required
```

## 중요한 금지선

code가 다음처럼 판단하면 안 된다.

```text
"암구호"라는 단어가 있으니 memory mode
"문서"라는 단어가 있으니 document mode
"방금"이라는 단어가 있으니 recent memory mode
```

이것은 숨은 휴리스틱이다.

code의 역할은 가능한 근거 버킷과 절대 count를 정직하게 제공하는 것이다.
어떤 근거 버킷을 주근거로 삼아 답할지는 node_2의 명시된 판단 책임으로 두어야 한다.

단, node_2가 LLM 판단을 사용한다면 반드시 다음을 드러내야 한다.

```text
generated_by
info_class
semantic_judgement_status
source_data_ids
source_trace_ids
```

## 근거 버킷 후보

현재 구조에서 node_3 답변 재료가 될 수 있는 근거 버킷은 대략 다음과 같다.

```text
read_documents
allowed_claims
runtime_task_sequence
selected_recent_memory_contexts
search_candidate_documents
```

단, `search_candidate_documents`는 읽은 문서가 아니다.
후보 문서명은 내용 근거로 쓰면 안 된다.

앞으로 추가 검토할 버킷:

```text
current_user_utterance_evidence
```

이 버킷은 현재 턴에서 사용자가 직접 말한 원문을 node_3가 답변 근거로 사용할 수 있게 하는 장치다.

예:

```text
사용자: 이번 암구호는 "전진"이야.
```

이 경우 `"전진"`은 내부 문서 근거가 아니라 현재 사용자 발화 근거다.

## 다음 MVP 후보

다음 MVP는 구현 전에 별도 발주서로 좁혀야 한다.

후보 제목:

```text
ORDER_TBD_NODE2_ANSWER_BASIS_MODE_FOR_NODE3_V0
```

번호는 아직 확정하지 않는다. `ORDER_112`는 2026-06-27에 explicit artifact priority와 whole-document context packing 발주서로 사용했다.

목표 후보:

1. node_2가 node_3 brief에 `answer_basis_mode`를 넣는다.
2. node_3는 그 mode에 따라 주근거와 보조근거를 구분해 답한다.
3. node_4는 답변이 지정된 basis mode를 어겼는지 검사한다.
4. code는 단어 매칭 휴리스틱으로 mode를 정하지 않는다.

## 현재 결론

최근 기억은 이제 전달된다.

다음 병목은 기억 자체가 아니라 "어떤 근거를 중심으로 답해야 하는가"이다.
