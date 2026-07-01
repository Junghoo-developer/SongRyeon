# ORDER_160 Local Vessel Neo4j First Write 실행 기록

## 작업 일시

2026-07-01

## 목적

ORDER_159 `GraphVesselWritePlan`을 입력으로 받아 로컬 Neo4j/Vessel에 수동 opt-in first write를 수행할 수 있는 writer와 CLI를 추가했다.

## 구현 내용

- `songryeon_core/core/graph_vessel_neo4j.py` 추가
  - `GraphVesselNeo4jConfig`
  - `GraphVesselNeo4jWriteResultFrame`
  - `write_graph_vessel_plan_to_neo4j`
  - `record_graph_vessel_neo4j_write_result`
- `songryeon_core/runtime/graph_vessel_first_write.py` 추가
  - tiny fixture graph 생성
  - export packet 생성
  - write plan 생성
  - Neo4j writer 실행
- `main.py`에 수동 명령 추가
  - `python main.py vessel-first-write`
- graph fast-test profile에 ORDER_160 pytest 포함

## 로컬 Vessel 경계

- target adapter: `songryeon-neo4j-vessel`
- database default: `songryeon_vessel`
- namespace: `songryeon_core_graph_v0`
- 기본 접속 URI: `bolt://localhost:7687`

## 메타정보 경계

- `generated_by=CODE:GRAPH_VESSEL_NEO4J_WRITER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

Neo4j writer는 write result/status/count만 생성하며 의미 요약이나 topic/embedding 필드를 생성하지 않는다.

## 하지 않은 것

- qwen-chat 자동 연결 없음
- R live route 자동 연결 없음
- 기존 송련 브레인 DB와 혼합 없음
- DataStore 전체 무차별 write 없음
- LLM 요약/상대정보/혼합정보 생성 없음
- embedding/vector 검색 없음
- 의미축 생성 없음
- 기존 DataStore 삭제/변형 없음

## 검증 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_160_local_vessel_neo4j_writer.py -q`: 7 passed
- `python -m pytest tests/test_import_baseline.py tests/test_order_154_fast_test_gate.py -q`: 5 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 52 passed
- `python -m pytest`: 183 passed
- `python main.py smoke-test`: SMOKE_TEST_OK

## 로컬 실행 확인

`python main.py vessel-first-write`를 실행했다.

결과:

- `status=VESSEL_FIRST_WRITE_NOT_WRITTEN`
- `write_status=adapter_unavailable`
- `failure_type=neo4j_config_missing`
- `failure_reason=Neo4j password is not configured. Set SONGRYEON_NEO4J_PASSWORD or pass --password.`
- `operation_count=10`
- `attempted_operation_count=0`
- `written_operation_count=0`

현재 환경 확인:

- Python `neo4j` driver는 설치되어 있다.
- `neo4j` CLI command는 발견되지 않았다.
- `localhost:7474`, `localhost:7687` listening connection은 발견되지 않았다.
- `SONGRYEON_*` Neo4j 환경변수는 발견되지 않았다.

따라서 ORDER_160 writer/CLI는 구현되었지만, 실제 로컬 Neo4j 서버/비밀번호가 준비되지 않아 first write는 아직 수행되지 않았다.

## 확인한 경계

- writer 입력은 `GraphVesselWritePlan`으로 제한된다.
- `plan_status=ready_to_write`, `external_write_status=not_run`, `graph_integrity_status=passed`, target adapter 일치 조건을 검사한다.
- Neo4j 설정 누락은 `adapter_unavailable`으로 정직하게 닫힌다.
- fake Neo4j driver 기준 write operation이 실행되고 result frame이 `written`으로 기록된다.
- writer는 의미/요약/topic/embedding 필드를 생성하지 않는다.
