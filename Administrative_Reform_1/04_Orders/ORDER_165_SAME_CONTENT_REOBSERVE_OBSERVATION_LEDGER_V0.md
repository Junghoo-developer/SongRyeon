# ORDER_165 Same-Content Reobserve Observation Ledger v0

## 목표

동적 원본 파일을 다시 봤는데 내용 hash가 같을 때 새 `RawSource` graph node를 만들지 않고, "검사했지만 unchanged였다"는 관측 장부만 남긴다.

## 배경

ORDER_164는 source version lineage에 `same_content_reobserved` 상태를 두었다. 이 방식은 감사에는 친절하지만, 같은 파일/같은 내용이 관측 시각만 다르다는 이유로 graph raw source version이 계속 늘어날 위험이 있다.

그래프 메모리에서는 "내용이 같은 원본"은 같은 원본 버전으로 유지하고, 관측 시각은 별도 장부로 빼는 편이 더 단순하다.

## 구현 방향

1. `SourceVersionLineageFrame.lineage_status`에서 `same_content_reobserved`를 제거한다.
   - 허용 상태는 `single_version`, `content_changed`만 둔다.

2. `raw_source` graph node identity에서 `observed_at`을 제외한다.
   - 기준은 `source_kind + path + content_sha1`이다.
   - 같은 파일/같은 내용이면 기존 `raw_source` node를 재사용한다.
   - 파일 내용이 바뀌면 content hash가 달라지므로 새 `raw_source` node가 생긴다.

3. `SourceObservationLedgerFrame`을 추가한다.
   - 현재 ingest batch의 source file observation들을 기록한다.
   - observation status는 `new_source_version`, `unchanged`, `content_changed` 중 하나다.
   - unchanged는 새 raw source version을 만들지 않는다.

4. summary invalidation은 content_changed일 때만 작동한다.
   - unchanged observation은 기존 summary를 무효화하지 않는다.

## 금지

- LLM 요약 생성 금지.
- raw source나 summary record 삭제 금지.
- unchanged 파일에 대해 새 raw source version을 만드는 fallback 금지.
- source 의미 유사도/키워드 휴리스틱 금지.
- R route/R traversal 정책 변경 금지.
- Neo4j live write 자동 실행 변경 금지.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_164_source_version_lineage_and_invalidation.py tests/test_order_165_same_content_observation_ledger.py -q`
- 관련 graph/source/export fast-test 통과
- `git diff --check`

## 기대 효과

동적 원본 파일을 자주 검사해도 같은 내용의 raw source graph node가 불필요하게 늘지 않는다.

대신 "언제 다시 검사했고, 그때 바뀌었는지/안 바뀌었는지"는 observation ledger로 추적할 수 있다.
