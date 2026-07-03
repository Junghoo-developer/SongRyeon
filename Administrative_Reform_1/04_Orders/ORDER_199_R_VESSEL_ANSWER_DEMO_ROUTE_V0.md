# ORDER 199: R Vessel Answer Demo Route v0

## Status

Prepared on 2026-07-03 as the sixth implementation step after ORDER 194-198.

This order should be implemented only after at least ORDER 194, ORDER 195, and ORDER 198 are complete. ORDER 196 and ORDER 197 are strongly recommended first.

## Trigger

After ORDER 193, SongRyeon can package R traversal material for node_3.

After ORDER 194-198, R traversal should also have:

- node_0 start handoff
- R activity ledger
- raw capsule/activity linkage
- optional node_0 continuation checkpoints
- node_0 return packet

The next useful demo is one command that runs the whole R-to-answer path without turning on default `route=R`.

## Goal

Add a narrow manual demo CLI that runs:

```text
user question
-> node_0 Vessel R start handoff
-> Vessel R traverse
-> Vessel R activity ledger
-> node_0 R return packet
-> node_2 handoff
-> node_3 answer
-> node_4 guard
-> final renderer
```

Elementary explanation:

```text
Ask one question.
R searches Vessel.
0 records what happened.
3 answers using the R material.
4 checks that the answer does not lie about the material.
```

## CLI Shape

Suggested command:

```powershell
python main.py vessel-r-answer-demo "질문" --database neo4j --llm-mode fake --format text
python main.py vessel-r-answer-demo "질문" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Optional arguments:

```text
--limit
--max-node-reads
--max-raw-original-material-reads
--format text|json
--write-trace-cache
```

## Scope

This route may reuse existing fake/qwen adapters.

The route must create or expose:

- Vessel read packet
- node_0 R start handoff packet
- R traverse result
- R activity ledger
- node_0 R return packet
- node_2 handoff
- node_3 input brief with Vessel R material
- node_3 rendered report
- node_4 gatekeeper frame

The route should produce safe fallback output if node_3 or node_4 fails.

## Node3/Node4 Boundaries

node_3 may say:

```text
I used graph-memory material found by Vessel R traversal.
```

node_3 must not say:

```text
This was read_doc evidence.
This proves the whole graph memory is complete.
R route is now generally enabled.
```

node_4 must preserve the ORDER 193 checks:

- failed/partial R traversal cannot be reported as full success
- raw `graph:*` IDs should not leak in final user-facing answer
- R material must not be mislabeled as L document evidence

## Non-Goals

- Do not enable automatic route=R in `qwen-chat`.
- Do not change node_1 router policy.
- Do not write new Vessel graph nodes as part of answer demo.
- Do not add scheduler or autonomous background R.
- Do not add semantic search over graph nodes.
- Do not remove existing `vessel-r-traverse`.

## Test Plan

Required:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

Focused tests:

1. Fake demo route completes from start handoff to node_4 pass.
2. Failed R traversal demo route produces safe non-answer or partial answer.
3. node_3 brief contains Vessel R material from node_0 return packet.
4. node_4 blocks a fake answer that overclaims R success.
5. JSON output includes all key frame IDs for debugging.

Manual live test:

```powershell
python main.py vessel-r-answer-demo "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 설명해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Expected:

- The answer mentions graph-memory/Vessel R material.
- The answer does not call it `read_doc`.
- Runtime shows start handoff, activity ledger, return packet, node_3 brief, node_4 result.

## Done Criteria

The user can run one command and see:

```text
R found graph memory.
0 recorded the start/end boundary.
node_3 used the R material.
node_4 checked the answer.
```

without pretending that normal live chat now automatically routes through R.
