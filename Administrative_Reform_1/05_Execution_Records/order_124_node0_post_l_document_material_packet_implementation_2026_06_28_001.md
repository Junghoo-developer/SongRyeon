# ORDER_124 Node0 Post-L Document Material Packet 구현 기록 2026-06-28 001

## 구현 요약

L 이후 node_0이 문서별 장부를 만드는 `Node0DocumentMaterialPacketFrame`을 추가했다.

이 frame은 의미 요약을 만들지 않고, 기존 구조화 record에서 다음 절대정보만 복사/정렬한다.

- 검색 후보 여부
- 실제 `read_doc` / `read_artifact` 도구 원문 읽기 여부
- node_3 supplied document context 포함 여부
- document context pack 제외 여부
- unread candidate 여부
- 문서별 rank/count/source id

## 핵심 변경

- `songryeon_core/core/schemas.py`
  - `Node0DocumentMaterialItem`
  - `Node0DocumentMaterialPacketFrame`
  - `validate_node0_document_material_packet_frame`
- `songryeon_core/nodes/node_0_memory_supplier.py`
  - `record_node0_document_material_packet`
  - `build_node0_document_material_packet_frame`
  - L loop return summary 기록 시 document material packet도 함께 기록
  - loop return memory packet에 `document_material_packet_status` item 추가
- `songryeon_core/runtime/dry_run.py`
  - node_2 input source 범위에 document material frame id 추가
- `songryeon_core/nodes/node_2_handoff.py`
  - route=2 handoff와 node_3 input brief가 document material packet을 읽고 보존
  - node_3 LLM payload에 raw internal id 없이 문서명/역할/rank/count만 전달
- `songryeon_core/runtime/terminal_view.py`
  - runtime에 `node_0 document material packet` 섹션 표시
  - node_3 input brief에 `document_materials` count 표시
- `songryeon_core/prompts/node_3_reporter_v0.md`
  - document material packet은 의미 요약이 아니라 code-built document ledger임을 명시

## 테스트

추가 pytest:

- `tests/test_order_124_node0_document_material_packet.py`

확인한 사항:

- 검색 후보 3개, 실제 read_doc 2개, supplied context 3개 상황에서 문서별 item 3개가 만들어진다.
- unread candidate는 search candidate이면서 actual read가 아닌 문서만 잡힌다.
- node_0 document material packet은 `semantic_judgement_status=not_run`이다.
- route=2 handoff가 document material packet id/count를 보존한다.
- node_3 brief와 LLM payload가 document material ledger를 받는다.
- node_3 LLM payload의 material items에는 raw `source_data_ids`가 직접 들어가지 않는다.

## 검증 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: `48 passed`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `python main.py fake-turn "문서 장부 확인: 검색 후보, 실제 read_doc, 공급 context, unread 후보를 구분해줘" --pretty`: 통과

fake-turn 확인값:

- runtime `node_0 document material packet`: `items=12 / search_candidates=12 / actual_read=2 / supplied_contexts=11 / unread_candidates=10`
- runtime `node_3 input brief`: `document_materials=12`
- node_3 brief 내부 material packet: `items=12 / unread_candidates=10`

## 제외한 것

- L3 문서 요약은 구현하지 않았다.
- node_0은 문서 중요도/관련성/요약 의미 판단을 만들지 않는다.
- 장기기억 DB, vector DB, scheduler, W/R loop, node_5 압축, node_4 자동 재작성 루프는 열지 않았다.
