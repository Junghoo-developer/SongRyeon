# ORDER 149: R Graph Traversal Candidate Surface v0

## 1. Goal

R loop가 다음 graph node로 이동하기 전에, code가 확인 가능한 graph 좌표만 모아 `RGraphTraversalCandidateSurfaceFrame`으로 정리한다.

ORDER_148은 R skeleton이 어떤 graph node를 보았는지 `TurnGraphAccessLedgerFrame`으로 남겼다. ORDER_149는 그 다음 단계로, R3가 검사한 graph node에서 이동 가능한 후보를 명시적인 후보판으로 만든다.

## 2. Background

현재 R skeleton은 다음 frame을 만든다.

- `R2GraphNodeSelectionFrame`
- `R3GraphInspectionFrame`
- `RLoopContinuationFrame`
- `RLoopReturnSummaryFrame`
- `TurnGraphAccessLedgerFrame`

그러나 R3 이후 다음 R2가 볼 수 있는 후보 목록이 별도 frame으로 정리되어 있지 않다.

ORDER_148에서 raw capsule 사이 `NEXT` edge가 추가되었으므로, 이제 code는 다음 후보를 절대정보로 모을 수 있다.

- inspected node의 child/source graph nodes
- inspected node의 outgoing `NEXT` target
- inspected node의 incoming `NEXT` source

## 3. Scope

### 3.1 New schema

Add:

```text
RGraphTraversalCandidateSurfaceFrame
```

Minimum fields:

- `frame_id`
- `source_r3_inspection_frame_id`
- `inspected_graph_node_id`
- `child_candidate_node_ids`
- `next_candidate_node_ids`
- `previous_candidate_node_ids`
- `candidate_graph_node_ids`
- `candidate_records`
- `candidate_count`
- `source_data_ids`
- `source_trace_ids`
- `generated_by=CODE:R_GRAPH_TRAVERSAL_CANDIDATE_SURFACE`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

### 3.2 Candidate sources

Code may copy only these coordinates:

- `R3GraphInspectionFrame.child_node_ids`
- DataStore graph edge payloads where:
  - `edge_kind=NEXT`
  - `from_node_id == inspected_graph_node_id`
  - `to_node_id == inspected_graph_node_id`

Candidate records must include:

- `candidate_node_id`
- `relation`
- `source_frame_id` or `source_edge_id`
- `source_field`

### 3.3 R skeleton connection

- `run_r_loop_dry_run_skeleton()` creates and records this frame after R3 inspection.
- The access ledger includes this candidate surface as an additional `candidate_seen` source.
- R2 selection behavior is not changed in this order.

## 4. Non-goals

- Do not implement multi-step R traversal.
- Do not let R2 choose from the new candidate surface yet.
- Do not add R LLM traversal.
- Do not open live R route beyond existing experimental gate.
- Do not add semantic relevance ranking.
- Do not connect Neo4j or external DB.
- Do not summarize graph node contents.

## 5. Test Plan

Required commands:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Additional pytest:

- Candidate surface copies R3 child candidates.
- Candidate surface copies outgoing `NEXT` target.
- Candidate surface copies incoming `NEXT` source as previous candidate.
- Candidate surface is code-generated absolute information.
- R skeleton records the candidate surface to DataStore.
- Access ledger includes candidate records sourced from the candidate surface.

## 6. Completion Report Must Include

- where the candidate surface schema is defined
- where the candidate surface is generated
- which graph relations are copied
- what was deliberately not implemented
- compileall / pytest / smoke-test result
