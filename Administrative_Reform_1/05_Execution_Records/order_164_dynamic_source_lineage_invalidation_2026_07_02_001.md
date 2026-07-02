# ORDER_164 Dynamic Source Version Lineage And Summary Invalidation Ledger 실행 기록

## 작업 요약

동적 원본 파일이 바뀌었을 때 기존 raw source와 파생 summary를 삭제하지 않고 추적할 수 있도록, code-generated absolute 장부를 추가했다.

## 핵심 변경

- `SourceVersionLineageFrame` 추가
  - 같은 `source_kind + path`를 stable source identity로 묶는다.
  - 관측된 raw source graph node를 `observed_at` 순서로 기록한다.
  - 최신 raw source를 active version으로 표시한다.
  - content hash가 바뀌면 `lineage_status=content_changed`로 표시한다.

- `SummaryInvalidationLedgerFrame` 추가
  - content-changed lineage의 superseded raw source를 근거로 하는 summary node를 찾는다.
  - summary record를 수정/삭제하지 않고 별도 invalidation record를 남긴다.
  - 무효화 reason은 `source_content_changed`, validity status는 `invalidated_by_source_change`로 고정했다.

- `graph_source_ingest` 이후 lineage/ledger frame을 자동 기록한다.
  - source ingest 결과에 lineage frame id와 summary invalidation ledger id를 포함한다.
  - 같은 batch/source 재기록은 기존 idempotency 규칙을 유지한다.

- export/Vessel boundary에 lineage/ledger record를 support record로 포함했다.

## 정보 분류

- source lineage: `generated_by=CODE:SOURCE_VERSION_LINEAGE_BUILDER`, `info_class=absolute`, `semantic_judgement_status=not_run`
- invalidation ledger: `generated_by=CODE:SUMMARY_INVALIDATION_LEDGER_BUILDER`, `info_class=absolute`, `semantic_judgement_status=not_run`

이번 작업에서 code가 의미 요약을 만들지 않았다. code는 source graph node id, file metadata, content hash 변화, summary의 source_graph_node_ids만 검사했다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_164_source_version_lineage_and_invalidation.py -q`: 3 passed
- `python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_order_156_graph_source_observation_time_and_core_link.py tests/test_order_157_songryeon_core_source_manifest.py tests/test_order_158_graph_memory_export_packet.py tests/test_order_159_vessel_adapter_boundary.py tests/test_order_160_local_vessel_neo4j_writer.py -q`: 33 passed
- `python -m pytest tests/test_schema_split_compat.py -q`: 2 passed
- `python -m pytest tests/test_order_154_fast_test_gate.py -q`: 4 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 72 passed
- `git diff --check`: 통과

## 일부러 하지 않은 것

- LLM summary 생성 없음.
- summary node payload 수정/삭제 없음.
- raw_source node 삭제 없음.
- R route/R traversal 정책 변경 없음.
- Neo4j live write 자동 실행 변경 없음.
- source 의미 유사도/키워드 휴리스틱 추가 없음.

## 남은 위험

- 실제 심야정부 LLM summary node가 생기면, 그 summary가 `source_graph_node_ids`로 원본 raw source를 정확히 가리키도록 별도 발주가 필요하다.
- 현재 ledger는 summary record를 직접 mutate하지 않는다. downstream이 current answer 근거에서 invalidated summary를 제외하도록 읽는 정책은 후속 발주 대상이다.
