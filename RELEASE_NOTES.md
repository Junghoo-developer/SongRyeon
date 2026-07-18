# Release Notes

## 2026-07-18: Read-Only External Workspace Boundary

- Added a local-only, read-only workspace boundary for user-selected folders:

```powershell
python main.py workspace-check "C:\path\to\work"
python main.py qwen-chat --workspace "C:\path\to\work"
```

- The code-owned manifest records supported file coordinates, sizes, modification times,
  hashes, and explicit exclusion counts without copying the files.
- Supported extensions are `.md`, `.txt`, `.py`, `.json`, `.toml`, `.yaml`, and `.yml`.
- Explicit secret names, Git/virtual-environment/cache/build directories, paths outside the
  selected root, and symbolic-link escapes are excluded by policy.
- Workspace candidates remain distinct from files actually read by L-loop tools.
- Explicit workspace paths remain detectable when a Korean particle directly follows the file
  name, and the terminal now distinguishes the first L3 judgment from the latest revision.
- Existing L2/L3 `llm_call` failure records are rendered as compact fallback diagnostics without
  exposing raw model text.
- External API commands do not expose the workspace option, workspace-enabled Qwen HTTP calls
  require a loopback endpoint, and no automatic Neo4j or night ingestion is performed.
- Completed LLM calls now record UTC start/end, monotonic duration, and the configured adapter
  timeout. Live trace prints the node before a model call starts, without changing official trace
  counts or IDs.
- A 150-second forced-L observation identified an unfinished direct Ollama L1 call. The configured
  timeout was not enforced by the previous module-level `ollama.chat(...)` transport.
- Direct Ollama calls now use `ollama.Client(timeout=N)`, which forwards the configured timeout to
  the package's internal httpx client. Runtime output names the transport enforcement boundary.
- A live five-second timeout test returned each local Qwen call in roughly 5.0-5.3 seconds and kept
  the final strict router failure visible instead of silently fabricating a route.
- Local verification: 496 passed, 1 skipped, 5 deselected; `SMOKE_TEST_OK`; competition demo
  three scenes passed.
- A repeated forced-L Qwen live measurement exceeded the 600-second command limit. The feature
  boundary passes deterministic tests, but live sequential-call latency remains an open risk.

## 2026-07-17: Competition Reviewer Demo And Product Positioning

- Added a deterministic one-command reviewer demo:

```powershell
python main.py competition-demo
```

- The screen reproduces three boundaries without an external API or Neo4j:
  - local report/check path,
  - honest failed fallback,
  - explicit unread-document role conflict blocked by a CODE guard.
- The controlled guard scene exposes five candidates, two actual `read_doc` results, and
  three unread candidates.
- README and demo documentation now lead with user-facing states: code verified, model
  interpreted, public release allowed, and revision required.
- Added a competition report outline and tightened third-party license disclosures.
- This checkpoint does not claim general hallucination detection or semantic truth checking.
- Local verification: 478 passed, 5 deselected; `SMOKE_TEST_OK`.

## 2026-07-17: Competition Submission Readiness Checkpoint

- ORDER 261/262 tighten code-range evidence assembly, current-run scoping, L3 evidence binding,
  node_3 code-text budgeting, latest revision propagation, and count consistency.
- A compact first-run view is available through:

```powershell
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --compact
```

- Third-party component and model disclosure notes are in `THIRD_PARTY_LICENSES.md`.
- Local verification baseline before publication: 476 passed, 5 deselected; `SMOKE_TEST_OK`.
- Remote GitHub Actions for this checkpoint must be confirmed after push.

## 2026-07-03: Vessel Graph Memory And R Traversal Baseline

This is the first public baseline where SongRyeon Core can show a local graph-memory path end to end.

Merged PR:

- [PR #2: Integrate Vessel graph memory and R traversal baseline](https://github.com/Junghoo-developer/SongRyeon/pull/2)

Main commit:

- `8fe05aa Merge Vessel graph memory and R traversal baseline`

## What Is New

- Graph memory foundation:
  - `CoreEgo`
  - `Time Axis`
  - `Time Bundle`
  - raw capsules, source ingest bundles, source kind bundles, raw sources, and summary nodes
- Local Neo4j Vessel adapter:
  - write plan boundary
  - first write command
  - readback verification
  - inspect command
- Source ingest and night summary pipeline:
  - changed source leaf summaries
  - token-budget summary layers
  - checkpointed long-run support
  - summary invalidation/source lineage groundwork
- Experimental Vessel-backed R traversal:
  - R1 goal setting
  - R2 graph node selection
  - R3 inspection/sufficiency
  - multi-step traversal
  - summary-before-raw traversal
  - raw original read cap
  - user-question anchor copy guard
- Development gates:
  - full pytest baseline
  - smoke-test GitHub Actions
  - graph-focused fast-test profile

## Verified Before Merge

```text
python -m pytest -> 279 passed
python main.py smoke-test -> SMOKE_TEST_OK
python main.py fast-test --profile graph -> FAST_TEST_OK
git diff --check -> passed
```

After merge to `main`, GitHub Actions `smoke-test` completed successfully.

## What This Is Not Yet

- Not a production assistant.
- Not a hosted cloud service.
- Not a fully automatic long-term memory system.
- Not yet a normal live-chat route that automatically uses R traversal in final answers.
- Not yet a polished external developer SDK.

## Next Development Target

The next narrow MVP is `ORDER_193_R_RESULT_TO_NODE3_VESSEL_MATERIAL_V0`.

Goal:

```text
Let R traversal results become explicit read-only material for node_3,
without pretending that graph traversal is already part of the normal answer route.
```
