# ORDER 257 실행 기록: Node4 과업 수행과 본문 일관성 검사

## 결과

구현 및 검증 완료.

## 원인

기존 node_4는 grounding count, 문서 역할, 최근 대화, Vessel 상태를 검사했지만 사용자 과업을
실제로 수행했는지와 본문이 절대 count에 의미상 모순되는지는 별도 구조로 판정하지 않았다.
따라서 내부 실행 상태를 정직하게 적었어도 사용자 질문에는 답하지 않은 보고가 통과할 여지가 있었다.

## 구현

`Node4GatekeeperFrame`에 다음 node_4 LLM 판단을 추가했다.

```text
task_fulfillment_status = fulfilled | partial | not_fulfilled | not_checkable
grounding_consistency_status = consistent | contradiction | not_checkable
task_failure_reasons
```

node_4 LLM은 다음을 검사한다.

- 사용자 요청의 핵심 행동을 수행했는가
- runtime inventory가 사용자 답변을 대신했는가
- code가 공급한 절대 count와 본문이 충돌하는가
- 근거 비의존 요청을 문서 부재만으로 거절했는가

code는 본문 의미를 직접 판정하지 않는다. 대신 node_4 LLM이 `not_fulfilled`, `partial`,
`contradiction` 또는 `not_checkable`을 냈을 때 silent pass가 되지 않도록 `needs_revision` 이하로
강제한다. 기존 count/document/recent-memory/Vessel guard는 유지했다.

## smoke 호환 수정

기존 count 교정 smoke의 가짜 node_4 응답은 새 검사 필드를 반환하지 않았다. 제품 validator나
guard를 느슨하게 하지 않고, 그 smoke adapter가 과업 수행과 본문 일관성 검사를 완료했다고
명시하도록 테스트 fixture만 갱신했다.

## 검증

```text
python -m compileall songryeon_core main.py
passed

ORDER 257 전용 테스트
4 passed

node_3/node_4 관련 회귀시험
47 passed

python -m pytest
444 passed, 5 deselected in 75.64s

python main.py smoke-test
SMOKE_TEST_OK in 91.6s
```

검증한 경우는 다음과 같다.

- LLM이 pass를 써도 `not_fulfilled`이면 code가 needs_revision으로 낮춘다.
- grounding contradiction이면 needs_revision으로 낮춘다.
- 기록된 과업인데 새 검사가 누락되면 silent pass하지 않는다.
- fulfilled/consistent인 근거 비의존 답변은 grounding block 없이 pass할 수 있다.

## 일부러 하지 않은 것

- code의 문장 의미 분석 또는 질문 키워드 휴리스틱
- node_4 자동 재작성, 새 검색, 라우팅 권한
- 기존 guard 약화
- L/R 반복 횟수, 외부 DB, 그래프 구조 변경

## 남은 위험

- node_4 판단 자체는 LLM 판단이므로 오판할 수 있다. code는 구조와 fail-closed 정책만 보장한다.
- 실제 Qwen node_3/node_4 조합의 과업 수행 판정은 별도 live 시험으로 확인해야 한다.
