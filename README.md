# SongRyeon Core

[한국어 README](README.ko.md)

SongRyeon Core is a small, local-first agent runtime experiment.

The project asks one practical question:

> How can an LLM-based agent explain what it knows, what it inferred, and what the code actually verified?

Instead of treating every generated sentence as the same kind of output, SongRyeon Core separates runtime information into explicit classes:

- **Absolute information**: values the system can verify from code, schema, files, trace events, or data records.
- **Relative information**: a semantic judgment grounded in one specific source record or field.
- **Mixed information**: a semantic judgment synthesized from a source bundle, where pinning it to one source would be misleading.

This repository is intentionally small. It is a practice-grade core for studying traceable agent architecture before building a larger assistant.

## Why This Exists

Most agent demos look good until you ask:

- Did code verify this, or did the model infer it?
- Which internal step produced this answer?
- Did the agent quietly fall back from an LLM decision to a rule?
- Did a report use the latest loop run, or an older stale record?
- When a count appears in the final answer, did the LLM count it or did code count it?

SongRyeon Core explores those questions with schemas, trace records, runtime labels, and smoke tests.

## Current Capabilities

- Node-based runtime skeleton: `node_0`, `node_1`, `L loop`, `node_2`, `node_3`, `node_4`.
- TraceStore and DataStore for event and payload provenance.
- L loop for internal document search and evidence gathering.
- Code-generated grounding counts for final reports.
- Router fallback honesty: failed LLM routing and policy fallback are recorded separately.
- Same-turn L reroute guard: default one L run, policy-enabled second run, third run blocked.
- Recent turn capsule and raw-conversation alignment packets.
- Relative/mixed semantic information split with smoke coverage.
- Pretty runtime output that exposes generator, info class, source IDs, and judgment status.

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

## Quick Start

The default smoke test uses only the Python standard library.

```powershell
python -m compileall songryeon_core main.py
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

As of 2026-06-26:

- `python -m compileall songryeon_core main.py` passes.
- `python main.py smoke-test` passes.
- Relative direct-field claims are tested.
- Source-bundle planner claims remain mixed information.
- Node 3 report grounding counts are code-supplied.
- Node 4 can block unsafe or mismatched reports.

## Notes

This project is not a production assistant.

It is a learning and architecture prototype focused on provenance, runtime honesty, and agent self-reporting. The code favors explicit records and small smoke-tested MVPs over polished UX.
