# ORDER_130_DOCUMENT_EVIDENCE_ROLE_CLAIM_GUARD_V0

상태: 구현 발주서
작성일: 2026-06-29

## 1. 목표

node_3 최종 답변이 문서 근거 역할을 섞어 말하지 않게 한다.

특히 다음 역할을 구분한다.

- `actual_tool_read_doc`: 실제 `read_doc` / `read_artifact` 도구가 원문을 읽은 문서
- `supplied_document_context`: node_3에게 context로 공급된 문서
- `search_candidate`: 검색 후보로 발견된 문서
- `excluded_document_context`: context 예산 때문에 공급되지 않은 문서
- `unread_candidate`: 검색 후보였지만 실제 read_doc은 되지 않은 문서

## 2. 배경

최근 live test에서 explicit resolver와 document context pack은 ORDER_122~128 문서를 찾아 node_3에게 공급했다.

하지만 실제 `read_doc`으로 읽힌 문서는 일부 다른 문서였고, node_3 답변은 `ORDER_122는 read_doc으로 읽혔다`처럼 말할 수 있었다.

이것은 의미 판단 문제가 아니라 문서 역할 장부와 user-facing claim의 불일치 문제다.

## 3. 구현 원칙

- 코드가 문서 내용을 요약하거나 의미 판단하지 않는다.
- node_0 document material packet의 role flag는 절대정보 장부로 사용한다.
- node_3는 문서별 role flag가 true인 역할만 주장한다.
- node_4는 명시 role claim이 장부와 충돌하면 반려한다.
- 넓은 자연어 의미 판단은 node_4 LLM 책임으로 남긴다.
- code guard는 `read_doc`, `actual_tool_read_doc`, `supplied_document_context` 같은 명시 역할 표현의 장부 충돌만 잡는다.

## 4. 구현 범위

1. node_3 LLM payload에 문서 역할 경계표를 추가한다.
   - 실제 read_doc 문서명
   - node_3 context 공급 문서명
   - 검색 후보 문서명
   - 제외 문서명
   - unread candidate 문서명
   - context로 공급됐지만 실제 read_doc은 아닌 문서명

2. node_3 prompt에 역할 경계 규칙을 보강한다.
   - context로 공급된 문서를 `read_doc으로 읽었다`고 말하지 않는다.
   - role flag가 true인 역할만 해당 문서에 주장한다.

3. node_4 prompt에 역할 경계 검사를 보강한다.

4. node_4 code guard를 추가한다.
   - 보고문이 특정 문서명과 `read_doc` 계열 명시 역할을 같은 줄에서 긍정 주장할 때,
     해당 문서의 `was_actual_tool_read_doc`이 false면 `needs_revision`으로 막는다.
   - 보고문이 특정 문서명과 `supplied_document_context` 계열 명시 역할을 같은 줄에서 긍정 주장할 때,
     해당 문서의 `was_supplied_document_context`가 false면 `needs_revision`으로 막는다.

## 5. 금지

- L3 per-document summary 구현 금지
- search/read 예산 변경 금지
- L revision 전략 변경 금지
- node_4 guard 약화 금지
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 금지
- 문서 내용 의미 요약을 code가 생성하는 것 금지

## 6. 완료 조건

- node_3 payload가 문서 역할 경계표를 제공한다.
- node_3 prompt가 역할 혼동 금지를 명시한다.
- node_4가 `read_doc` 명시 claim과 material packet role flag 충돌을 막는다.
- 실제 read_doc 문서에 대한 read_doc claim은 통과한다.
- context로만 공급된 문서를 context로 말했다면 통과한다.

## 7. 검증

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
