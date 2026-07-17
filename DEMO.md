# SongRyeon Core Demo Path

This file is the practical path for showing SongRyeon Core to another developer.

The demo is split into three layers:

```text
Layer 1. No model, no Neo4j: prove the runtime can run.
Layer 2. Local verification: prove the baseline tests pass.
Layer 3. Optional graph memory: show the Neo4j Vessel / R traversal path.
```

## Three-Minute Reviewer Path

This path needs only Python and the repository. It does not need model weights, Ollama,
Neo4j, or an external API.

```powershell
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --compact
python main.py quick-smoke
```

What to verify in the first output:

1. The runtime names the fake adapter instead of pretending it is Qwen.
2. Route, L/R execution, memory transfer, evidence counts, and node_4 status are code-owned counts.
3. The answer labels itself as a deterministic no-model demo.
4. The full ledger is still available through the same command with `--pretty`.

## What To Say First

SongRyeon Core is not a polished assistant.
It is a local-first agent runtime experiment focused on provenance, runtime honesty, and separating code-verified facts from LLM judgments.

The most stable story today is:

```text
1. The runtime records code-verified facts and LLM judgments separately.
2. A fake adapter can run the full node/report/check path without Qwen.
3. Internal documents and source files can be ingested into graph memory.
4. A local Neo4j Vessel can store that graph.
5. Experimental R traversal can walk that graph through explicit R1/R2/R3 frames.
```

## Layer 1: First Run Without Qwen Or Neo4j

Use this when someone has only Python and the repository.

```powershell
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty
```

Expected signals:

```text
상태: ok
route=2
node_4 gatekeeper: pass
FINAL_BLOCKED_BY_GATEKEEPER does not appear
```

What this proves:

- The CLI starts.
- The fake LLM adapter works.
- node_1 -> node_2 -> node_3 -> node_4 can complete.
- The final answer admits that it is a deterministic fake demo, not a real Qwen answer.

What this does not prove:

- It does not prove Qwen quality.
- It does not prove Neo4j setup.
- It does not prove R traversal.

## Layer 2: Local Baseline Tests

Install dev/test dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the normal baseline:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Expected smoke result:

```text
SMOKE_TEST_OK
```

Faster graph-focused check:

```powershell
python main.py fast-test --profile graph
```

What this proves:

- Syntax/import checks pass.
- Pytest regression tests pass.
- Integrated runtime smoke still passes.

## Layer 3: Optional Neo4j Vessel Setup

Neo4j is optional. The normal tests do not require it.

For local Vessel commands, configure these environment variables in your PowerShell session:

```powershell
$env:SONGRYEON_NEO4J_URI="bolt://localhost:7687"
$env:SONGRYEON_NEO4J_USER="neo4j"
$env:SONGRYEON_NEO4J_PASSWORD="<your-local-password>"
$env:SONGRYEON_NEO4J_DATABASE="neo4j"
```

If you use a local env script, do not commit it.

Useful failure meanings:

```text
neo4j_config_missing  -> password/env was not supplied
adapter_unavailable   -> Neo4j connection/config failed before graph read
read_failed           -> Neo4j was reached, but auth/query/read failed
```

## Vessel Readback

Check whether the basic CoreEgo -> Time Axis -> Time Bundle path exists:

```powershell
python main.py vessel-readback --database neo4j
```

Useful success fields:

```text
status: VESSEL_READBACK_OK
readback_status: passed
core_path_exists: true
```

## Vessel Inspect

Print a readable graph path:

```powershell
python main.py vessel-inspect --database neo4j --format text
```

The output should show a path shaped like:

```text
CoreEgo
  HAS_AXIS -> Time Axis
    HAS_BUNDLE -> Time Bundle
      CONTAINS_MEMORY -> Raw Capsule
```

When source ingestion and night summaries exist, inspect output can also show source/summary layers.

## R Traversal Demo

Deterministic fake traversal:

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조를 계층적으로 탐색해줘" --database neo4j --llm-mode fake --format text
```

Live Qwen/Ollama traversal:

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘. 과거 대화 기억 가지가 아니라 코드/문서 소스 가지를 우선 보고, 시간축에서 시작해서 어떤 묶음을 거쳐 내려가는지 말해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

Important output fields:

```text
status
traverse_status
step_count
final_graph_node_id
terminal_material_seen_count
raw_original_material_seen_count
```

What this proves:

- The CLI can read graph-memory candidates from Vessel.
- R1/R2/R3 traversal frames can run.
- The traversal reports whether it reached terminal material.

What this does not prove:

- It does not mean the normal chat route always uses R.
- It does not mean R traversal is production-ready.
- It does not replace L document/source-code lookup.

## Optional Qwen Turn

If Ollama/Qwen is configured:

```powershell
python main.py qwen-ping --timeout 60
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇인지 알려줘" --timeout 120 --pretty
```

To let node_1 choose the experimental Vessel R route when appropriate:

```powershell
python main.py qwen-turn "송련 Core의 그래프 기억 구조를 설명해줘. 문서 검색보다 그래프 기억 탐색이 적합한지 판단해서 답해줘." --enable-vessel-r-route --database neo4j --timeout 180 --pretty
```

Useful failure meanings:

```text
structure_failed             -> a schema/runtime boundary failed
FINAL_BLOCKED_BY_GATEKEEPER  -> node_4 refused to publish an unsafe or mismatched answer
adapter_missing              -> Qwen adapter was not available
```

## Night Summary Pipeline

The source summary path can be slow with a real local LLM.

Changed source leaf summary:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode fake --write-vessel --database neo4j
```

Real Qwen run:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen --write-vessel --database neo4j --timeout 180
```

Token-budget layer summary:

```powershell
python main.py night-summarize-token-layer --llm-mode fake --write-vessel --database neo4j --until-context-budget
```

Checkpointed longer run:

```powershell
python main.py night-summarize-token-layer --llm-mode qwen --write-vessel --database neo4j --until-context-budget --vessel-write-mode every-step --max-runtime-minutes 30 --progress-jsonl .songryeon_core_cache/night_token_layer_progress.jsonl
```

## Current Limits

- R traversal is still experimental.
- Normal `qwen-chat` is not a polished public assistant product.
- Neo4j setup is local and manual.
- Qwen/Ollama quality depends on the local model and machine.
- The project favors provenance and testable records over polished UX.
