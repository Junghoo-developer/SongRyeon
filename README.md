# SongRyeon Core

[![smoke-test](https://github.com/Junghoo-developer/SongRyeon/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/Junghoo-developer/SongRyeon/actions/workflows/smoke-test.yml)

[한국어 README](README.ko.md)

**Keywords:** LLM agents, provenance, runtime honesty, traceability, local-first AI, smoke-tested agent architecture.

SongRyeon Core is a tiny agent runtime that forces an LLM to separate **what the code verified** from **what the model inferred**.

The goal is simple: when an agent answers, it should not blur facts, guesses, summaries, tool results, and internal routing decisions into one confident-looking paragraph.

## The Difference

A normal agent might say:

```text
I read 3 documents and found enough evidence.
```

SongRyeon Core tries to say something closer to:

```text
Code-verified counts:
- reportable_documents = 2
- raw_extract_records = 3
- empty_extract_records = 1

LLM judgment:
- The answer can only be partial because two readable documents were available.

Runtime honesty:
- The top-level L reroute request was blocked by policy.
- The visible report uses the latest L run, not a stale legacy ID.
```

That is the heart of the project.

## What It Tracks

SongRyeon Core separates runtime information into three buckets:

- **Absolute information**: values the system can verify from code, schema, files, trace events, or data records.
- **Relative information**: a semantic judgment grounded in one specific source record or field.
- **Mixed information**: a semantic judgment synthesized from a source bundle, where pinning it to one source would be misleading.

In shorter terms:

```text
Code facts stay code facts.
LLM judgments stay LLM judgments.
Multi-source synthesis must say it is multi-source synthesis.
```

## Why I Built This

Most agent demos look good until you ask:

- Did code verify this, or did the model infer it?
- Which internal step produced this answer?
- Did the agent quietly fall back from an LLM decision to a rule?
- Did a report use the latest loop run, or an older stale record?
- When a count appears in the final answer, did the LLM count it or did code count it?

SongRyeon Core is my small, local-first attempt to make those questions visible in the runtime itself.

## Current Highlights

- TraceStore and DataStore for event and payload provenance.
- Internal document-search L loop with evidence gathering.
- Code-generated grounding counts for final reports.
- Router fallback honesty: failed LLM routing and policy fallback are recorded separately.
- Same-turn L reroute guard: default one L run, policy-enabled second run, third run blocked.
- Recent turn capsule and raw-conversation alignment packets.
- Relative/mixed semantic information split with smoke coverage.
- Pretty runtime output that exposes generator, info class, source IDs, and judgment status.

## Suggested GitHub Topics

If you are viewing this on GitHub, the repository is easiest to discover with these topics:

```text
llm
agents
python
local-first
provenance
traceability
runtime
agent-architecture
```

## Quick Start

The full local baseline uses pytest as a dev/test dependency. The CLI smoke test itself still runs through `python main.py smoke-test`.

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

Expected result:

```text
SMOKE_TEST_OK
```

Run a deterministic local turn without a real LLM:

```powershell
python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇인지 알려줘" --pretty
```

Run a dry turn:

```powershell
python main.py dry-run
```

## Optional Local LLM

The Qwen path is optional. If you use Ollama and have a compatible local model:

```powershell
pip install ollama
python main.py qwen-ping --timeout 60
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇인지 알려줘" --timeout 120 --pretty
```

You can also point `QWEN_LOCAL_ENDPOINT` at an OpenAI-compatible local HTTP endpoint.

## Design Principles

1. Code writes absolute information.
2. LLMs write semantic judgments.
3. Mixed information must reveal its source bundle.
4. Code must not pretend to be an LLM.
5. LLM judgment must not be shown as code fact.
6. Heuristics should be explicit policy, not hidden behavior.
7. A demo is not trusted until smoke tests pass.

## Current Baseline

As of 2026-06-27:

- `python -m compileall songryeon_core main.py` passes.
- `python -m pytest` passes.
- `python main.py smoke-test` passes.
- Pytest has import, schema split compatibility, and domain smoke-case coverage.
- Relative direct-field claims are tested.
- Source-bundle planner claims remain mixed information.
- Node 3 report grounding counts are code-supplied.
- Node 4 can block unsafe or mismatched reports.

Test layers:

- `compileall`: syntax/import floor.
- `pytest`: unit and domain regression checks.
- `smoke-test`: integrated runtime baseline.
- `qwen-turn` / `qwen-chat`: manual live LLM checks, not CI requirements.

## Repository Map

- `songryeon_core/core/`: schemas, trace store, data store, registry, failure signals.
- `songryeon_core/state/`: zero state, unified state, turn capsule helpers.
- `songryeon_core/nodes/`: node implementations.
- `songryeon_core/loops/`: L loop runtime and loop policies.
- `songryeon_core/tools/`: document tools, hash embedding search, tool result distillation.
- `songryeon_core/llm/`: LLM adapter interface, fake adapter, Qwen/Ollama adapter.
- `songryeon_core/runtime/`: dry run, user turn, terminal view, smoke tests, replay.
- `songryeon_core/prompts/`: node prompt files.
- `Administrative_Reform_1/`: design notes, maps, orders, execution records.
- `main.py`: CLI entrypoint.

## Notes

This project is not a production assistant.

It is a learning and architecture prototype focused on provenance, runtime honesty, and agent self-reporting. The code favors explicit records and small smoke-tested MVPs over polished UX.
