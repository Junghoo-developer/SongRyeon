# ORDER 128 Node3 Actual Read Doc Identity Key 실행 기록

일시: 2026-06-28

## 배경

ORDER_127 이후 runtime, L budget, route=2 handoff, node_0 material packet, L return summary는 실제 read_doc count를 7개로 맞췄다.

하지만 live qwen 테스트에서 node_3 input brief와 최종 grounding count는 6개로 줄었다.

## 원인

node_3 actual read document 목록을 만들 때 document extract record의 `doc_id`를 파일명으로 줄인 뒤 중복 제거했다.

예를 들어 아래 두 문서는 서로 다른 문서다.

- `04_Orders/README.md`
- `05_Execution_Records/README.md`

하지만 파일명만 쓰면 둘 다 `README.md`가 되어 하나로 합쳐질 수 있었다.

## 변경

- `songryeon_core/nodes/node_2_handoff.py`
  - `_actual_tool_read_doc_documents()`가 중복 제거 기준을 파일명 대신 `doc_id` 또는 document extract record identity로 잡게 했다.
  - 표시 label은 파일명이 유일하면 짧은 파일명을 쓰고, 같은 파일명이 여러 `doc_id`에 있으면 경로 포함 label을 쓴다.
  - `_read_doc_display_labels()` helper를 추가했다.

- `tests/test_order_128_node3_actual_read_doc_identity_key.py`
  - `04_Orders/README.md`와 `05_Execution_Records/README.md`가 서로 다른 실제 read_doc 문서로 2개 count 되는지 확인한다.

## 하지 않은 것

- node_3 LLM prompt는 바꾸지 않았다.
- grounding block 정책은 바꾸지 않았다.
- node_4 guard는 약화하지 않았다.
- L 검색 전략과 read_doc 예산은 바꾸지 않았다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB는 건드리지 않았다.

## 검증

- `python -m compileall songryeon_core main.py`
  - 통과
- `python -m pytest tests/test_order_127_revision_document_extract_count_alignment.py tests/test_order_128_node3_actual_read_doc_identity_key.py`
  - 4 passed
- `python -m pytest`
  - 54 passed
- `python main.py smoke-test`
  - `SMOKE_TEST_OK`
