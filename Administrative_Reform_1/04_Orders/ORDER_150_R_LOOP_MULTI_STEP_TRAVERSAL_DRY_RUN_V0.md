# ORDER 150: R Loop Multi-Step Traversal Dry-Run v0

## 1. Goal

ORDER_149에서 만든 `RGraphTraversalCandidateSurfaceFrame`을 R dry-run skeleton이 실제로 한 번 이상 소비하게 만든다.

이번 발주는 live R route 확장이 아니라, dry-run/fake 환경에서만 graph traversal frame chain이 예산 안에서 여러 step 이어질 수 있는지 검증하는 작업이다.

## 2. Background

현재 R skeleton은 다음 흐름을 가진다.

```text
R1 goal
R budget
R2 select entry node
R3 inspect selected node
candidate surface
continuation
return summary
access ledger
```

그러나 continuation이 `continue_deeper`를 내도 실제 다음 R2/R3 step은 열리지 않는다.

ORDER_150은 다음을 확인한다.

```text
R3 says continue_deeper
candidate surface has candidate nodes
budget remains
-> dry-run code selects the next candidate coordinate
-> R3 inspects it
-> repeat within narrow cap
```

## 3. Scope

### 3.1 Multi-step dry-run only

- `run_r_loop_dry_run_skeleton()` 안에서만 multi-step traversal을 연다.
- qwen-chat/live R route 일반 개방은 하지 않는다.
- R LLM selector는 만들지 않는다.

### 3.2 Candidate consumption

- R2 step 1은 기존처럼 handoff entry node를 선택한다.
- R2 step 2+는 직전 `RGraphTraversalCandidateSurfaceFrame.candidate_graph_node_ids` 안에서만 선택한다.
- 이번 dry-run의 deterministic selection은 의미 판단이 아니라 wiring verification이다.
- selection reason은 `CODE_STATUS:*`로 명시한다.

### 3.3 Budget semantics

- entry node를 읽는 것은 traversal depth 0으로 본다.
- child edge를 따라 한 번 내려가면 traversal depth 1이다.
- `max_traversal_depth=2`면 `time_axis -> time_bundle -> raw_capsule`까지 확인 가능하다.
- node read count는 실제 inspected graph node 수를 따른다.

### 3.4 Summary and ledger

- return summary는 모든 selected/inspected graph node id를 누적한다.
- access ledger는 모든 candidate/selected/inspected graph node id를 누적한다.
- candidate surface frame도 step별로 기록한다.

## 4. Non-goals

- 외부 DB/Neo4j 연결을 열지 않는다.
- R LLM traversal을 만들지 않는다.
- live R route policy를 넓히지 않는다.
- node_3 답변 본문에 graph traversal 내용을 새로 주입하지 않는다.
- graph node 원문 요약/의미 요약을 만들지 않는다.
- semantic relevance ranking을 만들지 않는다.

## 5. Test Plan

Required commands:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Additional pytest:

- default R dry-run reaches raw capsule through candidate surface within depth 2.
- step 2+ R2 selection only chooses IDs from previous candidate surface.
- final return summary accumulates selected/inspected graph nodes.
- access ledger accumulates candidate/selected/inspected graph nodes across steps.
- force budget exhausted still stops after first step.

## 6. Completion Report Must Include

- how many R traversal steps dry-run executes
- how candidate surface is consumed
- how budget usage is counted
- what remains unopened
- compileall / pytest / smoke-test result
