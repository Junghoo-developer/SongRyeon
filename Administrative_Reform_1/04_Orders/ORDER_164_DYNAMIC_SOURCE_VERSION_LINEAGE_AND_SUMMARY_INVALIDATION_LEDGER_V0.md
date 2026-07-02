# ORDER_164 Dynamic Source Version Lineage And Summary Invalidation Ledger v0

## 목표

동적 원본 파일이 바뀌었을 때, 기존 raw source graph node와 그 원본에서 파생된 요약/혼합정보를 지우지 않고 추적 가능하게 무효화할 수 있는 최소 장부를 만든다.

이번 발주는 LLM 요약 생성이 아니라 code-generated absolute infrastructure다.

## 배경

현재 graph source ingest는 파일 경로, source kind, observed_at, ingested_at, source_last_modified_at, content_sha1, raw_source graph node를 저장한다.

하지만 같은 파일이 나중에 다시 관측됐을 때 다음 질문에 바로 답하기 어렵다.

- 이 raw source는 같은 파일의 몇 번째 관측본인가?
- 내용이 그대로 다시 관측된 것인가, 실제로 바뀐 것인가?
- 예전 관측본에 기대어 만든 LLM summary가 있다면 이제 current answer 근거로 써도 되는가?

## 구현 범위

1. SourceVersionLineageFrame을 추가한다.
   - 같은 source_kind + path를 하나의 source identity로 묶는다.
   - 관측된 raw_source graph node들을 observed_at 순서로 나열한다.
   - active source는 최신 관측본으로 둔다.
   - content_sha1이 바뀌면 lineage_status=content_changed로 기록한다.
   - 참고: ORDER_165 이후 content hash가 같은 재관측은 source version lineage 상태가 아니라 observation ledger의 unchanged 기록으로 분리한다.

2. SummaryInvalidationLedgerFrame을 추가한다.
   - changed lineage의 superseded raw_source를 근거로 하는 summary node를 찾는다.
   - 해당 summary를 삭제하지 않고 invalidation record로 표시한다.
   - invalidated_reason_code=source_content_changed를 사용한다.

3. graph source ingest 이후에도 이 장부를 code가 만들 수 있게 한다.
   - code는 의미 요약을 만들지 않는다.
   - code는 어떤 요약이 낡았는지 source_graph_node_ids와 content_sha1 변화만으로 판단한다.

4. export packet / Vessel write plan이 이 장부 record를 support record로 다룰 수 있게 한다.

## 금지

- LLM 요약 생성 금지.
- summary node 본문 변경/삭제 금지.
- 기존 raw_source graph node 삭제 금지.
- Neo4j에 직접 semantic summary를 쓰는 기능 금지.
- R route, R1/R2/R3 탐색 정책 변경 금지.
- source 내용 유사도/키워드 휴리스틱 추가 금지.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_164_source_version_lineage_and_invalidation.py`
- 관련 source ingest/export pytest 통과
- `git diff --check`

## 기대 효과

나중에 심야정부가 raw source에서 상대/혼합 요약을 만들더라도, 그 요약이 어느 원본 버전에 기대고 있는지 추적할 수 있다.

동적 원본이 바뀌면 예전 요약은 지우지 않고 `invalidated_by_source_change` 계열 장부로 current answer 근거에서 제외할 수 있다.
