# ORDER_124 Node0 Post-L Document Material Packet v0

## 목표

L 루프 이후 node_0이 문서 관련 절대정보 장부를 정리해 node_2와 node_3가 사용할 수 있게 만든다.

이번 발주는 문서 의미 요약이 아니라, 검색 후보 / 실제 read_doc / node_3 공급 context / 읽지 않은 후보를 같은 표에서 구분하는 `document_material_packet` 또는 동등한 frame을 제안한다.

## 배경

ORDER_123에서 실제 `read_doc` 도구 원문 읽기 수와 node_3 공급 문서 context 수는 구조적으로 분리되었다.

하지만 현재 구조는 문서 장부가 여러 곳에 흩어져 있다.

- `L3:preserved_info_frame`: 검색 후보 목록
- `L3:achievement_frame`: `read_doc_ids`, `search_result_doc_ids`, L3 성패 판단
- `L:return_summary_frame`: actual read count, search candidate count, budget 잔량
- `L:document_context_pack_frame`: node_3에게 공급된 whole-document context included/excluded 목록
- `memory_packet:node_1:loop_return_summary`: node_1 재라우팅을 위한 짧은 summary items
- `node_3:input_brief_frame`: node_3에게 공급되는 최종 brief

즉 조각 기능은 이미 있으나, node_0이 L 이후 문서 재료를 한 장부로 정리하는 전용 packet은 아직 없다.

## 정보 경계

node_0이 해도 되는 일:

- 문서 ID와 문서명 복사
- 검색 후보 여부 표시
- 실제 `read_doc` / `read_artifact` 원문 읽기 여부 표시
- node_3 supplied context 포함 여부 표시
- unread candidate 여부 표시
- 각 문서 항목의 source data id / trace id 연결
- count, rank, char_count 같은 절대정보 복사

node_0이 하면 안 되는 일:

- 문서 중요도 의미 판단
- 문서 내용 요약
- 사용자 의도와의 관련성 판단
- 여러 문서의 결론 종합
- 읽지 않은 문서를 읽은 문서처럼 표현

## 제안 구조

새 frame 후보:

```text
Node0DocumentMaterialPacketFrame
```

또는 기존 `MemoryPacketPayload`에 다음 material section을 추가한다.

```text
document_material_items:
- doc_id
- document_name
- source_roles
  - search_candidate
  - actual_tool_read_doc
  - supplied_document_context
  - unread_candidate
- search_candidate_rank
- actual_read_rank
- supplied_context_rank
- char_count
- source_trace_ids
- source_data_ids
- generated_by=CODE:NODE0_DOCUMENT_MATERIAL_PACKET
- info_class=absolute_material_index
- semantic_judgement_status=not_run
```

MVP에서는 frame 분리가 더 안전하다.

## 입력 소스 후보

- `L3PreservedInfoFrame.candidates`
- `L3AchievementFrame.read_doc_ids`
- `L3AchievementFrame.search_result_doc_ids`
- `LLoopReturnSummaryFrame.read_doc_ids`
- `LLoopReturnSummaryFrame.search_result_doc_ids`
- `DocumentContextPackFrame.included_documents`
- `DocumentContextPackFrame.excluded_documents`
- `tool_result:read_doc`
- `tool_result:read_artifact`

## 배선 후보

1. L loop가 끝난 뒤 `record_l_loop_return_summary_for_node1()` 근처에서 node_0 document material frame을 기록한다.
2. frame id를 `memory_packet:node_1:loop_return_summary` 또는 node_2 input source_data_ids에 포함한다.
3. node_2 handoff와 node_3 input brief는 이 frame을 읽어 문서 목록/count/역할을 표시한다.
4. terminal view는 document material packet 요약을 표시한다.

## 완료 조건 후보

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`

추가 pytest:

- 검색 후보 10개, 실제 read_doc 2개, supplied context 10개 상황에서 document material items가 10개 문서 단위로 정렬된다.
- 각 item은 `search_candidate`, `actual_tool_read_doc`, `supplied_document_context`, `unread_candidate` role을 독립적으로 가진다.
- 실제 read_doc이 아닌 supplied context를 actual read로 표시하지 않는다.
- unread candidate는 search candidate이지만 actual read가 아닌 문서로만 계산된다.
- node_0 packet/frame은 `semantic_judgement_status=not_run`을 유지한다.
- node_3 brief가 document material packet id를 source_data_ids에 포함한다.

## 제외 범위

- L3 문서 요약 생성은 이번 발주에서 하지 않는다.
- node_5 기억 압축, 장기기억 DB, 벡터 DB, scheduler는 열지 않는다.
- node_4 자동 재작성 루프는 열지 않는다.
- W/R loop는 열지 않는다.
- same-turn L reroute 횟수는 늘리지 않는다.

## 다음 후보

ORDER_125 후보: L3 또는 별도 노드가 실제 읽은 문서별 요약 frame을 만들지 여부를 설계한다.

이때 문서 1개에 대응하는 요약은 `relative`, 여러 문서 묶음 요약은 `mixed`로 분류해야 하며, node_4 검증/출처 표시 경계를 별도로 설계해야 한다.
