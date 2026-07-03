# order_167_night_summary_naming_clarity_2026_07_02_001

## Summary

ORDER 167을 구현했다.

ORDER 166에서 추가한 심야정부 TimeBundle summary worker의 표준 이름을 더 읽기 쉬운 형태로 정리했다.

새 표준 이름:

```text
night_summarize_time_bundle
run_night_summarize_time_bundle
songryeon_core/prompts/night_summarize_time_bundle_v0.md
```

기존 이름은 compatibility wrapper로 유지했다.

## Changed Files

- `Administrative_Reform_1/04_Orders/ORDER_167_NIGHT_SUMMARY_NAMING_CLARITY_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schema_parts/graph_memory.py`
- `songryeon_core/nodes/night_summarize_time_bundle.py`
- `songryeon_core/nodes/night_time_bundle_summary_worker.py`
- `songryeon_core/prompts/night_summarize_time_bundle_v0.md`
- `tests/test_order_166_night_time_bundle_summary_node.py`

## Naming Result

Old implementation module was moved to:

```text
songryeon_core/nodes/night_summarize_time_bundle.py
```

Old module now exists only as a compatibility import surface:

```text
songryeon_core/nodes/night_time_bundle_summary_worker.py
```

New code should call:

```python
run_night_summarize_time_bundle(...)
```

Old code may still call:

```python
run_night_time_bundle_summary_worker(...)
```

## Data Naming

New node id:

```text
night_summarize_time_bundle
```

New prompt ref:

```text
songryeon_core/prompts/night_summarize_time_bundle_v0.md
```

Failed frame data type:

```text
node_output:night_summarize_time_bundle_frame
```

Successful graph summary node and edge data types are unchanged:

```text
graph_memory:node:summary
graph_memory:edge:SUMMARY_OF
```

## Deliberately Not Changed

- `NightTimeBundleSummaryFrame` schema name remains unchanged.
- Existing graph summary node IDs remain compatible.
- Summary generation policy is unchanged.
- R loop usage remains unopened.
- Source kind bundle summary worker is not implemented here.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

Passed.

```powershell
python -m pytest tests/test_order_166_night_time_bundle_summary_node.py -q
```

Passed: `4 passed`.

```powershell
python main.py fast-test --profile graph
```

Passed: `FAST_TEST_OK`, graph pytest `78 passed`.

## Remaining Note

The old names still appear in compatibility wrappers and historical execution records. That is intentional. They should not be used as the primary names for new work.
