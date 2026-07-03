# ORDER_159 Vessel Adapter Write Plan Boundary 실행 기록

## 작업 일시

2026-07-01

## 목적

ORDER_158의 `GraphMemoryExportPacket`을 입력으로 받아 외부 Vessel/Neo4j write 직전의 `GraphVesselWritePlan`을 생성했다.

이번 작업은 실제 외부 DB write가 아니라 write operation 목록을 code-generated absolute 정보로 고정하는 단계다.

## 구현 내용

- `songryeon_core/core/graph_vessel_adapter.py` 추가
  - `GraphVesselWritePlan`
  - `GraphVesselWriteOperation`
  - `build_graph_vessel_write_plan`
  - `record_graph_vessel_write_plan`
- write plan data type 추가
  - `graph_vessel:write_plan`
- operation 종류 고정
  - `upsert_source_payload`
  - `upsert_graph_node`
  - `upsert_graph_edge`
  - `upsert_support_record`
- operation 순서 고정
  - source payload -> graph node -> graph edge -> support record
- target adapter는 `songryeon-neo4j-vessel`만 허용
- graph integrity가 실패한 export packet은 `blocked_integrity_failed`로 닫고 operation list를 비운다.
- graph fast-test profile에 ORDER_159 pytest 포함

## 메타정보 경계

- `generated_by=CODE:GRAPH_VESSEL_ADAPTER_BOUNDARY`
- `info_class=absolute`
- `semantic_judgement_status=not_run`
- `external_write_status=not_run`

이번 작업은 record ID, data type, operation order, target adapter name, integrity status 같은 code-checkable absolute 정보만 생성한다.

## 하지 않은 것

- Neo4j driver 추가 없음
- 외부 DB 연결 없음
- 실제 write 없음
- LLM 요약/상대정보/혼합정보 생성 없음
- 의미축 생성 없음
- R live route 변경 없음
- scheduler/장기기억 DB 변경 없음

## 검증 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_159_vessel_adapter_boundary.py -q`: 5 passed
- `python -m pytest tests/test_import_baseline.py tests/test_order_154_fast_test_gate.py -q`: 5 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 45 passed
- `python main.py smoke-test`: SMOKE_TEST_OK
- `python -m pytest`: 176 passed

## 검증 중 메모

처음에 `python -m pytest`와 `python main.py smoke-test`를 동시에 실행했을 때 Windows cache file write 경합으로 `.songryeon_core_cache/document_memory_indexes/*`에서 `PermissionError`가 1회 발생했다.

이후 `python main.py smoke-test`는 통과했고, `python -m pytest`를 단독으로 재실행하자 176개 테스트가 모두 통과했다.

따라서 ORDER_159 기능 실패가 아니라 병렬 캐시 쓰기 경합으로 기록한다.

## 확인한 경계

- write plan은 `external_write_status=not_run`이며 실제 외부 DB write를 수행하지 않는다.
- target adapter는 `songryeon-neo4j-vessel`만 허용한다.
- graph integrity 실패 export packet은 `blocked_integrity_failed`로 닫고 operation list를 비운다.
- operation order는 source payload -> graph node -> graph edge -> support record 순서로 고정된다.
- write plan은 의미/요약/embedding/topic 필드를 생성하지 않는다.
