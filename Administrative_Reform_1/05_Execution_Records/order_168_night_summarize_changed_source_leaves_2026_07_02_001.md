# ORDER 168 Night Summarize Changed Source Leaves - Execution Record

## Summary

Implemented ORDER_168_NIGHT_SUMMARIZE_CHANGED_SOURCE_LEAVES_V0.

The MVP summarizes newly observed or changed code/document `raw_source` leaves one-to-one.

Successful result shape:

```text
raw_source leaf <- SUMMARY_OF <- source leaf SummaryGraphNode
```

## Key Changes

- Added `NightSourceLeafSummaryFrame`.
- Added `songryeon_core/nodes/night_summarize_source_leaf.py`.
- Added `songryeon_core/prompts/night_summarize_source_leaf_v0.md`.
- Added `run_night_summarize_source_leaf(...)`.
- Added `run_night_summarize_changed_source_leaves(...)`.
- Added ORDER_168 graph fast-test coverage.

## Selection Rule

Code reads `SourceObservationLedgerFrame`.

Summarized:

- `observation_status=new_source_version`
- `observation_status=content_changed`

Not summarized:

- `observation_status=unchanged`

This selection is code-checkable absolute information based on source observation records.

## Text Snapshot Rule

If the raw source has a text snapshot and non-empty text, the LLM summary runs.

If the raw source has no text snapshot:

```text
summary_status=skipped_no_text_snapshot
info_class=absolute
semantic_judgement_status=not_run
```

If the text snapshot is empty:

```text
summary_status=skipped_empty_text
info_class=absolute
semantic_judgement_status=not_run
```

Code does not invent semantic summary text.

## Metainfo

Successful source leaf summaries are:

```text
info_class=relative
source_mode=single_source
claim_alignment=single_absolute_record
semantic_judgement_status=ran
generated_by=LLM:*:night_summarize_source_leaf
```

Reason:

One LLM summary is grounded in exactly one `raw_source` graph node and its copied text snapshot.

## Validation

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_168_night_summarize_changed_source_leaves.py -q
python main.py fast-test --profile graph
```

Observed:

```text
ORDER_168 pytest: 6 passed
graph fast-test: FAST_TEST_OK, 84 passed
```

## Non-goals Preserved

- Did not summarize unchanged observations.
- Did not summarize source kind bundles.
- Did not summarize conversation TimeBundles in this order.
- Did not create semantic axis.
- Did not auto-feed summaries into R loop or node_3.
- Did not delete or overwrite old summaries.
- Did not make code write semantic summary text.
