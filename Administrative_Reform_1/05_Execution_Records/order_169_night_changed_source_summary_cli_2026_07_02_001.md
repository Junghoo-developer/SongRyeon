# ORDER 169 Night Changed Source Summary CLI - Execution Record

## Summary

Implemented ORDER_169_NIGHT_CHANGED_SOURCE_SUMMARY_CLI_V0.

Added a manual opt-in CLI command:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen
```

Optional Vessel write:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen --write-vessel
```

## Runtime Flow

```text
SongRyeon Core source manifest
-> graph source ingest with text snapshots
-> SourceObservationLedgerFrame
-> summarize new/content_changed raw_source leaves
-> graph export packet
-> Vessel write plan
-> optional Neo4j write
```

## Local Cache

The command stores trace/data cache under:

```text
.songryeon_core_cache/night_changed_sources/
```

This is required so the next run can compare source observations and skip `unchanged` files.

Without this cache, every fresh process would treat every file as `new_source_version`.

## Metainfo

Successful source leaf summaries remain:

```text
info_class=relative
source_mode=single_source
claim_alignment=single_absolute_record
semantic_judgement_status=ran
```

Reason:

Each summary is grounded in exactly one `raw_source` graph leaf and its copied text snapshot.

The batch command summary itself is code-generated absolute runtime status.

## Safety

- Neo4j write is explicit opt-in via `--write-vessel`.
- Default `--llm-mode` is `off`.
- `--llm-mode fake` is deterministic test mode.
- `--llm-mode qwen` uses the normal Qwen adapter/runtime config.
- The command does not feed summaries into R loop or node_3.
- The command does not create semantic axis.
- The command does not overwrite old summaries.

## Validation

Passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_169_night_changed_source_summary_cli.py -q
python main.py fast-test --profile graph
```

Observed:

```text
ORDER_169 pytest: 4 passed
graph fast-test: FAST_TEST_OK, 88 passed
```
