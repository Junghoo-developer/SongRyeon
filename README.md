# SongRyeon Core

[![smoke-test](https://github.com/Junghoo-developer/SongRyeon/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/Junghoo-developer/SongRyeon/actions/workflows/smoke-test.yml)

[한국어 README](README.ko.md) | [Three-Minute Demo](DEMO.md) | [Competition Report Outline](COMPETITION_SUBMISSION_REPORT_OUTLINE.md) | [Release Notes](RELEASE_NOTES.md) | [Third-Party Licenses](THIRD_PARTY_LICENSES.md)

> **A local agent that shows what it read and how far its answer can be trusted, instead of merely sounding smarter.**

SongRyeon Core is a local document and source-code investigation agent. It shows what a
small local model searched and actually read, separates **what code verified** from **what
the model inferred**, and blocks explicit evidence-role conflicts before public release.

## Reproduce It In One Minute

Only Python and this repository are required. No external API, model weights, or Neo4j
instance is needed.

```powershell
python main.py competition-demo
```

The single screen reproduces three deterministic scenes:

```text
LOCAL           runs the local report-and-check path with test doubles
HONEST FALLBACK records a broken model response as a failed CODE:FALLBACK
CODE GUARD      blocks an explicit claim that an unread candidate was actually read
```

The first-screen vocabulary is intentionally plain:

- **Code verified**: candidate, actual-read, unread, and final-gate counts/statuses.
- **Model inferred**: semantic interpretation, answer text, and evidence-role judgment.
- **Public release allowed**: the report passed the structural checks.
- **Revision required**: an explicit model claim conflicts with the code-owned ledger.

This demo does not claim to solve hallucinations in general. It reproduces the narrower
boundary the code can prove: explicit structural conflicts involving evidence roles,
actual document reads, and counts.

**Keywords:** LLM agents, provenance, runtime honesty, traceability, local-first AI, smoke-tested agent architecture.

## Feedback Wanted

SongRyeon Core is still an early research/runtime prototype. I am especially looking for feedback on:

- Is the **absolute / relative / mixed information** split useful for building more trustworthy agents?
- Is SongRyeon better framed as an **agent runtime**, an **audit layer**, or a **research prototype**?
- What should be simplified first so another developer can assemble a small trustworthy agent with it?
- Does the Qwen-vs-SongRyeon comparison make the runtime value clear?

Please open a [feedback issue](https://github.com/Junghoo-developer/SongRyeon/issues/new?template=feedback.md) with criticism, confusion, or comparisons to projects like LangGraph, LangSmith, Dify, OpenHands, or SWE-agent.

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
- Read-only source-code inspection tools for codebase questions.
- Graph memory foundation: CoreEgo -> Time Axis -> Time Bundle -> raw/source/summary nodes.
- Local Neo4j "Vessel" adapter with write, readback, and inspect commands.
- Night summary pipeline for changed source leaves and token-budget summary layers.
- Experimental Vessel-backed R traversal that can walk graph memory through R1/R2/R3 frames.

## Current Demo Path

Reviewers and first-time users can start without a model or Neo4j:

```powershell
python main.py competition-demo
```

Use `python main.py competition-demo --json` for the structured result. The existing
`fake-turn --compact` and `--pretty` views remain available for the general short demo and
full ledger audit.

After creating a local `.env`, the normal interactive start is now one command:

```powershell
python main.py
```

With complete Neo4j values, the launcher automatically enables the experimental Vessel R
route. Without them, it starts Qwen chat without Vessel R. The existing advanced commands
remain available for audits and development.

Start with the no-model path:

```powershell
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty
```

Then verify the local baseline:

```powershell
python main.py smoke-test
```

If you want to see the optional graph-memory path, use Neo4j Vessel commands:

```powershell
python main.py vessel-readback --database neo4j
python main.py vessel-inspect --database neo4j --format text
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조를 계층적으로 탐색해줘" --database neo4j --llm-mode fake --format text
```

For Qwen/Ollama live traversal:

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

See [DEMO.md](DEMO.md) for the fuller three-layer local setup, including Neo4j environment variables and failure meanings.

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
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty
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

Local checkpoint as of 2026-07-17:

- `python -m compileall songryeon_core main.py` passes.
- `python -m pytest` passes: 478 passed, 5 deselected.
- `python main.py smoke-test` passes.
- `python main.py fast-test --profile graph` passes.
- GitHub Actions for this checkpoint must be confirmed after the latest branch is pushed.
- Pytest has import, schema split compatibility, and domain smoke-case coverage.
- Relative direct-field claims are tested.
- Source-bundle planner claims remain mixed information.
- Node 3 report grounding counts are code-supplied.
- Node 4 can block unsafe or mismatched reports.
- Vessel readback/inspect and experimental R traversal are available through CLI commands.

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

## License

This project is released under the [MIT License](LICENSE).

## Third-Party Components

- No model weights are included in this repository.
- The Qwen/Ollama path is optional; users must follow the license of the model they configure.
- The Neo4j Vessel path is optional and requires a local Neo4j setup.
- Development tests use `pytest` through `requirements-dev.txt`.
- See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for contest-oriented license notes.
