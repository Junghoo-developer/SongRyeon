# ORDER_131_SEARCH_CANDIDATE_SCOPE_SPLIT_V0

상태: 구현 발주서
작성일: 2026-06-29
선행 감사: `ORDER_129_SEARCH_CANDIDATE_COUNT_BASIS_AUDIT_V0`

## 1. 목표

`search_candidate_count`가 화면마다 다른 뜻으로 보이는 문제를 줄인다.

현재는 다음 두 범위가 같은 이름으로 섞일 수 있다.

- 최종/최신 L3 return summary 기준 검색 후보
- L3 initial/revision preserved frame 전체 누적 검색 후보

이번 발주는 이 둘을 분리한다.

## 2. 구현 방향

`Node3InputBriefFrame`에 다음 필드를 추가한다.

- `final_search_candidate_count`
- `final_search_candidate_documents`
- `accumulated_search_candidate_count`
- `accumulated_search_candidate_documents`

호환용 기존 필드인 `search_candidate_count`와 `search_candidate_documents`는 유지하되, 의미를 `final_search_candidate_*` alias로 고정한다.

## 3. 기준

최종 후보:

- node_0 document material packet의 `was_search_candidate=true` item 기준
- material packet이 없으면 L return summary의 `search_result_doc_ids` fallback
- identity 기준은 `doc_id`

누적 후보:

- L3 preserved info frame 전체의 `candidates[].doc_id` 기준
- initial/revision preserved frame을 모두 포함
- identity 기준은 `doc_id`

표시용 문서명은 내부 ID를 그대로 노출하지 않되, 같은 파일명이 여러 경로에 있으면 전체 path label로 구분한다.

## 4. 변경 범위

- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_3_reporter.py`
- `songryeon_core/nodes/node_4_gatekeeper.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/runtime/smoke_test.py`
- 관련 pytest

## 5. 금지

- L3 per-document summary 구현 금지
- 검색/read 예산 변경 금지
- L revision 전략 변경 금지
- node_4 guard 약화 금지
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 금지
- 휴리스틱으로 검색 후보를 재분류하는 것 금지

## 6. 완료 조건

- node_3 brief가 최종 후보와 누적 후보 count를 둘 다 가진다.
- legacy `search_candidate_count`는 final count와 일치한다.
- node_3 grounding block이 최종/누적 검색 후보 count를 분리 표시한다.
- node_4 count guard가 두 count를 각각 검증한다.
- terminal runtime이 두 count를 구분 표시한다.
- 같은 파일명 다른 doc_id 후보가 누적 후보 count에서 collapse되지 않는다.

## 7. 검증

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
