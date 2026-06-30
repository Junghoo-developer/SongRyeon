# order_142_external_graph_db_adapter_boundary_2026_06_30_001

## 1. 작업 요약

ORDER_142 후보 발주를 사용자 승인에 따라 external graph DB adapter boundary 구현으로 승격했다.

이번 작업은 Neo4j/SQLite/vector DB를 실제 연결하지 않는다.

송련 내부 `GraphMemoryNodeFrame`, `GraphMemoryEdgeFrame`, `GraphMemorySnapshotFrame`을 저장/조회하는 protocol과 in-memory adapter를 추가해 외부 DB 연결 전 경계를 잠갔다.

## 2. 핵심 변경

- `songryeon_core/core/graph_memory_store.py`
  - `GraphMemoryStoreProtocol`
  - `InMemoryGraphMemoryStore`
  - Vessel 이름 상수:
    - `SONGRYEON_VESSEL_SERVICE_NAME = "songryeon-neo4j-vessel"`
    - `SONGRYEON_VESSEL_DATABASE_NAME = "songryeon_vessel"`
    - `SONGRYEON_GRAPH_NAMESPACE = "songryeon_core_graph_v0"`
- `tests/test_order_142_graph_memory_store_boundary.py`
  - node/edge upsert와 조회
  - same-payload idempotent upsert
  - same-id different-payload collision rejection
  - source provenance round-trip
  - snapshot count round-trip
  - semantic topic/embedding field 미생성
  - Vessel 이름 예약 확인

## 3. 금지선

- Neo4j driver/dependency 추가 없음.
- SQLite/vector DB 추가 없음.
- 의미 검색 없음.
- embedding retrieval 없음.
- semantic topic/meaning cluster 생성 없음.
- 외부 DB record가 내부 graph memory schema를 우회하는 경로 없음.

## 4. 검증

다음 명령을 실행했다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_142_graph_memory_store_boundary.py
python -m pytest tests/test_order_139_graph_memory_foundation.py tests/test_order_140_r_loop_frame_state_machine.py tests/test_order_142_graph_memory_store_boundary.py
python -m pytest
python main.py smoke-test
git diff --check
```

결과:

- `compileall`: 통과
- ORDER_142 단독 pytest: `7 passed`
- ORDER_139/140/142 graph/R-loop 묶음 pytest: `19 passed`
- 전체 pytest: `96 passed`
- smoke-test: `SMOKE_TEST_OK`
- `git diff --check`: 통과

## 5. 확인된 경계

- in-memory store에 graph node/edge를 upsert하고 다시 조회할 수 있다.
- 같은 node/edge payload를 다시 upsert해도 중복되지 않는다.
- 같은 ID에 다른 payload가 들어오면 collision으로 거부한다.
- `source_graph_node_ids`, `source_trace_ids`, `source_data_ids`가 round-trip 된다.
- `songryeon-neo4j-vessel`, `songryeon_vessel`, `songryeon_core_graph_v0` 이름은 예약했지만 실제 Neo4j 연결은 열지 않았다.
- adapter는 semantic topic, meaning cluster, embedding id를 생성하지 않는다.
