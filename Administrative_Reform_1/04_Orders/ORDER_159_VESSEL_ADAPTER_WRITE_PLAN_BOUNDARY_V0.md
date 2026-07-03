# ORDER_159_VESSEL_ADAPTER_WRITE_PLAN_BOUNDARY_V0

## 목표

ORDER_158의 `GraphMemoryExportPacket`을 입력으로 받아, 외부 Vessel/Neo4j에 실제로 쓰기 전에 code-generated absolute `GraphVesselWritePlan`을 만든다.

이번 발주는 “DB write”가 아니라 “DB write 직전 계획서”다.

## 배경

ORDER_142에서 `songryeon-neo4j-vessel` 이름과 graph store boundary가 예약되었다.

ORDER_158에서 DataStore 안 graph/source record를 export packet으로 묶었다.

다음 단계에서 바로 Neo4j driver를 붙이면 다음 위험이 있다.

- 어떤 record를 썼는지 추적이 흐려질 수 있다.
- node/edge/source payload write 순서가 암묵화될 수 있다.
- graph integrity 실패 상태에서도 외부 write가 시도될 수 있다.
- 외부 DB adapter가 의미 판단 필드를 몰래 추가할 수 있다.

따라서 먼저 export packet을 읽고 write operation 목록만 생성하는 boundary를 둔다.

## 구현 범위

1. 새 모듈을 추가한다.
   - 후보 파일: `songryeon_core/core/graph_vessel_adapter.py`

2. 새 plan을 만든다.
   - `GraphVesselWritePlan`
   - `GraphVesselWriteOperation`
   - data type: `graph_vessel:write_plan`
   - generator: `CODE:GRAPH_VESSEL_ADAPTER_BOUNDARY`

3. write operation 종류를 좁게 고정한다.
   - `upsert_source_payload`
   - `upsert_graph_node`
   - `upsert_graph_edge`
   - `upsert_support_record`

4. operation 순서를 code가 고정한다.
   - source payload
   - graph node
   - graph edge
   - support record

5. graph integrity가 실패한 export packet은 외부 write plan을 `blocked_integrity_failed`로 닫는다.
   - operation list는 비운다.
   - 실패 이유와 integrity summary는 plan에 남긴다.

6. plan은 `DataStore`와 `TraceStore`에 기록한다.

## 메타정보 경계

- `generated_by=CODE:GRAPH_VESSEL_ADAPTER_BOUNDARY`
- `info_class=absolute`
- `semantic_judgement_status=not_run`
- `external_write_status=not_run`

이번 작업은 record ID, data type, operation order, integrity status 같은 code-checkable absolute 정보만 생성한다.

## 금지

- Neo4j driver 추가 금지
- 외부 DB 연결 금지
- 실제 write 금지
- LLM 요약/상대정보/혼합정보 생성 금지
- 의미축 생성 금지
- R live route 변경 금지
- scheduler/장기기억 DB 변경 금지

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_159_vessel_adapter_boundary.py -q`
- `python main.py fast-test --profile graph`
- 가능하면 `python -m pytest`, `python main.py smoke-test`

## 기대 결과

ORDER_159 이후에는 외부 DB adapter가 export packet을 바로 해석해 임의로 쓰는 것이 아니라, 먼저 write plan을 만들고 그 plan에 적힌 operation만 수행하는 구조로 갈 수 있다.

즉 다음 ORDER에서 Neo4j/Vessel write를 열더라도 “무엇을 어떤 순서로 쓸지”가 이미 DataStore/TraceStore에 남는다.
