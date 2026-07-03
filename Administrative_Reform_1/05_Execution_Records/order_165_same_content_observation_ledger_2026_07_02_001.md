# ORDER_165 Same-Content Reobserve Observation Ledger 실행 기록

## 작업 요약

같은 source file을 다시 관측했지만 content hash가 같을 때, 새 `RawSource` graph node를 만들지 않고 observation ledger에 `unchanged`로 기록하도록 바꿨다.

## 핵심 변경

- `SourceVersionLineageFrame.lineage_status`에서 same-content 재관측 상태를 제거했다.
  - 현재 lineage status는 `single_version`, `content_changed`만 허용한다.

- `raw_source` graph node ID 기준에서 `observed_at`을 제외했다.
  - 기준: `source_kind + path + content_sha1`
  - 같은 파일/같은 내용이면 기존 raw source node를 재사용한다.
  - 파일 내용이 바뀌면 content hash가 달라져 새 raw source node가 생긴다.

- `SourceObservationLedgerFrame`을 추가했다.
  - 현재 ingest batch에서 관측한 source file metadata를 기록한다.
  - observation status:
    - `new_source_version`
    - `unchanged`
    - `content_changed`
  - unchanged는 summary invalidation을 일으키지 않는다.

- export/Vessel boundary에 observation ledger를 support record로 포함했다.

## 정보 분류

- source observation ledger: `generated_by=CODE:SOURCE_OBSERVATION_LEDGER_BUILDER`, `info_class=absolute`, `semantic_judgement_status=not_run`
- source lineage: `generated_by=CODE:SOURCE_VERSION_LINEAGE_BUILDER`, `info_class=absolute`, `semantic_judgement_status=not_run`
- summary invalidation ledger: `generated_by=CODE:SUMMARY_INVALIDATION_LEDGER_BUILDER`, `info_class=absolute`, `semantic_judgement_status=not_run`

이번 작업에서 code는 원본 의미를 요약하거나 해석하지 않았다. content hash와 source coordinate만 사용했다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_164_source_version_lineage_and_invalidation.py tests/test_order_165_same_content_observation_ledger.py tests/test_order_156_graph_source_observation_time_and_core_link.py -q`: 10 passed
- `python -m pytest tests/test_order_154_fast_test_gate.py tests/test_schema_split_compat.py -q`: 6 passed
- `python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_order_157_songryeon_core_source_manifest.py tests/test_order_158_graph_memory_export_packet.py tests/test_order_159_vessel_adapter_boundary.py tests/test_order_160_local_vessel_neo4j_writer.py -q`: 28 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 74 passed
- `git diff --check`: 통과

## 일부러 하지 않은 것

- LLM summary 생성 없음.
- raw source/summary record 삭제 없음.
- unchanged source observation을 이유로 summary 무효화하지 않음.
- R route/R traversal 정책 변경 없음.
- Neo4j live write 자동 실행 변경 없음.

## 남은 위험

- 현재 source ingest batch node/source kind bundle/snapshot은 여전히 batch 실행 사실을 남긴다. 즉 unchanged source라도 "검사 실행 장부"는 남는다.
- downstream R loop가 invalidated summary를 자동 제외하는 정책은 아직 후속 발주 대상이다.
