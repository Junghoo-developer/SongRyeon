# ORDER_161 Vessel Display Vocabulary 실행 기록

## 작업 일시

2026-07-01

## 목적

Neo4j Browser에서 사람이 보는 node label, relationship type, display properties를 더 읽기 쉬운 이름으로 바꾸었다.

내부 `data_id`, payload, provenance, schema는 유지했다.

## 구현 내용

- `songryeon_core/core/graph_vessel_neo4j.py`의 Neo4j write vocabulary 변경
- base label 변경
  - 기존: `SongRyeonRecord`
  - 신규: `VesselRecord`
- graph node display label 추가
  - `CoreEgo`
  - `TimeAxis`
  - `TimeBundle`
  - `RawCapsule`
  - `RawSource`
  - `SourceKindBundle`
  - `SourceIngestBundle`
  - fallback: `GraphMemoryNode`
- support/display record label 변경
  - `GraphMemorySnapshot`
  - `RLoopGuide`
  - `GraphMemoryIndex`
  - `GraphMemorySource`
  - `GraphMemoryEdgeRecord`
- relationship type 변경
  - `HAS_AXIS`
  - `HAS_BUNDLE`
  - `CONTAINS_MEMORY`
  - `NEXT`
  - `HAS_SOURCE_KIND`
  - `CONTAINS_SOURCE`
  - fallback: `CONTAINS`
- display properties 추가
  - `display_name`
  - `display_kind`
  - `display_label`
  - relationship `display_relationship_type`

## 기존 실험 데이터 처리

새 writer는 같은 `data_id`/namespace 노드에 새 label을 붙이고 기존 old `SongRyeon*` label을 제거한다.

같은 `edge_id`/namespace의 기존 old `SONGRYEON_GRAPH_EDGE` 관계는 삭제한 뒤 새 relationship type으로 재생성한다.

## 메타정보 경계

- 내부 `data_id` 유지
- `source_data_ids`, `source_trace_ids`, `payload_json` 유지
- LLM 요약/상대정보/혼합정보 생성 없음
- qwen-chat/R live route 자동 연결 없음

## 검증 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_160_local_vessel_neo4j_writer.py -q`: 8 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 53 passed
- `python -m pytest`: 184 passed
- `python main.py smoke-test`: SMOKE_TEST_OK

## 로컬 실행 메모

현재 Codex 실행 터미널에는 Neo4j password 환경변수가 없어서 `python main.py vessel-first-write --database neo4j`는 `adapter_unavailable / neo4j_config_missing`으로 닫혔다.

사용자가 Neo4j password 환경변수를 설정한 터미널에서 같은 명령을 다시 실행하면 기존 old `SongRyeon*` label이 제거되고 새 display vocabulary가 적용된다.

예상 확인 쿼리:

```cypher
MATCH path = (core:CoreEgo)-[:HAS_AXIS]->(:TimeAxis)-[:HAS_BUNDLE]->(:TimeBundle)-[:CONTAINS_MEMORY]->(:RawCapsule)
RETURN path;
```
