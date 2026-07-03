# ORDER 168: Night Summarize Changed Source Leaves v0

## 1. Goal

새로 들어왔거나 내용이 바뀐 코드/문서 `raw_source` leaf를 전부 1:1로 LLM 요약한다.

이번 발주의 핵심:

```text
RawSource leaf 하나
  <- SUMMARY_OF
SummaryGraphNode 하나
```

즉 source kind bundle을 먼저 요약하지 않는다.

원본 파일 leaf와 바로 1:1 대응되는 첫 summary node를 만든다.

## 2. Source Selection Rule

Code selects source leaves only from `SourceObservationLedgerFrame`.

요약 대상:

- `observation_status=new_source_version`
- `observation_status=content_changed`

요약 제외:

- `observation_status=unchanged`

이 선택은 의미 판단이 아니다.

새 raw source version이 생겼는지, 기존 source content가 바뀌었는지는 code가 content hash와 observation ledger로 확인한 절대정보다.

## 3. Text Availability Rule

LLM summary는 원문 text snapshot이 있는 raw source에만 실행한다.

If a raw source has no text snapshot:

```text
summary_status=skipped_no_text_snapshot
semantic_judgement_status=not_run
```

If a raw source text snapshot is empty:

```text
summary_status=skipped_empty_text
semantic_judgement_status=not_run
```

Code must not invent a summary for missing/empty text.

## 4. Metainfo Rule

Each successful summary is directly grounded in exactly one raw source leaf.

Therefore:

```text
info_class=relative
source_mode=single_source
claim_alignment=single_absolute_record
```

Failed LLM attempts remain `relative/failed` because the attempted semantic output was supposed to be a one-source summary.

Skipped no-text cases are code-checkable status records:

```text
info_class=absolute
semantic_judgement_status=not_run
```

## 5. Scope

- Add `NightSourceLeafSummaryFrame`.
- Add `run_night_summarize_source_leaf()`.
- Add `run_night_summarize_changed_source_leaves()`.
- Record successful summaries as `graph_memory:node:summary`.
- Record successful edges as `graph_memory:edge:SUMMARY_OF`.
- Record skipped/failed attempts as `node_output:night_summarize_source_leaf_frame`.
- Include new test in graph fast-test profile.

## 6. Non-goals

- Do not summarize unchanged source observations.
- Do not summarize source kind bundles.
- Do not summarize conversation TimeBundles here.
- Do not open semantic axis.
- Do not auto-feed summaries into R loop or node_3.
- Do not make code write semantic summary text.
- Do not delete or overwrite old summaries.

## 7. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_168_night_summarize_changed_source_leaves.py -q
python main.py fast-test --profile graph
git diff --check
```
