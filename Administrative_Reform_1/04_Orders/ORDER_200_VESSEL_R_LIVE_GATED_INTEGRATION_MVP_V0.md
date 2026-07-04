# ORDER 200: Vessel R Live Gated Integration MVP v0

## Status

Implemented on 2026-07-04.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_200_vessel_r_live_gated_integration_implementation_2026_07_04_001.md`

## Trigger

ORDER 199 proved that a manual demo can run:

```text
Vessel read packet
-> R traverse
-> R activity ledger
-> node_0 R return packet
-> node_2
-> node_3
-> node_4
```

The next useful step is to let the normal live turn runtime use the same path, but only under an explicit gate.

## Goal

Add a narrow live-turn integration gate:

```text
qwen-turn/fake-turn/qwen-chat + explicit flag
-> node_1 may select route=R
-> Vessel R traverse runs
-> node_0 records start/end R packets
-> node_1 closes to route=2
-> node_2/node_3/node_4 use the R return material
```

Elementary explanation:

```text
Default chat still does not use R.
When the user turns on the special switch, 1 is allowed to choose R.
If R runs, it reads Vessel, 0 writes the receipt, then 3 answers with that receipt.
```

## CLI Shape

Add explicit flags to turn commands:

```powershell
python main.py qwen-turn "송련 Core의 그래프 기억 구조를 설명해줘" --enable-vessel-r-route --database neo4j --timeout 180 --pretty
python main.py qwen-chat --enable-vessel-r-route --database neo4j --timeout 180
python main.py fake-turn "Vessel 그래프 기억 구조를 설명해줘" --enable-vessel-r-route --pretty
```

`--enable-r-route-experimental` remains the older skeleton gate.

`--enable-vessel-r-route` is the new Vessel-backed live gate.

## Scope

The live runtime should record:

- `r_loop:vessel_read_packet`
- `r_loop:vessel_start_handoff_packet`
- `r_loop:vessel_traverse_result`
- `r_loop:vessel_activity_ledger`
- `r_loop:vessel_return_packet`
- turn activity graph link
- route close back to `route=2`
- node_2 source data ids including the Vessel R frames
- node_3 brief with Vessel R material when available

## Safety Boundaries

- Do not enable default route=R.
- Do not replace L route.
- Do not remove the older frame-only R skeleton.
- Do not write new Vessel graph memory nodes during the live answer path.
- Do not create scheduler/background R.
- Do not weaken node_4 checks.
- Do not make code generate semantic answers about graph content.

## Expected Failure Behavior

If Neo4j configuration is missing or R traversal fails:

```text
R return packet status = failed
node_3 may report the failure state
node_3 must not pretend graph memory was successfully inspected
node_4 must still block overclaims
```

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py
python -m pytest
python main.py smoke-test
git diff --check
```

Focused tests:

1. Default turn does not run Vessel R.
2. `--enable-vessel-r-route` allows route=R and records Vessel read/start/traverse/ledger/return frames.
3. The live route closes back to `route=2`.
4. node_3 brief receives Vessel R return material.
5. A failed Vessel read still creates a failed return packet and safe downstream state.

## Done Criteria

The user can run live turn commands with an explicit flag and see:

```text
R was gated.
R read Vessel.
0 recorded R start/end.
2/3/4 received the R material.
Default live chat remains unchanged when the flag is absent.
```
