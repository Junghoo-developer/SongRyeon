# ORDER 151: L Loop Activity Ledger For Graph Backup v0

## 1. Goal

L루프가 한 턴에서 만든 주요 산출물과 문서/코드 근거 좌표를 `LLoopActivityLedgerFrame`으로 한 번 더 묶는다.

이 작업은 L 검색 전략을 바꾸지 않는다. 의미 판단, 요약, 그래프 DB 연결도 하지 않는다.
목표는 나중에 `graph:raw_capsule:{turn_id}`와 L 활동 산출물을 안전하게 연결할 수 있는 절대정보 장부 표면을 만드는 것이다.

## 2. Background

ORDER_148~150으로 R루프에는 다음 기반이 생겼다.

- raw capsule 사이 `NEXT` edge
- R graph traversal candidate surface
- R turn graph access ledger
- multi-step R dry-run traversal

반면 L루프는 `LLoopResult`, `LLoopReturnSummaryFrame`, `Node0DocumentMaterialPacketFrame` 등 원재료는 충분히 남지만, "이번 L이 어떤 DataStore record를 만들고 어떤 문서/코드 좌표를 남겼는가"를 한 장으로 모은 전용 ledger는 없다.

## 3. Scope

추가한다.

- `LLoopActivityLedgerFrame`
- `record_l_loop_activity_ledger()`
- `run_dry_turn()` 배선
- runtime 표시
- smoke/pytest 검증

열지 않는다.

- L 검색 전략 변경
- L3 의미 판단 변경
- R live route 확장
- 외부 DB/Neo4j 연결
- 그래프 노드/edge 실제 연결
- summary layer

## 4. Frame Contract

`LLoopActivityLedgerFrame`은 code-generated absolute ledger다.

필수 경계:

- `generated_by=CODE:L_LOOP_ACTIVITY_LEDGER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`
- `turn_capsule_graph_node_id=graph:raw_capsule:{turn_id}`

주요 필드:

- `run_frame_data_ids`
- `goal_data_ids`
- `query_plan_data_ids`
- `query_data_ids`
- `control_data_ids`
- `tool_result_data_ids`
- `tool_budget_data_ids`
- `continuation_data_ids`
- `revision_*_data_ids`
- `preserved_data_ids`
- `achievement_data_ids`
- `return_summary_frame_id`
- `document_material_packet_frame_id`
- `output_data_ids`
- `search_candidate_doc_ids`
- `read_doc_ids`
- `read_code_file_paths`
- `activity_records`
- `source_trace_ids`
- `source_data_ids`

## 5. Rules

- code는 기존 record ID와 count만 복사한다.
- code는 "중요한 문서", "관련 문서", "성공한 검색" 같은 의미 판단을 새로 만들지 않는다.
- `activity_records`는 `stage`, `data_id`, `source_field`만 담는다.
- 모든 activity data id는 `source_data_ids`에 포함되어야 한다.
- count는 대응 list 길이와 일치해야 한다.

## 6. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_151_l_loop_activity_ledger.py
python -m pytest
python main.py smoke-test
```

## 7. Done Criteria

- dry turn에서 `L:activity_ledger_frame`이 DataStore에 기록된다.
- ledger는 `L:return_summary_frame`과 `node_0:document_material_packet_frame`을 source로 가진다.
- ledger는 read_doc/search candidate/code file 좌표를 count와 함께 보존한다.
- ledger의 `semantic_judgement_status`는 `not_run`이다.
- smoke-test가 ledger 존재와 주요 source 연결을 확인한다.
