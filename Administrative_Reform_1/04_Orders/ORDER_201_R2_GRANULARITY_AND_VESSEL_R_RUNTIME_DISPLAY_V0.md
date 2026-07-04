# ORDER 201: R2 Granularity Enum Contract And Vessel R Runtime Display v0

## Status

Implemented on 2026-07-04.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_201_r2_granularity_and_vessel_r_runtime_display_2026_07_04_001.md`

## Trigger

After ORDER 200, live `qwen-turn --enable-vessel-r-route` successfully entered route `R`.

However, the first live test exposed two narrow issues:

1. R2 failed schema validation with `R2 expected_information_granularity is invalid`.
2. Runtime display still described the Vessel R path as the older `R:R1_R2_R3_experimental_skeleton` path, and activity graph output did not clearly show the R Vessel ledger count.

## Goal

Fix the narrow contract/display mismatch without changing graph traversal semantics.

## Key Changes

- Add a code-supplied allowed granularity enum list to R2 input payload.
- Tell R2 to copy `expected_information_granularity` exactly from that enum list.
- Keep the R2 validator strict.
- Do not normalize or silently repair invalid LLM granularity output.
- Distinguish Vessel R from the older frame-only R skeleton in route path display.
- Show R Vessel ledger counts separately in terminal/runtime summaries.

## Non-Goals

- Do not force route `R`.
- Do not weaken R2 schema validation.
- Do not add hidden fallback or heuristic repair for bad R2 payloads.
- Do not change R1/R2/R3 traversal semantics.
- Do not change Neo4j writes.
- Do not enable R by default.

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py -q
python -m pytest tests/test_order_201_r2_granularity_and_vessel_r_display.py -q
python main.py smoke-test
git diff --check
```

Focused checks:

1. R2 input payload includes the allowed enum list.
2. The R2 prompt instructs exact enum copy.
3. Vessel R route path says `Vessel_R` rather than old skeleton.
4. Turn activity graph display separates `R_vessel_ledgers`.
5. Existing ORDER 200 live-gated fake flow still passes.

## Done Criteria

The next live R test should fail only for real traversal or model-choice reasons, not because the runtime failed to provide the R2 granularity enum contract. Runtime output should also make it obvious whether the path was old skeleton R or Vessel R.
