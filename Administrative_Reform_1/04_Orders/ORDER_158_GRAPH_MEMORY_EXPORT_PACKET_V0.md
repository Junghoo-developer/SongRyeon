# ORDER_158_GRAPH_MEMORY_EXPORT_PACKET_V0

## 목표

외부 Vessel/Neo4j 어댑터를 만들기 전에, 현재 `DataStore`에 쌓인 graph memory / graph source 기록 중 외부 DB로 내보낼 수 있는 기록 목록을 code-generated absolute export packet으로 고정한다.

이번 발주는 외부 DB write가 아니라 export 직전의 “수출 명세서”를 만드는 작업이다.

## 배경

ORDER_139부터 ORDER_157까지 진행하면서 송련 Core는 다음 절대정보 기반을 갖추었다.

- `TurnStateCapsule` 기반 raw capsule graph node
- CoreEgo -> time axis -> time bundle -> raw capsule 구조
- source-kind separated ingest
- source observation timestamp
- SongRyeon Core 내부 문서/source code manifest
- graph integrity audit

하지만 아직 Vessel/Neo4j로 실제 기록을 보내기 전에 어떤 record를 보낼지, 어떤 source trace에 근거하는지, graph integrity가 어떤 상태인지 한 번에 묶은 export packet이 없다.

## 구현 범위

1. 새 builder를 추가한다.
   - 후보 파일: `songryeon_core/core/graph_memory_export.py`

2. `DataStore`에서 다음 record를 수집한다.
   - `graph_memory:node:*`
   - `graph_memory:edge:*`
   - `graph_memory:snapshot`
   - `graph_memory:core_ego_time_axis_frame`
   - `graph_memory:rloop_guide_packet`
   - `graph_source:file_metadata`
   - `graph_source:file_text_snapshot`
   - `graph_source:source_kind_ingest_frame`
   - `graph_source:songryeon_core_source_manifest_frame`

3. export packet에는 다음을 남긴다.
   - packet id
   - batch id
   - target adapter name: `songryeon-neo4j-vessel`
   - external write status: `not_run`
   - included data ids
   - category별 data ids
   - source trace ids
   - data type counts
   - graph integrity summary
   - `generated_by=CODE:GRAPH_MEMORY_EXPORT_PACKET_BUILDER`
   - `info_class=absolute`
   - `semantic_judgement_status=not_run`

4. export packet 자체도 `DataStore`에 기록한다.
   - data type: `graph_memory:export_packet`
   - trace actor: `graph_memory_export_packet_builder`

5. graph fast-test profile에 ORDER_158 테스트를 포함한다.

## 금지

- 외부 DB에 실제 write하지 않는다.
- Neo4j driver를 추가하지 않는다.
- Vessel adapter를 구현하지 않는다.
- LLM 요약, 상대정보, 혼합정보를 만들지 않는다.
- graph integrity guard를 약화하지 않는다.
- 의미축, R live route, scheduler, 장기기억 DB를 열지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_158_graph_memory_export_packet.py -q`
- `python main.py fast-test --profile graph`
- 가능하면 `python -m pytest`, `python main.py smoke-test`

## 기대 결과

ORDER_158 이후에는 외부 DB 어댑터가 바로 DataStore 전체를 뒤지는 것이 아니라, 먼저 code가 만든 export packet을 읽고 그 목록만 Vessel/Neo4j write 대상으로 삼을 수 있다.

즉, “외부 DB에 뭘 썼는지 모르겠다”가 아니라 “이 packet에 적힌 절대정보 record만 내보낸다”는 경계가 생긴다.
