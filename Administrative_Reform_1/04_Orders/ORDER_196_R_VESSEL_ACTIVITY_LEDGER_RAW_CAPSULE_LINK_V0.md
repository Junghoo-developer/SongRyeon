# ORDER 196: R Vessel Activity Ledger Raw Capsule Link v0

## Status

Implemented on 2026-07-03 as the third implementation step after ORDER 195.

This order depends on ORDER 195.

Execution record:

- `Administrative_Reform_1/05_Execution_Records/order_196_r_vessel_activity_ledger_raw_capsule_link_implementation_2026_07_03_001.md`

## Trigger

ORDER 152 links raw turn capsules to L activity ledgers and older R graph access ledgers.

But the new Vessel-backed R traversal will have its own activity ledger after ORDER 195.

That new ledger must also be discoverable from the turn's raw capsule.

## Goal

Connect the current turn's raw capsule graph node to the Vessel R activity ledger graph node.

Elementary explanation:

```text
The turn capsule says, "What happened this turn?"
The R ledger says, "Here is what R looked at."
This order ties those two cards together.
```

## Graph Shape

Add or extend the existing activity link shape:

```text
graph:raw_capsule:{turn_id}
  -[HAS_ACTIVITY_LEDGER]->
graph:activity_ledger:{r_vessel_activity_ledger_data_id}
```

The activity ledger graph node should keep a clear `data_kind`, for example:

```text
vessel_r_activity_ledger
```

This must remain different from:

```text
l_loop_activity_ledger
r_graph_access_ledger
```

unless a later explicit refactor merges those types.

## Scope

Extend or wrap:

```text
record_turn_activity_graph_links(...)
```

Suggested new input:

```text
r_vessel_activity_ledger_data_ids: list[str] | None = None
```

Suggested frame field:

```text
r_vessel_activity_ledger_data_ids
```

Rules:

- Create activity ledger graph nodes for Vessel R ledger records.
- Create `HAS_ACTIVITY_LEDGER` edges from raw capsule to those nodes.
- Record source trace/data IDs.
- Do not rewrite the raw capsule.
- Do not summarize ledger contents.

## Non-Goals

- Do not write to Neo4j automatically unless an existing graph export path explicitly picks up these graph memory records.
- Do not add R answer route.
- Do not add node_0 checkpoints.
- Do not infer relevance or importance.
- Do not delete older activity ledger nodes.

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

Focused tests:

1. Given a Vessel R activity ledger, raw capsule link frame records its data ID.
2. The generated activity ledger graph node uses `data_kind=vessel_r_activity_ledger`.
3. The generated edge points from `graph:raw_capsule:{turn_id}` to that activity node.
4. Existing L ledger and old R dry-run ledger links still pass.
5. Missing Vessel R ledger list does not create fake nodes.

## Done Criteria

From one turn, code can trace:

```text
TurnStateCapsule
-> raw capsule graph node
-> Vessel R activity ledger node
-> R selected/inspected graph node IDs
```

without re-running R traversal.
