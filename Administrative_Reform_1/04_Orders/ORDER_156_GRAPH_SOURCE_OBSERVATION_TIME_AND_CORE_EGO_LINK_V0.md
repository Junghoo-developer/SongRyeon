# ORDER 156: Graph Source Observation Time And CoreEgo Link v0

## 1. Goal

ORDER 155의 source-kind separated ingest를 한 단계 잠근다.

내부 문서와 코드 파일은 대화 턴과 달리 계속 바뀌거나 삭제될 수 있다. 따라서 graph raw source node는 "현재 파일의 영원한 진실"이 아니라, 특정 시각에 특정 경로에서 관측한 source snapshot coordinate임을 payload 자체에 기록해야 한다.

또한 source kind bundle은 R loop가 CoreEgo 시간축에서 발견할 수 있도록 CoreEgo time axis 아래에 연결되어야 한다.

## 2. Required Absolute Fields

Raw source file metadata and raw source graph nodes must record:

- `observed_at`
- `ingested_at`
- `source_last_modified_at`
- `exists_at_ingest`
- `content_sha1`

Meanings:

- `observed_at`: code observed the filesystem state at this time.
- `ingested_at`: code recorded the observation into graph/DataStore at this time.
- `source_last_modified_at`: OS file last modified timestamp at observation time.
- `exists_at_ingest`: whether the file existed when code observed it.
- `content_sha1`: content fingerprint for that observation.

## 3. CoreEgo Link

Source ingest must create this shape when a CoreEgo time axis already exists in DataStore:

```text
graph:core_ego:root
  -> graph:axis:time
    -> graph:source_ingest_time_bundle:{batch_id}
      -> graph:source_kind_bundle:{batch_id}:{source_kind}
        -> graph:raw_source:{source_kind}:{observation_digest}
```

The source ingest code must not silently invent a detached CoreEgo root if the root/time axis is missing. Missing CoreEgo time axis should fail loudly, because otherwise downstream R traversal would see an inconsistent graph surface.

## 4. What Code May Write

Code may write only absolute observation coordinates:

- source kind
- normalized path
- file name
- suffix
- exists-at-ingest flag
- char count
- source last modified timestamp
- observed/ingested timestamp
- content SHA-1
- deterministic graph/data IDs for that observation
- CoreEgo time-axis graph edges
- source ingest snapshot/guide packet coordinates

## 5. What Code Must Not Write

Code must not write:

- semantic topic
- summary
- importance score
- relevance judgment
- meaning cluster
- current-truth claim that the file still has the same content later

## 6. Non-goals

This order does not open:

- Neo4j/Vessel connection
- night-government summary worker
- semantic axis
- R LLM selector
- automatic source path discovery
- node_3 answer injection

## 7. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_order_156_graph_source_observation_time_and_core_link.py tests/test_import_baseline.py -q
python main.py fast-test --profile graph
git diff --check
```
