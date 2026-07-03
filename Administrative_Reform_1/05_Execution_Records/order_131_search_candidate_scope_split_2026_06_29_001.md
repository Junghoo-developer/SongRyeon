# order_131_search_candidate_scope_split_2026_06_29_001

작성일: 2026-06-29
관련 발주서: `Administrative_Reform_1/04_Orders/ORDER_131_SEARCH_CANDIDATE_SCOPE_SPLIT_V0.md`
선행 감사: `Administrative_Reform_1/04_Orders/ORDER_129_SEARCH_CANDIDATE_COUNT_BASIS_AUDIT_V0.md`

## 1. 목적

`search_candidate_count`가 최종 후보와 누적 후보를 섞어 표시하던 문제를 분리했다.

기존 감사 결론:

- node_0 material packet / L return summary는 최신/최종 L3 기준 검색 후보에 가깝다.
- node_3 input brief는 L3 preserved frame 전체를 훑어 누적 후보에 가깝게 세고 있었다.
- 같은 파일명 다른 경로 후보가 document name 기준으로 collapse될 위험도 있었다.

## 2. 변경 내용

### 2.1 Node3InputBriefFrame 필드 추가

추가 필드:

- `final_search_candidate_count`
- `final_search_candidate_documents`
- `accumulated_search_candidate_count`
- `accumulated_search_candidate_documents`

호환용 기존 필드:

- `search_candidate_count`
- `search_candidate_documents`

기존 필드는 유지하되, 이제 `final_search_candidate_*`와 같은 값이어야 한다.

### 2.2 count source 분리

최종 후보:

- node_0 document material packet의 `was_search_candidate=true` item 기준
- material packet이 없으면 L return summary의 `search_result_doc_ids` fallback
- identity 기준은 `doc_id`

누적 후보:

- L3 preserved info frame 전체의 `candidates[].doc_id`
- initial/revision preserved frame 전체 포함
- identity 기준은 `doc_id`

표시용 label은 같은 파일명이 여러 경로에 있으면 전체 path로 구분한다.

### 2.3 node_3 grounding block 변경

기존:

- `검색 후보 문서: N개`

변경:

- `검색 후보 문서(최종): N개`
- `검색 후보 문서(누적): N개`

### 2.4 node_4 count guard 변경

node_4 code grounding count guard가 최종/누적 검색 후보 count를 각각 검증한다.

### 2.5 terminal view 변경

node_3 input brief runtime 표시가 다음처럼 분리된다.

- `search_candidates_final`
- `search_candidates_accumulated`

### 2.6 node_3 LLM payload 변경

`search_candidate_scope`를 추가했다.

포함 항목:

- `final_search_candidate`
- `accumulated_search_candidate`
- `legacy_search_candidate_count_is`
- `boundary`

## 3. 테스트

추가 pytest:

- `tests/test_order_131_search_candidate_scope_split.py`

검증한 것:

- final 후보와 accumulated 후보가 다른 source에서 온다.
- legacy `search_candidate_count`는 final 후보 count와 같다.
- 같은 파일명 다른 doc_id 후보가 accumulated 후보에서 collapse되지 않는다.
- material packet이 없으면 final 후보가 L return summary `search_result_doc_ids`로 fallback된다.
- node_3 grounding block이 최종/누적 count를 분리 표시한다.

## 4. 검증 결과

- `python -m pytest tests/test_order_131_search_candidate_scope_split.py tests/test_order_123_actual_read_doc_vs_context_pack_count.py tests/test_order_130_document_evidence_role_claim_guard.py`
  - 11 passed
- `python -m compileall songryeon_core main.py`
  - 통과
- `python -m pytest`
  - 60 passed in 307.86s
- `python main.py smoke-test`
  - `SMOKE_TEST_OK`

## 5. 하지 않은 것

- L3 per-document summary 구현 없음
- 검색/read 예산 변경 없음
- L revision 전략 변경 없음
- node_4 guard 약화 없음
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 없음
- 휴리스틱으로 검색 후보 재분류 없음

## 6. 남은 위험

이번 작업은 candidate count scope를 분리했지만, L3가 어떤 후보를 더 읽을지 고르는 전략은 바꾸지 않았다.

다음 후보는 L3 per-document summary 재개 또는 node_3 context 폭탄 정리다.
