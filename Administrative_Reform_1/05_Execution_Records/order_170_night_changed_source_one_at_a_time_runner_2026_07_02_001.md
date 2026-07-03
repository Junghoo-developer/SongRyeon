# ORDER 170 Execution Record: Night Changed Source One-At-A-Time Runner

## Summary

Implemented `night-summarize-changed-sources --one-at-a-time`.

The default ORDER_169 all-at-once mode remains unchanged. The new one-at-a-time mode records a code-generated queue of `new_source_version` / `content_changed` raw source leaves and processes exactly one unprocessed leaf per command run.

## Key Changes

- Added order document:
  - `Administrative_Reform_1/04_Orders/ORDER_170_NIGHT_CHANGED_SOURCE_ONE_AT_A_TIME_RUNNER_V0.md`
- Updated order index:
  - `Administrative_Reform_1/04_Orders/README.md`
- Added source leaf selection helper:
  - `songryeon_core/nodes/night_summarize_source_leaf.py`
- Added one-at-a-time runtime queue and step runner:
  - `songryeon_core/runtime/night_changed_source_summary.py`
- Added CLI option:
  - `python main.py night-summarize-changed-sources --one-at-a-time`
- Added tests:
  - `tests/test_order_170_night_changed_source_one_at_a_time.py`

## Design Notes

- The queue is `info_class=absolute` and `semantic_judgement_status=not_run`.
- The queue is not an LLM summary. It is a code-generated list of graph leaf IDs selected from `SourceObservationLedgerFrame`.
- The LLM still writes only the summary text for one raw source leaf at a time.
- DataStore records are not updated in place. Progress is computed from existing summary node/frame records.
- Re-running the same one-at-a-time `batch_id` reads the existing queue instead of re-observing all source files, so unprocessed targets do not disappear as `unchanged`.
- Optional Vessel/Neo4j write remains explicit through `--write-vessel`.

## Verification

```powershell
python -m compileall songryeon_core main.py
# passed

python -m pytest tests/test_order_170_night_changed_source_one_at_a_time.py tests/test_order_169_night_changed_source_summary_cli.py -q
# 7 passed

python main.py fast-test --profile graph
# FAST_TEST_OK, 91 passed

git diff --check
# passed
```

## Not Done

- No semantic axis.
- No R loop activation.
- No source kind bundle or source ingest time bundle summary.
- No automatic failed-leaf retry policy.
- No deletion or overwrite of older summary records.
