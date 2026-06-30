# order_129_search_candidate_count_basis_audit_2026_06_28_001

작성일: 2026-06-28
관련 발주서: `Administrative_Reform_1/04_Orders/ORDER_129_SEARCH_CANDIDATE_COUNT_BASIS_AUDIT_V0.md`

## 1. 감사 범위

이번 기록은 구현 없이 search candidate count 기준만 감사한다.

확인한 파일:

- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/l3_result_keeper.py`
- `songryeon_core/runtime/terminal_view.py`
- `songryeon_core/core/schemas.py`
- `Administrative_Reform_1/04_Orders/ORDER_124_NODE0_POST_L_DOCUMENT_MATERIAL_PACKET_V0.md`
- `Administrative_Reform_1/04_Orders/ORDER_128_NODE3_ACTUAL_READ_DOC_IDENTITY_KEY_V0.md`

## 2. 결론 요약

`read_doc` count 쪽은 ORDER_128 이후 doc_id identity 기준으로 많이 정렬됐다.

반면 `search_candidate_count`는 현재 같은 이름 아래 두 가지 범위가 섞일 수 있다.

- node_0 material packet / L return summary: 최신 또는 최종 L3 achievement/return summary가 들고 온 `search_result_doc_ids` 중심
- node_3 input brief: namespace 안의 모든 `node_output:L3...preserved_info_frame` record 후보를 훑은 누적 후보 중심

따라서 revision이 많은 턴에서는 node_0은 `search_candidates=7`, node_3 brief는 `search_candidates=44`처럼 다르게 보일 수 있다.

이것은 단순히 "숫자가 틀렸다"기보다, 같은 label이 서로 다른 scope를 가리키는 상태에 가깝다.

## 3. 항목별 감사

### 3.1 node_0 material packet

파일 위치:

- `songryeon_core/nodes/node_0_memory_supplier.py`

현재 count source:

- `build_node0_document_material_packet_frame()`은 `return_summary_payload.get("search_result_doc_ids")`를 먼저 사용한다.
- 없으면 최신 L3 payload의 `search_result_doc_ids`를 fallback으로 사용한다.

현재 identity 기준:

- `item_map`의 key는 `doc_id`다.
- filename이 아니라 전체 `doc_id` 기준으로 material item을 만든다.

실제로 의미하는 candidate scope:

- 최종 L return summary 또는 최신 L3 achievement가 보존한 검색 후보 문서 집합에 가깝다.
- 모든 revision preserved frame의 누적 후보라기보다는 최종 요약 후보에 가깝다.

문제 여부:

- 자체 기준은 비교적 안전하다.
- 다만 사용자-facing label이 node_3의 `search_candidate_count`와 같으면 혼동이 생긴다.

수정 위험도:

- 낮음에서 중간.
- node_0 자체보다 downstream label/field 분리가 더 중요하다.

바로 고쳐도 되는지:

- 구현 전 설계 결재 권장.
- `final_search_candidate_count`라는 명시적 이름으로 분리하는 것이 안전하다.

### 3.2 L loop return summary

파일 위치:

- `songryeon_core/nodes/node_0_memory_supplier.py`

현재 count source:

- `build_l_loop_return_summary_frame()`은 최신 L3 achievement payload의 `search_result_doc_ids` 길이를 사용한다.
- 없으면 `candidate_count`를 fallback으로 사용한다.

현재 identity 기준:

- `search_result_doc_ids` list에 들어온 doc_id 기준이다.

실제로 의미하는 candidate scope:

- 최신 L3 achievement 기준의 검색 후보 수다.

문제 여부:

- return summary 자체는 "최신/최종 L3 기준"으로 보면 일관적이다.
- 하지만 accumulated candidate와 구분하는 field name은 없다.

수정 위험도:

- 중간.
- L3 achievement schema와 node_0 material packet, terminal label이 함께 움직여야 한다.

바로 고쳐도 되는지:

- 설계 결재 권장.
- 최소 구현은 기존 field를 유지하고 새 field를 추가하는 방향이 안전하다.

### 3.3 node_3 input brief

파일 위치:

- `songryeon_core/nodes/node_2_handoff.py`

현재 count source:

- `_search_candidate_documents()`가 DataStore 전체 record 중 namespace에 속한 `node_output:L3...preserved_info_frame`을 모두 훑는다.
- 각 preserved frame의 `candidates`에서 `doc_id`를 꺼낸다.

현재 identity 기준:

- `doc_id`를 `_document_name(doc_id)`로 바꾼 뒤 `_unique_strings(names)`로 중복 제거한다.
- 즉 count identity가 doc_id가 아니라 표시용 document name이다.

실제로 의미하는 candidate scope:

- initial L3 preserved frame과 revision L3 preserved frame을 모두 포함한 누적 후보 문서명 집합에 가깝다.

문제 여부:

- revision이 많으면 node_0 material packet보다 크게 나올 수 있다.
- 같은 파일명 다른 경로 문서는 하나로 접힐 수 있다.
- ORDER_128에서 actual read_doc에 대해 해결한 identity 문제가 search candidate 쪽에는 아직 남아 있다.

수정 위험도:

- 중간.
- node_3 prompt, final grounding block, node_4 count guard와 연결되어 있어 label 변경이 필요하다.

바로 고쳐도 되는지:

- 설계 결재 권장.
- `accumulated_search_candidate_count`와 `final_search_candidate_count`를 분리할지 먼저 결정해야 한다.

### 3.4 terminal/runtime display

파일 위치:

- `songryeon_core/runtime/terminal_view.py`

현재 count source:

- node_3 input brief 표시에서는 `node3_brief["search_candidate_documents"]` list 길이를 세어 `search_candidates`로 출력한다.

현재 identity 기준:

- node_3 brief가 만든 document name list 기준이다.

실제로 의미하는 candidate scope:

- node_3 brief의 누적 preserved frame 기반 후보 문서명 수다.

문제 여부:

- terminal에 node_0 material packet의 `search_candidate_count`도 따로 보이면, 같은 `search_candidates` label 아래 다른 숫자가 같이 나타날 수 있다.

수정 위험도:

- 낮음.
- 표시 label만 바꾸는 것은 쉽지만, schema 의미 정리 없이 표시만 바꾸면 근본 해결은 아니다.

바로 고쳐도 되는지:

- 후속 구현에서 schema field와 함께 고치는 것이 낫다.

### 3.5 node_3 final grounding block

파일 위치:

- `songryeon_core/nodes/node_3_reporter.py`

현재 count source:

- `brief_frame.search_candidate_count`

현재 identity 기준:

- node_3 input brief가 채운 count 기준이다.

실제로 의미하는 candidate scope:

- 현재 구현상 누적 L3 preserved 후보 문서명 count에 가깝다.

문제 여부:

- 사용자는 이 숫자를 node_0 material packet의 최종 검색 후보 수와 같은 뜻으로 이해할 수 있다.
- final answer에서 `검색 후보 문서: 44개`가 나오면 "최종 후보가 44개였다"로 오해될 수 있다.

수정 위험도:

- 중간.
- node_4 grounding count guard가 이 count를 비교하므로, field 추가/label 변경 시 test 보강이 필요하다.

바로 고쳐도 되는지:

- 설계 결재 후 후속 발주에서 고치는 것이 안전하다.

## 4. 원인 정리

원인은 크게 두 가지다.

1. scope 불일치
   - node_0은 최종/최신 L3 summary 계열을 본다.
   - node_3는 모든 L3 preserved frame 후보를 본다.

2. identity 불일치
   - node_0은 doc_id 기준이다.
   - node_3 search candidate list는 document name 기준으로 접는다.

## 5. 추천 후속 작업

후속 구현은 L3 per-document summary보다 먼저 하는 것을 권장한다.

권장 방향:

- 기존 `search_candidate_count`의 의미를 바로 바꾸지 말고, 새 field를 추가한다.
- 후보 field:
  - `final_search_candidate_count`
  - `final_search_candidate_documents`
  - `accumulated_search_candidate_count`
  - `accumulated_search_candidate_documents`
- node_0 material packet은 final/canonical candidate source로 유지한다.
- node_3 brief는 누적 후보를 보존하되, final grounding block에는 label을 명확히 한다.
- search candidate identity는 doc_id 기준으로 세고, 사용자 표시용 label은 별도 생성한다.

## 6. 이번에 하지 않은 것

- code logic 수정 없음
- schema field 추가 없음
- L3 per-document summary 구현 없음
- prompt 수정 없음
- 테스트 추가 없음
- live qwen 재실행 없음

## 7. 검증

이번 작업은 감사/문서화 전용이라 compileall, pytest, smoke-test는 실행하지 않았다.

다음 구현 발주에서 최소 검증은 다음이 필요하다.

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- initial/revision preserved frame이 함께 있을 때 final candidate count와 accumulated candidate count가 분리되는 pytest
- 같은 파일명 다른 doc_id candidate가 collapse되지 않는 pytest
