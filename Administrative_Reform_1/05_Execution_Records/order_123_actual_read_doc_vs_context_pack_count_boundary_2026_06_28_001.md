# ORDER_123 Actual Read Doc Vs Context Pack Count Boundary 실행 기록 2026-06-28 001

## 배경

live 테스트에서 `L 도구 예산: read_doc=2/10`과 `document_context_pack included=10`이 동시에 나타났다.
이후 node_3 최종 답변이 context pack 공급 문서 수를 실제 `read_doc` 도구 읽기 수처럼 말할 위험이 확인되었다.

## 구현 판단

이번 수정은 문장 키워드 탐지 휴리스틱을 추가하지 않았다.
대신 `Node3InputBriefFrame` 안에서 다음 절대 count를 구조적으로 분리했다.

- `actual_tool_read_doc_count`: L return summary 또는 실제 도구 extract record 기준의 도구 원문 읽기 수
- `actual_tool_read_doc_documents`: 실제 도구 원문 읽기 문서명 목록
- `supplied_document_context_count`: node_3에게 본문 context로 공급된 문서 수

## 변경 요약

- `Node3InputBriefFrame`에 실제 read_doc 계열 도구 읽기 count와 node_3 공급 context count를 별도 필드로 추가했다.
- node_3 grounding block을 다음처럼 분리했다.
  - 실제 read_doc 도구 원문 읽기
  - node_3 공급 문서 context
  - 검색 후보 문서
  - 현재 턴 실행 순서 자료
- node_3 LLM payload에 `actual_tool_read_doc`와 `supplied_document_context`를 분리해서 넣었다.
- 기존 `read_documents` payload는 호환 alias로 유지하되, `legacy_alias=supplied_document_context`를 붙였다.
- node_3 prompt는 실제 read_doc 수를 말할 때 `actual_tool_read_doc.count`만 쓰도록 경계를 강화했다.
- terminal runtime view는 node_3 input brief를 `actual_read_doc`와 `supplied_contexts`로 분리 표시한다.
- node_4 grounding count guard는 새 라벨 기준으로 count mismatch를 검사한다.

## 테스트

추가 pytest:

- `tests/test_order_123_actual_read_doc_vs_context_pack_count.py`

확인한 사항:

- actual `read_doc` count와 supplied context count가 서로 다르게 보존된다.
- grounding block이 두 count를 다른 라벨로 출력한다.
- node_3 LLM payload에서 `actual_tool_read_doc.count`와 `supplied_document_context.count`가 분리된다.
- `supplied_document_context_count`가 `read_documents` 길이와 다르면 schema validation이 실패한다.
- node_4 count guard는 context count가 아니라 actual read_doc count를 기준으로 mismatch를 잡는다.

검증 결과:

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: `45 passed`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- live qwen-turn 재현 테스트: `status=ok`

live qwen-turn 확인값:

- runtime `node_3 input brief`: `actual_read_doc=2 / supplied_contexts=10 / search_candidates=10`
- 최종 grounding block: `실제 read_doc 도구 원문 읽기: 2개`
- 최종 grounding block: `node_3 공급 문서 context: 10개`
- 본문 `read_doc 수`: 2개로 출력
- 본문 `node_3 공급 문서 context 수`: 10개로 출력

## 제외한 것

- `read_doc`라는 단어가 포함된 문장을 탐지해 막는 휴리스틱 guard는 추가하지 않았다.
- node_3 문서 context 압축/정렬은 하지 않았다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB, same-turn L reroute 횟수는 변경하지 않았다.
