# ORDER_146 R Route Experimental Gate Implementation

Date: 2026-07-01

## Scope

Added an explicit experimental gate for node_1 LLM route=R.

This is not a general live R route opening. It only allows R when the runtime caller explicitly sets `enable_r_route_experimental=True` or the CLI flag `--enable-r-route-experimental`.

## Changed Files

- `songryeon_core/core/schemas.py`
  - Added route=R validation conditions for the experimental policy flag.
- `songryeon_core/nodes/node_1_router.py`
  - Added conditional `allowed_routes` expansion and R payload validation.
- `songryeon_core/runtime/dry_run.py`
  - Added `enable_r_route_experimental`.
  - Runs `R:experimental:*` skeleton when node_1 LLM selects R.
  - Closes back to `route:2` after the experimental R summary.
- `songryeon_core/loops/r_loop_dry_run.py`
  - Parameterized the deterministic R skeleton frame label/generator.
  - Added fallback R3 inspection from handoff coordinates when graph node records are not yet in DataStore.
- `songryeon_core/nodes/node_0_memory_supplier.py`
  - Allowed custom R handoff packet ids to avoid collision with the normal end-of-turn handoff.
- `songryeon_core/nodes/node_2_handoff.py`
  - Displays R experimental route path distinctly.
- `songryeon_core/runtime/terminal_view.py`
  - Distinguishes experimental R skeleton from dry-run R skeleton.
- `songryeon_core/runtime/user_turn.py`
  - Exposes experimental R status in turn summaries.
- `main.py`
  - Added `--enable-r-route-experimental`.
- `songryeon_core/prompts/node_1_router_v0.md`
  - Replaced hardcoded L/2 rule with payload-driven `allowed_routes`.
- `tests/test_order_146_r_route_experimental_gate.py`
  - Added focused tests.

## Boundary

- code does not choose R by keyword.
- node_1 LLM may choose R only when the explicit experimental gate is open.
- route=R frame must reveal:
  - `policy_flag=enable_r_route_experimental`
  - `route_source=LLM:*`
  - `llm_routing_status=ran`
  - `expected_next_0_mode=r_loop_graph_guide_handoff`
- experimental R records use `generated_by=CODE:R_ROUTE_EXPERIMENTAL_GATE`.
- experimental R closes to `route=2`; it does not create an open-ended R loop.

## Verification

Verification passed:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_146_r_route_experimental_gate.py -q
python -m pytest tests/test_order_145_r_loop_pre_live_route_baseline.py tests/test_order_146_r_route_experimental_gate.py -q
python -m pytest
python main.py smoke-test
git diff --check
```

Result:

- `python -m compileall songryeon_core main.py`: passed
- `python -m pytest tests/test_order_146_r_route_experimental_gate.py -q`: `6 passed`
- `python -m pytest tests/test_order_145_r_loop_pre_live_route_baseline.py tests/test_order_146_r_route_experimental_gate.py -q`: `13 passed`
- `python -m pytest`: `125 passed`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: passed

Additional manual parser check:

```powershell
python main.py fake-turn "R 실험 플래그 CLI 확인" --enable-r-route-experimental --pretty
```

The command ran successfully. The default fake adapter still chose route=2, which is expected because ORDER_146 does not add a keyword heuristic that forces R.

## Baseline Conclusion

The system now has three distinct R states:

```text
default runtime: route=R closed
dry-run fixture: enable_r_route_dry_run=True creates R:dry_run:* skeleton
experimental gate: enable_r_route_experimental=True allows node_1 LLM to choose route=R and creates R:experimental:* skeleton before closing to route=2
```

This is still not a full R loop. It is a controlled experimental gate and one-pass skeleton.
