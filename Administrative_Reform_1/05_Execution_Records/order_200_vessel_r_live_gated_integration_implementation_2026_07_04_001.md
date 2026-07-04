# ORDER 200 Vessel R Live Gated Integration Implementation - 2026-07-04 001

## Summary

Implemented a gated live-turn Vessel R route.

The default live runtime still does not enable route `R`. A live turn may use the Vessel-backed R path only when `enable_vessel_r_route` / `--enable-vessel-r-route` is explicitly set.

## Changed Files

- `Administrative_Reform_1/04_Orders/ORDER_200_VESSEL_R_LIVE_GATED_INTEGRATION_MVP_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/runtime/r_loop_vessel_live_route.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/user_turn.py`
- `main.py`
- `songryeon_core/llm/fake.py`
- `tests/test_import_baseline.py`
- `tests/test_order_200_vessel_r_live_gated_integration.py`

## Implementation Notes

- Added `record_vessel_r_live_route()` as a shared runtime helper.
- Added live turn parameters and CLI flags:
  - `--enable-vessel-r-route`
  - `--vessel-uri`
  - `--vessel-user`
  - `--vessel-password`
  - `--database`
  - `--vessel-allow-no-auth`
  - `--vessel-limit`
  - `--vessel-max-node-reads`
  - `--vessel-max-raw-original-material-reads`
- `--enable-r-route-experimental` remains the older frame-only skeleton route.
- `--enable-vessel-r-route` is the new Vessel-backed route gate.
- When node_1 selects route `R` under the Vessel gate, the live runtime records:
  - Vessel R read packet
  - node_0 Vessel R start handoff
  - Vessel R traversal result
  - Vessel R activity ledger
  - node_0 Vessel R return packet
  - turn activity graph link
  - route close back to `route=2`
- The Vessel R output data ids are included in `Node2InputFrame.source_data_ids`, so node_2/node_3 can see the node_0 return packet.
- The runtime summary now exposes Vessel R read/traverse/return/node3 material status.
- Fake node_1 selects route `R` only when route `R` is allowed by the runtime payload and the request is graph/Vessel related.
- Fake node_3 now chooses the first Vessel R material item with summary text instead of assuming the first path item has summary text.

## Boundaries Preserved

- Default `qwen-turn` / `qwen-chat` route `R` is not enabled.
- The older R experimental skeleton remains available separately.
- No new Vessel graph memory nodes are written during the live answer path.
- No scheduler/background R route was added.
- node_4 checks were not weakened.
- Code does not write graph-content semantic answers; it records and transports R material.

## Verification

Commands:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py -q
python -m pytest tests/test_import_baseline.py tests/test_order_199_r_vessel_answer_demo_route.py tests/test_order_200_vessel_r_live_gated_integration.py -q
python main.py smoke-test
python -m pytest
git diff --check
```

Results:

- `compileall`: passed
- focused ORDER 200 pytest: `3 passed`
- focused import/order199/order200 pytest: `8 passed`
- smoke-test: `SMOKE_TEST_OK`
- full pytest: `307 passed in 1071.70s`
- `git diff --check`: passed

## Remaining Notes

- Live Qwen route `R` still depends on node_1 selecting route `R` under the explicit gate.
- This order does not make R the default route.
- This order does not yet add a polished final-answer UX for general graph questions; it only makes the live gated path structurally available and verifiable.
