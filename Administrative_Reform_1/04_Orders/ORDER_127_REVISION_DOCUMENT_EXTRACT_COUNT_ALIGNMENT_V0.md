# ORDER 127: Revision Document Extract Count Alignment v0

## 목표

L revision 흐름에서 추가로 실행된 `read_doc` / `read_artifact` document extract record가 node_0 문서 장부와 node_3 input brief의 실제 원문 읽기 count에 빠지지 않게 한다.

## 배경

ORDER_126 live 테스트에서 terminal runtime view는 `tool_result:read_doc` record 7개를 전부 표시했다.

하지만 다른 장부는 다음처럼 더 작은 값을 보여줬다.

- `L 도구 예산`: `read_doc=7/10`
- `route=2 handoff`: `raw_extract_records=7`
- `node_0 document material packet`: `actual_read=3`
- `node_3 input brief`: `actual_read_doc=3`
- node_3 최종 grounding block: `실제 read_doc 도구 원문 읽기: 3개`

즉 실제 document extract record는 남아 있는데, node_0 material packet과 node_3 brief가 일부 L3/return summary의 `read_doc_ids`만 기준으로 삼아 revision read_doc 결과를 누락할 수 있었다.

## 구현 범위

1. `build_l_loop_return_summary_frame()`가 L3/budget의 `read_doc_ids`뿐 아니라, 같은 L run source 범위의 실제 `tool_result:read_doc` / `tool_result:read_artifact` record도 병합한다.
2. `build_node0_document_material_packet_frame()`가 return summary의 `read_doc_ids`에 빠진 document extract record도 `actual_tool_read_doc` 역할로 표시한다.
3. `record_node3_input_brief()`의 actual read count helper가 return summary 값만 믿지 않고, DataStore에 남은 document extract record를 병합해 count와 문서명을 만든다.
4. 의미 요약, 관련성 판단, 문서 우선순위 판단은 추가하지 않는다.

## 정보 등급

- document extract record의 존재, `data_id`, `doc_id`, `text` 존재 여부, `char_count`는 절대정보다.
- 이 발주서는 문서의 중요도나 의미를 판단하지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- 추가 pytest:
  - stale L3/return summary가 일부 read_doc만 들고 있어도 return summary가 실제 document extract record를 병합한다.
  - node_0 material packet이 revision read_doc 문서를 `actual_tool_read_doc`으로 표시한다.
  - node_3 input brief의 `actual_tool_read_doc_count`가 revision document extract record를 반영한다.

## 금지

- L 검색 전략 변경 금지
- read_doc 예산 변경 금지
- node_3 문서별 의미 요약 추가 금지
- node_4 guard 약화 금지
- W/R loop, scheduler, 외부 DB, 장기기억 DB 변경 금지
