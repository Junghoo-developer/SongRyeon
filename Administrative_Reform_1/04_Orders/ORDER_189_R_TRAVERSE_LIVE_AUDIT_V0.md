# ORDER 189: R Traverse Live Audit v0

## Status

Approved by the user on 2026-07-03 for immediate audit.

## Trigger

ORDER 184-188 made R Vessel traversal able to start from CoreEgo, descend through graph layers, prefer summary layers before raw originals, and cap raw original material inspection at 5.

The next risk is not missing another large feature. The next risk is believing the R loop is useful before live traversal behavior is checked.

## Goal

Audit whether current R Vessel traversal can safely and usefully inspect the Vessel graph in live/manual tests.

This order is an audit order, not a feature expansion order.

## Questions To Answer

1. Does R traversal start from the CoreEgo/time-axis surface instead of seeing every summary at once?
2. Does R traversal descend through graph layers in a readable order?
3. Does R traversal prefer summary material before raw source material?
4. Does R traversal open raw originals only when traversal requires it?
5. Does the raw original material cap stay visible and enforced?
6. Does the final result distinguish:
   - summary-only inspection
   - raw-original inspection
   - partial traversal
   - budget/cap stop
7. Does the output provide enough information for the next MVP without pretending to be a full user-facing answer?

## Expected Traversal Shape

The expected high-level path is:

```text
CoreEgo
-> Time Axis
-> Time Bundle or Source Ingest Bundle
-> Source Kind Bundle
-> Token Budget Bundle / Summary Layer
-> Source Leaf Summary
-> RawSource only if needed
```

This order does not require every test to reach every layer. It requires the runtime to make the reached layer, stop reason, and material type clear.

## Live Test Pack

Run at least one fake-adapter test and, if Qwen is available, at least two Qwen tests.

### Test 1: Structure Walk

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조를 CoreEgo에서 시작해서 한 단계씩 내려가며 설명 가능한 만큼만 탐색해줘" --database neo4j --llm-mode fake --format text
```

Expected:

- read packet passes.
- traversal starts from graph entry layer.
- no raw original material is opened unnecessarily.

### Test 2: Summary Layer Link

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Expected:

- traversal does not jump straight to arbitrary leaf summaries.
- token-budget or summary layer appears before raw originals.
- if traversal ends partial, the stop reason is clear.

### Test 3: Code/Document Separation

```powershell
python main.py vessel-r-traverse "송련 Core 그래프 기억에서 코드 파일과 내부 문서가 서로 어떻게 분리되어 저장됐는지 계층적으로 확인해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Expected:

- source kind separation is visible.
- R2/R3 does not claim raw text was read unless raw material count confirms it.

### Test 4: Raw Cap Stress

```powershell
python main.py vessel-r-traverse "가능하면 원본까지 내려가되, 원본을 너무 많이 열지 말고 어떤 지점에서 멈추는지 확인해줘" --database neo4j --llm-mode qwen --timeout 180 --format text
```

Expected:

- raw original material count is visible.
- raw original material count never exceeds 5.
- if cap is reached, reason uses `CODE_STATUS:r_loop_raw_original_read_cap_reached`.

## Audit Report Template

For each live test, record:

- command
- status
- step_count
- final_graph_node_id
- final_sufficiency_status
- final_continuation_status
- r_loop_task_status
- terminal_material_seen_count
- raw_original_material_seen_count
- max_raw_original_material_count
- raw_original_read_cap_reached
- whether traversal path is understandable
- whether the result is pass, partial, or fail
- observed bottleneck

## Non-Goals

- Do not connect R traversal to normal qwen-chat routing.
- Do not make node_1 choose route=R by default.
- Do not change R1/R2/R3 prompt policy unless the audit proves a narrow defect.
- Do not add semantic-axis traversal.
- Do not add graph write behavior.
- Do not increase raw original cap.
- Do not replace summaries with raw originals.
- Do not add keyword heuristics.

## Completion Criteria

- ORDER 189 is documented.
- At least fake traversal is run and recorded.
- If Neo4j/Qwen are available, Qwen live traversal is run and recorded.
- The audit report states the next MVP candidate based on observed behavior.

