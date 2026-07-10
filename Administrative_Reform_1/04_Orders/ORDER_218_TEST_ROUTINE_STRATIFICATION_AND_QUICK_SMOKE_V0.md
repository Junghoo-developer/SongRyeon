# ORDER 218: Test Routine Stratification And Quick Smoke v0

## Status

Implemented on 2026-07-08.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_218_test_routine_stratification_and_quick_smoke_2026_07_08_001.md`

## Goal

Separate SongRyeon Core's fast daily checks from the expensive full smoke
baseline.

## Background

`smoke-test` started as a small health check, but it now runs many integration
cases. The current `songryeon_core/runtime/smoke_test.py` file contains dozens
of internal smoke cases and repeatedly runs full dry-turn flows. Document
memory smoke also rebuilds document/search surfaces over hundreds of Markdown
files.

This makes ordinary development feel slower than it needs to be.

## Scope

- Add a `quick-smoke` CLI command.
- Keep `smoke-test` as a legacy full integration baseline.
- Add `full-smoke` as an explicit alias for the full baseline.
- Exclude tests marked `smoke` from default `python -m pytest`.
- Keep focused pytest and fast-test available for normal development.

## Quick Smoke Rules

`quick-smoke` must not call:

- document search
- embedding index build
- Qwen/Ollama
- Neo4j/Vessel
- L/R traversal

It only checks the smallest local runtime skeleton:

- `TraceStore`
- `DataStore`
- default schema registry bindings

## Non-Goals

- Do not remove the full smoke baseline.
- Do not weaken existing smoke assertions.
- Do not cache or rewrite the document embedding index in this order.
- Do not change L/R runtime behavior.
- Do not touch Qwen or Neo4j execution policy.

## New Intended Routine

Daily tiny check:

```powershell
python main.py quick-smoke
```

Normal local check:

```powershell
python main.py fast-test --profile core
```

Graph/R-loop focused check:

```powershell
python main.py fast-test --profile graph
```

Full baseline:

```powershell
python main.py full-smoke
```

Pytest smoke-only run:

```powershell
python -m pytest -m smoke
```

## Completion Checks

- `python -m compileall songryeon_core main.py`
- `python main.py quick-smoke`
- `python -m pytest tests/test_order_218_test_routine_stratification.py`
- `python -m pytest tests/test_order_154_fast_test_gate.py tests/test_order_218_test_routine_stratification.py`
- `python main.py fast-test --profile core`
