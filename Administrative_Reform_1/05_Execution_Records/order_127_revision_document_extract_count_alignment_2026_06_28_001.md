# ORDER 127 Revision Document Extract Count Alignment 실행 기록

일시: 2026-06-28

## 배경

ORDER_126 live 테스트에서 terminal runtime view는 실제 `tool_result:read_doc` record 7개를 모두 표시했다.

그러나 node_0 material packet과 node_3 input brief는 `actual_read=3` / `actual_read_doc=3`으로 표시했다. route=2 handoff와 tool budget은 7개 record를 보고 있었기 때문에, revision read_doc 결과 일부가 downstream count 장부에 합류하지 않는 문제가 드러났다.

## 원인

- `build_l_loop_return_summary_frame()`는 L3/budget의 `read_doc_ids`를 우선 기준으로 삼았다.
- `build_node0_document_material_packet_frame()`도 return summary/L3의 `read_doc_ids`에 있는 문서만 `actual_tool_read_doc`으로 표시했다.
- node_3 brief의 actual read helper도 return summary count가 있으면 그 값을 우선 사용했다.

따라서 revision에서 추가 실행된 `tool_result:read_doc` / `tool_result:read_artifact` record가 DataStore에는 남아도, L3/return summary의 `read_doc_ids`에 반영되지 않으면 node_0 material packet과 node_3 brief count에서 빠질 수 있었다.

## 변경

- `songryeon_core/nodes/node_0_memory_supplier.py`
  - 실제 document extract record를 읽는 `_document_extract_sources()` / `_document_extract_doc_ids()` helper를 추가했다.
  - `build_l_loop_return_summary_frame()`가 L3/budget의 `read_doc_ids`와 실제 document extract record의 `doc_id`를 병합한다.
  - `build_node0_document_material_packet_frame()`가 return summary의 `read_doc_ids`에 빠진 document extract record도 `actual_tool_read_doc` 역할로 표시한다.

- `songryeon_core/nodes/node_2_handoff.py`
  - node_3 actual read helper가 return summary의 문서명과 DataStore document extract record 문서명을 병합한다.
  - actual read count는 병합된 문서명이 있으면 그 길이를 우선 사용한다.

- `tests/test_order_127_revision_document_extract_count_alignment.py`
  - stale L3/return summary + 추가 revision read_doc record 상황을 재현하는 pytest를 추가했다.

## 하지 않은 것

- L 검색 전략은 바꾸지 않았다.
- `read_doc` 예산은 바꾸지 않았다.
- node_3 문서별 의미 요약은 추가하지 않았다.
- node_4 guard는 약화하지 않았다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB는 건드리지 않았다.

## 검증

- `python -m compileall songryeon_core main.py`
  - 통과
- `python -m pytest tests/test_order_127_revision_document_extract_count_alignment.py`
  - 3 passed
- `python -m pytest`
  - 53 passed
- `python main.py smoke-test`
  - `SMOKE_TEST_OK`
