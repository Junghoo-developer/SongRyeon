# ORDER 256: Node2 Task Focus And Node3 Focused Payload v0

## 상태

구현 및 검증 완료.

## 문제

node_3는 사용자 질문과 답변 재료를 받지만, 전체 검색 장부·제외 문서·runtime task와
중복 reporting rule을 함께 받아 사용자 과업보다 실행 과정을 답하는 경향이 있다.
node_2 answer basis도 순서 기반 표본에서 L2 검색 계획을 주근거로 고를 수 있다.

## 목표

1. 기존 3개 answer basis mode는 유지한다.
2. node_2가 사용자 과업과 근거 필요성을 LLM 판단으로 구조화한다.
3. answer-ready material과 process material을 code가 record type 기준으로 구분해 후보표로 제공한다.
4. node_3 LLM에는 선택된 재료와 최소 상태만 집중 공급한다.
5. 전체 장부는 DataStore/brief에서 보존하고 삭제하지 않는다.

## Node2AnswerBasisFrame 확장

```text
user_task_summary
fulfillment_requirements
evidence_requirement = not_required | optional | required
```

이 필드는 node_2 LLM의 상대/혼합 판단이다. code는 enum, 비어 있지 않은 문자열,
공식 evidence ref 대응만 검증한다.

## answer material catalog

code는 DataStore record type과 field를 복사해 다음 구조적 종류를 구분한다.

- answer-ready: L3 문서별 요약, 공급 문서 context, selected recent memory, Vessel/R return material
- status: L/R return summary와 code count/status
- process: L2 검색 계획, 문서 역할 장부, runtime task sequence

code는 관련성을 판단하지 않는다. node_2 LLM이 primary/supporting/unused 역할을 고른다.

## focused node_3 payload

항상 포함:

- 원문 user question
- node_2 task summary와 fulfillment requirements
- answer basis mode와 evidence requirement
- code-supplied absolute grounding facts
- L/R 상태와 한계

선택 포함:

- node_2가 primary/supporting으로 고른 answer material
- 선택된 process material

제외:

- 선택되지 않은 process ledger
- payload 안의 중복 reporting_rules 41개
- 사용자 과업과 무관하게 항상 들어가던 runtime task sequence

DataStore와 Node3InputBriefFrame의 전체 장부는 보존한다.

## prompt 경계

- 인사, 문장 변환, 창작, 브레인스토밍처럼 외부 사실 근거가 필요 없는 요청은
  `relative_allowed + evidence_requirement=not_required`를 사용할 수 있다.
- evidence_requirement=not_required는 사실을 지어낼 권한이 아니다.
- mixed_or_uncertain은 자동 거절 모드가 아니다.
- 사용자 과업을 먼저 수행하고, 사실 주장에만 공급 근거 경계를 적용한다.

## 실패 정책

node_2 task selection 실패 시 code가 의미 계약을 대신 만들지 않는다.
기존 `CODE:FALLBACK + mixed_or_uncertain` 실패 상태를 유지하고 실패 이유를 노출한다.

## 금지

- 키워드 질문 분류 휴리스틱
- code 의미 답변 생성
- trace/DataStore 장부 삭제
- L/R 라우팅·반복 횟수 변경
- node_4 자동 재작성
- 외부 DB/그래프 구조 변경

## 검증

1. evidence_requirement enum 외 값은 실패한다.
2. node_2가 공식 catalog ref만 선택할 수 있다.
3. L3 summary가 answer-ready material로 node_2 후보표에 나타난다.
4. evidence not required 턴은 node_3 payload에서 빈 장부와 runtime sequence를 생략한다.
5. 선택되지 않은 process material은 node_3 LLM payload에서 빠진다.
6. runtime 과업에서 선택된 runtime sequence는 계속 공급할 수 있다.
7. 기존 brief/DataStore 장부는 유지된다.
8. compileall, pytest, smoke-test를 통과한다.
