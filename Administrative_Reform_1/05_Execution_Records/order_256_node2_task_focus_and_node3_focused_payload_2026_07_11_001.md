# ORDER 256 실행 기록: Node2 과업 초점과 Node3 집중 payload

## 결과

구현 및 검증 완료.

## 원인

기존 node_3는 사용자 질문을 받으면서도 전체 검색 장부, L2 검색 계획, runtime 실행 순서,
반복되는 reporting rule을 함께 받았다. 이 때문에 사용자 요청을 수행하기보다 송련 내부 실행
상태를 설명하거나, 답변 재료가 아닌 검색 계획을 근거처럼 다룰 수 있었다.

## 구현

`Node2AnswerBasisFrame`에 다음 LLM 판단을 추가했다.

```text
task_contract_status
user_task_summary
fulfillment_requirements
evidence_requirement = not_required | optional | required
```

code는 DataStore record의 종류와 실제 field 존재 여부를 복사해 answer-ready, status, process
후보표를 만든다. 어떤 자료가 사용자 질문에 관련 있는지는 판단하지 않는다. node_2 LLM이 공식
후보표 안에서 primary, supporting, unused 역할을 선택한다.

node_3에는 task contract가 정상 기록된 경우에만 집중 payload를 공급한다. 원문 질문, 과업 계약,
답변 자세, 절대 count, L/R 상태는 유지하고, node_2가 고른 재료만 포함한다. 전체 장부와 기존
`Node3InputBriefFrame`은 DataStore에 계속 보존한다.

외부 근거가 필요하지 않은 인사, 문장 변환, 창작 요청은
`evidence_requirement=not_required`를 사용할 수 있다. 이 경우 code grounding block을 붙이지 않아
사용자가 요구한 한 문장 형식을 보존한다. 이는 사실을 지어낼 권한이 아니다.

## 구현 중 발견한 회귀

초기 전체 pytest에서 비어 있는 selected-memory frame이 answer-ready 후보로 잡혀 Vessel 재료보다
먼저 선택되는 회귀가 발견됐다. 빈 memory frame은 catalog에서 제외하고, 일반 source ID를
answer-ready로 넓게 추정하지 않도록 record type 판정을 보수적으로 고쳤다.

이 수정은 키워드 관련성 휴리스틱이 아니라 실제 payload 존재 여부와 record type에 따른 구조 검사다.

## 검증

```text
python -m compileall songryeon_core main.py
passed

ORDER 256 전용 테스트
6 passed

ORDER 256 관련 회귀시험
53 passed

python -m pytest
444 passed, 5 deselected in 75.64s

python main.py smoke-test
SMOKE_TEST_OK
```

fake 통합 시험에서 근거 비의존 한 문장 인사 요청은 runtime 장부로 대체되지 않고 다음 한 문장으로
끝났다.

```text
안녕, 오늘도 잘 부탁해.
```

## 일부러 하지 않은 것

- code 키워드 질문 분류 또는 의미 관련성 판단
- 전체 trace/DataStore 장부 삭제
- L/R 라우팅, 반복 횟수, 그래프 DB 변경
- node_4 자동 재작성
- node_2 실패 시 code 의미 계약 생성

## 남은 위험

- 실제 Qwen이 task contract와 evidence role을 얼마나 안정적으로 고르는지는 live 시험 대상이다.
- answer-ready는 답변에 사용할 수 있는 구조를 뜻하며, 질문과 의미상 관련 있다는 보증이 아니다.
- 집중 payload가 지나치게 적거나 많은지는 실제 과업별 관측을 통해 조정해야 한다.
