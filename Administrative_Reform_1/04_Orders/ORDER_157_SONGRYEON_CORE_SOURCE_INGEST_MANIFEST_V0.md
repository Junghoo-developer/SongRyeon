# ORDER 157: SongRyeon Core Source Ingest Manifest v0

## 1. Goal

ORDER 155~156에서 만든 source-kind separated graph ingest를 SongRyeon Core 자체에 적용할 수 있는 명시 manifest/batch runner를 만든다.

이번 발주는 의미 판단이 아니라, 송련 코어 내부 문서/코드/test 파일을 source kind별로 분리하고 관측 시각이 붙은 graph source snapshot으로 올리는 작업이다.

## 2. Approved Policy

사용자 결재:

- 내부 문서/코드 원문 snapshot 저장 허용.
- `tests/**/*.py`도 `source_code_file`로 ingest한다.
- glob manifest는 허용한다. 단, glob은 의미 추측이 아니라 명시 정책이다.
- 명시 경로가 missing이면 실패한다.
- glob pattern 결과가 비어 있거나, 과거 파일이 사라져 glob에 잡히지 않는 경우는 이번 MVP에서 삭제 감지로 다루지 않는다.

## 3. Manifest Policy

Initial SongRyeon Core source manifest:

```text
internal_document:
  explicit:
    - AGENTS.md
    - README.md
  globs:
    - Administrative_Reform_1/**/*.md

source_code_file:
  explicit:
    - main.py
  globs:
    - songryeon_core/**/*.py
    - tests/**/*.py
```

`external_project_file` is not auto-ingested in this order. External project files must be provided explicitly by a later caller/order.

## 4. Text Snapshot Boundary

For SongRyeon Core internal documents and source code files, code may store a raw text snapshot as absolute copied source content.

Text snapshot records must include:

- source kind
- path
- observed_at
- ingested_at
- content_sha1
- char_count
- text
- generated_by
- info_class=`absolute_copied_source`
- semantic_judgement_status=`not_run`

Text snapshot records are raw copied content, not summaries.

## 5. What Code Must Not Do

Code must not:

- classify files by semantic guessing
- summarize files
- assign importance or relevance
- create semantic axis
- create Neo4j/Vessel records
- inject source ingest material into node_3 answers

## 6. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_157_songryeon_core_source_manifest.py tests/test_order_155_graph_source_kind_ingest.py tests/test_order_156_graph_source_observation_time_and_core_link.py tests/test_import_baseline.py -q
python main.py fast-test --profile graph
git diff --check
```
