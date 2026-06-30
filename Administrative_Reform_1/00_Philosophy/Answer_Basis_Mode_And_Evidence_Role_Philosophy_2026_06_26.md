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

## 2026-06-29 추가 메모: 메타정보 판단의 장기 위치

장기적으로 보면 메타정보 판단은 턴의 한 지점에만 묶일 일이 아니다.

턴 맨 앞에서는 다음 질문이 필요해진다.

```text
이번 입력은 무엇을 근거로 이해해야 하는가?
최근 대화인가?
현재 사용자 발화인가?
문서 검색인가?
실행 상태인가?
```

턴 중간에서는 다음 질문이 필요해진다.

```text
지금 수집된 자료는 절대정보인가, 상대정보인가, 혼합정보인가?
이 자료를 다음 노드에 원문으로 넘겨야 하는가, 장부로 넘겨야 하는가, 요약 후보로 넘겨야 하는가?
```

턴 끝에서는 다음 질문이 필요해진다.

```text
최종 답변은 어떤 정보 등급의 말하기 태도를 가져야 하는가?
절대정보 중심으로 좁혀야 하는가?
상대 해석을 허용해도 되는가?
여러 source bundle을 엮은 혼합정보로 한계를 드러내야 하는가?
```

즉 메타정보 판단은 장기적으로 2번 node 하나의 좁은 후처리만이 아니라, 송련 전체 런타임의 여러 지점에서 반복적으로 필요해질 수 있다.

하지만 지금 당장 이 전체 구조를 열면 범위가 너무 커진다.

따라서 단기 구현 경계는 다음처럼 둔다.

```text
이번 단계에서는 node_2가 node_3에게 답변 태도만 정해 준다.
```

여기서 말하는 답변 태도는 다음 세 갈래 정도로 좁힌다.

```text
absolute_first
relative_allowed
mixed_or_uncertain
```

이 경계 안에서는 node_2가 "이번 턴은 절대정보 중심으로 답해야 한다"라고 판단할 수 있다.

그 경우 node_3에게는 요약이나 감상보다 원문, count, trace/data 장부, document material packet 같은 검증 가능한 재료를 우선 공급하는 방향이 자연스럽다.

반대로 node_2가 상대정보 또는 혼합정보를 허용하는 답변 태도를 고른다면, 장기적으로는 L3, 5, 또는 별도 요약 노드가 source가 붙은 요약 카드나 문서별 근거 카드를 만들어 node_3에게 줄 수 있다.

단, 이 요약은 code가 의미를 대신 판단한 절대정보가 아니다.
요약은 LLM이 생성한 상대정보 또는 혼합정보로 남겨야 하며, 반드시 다음을 드러내야 한다.

```text
generated_by
info_class
semantic_judgement_status
source_data_ids
source_trace_ids
```

중요한 결론:

```text
장기적으로는 턴 전/중/후 어디서든 메타정보 판단이 필요할 수 있다.
하지만 지금은 node_2 -> node_3 답변 태도 전달까지만 구현 대상으로 삼는다.
```

이 제한은 후퇴가 아니다.
먼저 사용자-facing 최종 답변의 태도를 안정시킨 뒤, 나중에 기억 요약, L3 문서별 요약, 5 기억 압축, node_4 검토 루프와 함께 더 넓은 메타정보 판단 배치를 다시 설계하기 위한 안전한 순서다.

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
