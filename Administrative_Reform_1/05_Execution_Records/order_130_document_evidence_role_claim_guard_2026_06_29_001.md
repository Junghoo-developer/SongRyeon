# order_130_document_evidence_role_claim_guard_2026_06_29_001

작성일: 2026-06-29
관련 발주서: `Administrative_Reform_1/04_Orders/ORDER_130_DOCUMENT_EVIDENCE_ROLE_CLAIM_GUARD_V0.md`

## 1. 목적

node_3 최종 답변이 문서 역할을 섞어 말하지 않도록 잠갔다.

최근 live trace에서 explicit resolver와 document context pack은 ORDER_122~128 문서를 찾아 node_3에게 공급했지만, 실제 `read_doc`으로 읽힌 문서는 달랐다. 그런데 node_3는 `ORDER_122는 read_doc으로 읽혔다`처럼 말했고 node_4가 이를 통과시켰다.

이번 작업은 이 문제를 막기 위한 작은 정직성 패치다.

## 2. 변경 파일

- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_4_gatekeeper.py`
- `songryeon_core/prompts/node_3_reporter_v0.md`
- `songryeon_core/prompts/node_4_gatekeeper_v0.md`
- `tests/test_order_130_document_evidence_role_claim_guard.py`
- `Administrative_Reform_1/04_Orders/ORDER_130_DOCUMENT_EVIDENCE_ROLE_CLAIM_GUARD_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## 3. 구현 내용

### 3.1 node_3 payload 역할 경계표 추가

`node3_brief_llm_payload()`에 `document_evidence_role_boundaries`를 추가했다.

포함한 항목:

- `actual_tool_read_doc_document_names`
- `supplied_context_document_names`
- `search_candidate_document_names`
- `excluded_context_document_names`
- `unread_candidate_document_names`
- `supplied_but_not_actual_read_doc_document_names`

이 정보는 문서별 역할 장부에서 code가 복사한 절대정보다.

### 3.2 node_3 reporting rule/prompt 보강

node_3에게 다음 경계를 명시했다.

- 문서별 role flag가 true인 역할만 해당 문서에 주장한다.
- node_3 context로 공급된 문서라도 `was_actual_tool_read_doc=false`이면 `read_doc`으로 읽었다고 말하지 않는다.
- `document_context_pack`으로 공급된 문서는 usable context일 수 있지만, 실제 `read_doc` tool read와 다르다.

### 3.3 node_4 prompt 보강

node_4가 `document_material_packet.items`와 `document_evidence_role_boundaries`를 문서 역할 장부로 보게 했다.

### 3.4 node_4 code guard 추가

`_document_evidence_role_code_guard()`를 추가했다.

검사하는 것:

- 보고문 한 줄에 특정 문서명과 `read_doc` / `actual_tool_read_doc` 계열 명시 역할 주장이 함께 있고,
  해당 문서의 `was_actual_tool_read_doc`가 false이면 `needs_revision`.
- 보고문 한 줄에 특정 문서명과 `supplied_document_context` / context 공급 계열 명시 역할 주장이 함께 있고,
  해당 문서의 `was_supplied_document_context`가 false이면 `needs_revision`.

reason code:

- `CODE_STATUS:document_evidence_role_claim_mismatch`

contradiction 예:

- `read_doc_claim_without_actual_tool_read_doc:ORDER_122.md`

## 4. 의도적으로 하지 않은 것

- L3 per-document summary 구현 없음
- search/read 예산 변경 없음
- L revision 전략 변경 없음
- node_4 guard 약화 없음
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 없음
- code가 문서 의미 요약 생성하지 않음

## 5. 테스트

추가 pytest:

- `test_node3_payload_exposes_document_role_boundaries`
- `test_node4_blocks_read_doc_claim_for_supplied_only_document`
- `test_node4_allows_context_claim_for_supplied_only_document`
- `test_node4_allows_read_doc_claim_for_actual_read_document`

검증 결과:

- `python -m pytest tests/test_order_130_document_evidence_role_claim_guard.py`
  - 4 passed
- `python -m compileall songryeon_core main.py`
  - 통과
- `python -m pytest`
  - 58 passed in 344.83s
- `python main.py smoke-test`
  - 첫 실행은 출력 없이 exit 1로 종료되어 stderr/stdout 병합 재실행
  - 재실행 결과 `SMOKE_TEST_OK`

## 6. 남은 위험

이번 code guard는 넓은 자연어 의미 판단을 대신하지 않는다.

명시적으로 `read_doc` / `actual_tool_read_doc` / `supplied_document_context` 같은 역할 표현을 쓰는 경우의 장부 충돌만 막는다. 더 애매한 자연어 표현은 node_4 LLM 판단과 후속 설계 대상이다.

다음 후보:

- ORDER_129 구현: final search candidate count와 accumulated search candidate count 분리
- L3 per-document summary 설계 재개
- node_4의 문서 역할 claim 검사 coverage 확대
