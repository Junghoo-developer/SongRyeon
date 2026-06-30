# ORDER_142_EXTERNAL_GRAPH_DB_ADAPTER_BOUNDARY_V0_CANDIDATE

## Candidate Status

이 문서는 후보 발주서다.

ORDER_139의 in-memory/DataStore 기반 graph memory foundation이 안정되기 전에는 구현하지 않는다.

외부 DB를 바로 붙이는 발주가 아니다.

## 1. 목표

외부 graph DB를 붙이기 전에 adapter boundary를 설계한다.

핵심:

```text
송련 내부 graph frame/schema가 먼저다.
외부 DB는 그 frame을 저장/조회하는 adapter일 뿐이다.
```

이번 후보 발주의 목적은 Neo4j/SQLite/vector DB 중 하나를 바로 고르는 것이 아니라, 어떤 DB를 붙여도 송련 메타정보 원칙이 깨지지 않게 boundary를 정하는 것이다.

## 2. 선행 조건

- ORDER_139 완료.
- GraphMemoryNodeFrame/Edge/Snapshot의 최소 schema가 존재.
- graph node idempotency가 테스트로 잠겨 있어야 한다.

## 3. Adapter 후보 인터페이스

후보:

```text
GraphMemoryStoreProtocol
InMemoryGraphMemoryStore
JsonlGraphMemoryStore
ExternalGraphMemoryStoreAdapter
```

필수 method 후보:

```text
upsert_node(node_frame)
upsert_edge(edge_frame)
get_node(node_id)
list_children(node_id)
list_core_ego_entries(axis)
snapshot()
```

adapter는 의미 판단을 하지 않는다.

adapter는 저장/조회만 한다.

## 4. 금지

- Neo4j/SQLite/vector DB 의존성을 바로 추가하지 않는다.
- 의미 검색을 바로 구현하지 않는다.
- embedding 기반 retrieval을 열지 않는다.
- graph DB 안에서 relative/mixed source provenance를 생략하지 않는다.
- 외부 DB record가 내부 schema를 우회하게 하지 않는다.

## 5. 메타정보 원칙

외부 DB에 저장되는 모든 relative/mixed node는 다음을 보존해야 한다.

```text
info_class
generated_by
semantic_judgement_status
source_graph_node_ids
source_trace_ids
source_data_ids
source_bundle_kind
review_status
```

외부 DB가 이 필드를 표현하지 못하면, 그 DB는 첫 adapter 대상으로 부적합하다.

## 6. 테스트 후보

1. in-memory store에 node/edge를 upsert하고 다시 조회할 수 있다.
2. 같은 node id를 두 번 upsert해도 중복되지 않는다.
3. source provenance 필드가 round-trip 된다.
4. external adapter를 쓰지 않아도 전체 smoke가 통과한다.
5. adapter가 의미 분류나 topic label을 생성하지 않는다.

## 7. 완료 조건 후보

아직 구현 금지.

승격 시:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

