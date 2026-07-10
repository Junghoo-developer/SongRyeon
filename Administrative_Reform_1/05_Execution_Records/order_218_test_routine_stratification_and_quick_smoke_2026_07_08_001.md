# ORDER 218 Execution Record: Test Routine Stratification And Quick Smoke

## Date

2026-07-08

## Summary

Implemented a lightweight `quick-smoke` command and separated the expensive
full smoke baseline from default pytest execution.

## Audit Findings

- `songryeon_core/runtime/smoke_test.py` has 6059 lines.
- It contains 40 internal `_run_` smoke helpers and 16 `_check_` helpers.
- It calls `run_dry_turn()` 41 times.
- `Administrative_Reform_1` currently contains 491 Markdown files.
- The document search path builds 1793 chunks from those files.
- A direct `search_docs(top_k=1)` timing probe took about 4.143 seconds.
- `tests/smoke/test_document_memory.py` took about 18.06 seconds by itself.
- Recent focused R-loop tests were not the bottleneck.

## Changes

- Added `songryeon_core/runtime/quick_smoke.py`.
- Added `python main.py quick-smoke`.
- Added `python main.py full-smoke` as an explicit full baseline alias.
- Kept `python main.py smoke-test` as the existing full smoke baseline for compatibility.
- Updated `pyproject.toml` so default pytest excludes `smoke` marker tests.
- Added `tests/test_order_218_test_routine_stratification.py`.
- Updated `Administrative_Reform_1/04_Orders/README.md`.

## New Routine

Smallest local health check:

```powershell
python main.py quick-smoke
```

Fast daily baseline:

```powershell
python main.py fast-test --profile core
```

Focused graph/R baseline:

```powershell
python main.py fast-test --profile graph
```

Full smoke baseline:

```powershell
python main.py full-smoke
```

Pytest full smoke cases:

```powershell
python -m pytest -m smoke
```

## Verification

- `python -m compileall songryeon_core main.py`: passed
- `python main.py quick-smoke`: passed, `QUICK_SMOKE_OK`
- `python -m pytest tests/test_order_218_test_routine_stratification.py -q`: 3 passed
- `python -m pytest tests/test_order_154_fast_test_gate.py tests/test_order_218_test_routine_stratification.py -q`: 7 passed
- `python main.py fast-test --profile core`: passed, `FAST_TEST_OK`, about 1.024 seconds
- `python -m pytest --collect-only -q`: 336 selected / 5 deselected
- `python -m pytest -m smoke --collect-only -q`: 5 selected / 336 deselected

## Not Run

Full smoke was not re-run in this order. The purpose of this order was to stop
full smoke from running accidentally during ordinary pytest usage, not to change
the full smoke assertions.

## Remaining Risk

Default pytest is lighter now, but the non-smoke suite still contains many
integration-style tests. Further speed work should audit slow non-smoke tests
with `--durations` and should cache or restructure document embedding index
builds separately.
