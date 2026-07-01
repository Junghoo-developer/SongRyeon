# ORDER_161_VESSEL_DISPLAY_VOCABULARY_V0

## 목표

Neo4j Browser에서 사람이 보는 node label, relationship type, display properties를 더 이해하기 쉬운 graph vocabulary로 바꾼다.

내부 `data_id`, provenance, payload, schema는 유지한다.

## 배경

ORDER_160으로 로컬 Neo4j/Vessel first write가 성공했다.

하지만 Neo4j 화면에 보이는 이름은 다음처럼 너무 기술적이다.

- `SongRyeonRecord`
- `SongRyeonGraphNode`
- `SongRyeonGraphEdgeRecord`
- `SongRyeonSupportRecord`
- `SONGRYEON_GRAPH_EDGE`

이 이름들은 안전하지만 사람이 그래프를 훑을 때 직관적이지 않다.

## 구현 범위

1. base label을 `VesselRecord`로 바꾼다.

2. graph node payload에 따라 display label을 추가한다.
   - `core_ego` -> `CoreEgo`
   - `time_axis` -> `TimeAxis`
   - `time_bundle` -> `TimeBundle`
   - `raw_capsule` -> `RawCapsule`
   - `raw_source` -> `RawSource`
   - `source_kind_bundle` -> `SourceKindBundle`
   - `source_ingest_time_bundle` -> `SourceIngestBundle`
   - fallback -> `GraphMemoryNode`

3. support record는 더 구체적인 label로 나눈다.
   - `graph_memory:snapshot` -> `GraphMemorySnapshot`
   - `graph_memory:rloop_guide_packet` -> `RLoopGuide`
   - `graph_memory:core_ego_time_axis_frame` -> `GraphMemoryIndex`
   - source manifest / source ingest frame -> `GraphMemoryIndex`

4. source payload는 `GraphMemorySource` label을 사용한다.

5. edge record는 `GraphMemoryEdgeRecord` label을 사용한다.

6. relationship type을 사람이 읽기 쉬운 이름으로 바꾼다.
   - CoreEgo -> TimeAxis: `HAS_AXIS`
   - TimeAxis -> TimeBundle: `HAS_BUNDLE`
   - TimeBundle -> RawCapsule: `CONTAINS_MEMORY`
   - RawCapsule -> RawCapsule: `NEXT`
   - SourceIngestBundle -> SourceKindBundle: `HAS_SOURCE_KIND`
   - SourceKindBundle -> RawSource: `CONTAINS_SOURCE`
   - fallback: `CONTAINS`

7. display properties를 추가한다.
   - `display_name`
   - `display_kind`
   - `display_label`
   - relationship에는 `display_relationship_type`

## 기존 실험 데이터 처리

ORDER_160 first-write fixture는 작다.

새 writer는 기존 old label을 제거하고 새 display label을 붙일 수 있게 한다. 기존 old `SONGRYEON_GRAPH_EDGE` 관계는 같은 `edge_id`/namespace 기준으로 삭제한 뒤 새 relationship type으로 재생성한다.

## 금지

- 내부 `data_id` 변경 금지
- source/provenance/payload 삭제 금지
- 의미 요약/LLM 판단 추가 금지
- qwen-chat/R live route 자동 연결 금지
- 기존 송련 브레인과 혼합 금지

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_160_local_vessel_neo4j_writer.py -q`
- `python main.py fast-test --profile graph`
- 가능하면 `python -m pytest`, `python main.py smoke-test`

## 기대 결과

Neo4j Browser에서 다음처럼 볼 수 있어야 한다.

```cypher
MATCH path = (core:CoreEgo)-[:HAS_AXIS]->(:TimeAxis)-[:HAS_BUNDLE]->(:TimeBundle)-[:CONTAINS_MEMORY]->(:RawCapsule)
RETURN path;
```

즉, 송련 내부 ID는 그대로 유지하되 사람이 보는 그래프 이름은 읽기 쉬워진다.
