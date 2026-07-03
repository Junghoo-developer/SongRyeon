# ORDER_121 Node2 Evidence Source Alignment And L3 Failure Attitude v0

## 목표

`node_2 answer_basis`가 근거 ID를 고를 때 LLM에게 보인 sample ID와 validator가 허용한 ID 목록이 어긋나 schema 실패하는 문제를 막는다.

동시에 L3가 검색 목표 실패/예산소진을 남겼을 때 `node_3`가 그 신호를 답변 태도에 반영할 수 있게 한다.

## 구현 범위

- `node_2 answer_basis` 입력에 code-built `available_evidence_sources` 표를 추가한다.
- `evidence_roles.source_data_id`는 `available_evidence_sources` 안의 ID만 허용한다.
- `Node2AnswerBasisFrame` validator는 약화하지 않는다.
- `Node3InputBriefFrame`에 L loop 반환 요약 필드를 복사한다.
- `node_3` grounding block과 payload에 L 검색 목표 상태/예산소진 신호를 표시한다.
- `node_4`는 L loop 실패/예산소진 신호를 검색 성공처럼 말하는지 검사하도록 prompt/check 항목을 보강한다.

## 제외 범위

- L revision 검색 전략 자체는 바꾸지 않는다.
- search 반복 억제, query novelty 판단, unread candidate direct read_doc 경로는 이번 발주에서 구현하지 않는다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB, same-turn L reroute 횟수는 건드리지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- 추가 pytest로 다음을 확인한다.
  - 허용된 evidence source ID는 `node_2 answer_basis`에서 통과한다.
  - 허용 목록 밖 ID는 기존처럼 `schema_failed` fallback으로 닫힌다.
  - L loop 실패/예산소진 요약이 `node_3` brief/payload/grounding block에 보존된다.
  - L loop 실패를 성공처럼 말하는 보고는 `node_4`가 반려할 수 있다.
