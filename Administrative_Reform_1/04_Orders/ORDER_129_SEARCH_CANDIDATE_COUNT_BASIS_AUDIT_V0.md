# ORDER_129_SEARCH_CANDIDATE_COUNT_BASIS_AUDIT_V0

상태: 감사 전용 발주서
작성일: 2026-06-28

## 1. 목표

L루프가 여러 차례 검색/revision을 수행한 뒤 `search_candidate_count`가 화면마다 다르게 보이는 원인을 구현 전에 감사한다.

특히 다음 숫자들이 서로 다른 기준으로 세어지는지 확인한다.

- L return summary의 `search_candidate_count`
- node_0 document material packet의 `search_candidate_count`
- node_3 input brief의 `search_candidate_count`
- terminal/runtime의 `search_candidates`
- node_3 final grounding block의 `검색 후보 문서`

이번 발주는 L3 문서별 요약을 만들기 전, "검색 후보"라는 절대정보 count의 기준을 먼저 잠그기 위한 것이다.

## 2. 배경

ORDER_126부터 ORDER_128까지의 작업으로 실제 `read_doc` 원문 읽기 수는 많이 안정됐다.

최근 live test 기준으로 다음 count는 정렬됐다.

- runtime document extract tool results: 7
- L budget `read_doc`: 7
- route=2 raw extract records: 7
- node_0 material packet `actual_read`: 7
- L return summary `actual_read`: 7
- node_3 input brief `actual_read_doc`: 7
- final grounding `실제 read_doc 도구 원문 읽기`: 7

하지만 search candidate 쪽은 아직 기준이 흔들린다.

예를 들어 revision-heavy turn에서 node_0 material packet은 `search_candidates=7`로 보이는데, node_3 input brief는 `search_candidates=44`처럼 훨씬 크게 보일 수 있다.

이 차이가 버그인지, 서로 다른 scope를 세는 정상 동작인지, 사용자-facing label을 나눠야 하는지 감사한다.

## 3. 감사 질문

1. node_0 material packet은 search candidate를 어떤 source와 identity key로 세는가?
2. node_3 input brief는 search candidate를 어떤 source와 identity key로 세는가?
3. L3 preserved frame이 initial/revision마다 쌓일 때 candidate count가 누적되는가?
4. 같은 파일명 다른 경로 문서가 search candidate count에서 합쳐질 위험이 있는가?
5. terminal/runtime과 final grounding block이 어떤 count source를 사용자-facing count로 쓰는가?
6. L3 per-document summary를 열기 전에 `final_search_candidate_count`와 `accumulated_search_candidate_count`를 분리해야 하는가?

## 4. 감사 범위

- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/l3_result_keeper.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/nodes/node_3_reporter.py`
- `songryeon_core/nodes/node_4_gatekeeper.py`
- `songryeon_core/core/schemas.py`
- 관련 pytest/smoke test

## 5. 금지

- 이번 발주에서 code logic을 고치지 않는다.
- L3 per-document summary frame을 구현하지 않는다.
- search/read 예산을 늘리지 않는다.
- L revision 검색 전략을 바꾸지 않는다.
- node_4 guard를 약화하지 않는다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB를 열지 않는다.
- 휴리스틱으로 candidate를 재분류하지 않는다.

## 6. 감사 완료 조건

감사 보고서에는 항목마다 다음을 적는다.

- 파일 위치
- 현재 count source
- 현재 identity 기준
- 실제로 의미하는 candidate scope
- 문제 여부
- 수정 위험도
- 바로 고칠 수 있는지, 설계 결재가 필요한지

## 7. 후속 구현 후보

감사 결과 필요하다고 판단되면 후속 발주에서 다음 중 하나를 구현한다.

1. node_3 brief가 node_0 material packet의 `was_search_candidate` item을 canonical source로 사용한다.
2. `final_search_candidate_count`와 `accumulated_search_candidate_count`를 schema에서 분리한다.
3. search candidate list도 ORDER_128처럼 filename이 아니라 `doc_id` identity 기준으로 세고, 사용자 표시용 label만 별도로 만든다.
4. terminal/final grounding label을 `최종 검색 후보`와 `누적 검색 후보`로 나눈다.

## 8. 권장 판단

이번 감사의 예상 결론은 다음이다.

`search_candidate_count` 하나에 final candidate set과 accumulated revision candidate set을 동시에 담으려 하면 계속 헷갈린다.

따라서 L3 문서별 요약을 열기 전에 search candidate count의 scope를 명시적으로 분리하거나, 사용자-facing count의 canonical source를 하나로 정해야 한다.
