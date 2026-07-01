# ORDER_158 Graph Memory Export Packet 실행 기록

## 작업 일시

2026-07-01

## 목적

외부 Vessel/Neo4j write 전에 `DataStore`에 존재하는 graph memory / graph source record 목록을 code-generated absolute export packet으로 묶었다.

## 구현 내용

- `songryeon_core/core/graph_memory_export.py` 추가
  - `GraphMemoryExportPacket`
  - `record_graph_memory_export_packet`
  - `build_graph_memory_export_packet`
  - `graph_memory_export_packet_id`
- export packet data type 추가
  - `graph_memory:export_packet`
- target adapter name은 `songryeon-neo4j-vessel`로 기록
- `external_write_status=not_run`으로 외부 DB write 미실행을 명시
- `audit_graph_memory_integrity()` 결과를 packet에 포함
- graph fast-test profile에 ORDER_158 pytest 포함
- import baseline에 `songryeon_core.core.graph_memory_export` 추가

## 수집 대상

- `graph_memory:node:*`
- `graph_memory:edge:*`
- `graph_memory:snapshot`
- `graph_memory:core_ego_time_axis_frame`
- `graph_memory:rloop_guide_packet`
- `graph_source:file_metadata`
- `graph_source:file_text_snapshot`
- `graph_source:source_kind_ingest_frame`
- `graph_source:songryeon_core_source_manifest_frame`

## 메타정보 경계

- `generated_by=CODE:GRAPH_MEMORY_EXPORT_PACKET_BUILDER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

이번 작업은 record 목록, count, source trace id, integrity status 같은 code-checkable absolute 정보만 생성한다.

## 하지 않은 것

- Neo4j driver 추가 없음
- Vessel adapter 구현 없음
- 외부 DB write 없음
- LLM 요약/상대정보/혼합정보 생성 없음
- 의미축 생성 없음
- R live route 변경 없음
- scheduler/장기기억 DB 변경 없음

## 검증 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_158_graph_memory_export_packet.py -q`: 4 passed
- `python -m pytest tests/test_import_baseline.py tests/test_order_154_fast_test_gate.py -q`: 5 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 40 passed
- `python -m pytest`: 171 passed
- `python main.py smoke-test`: SMOKE_TEST_OK

## 확인한 경계

- 같은 batch/timestamp로 export packet을 다시 기록하면 기존 packet payload와 충돌하지 않고 existing으로 처리된다.
- export packet 자체는 graph/source export 대상에 다시 포함하지 않는다.
- 일반 `node_output:*` record는 export packet included list에서 제외된다.
- graph integrity 실패는 `graph_integrity_status=failed`로 packet에 기록되며, 외부 write는 여전히 `not_run`이다.
