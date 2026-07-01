# ORDER_160_LOCAL_VESSEL_NEO4J_FIRST_WRITE_V0

## 목표

로컬 데스크탑 Neo4j/Vessel에 최초 write를 수행한다.

단, 입력은 ORDER_159의 `GraphVesselWritePlan`으로 제한하고, qwen-chat 기본 실행이나 기존 송련 브레인에는 연결하지 않는다.

## 배경

현재까지의 흐름은 다음처럼 잠겼다.

1. DataStore에 graph/source record가 쌓인다.
2. ORDER_158이 export packet을 만든다.
3. ORDER_159가 write plan을 만든다.
4. ORDER_160에서 처음으로 로컬 Vessel에 write한다.

이번 작업은 “외부 DB를 아무렇게나 붙이는 작업”이 아니라, 이미 생성된 write plan에 적힌 operation만 실행하는 수동 opt-in write다.

## 로컬 원칙

- Vessel은 로컬 데스크탑 환경에서만 접속한다.
- cloud DB, remote URI 자동 업로드는 금지한다.
- 기존 송련 브레인과 섞지 않는다.
- 실험 DB/namespace는 다음 값을 사용한다.
  - service name: `songryeon-neo4j-vessel`
  - database name: `songryeon_vessel`
  - namespace: `songryeon_core_graph_v0`

## 구현 범위

1. Neo4j writer 모듈을 추가한다.
   - 후보 파일: `songryeon_core/core/graph_vessel_neo4j.py`

2. writer 입력은 `GraphVesselWritePlan`으로 제한한다.
   - `plan_status=ready_to_write`
   - `external_write_status=not_run`
   - `graph_integrity_status=passed`
   - target adapter: `songryeon-neo4j-vessel`

3. writer 출력 result frame을 만든다.
   - data type: `graph_vessel:neo4j_write_result`
   - generated_by: `CODE:GRAPH_VESSEL_NEO4J_WRITER`
   - info_class: `absolute`
   - semantic_judgement_status: `not_run`

4. Neo4j 미연결/설정 누락/driver 누락은 정직하게 닫는다.
   - `adapter_unavailable`
   - `neo4j_driver_missing`
   - `neo4j_config_missing`
   - `neo4j_write_failed`

5. 수동 CLI를 추가한다.
   - 후보 명령: `python main.py vessel-first-write`
   - 이 명령은 작은 fixture graph를 만들고 export packet -> write plan -> Neo4j writer 순서로 실행한다.

## 금지

- qwen-chat 자동 연결 금지
- R live route 자동 연결 금지
- 기존 송련 브레인 DB와 혼합 금지
- DataStore 전체를 무차별 write 금지
- LLM 요약/상대정보/혼합정보 생성 금지
- embedding/vector 검색 금지
- 의미축 생성 금지
- 기존 DataStore 삭제/변형 금지

## 완료 조건

- Neo4j writer 단위 테스트 통과
- Neo4j 미설정 시 `adapter_unavailable`으로 정직하게 닫힘
- fake Neo4j driver 기준 실제 operation write 흐름 검증
- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_160_local_vessel_neo4j_writer.py -q`
- `python main.py fast-test --profile graph`
- 가능하면 `python -m pytest`, `python main.py smoke-test`

## 기대 결과

ORDER_160 이후에는 송련 Core가 “로컬 그래프 DB에 첫 write를 수행할 수 있는 상태”가 된다.

단, 실제 제품 흐름은 아직 아니다. 이번 단계는 수동 opt-in local Vessel write까지만 연다.
