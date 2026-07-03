# ORDER 169: Night Changed Source Summary CLI v0

## 1. Goal

ORDER_168의 changed source leaf summary engine을 사람이 터미널에서 한 번에 실행할 수 있게 한다.

목표 실행 흐름:

```text
SongRyeon Core source manifest
-> graph source ingest with text snapshots
-> SourceObservationLedgerFrame
-> summarize new/content_changed raw_source leaves
-> graph export packet
-> Vessel write plan
-> optional local Neo4j write
```

## 2. Command

Add a manual opt-in CLI command:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen
```

Optional Neo4j write:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen --write-vessel
```

## 3. Rules

- Code selects source leaves only from `SourceObservationLedgerFrame`.
- Summarize only `new_source_version` and `content_changed`.
- Do not summarize `unchanged`.
- Use raw source text snapshots as the LLM input.
- Successful summaries remain `relative` because each summary maps to exactly one raw source leaf.
- Missing or empty text snapshots must produce skipped status records, not fake summary graph nodes.
- Neo4j write must remain explicit opt-in.

## 4. Non-goals

- Do not create semantic axis.
- Do not run R loop.
- Do not feed summaries into node_3 automatically.
- Do not summarize source kind bundles.
- Do not summarize conversation TimeBundles in this command.
- Do not delete or overwrite previous summaries.
- Do not make code write semantic summary text.

## 5. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_169_night_changed_source_summary_cli.py -q
python main.py fast-test --profile graph
git diff --check
```
