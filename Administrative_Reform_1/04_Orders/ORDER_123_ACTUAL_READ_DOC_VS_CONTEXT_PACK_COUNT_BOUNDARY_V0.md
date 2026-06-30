# ORDER_123 Actual Read Doc Vs Context Pack Count Boundary v0

## 목표

`read_doc` 도구가 실제로 읽은 문서 수와 `document_context_pack`이 node_3에게 공급한 문서 context 수를 구조적으로 분리한다.

최근 live 테스트에서 `read_doc=2/10`인데 `document_context_pack included=10`이 node_3에게 들어가면서, 최종 답변이 `read_doc 수 10개`처럼 말할 위험이 확인되었다.

## 구현 범위

- `Node3InputBriefFrame`에 실제 도구 읽기 수와 공급 context 수를 별도 절대 필드로 둔다.
- code가 생성하는 grounding block의 라벨을 다음처럼 분리한다.
  - 실제 `read_doc` 도구 원문 읽기 수
  - node_3 공급 문서 context 수
  - 검색 후보 문서 수
- node_3 LLM payload에도 `actual_tool_read_doc`과 `supplied_document_context`를 분리해 넣는다.
- node_3 prompt는 `read_doc` count를 말할 때 `actual_tool_read_doc.count`만 사용하게 한다.
- 기존 `read_documents` 호환 필드는 유지하되, user-facing count 기준으로 쓰지 않는다.

## 제외 범위

- 문장 키워드 탐지로 "read_doc 10개"를 잡는 휴리스틱 guard는 추가하지 않는다.
- node_3 문서 context 압축/정렬은 이번 발주에서 하지 않는다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB, same-turn L reroute 횟수는 건드리지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- 추가 pytest로 다음을 확인한다.
  - actual `read_doc` count와 context pack included count가 서로 다르게 보존된다.
  - grounding block이 두 count를 다른 라벨로 출력한다.
  - node_3 LLM payload에서 `actual_tool_read_doc.count`와 `supplied_document_context.count`가 분리된다.
  - node_4 grounding count guard가 새 라벨 기준으로 동작한다.
