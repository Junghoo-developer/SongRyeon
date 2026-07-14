# ORDER 257: Node4 Task Fulfillment And Body Consistency Guard v0

## 상태

구현 및 검증 완료.

## 문제

node_4는 grounding block count와 출처 경계를 검사하지만 다음을 놓칠 수 있다.

- 사용자 질문 대신 runtime 상태를 답함
- 근거 비의존 요청을 자료 부족으로 거절함
- code grounding count와 본문 일반 문장이 의미상 충돌함

## 목표

node_4 LLM 출력에 다음 판단을 추가한다.

```text
task_fulfillment_status = fulfilled | partial | not_fulfilled | not_checkable
grounding_consistency_status = consistent | contradiction | not_checkable
task_failure_reasons
```

이 값은 node_4 LLM의 상대/혼합 판단이다. code는 enum을 검증하고,
`not_fulfilled` 또는 `contradiction`이면 gate를 `needs_revision` 이하로 강제한다.

## 검사 질문

1. 사용자 요청의 핵심 행동을 실제로 수행했는가?
2. runtime inventory가 사용자 답변을 대체했는가?
3. code-supplied absolute grounding facts와 본문이 충돌하는가?
4. evidence_requirement=not_required인데 문서 부재만으로 거절했는가?

## 유지

- 기존 count guard
- document role guard
- recent memory guard
- Vessel/R status guard
- safe blocking answer

## 금지

- code 키워드 의미 판정
- node_4 자동 재작성 루프
- node_4의 새 검색/라우팅 권한
- 기존 guard 약화

## 검증

1. 직접 인사 요청을 근거 부족으로 거절하면 needs_revision.
2. read_doc 양수인데 본문이 원문 읽기 없음이라고 하면 needs_revision.
3. 사용자 과업 대신 runtime 단계만 나열하면 needs_revision.
4. 정상 답변은 기존 guard와 함께 pass.
5. compileall, pytest, smoke-test를 통과한다.
