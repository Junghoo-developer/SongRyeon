# ORDER 194-199 R Node0 Capsule Integration Order Batch 2026-07-03 001

## Summary

Prepared six implementation-ready orders to realize the missing R-loop memory/capsule integration discussed after ORDER 193.

The user's questions were:

- Does node_0 supply stable memory to R like it does for L?
- Does node_0 supply memory at R start and recover it at R end?
- Are R-loop activities stored in the turn capsule and graph-memory ledger?

Current answer before these orders:

- R has partial start handoff in older dry-run code.
- Vessel R traverse has read packet/traverse frames, but not a full node_0 start/end management path.
- Vessel R activity is not yet fully connected to TurnStateCapsule/RawCapsule as a ledger.

## Orders Added

- `ORDER_194_R_VESSEL_NODE0_START_HANDOFF_PACKET_V0.md`
- `ORDER_195_R_VESSEL_ACTIVITY_LEDGER_V0.md`
- `ORDER_196_R_VESSEL_ACTIVITY_LEDGER_RAW_CAPSULE_LINK_V0.md`
- `ORDER_197_R_VESSEL_NODE0_CONTINUATION_CHECKPOINT_PACKET_V0.md`
- `ORDER_198_R_VESSEL_NODE0_RETURN_PACKET_V0.md`
- `ORDER_199_R_VESSEL_ANSWER_DEMO_ROUTE_V0.md`

## Intended Sequence

```text
194: node_0 supplies R start packet
195: R traversal becomes one activity ledger
196: R activity ledger links to raw capsule
197: node_0 records mid-loop continuation checkpoints
198: node_0 records R return packet
199: one-command R answer demo route
```

## Boundary

These are order documents only.

No code implementation was performed in this batch.

The orders explicitly preserve these constraints:

- no default `route=R` in normal qwen-chat
- no semantic relevance heuristic
- no hidden code summary
- no weakening node_4
- no merging Vessel R material into L `read_doc` material
- no autonomous scheduler/background R

## Verification

```powershell
git diff --check
```

Passed after document creation.
