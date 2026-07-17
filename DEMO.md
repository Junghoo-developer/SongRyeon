# SongRyeon Core Demo Path

This is the official reviewer path for SongRyeon Core. The first demo needs only Python
and the repository. It does not need model weights, Ollama, Neo4j, or an external API.

## Three-Minute Reviewer Script

### 0:00-0:30 - State The Problem

Use this sentence:

> SongRyeon Core is a local document and source-code investigation agent that shows what
> a model actually read, separates code-verified facts from model interpretation, and
> blocks explicit evidence-role conflicts before public release.

Do not claim that the project solves hallucinations in general. The current code guard
checks explicit structural conflicts that code can prove, such as document roles, actual
read status, and counts.

### 0:30-1:00 - Run One Command

```powershell
python main.py competition-demo
```

The command runs deterministic test doubles only. `external_api_calls=0` and
`neo4j_connections=0` are part of the returned result, not an inference from timing.

### 1:00-1:30 - Scene 1: LOCAL

Point to the full local report/check path and the final `pass`. This proves that the
deterministic no-model path can traverse the reporting and gatekeeping boundary. It does
not prove live Qwen quality.

### 1:30-2:00 - Scene 2: HONEST FALLBACK

The controlled node_2 model returns broken JSON. Point to:

```text
generated_by=CODE:FALLBACK
semantic=failed
failure=parse_failed
```

The important behavior is not that fallback exists; it is that fallback does not pretend
to be an LLM judgment.

### 2:00-2:40 - Scene 3: CODE GUARD

The ledger contains five search candidates, two actual `read_doc` results, and three
unread candidates. A controlled model explicitly claims that one unread candidate was
read and returns a `pass` gate. The code-owned document-role guard changes the final gate
to `needs_revision` and the public answer to `blocked`.

This scene proves the explicit role-conflict guard only. It does not prove general semantic
truth checking.

### 2:40-3:00 - Show Reproducibility And Limits

```powershell
python main.py competition-demo --json
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Use `--json` when a reviewer wants the exact fields behind the short screen. The full
development ledger remains available through the existing `fake-turn --pretty` path.

## Deeper Demo Layers

```text
Layer 1. competition-demo: no model and no Neo4j.
Layer 2. local verification: compileall, pytest, and smoke-test.
Layer 3. optional live paths: Qwen/Ollama and Neo4j Vessel/R traversal.
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
