# ORDER 155: Graph Source Kind Separated Ingest Foundation v0

## 1. Goal

심야정부가 대화 턴만이 아니라 내부 문서와 코드 파일도 다룰 수 있게, source kind별로 분리된 graph source ingest 기반을 만든다.

이번 발주는 요약이나 의미 판단이 아니라 원본 좌표를 graph memory 표면에 올리는 작업이다.

## 2. Core Rule

데이터 종류는 처음부터 섞지 않는다.

예:

```text
internal_document bundle
  -> raw internal document source nodes

source_code_file bundle
  -> raw source code file nodes

external_project_file bundle
  -> raw external project file nodes
```

서로 다른 source kind를 같은 bundle에 넣지 않는다.

## 3. Source Kinds

초기 source kind:

- `internal_document`
- `source_code_file`
- `external_project_file`

대화 턴은 기존 `raw_capsule` 경로를 계속 사용한다. 이번 발주는 대화 턴 ingest를 새로 만들지 않는다.

## 4. What Code May Write

Code may write absolute file/source coordinates:

- source kind
- file path
- file suffix
- file exists
- char count
- deterministic source file data id
- deterministic graph node id
- source-kind bundle node id
- CONTAINS edge id

Code must not write:

- semantic topic
- summary
- importance score
- relevance judgment
- meaning cluster

## 5. Non-goals

This order does not open:

- Neo4j/Vessel connection
- night-government summary worker
- semantic axis
- R LLM selector
- R traversal over the new source kind bundles
- node_3 answer injection

## 6. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_155_graph_source_kind_ingest.py tests/test_import_baseline.py -q
python main.py fast-test --profile graph
git diff --check
```
