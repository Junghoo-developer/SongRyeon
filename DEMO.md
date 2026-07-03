# SongRyeon Core Demo Commands

This file is the short practical path for showing SongRyeon Core to another developer.

The most stable story today is:

```text
1. The runtime records code-verified facts and LLM judgments separately.
2. Source files and internal documents can be ingested into graph memory.
3. A local Neo4j Vessel can store that graph.
4. The experimental R traversal can walk the Vessel graph through explicit R1/R2/R3 frames.
```

## 1. Basic Runtime Baseline

Install test dependencies and run the local baseline:

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Expected smoke result:

```text
SMOKE_TEST_OK
```

Fast graph-focused check:

```powershell
python main.py fast-test --profile graph
```

## 2. Optional Neo4j Vessel Setup

Neo4j is optional. The normal tests do not require it.

For local Vessel commands, configure these environment variables in your PowerShell session:

```powershell
$env:SONGRYEON_NEO4J_URI="bolt://localhost:7687"
$env:SONGRYEON_NEO4J_USER="neo4j"
$env:SONGRYEON_NEO4J_PASSWORD="<your-local-password>"
$env:SONGRYEON_NEO4J_DATABASE="neo4j"
```

Do not commit local password files.

## 3. Vessel Readback

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

## 4. Vessel Inspect

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

## 5. R Traversal Smoke

Deterministic fake traversal:

```powershell
python main.py vessel-r-traverse "Trace how SongRyeon Core source summaries connect to token-bundle summaries." --database neo4j --llm-mode fake --format text
```

Live Qwen/Ollama traversal:

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘. 과거 대화 기억 가지가 아니라 코드/문서 소스 가지를 우선 보고, 시간축에서 시작해서 어떤 묶음을 거쳐 내려가는지 말해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

The important output fields are:

```text
status
traverse_status
step_count
final_graph_node_id
terminal_material_seen_count
raw_original_material_seen_count
```

## 6. Night Summary Pipeline

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

- R traversal is still experimental and CLI-driven.
- R traversal is not yet fully wired into the normal `qwen-chat` answer route.
- Neo4j setup is local and manual.
- The project favors provenance and testable records over polished UX.
