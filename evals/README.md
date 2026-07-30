# SongRyeon evaluation harness

This package scores normalized, deterministic fixtures. It deliberately does
not ask another LLM to decide whether an answer is correct.

## What it measures

- exact match, precision and recall for code-verified execution facts
- unsupported normalized code claims
- completion
- tool-call count
- latency
- optional scalar metrics such as context characters or rejection counts

`EvaluationCase` contains the expected fixture. `RecordedRun` contains one
system's normalized result. `evaluate_run()` compares them, and
`compare_systems()` aggregates multiple results.

```python
from evals import (
    EvaluationCase,
    ExecutionFact,
    RecordedRun,
    evaluate_run,
)

case = EvaluationCase(
    case_id="read-gates",
    expected_a_facts=(
        ExecutionFact("tool_call.1.name", "read_python_file"),
        ExecutionFact("tool_call.1.path", "runtime/gates.py"),
    ),
    supported_code_claims=("the gate limits rejection routing",),
)
run = RecordedRun(
    case_id="read-gates",
    system_name="songryeon",
    reported_a_facts=case.expected_a_facts,
    code_claims=("the gate limits rejection routing",),
    completed=True,
    tool_call_count=1,
    latency_ms=1200,
)

result = evaluate_run(case, run)
print(result.to_dict())
```

## Boundary of the current harness

The harness does not extract facts or claims from free-form answers. A fixture
builder or a human must normalize them first. That extraction step must be
versioned and disclosed; otherwise a comparison could silently encode the
reviewer's judgment.

No competition result should be published until:

1. the test cases are frozen,
2. all compared systems use the same questions and source fixtures,
3. model tag, model ID and configuration are recorded,
4. raw outputs are preserved,
5. failures are included instead of discarded.

## Reproducible fixture runner

The committed P0 case set contains ten frozen cases and a synthetic Python
project under `evals/cases/`. Run the evaluator contract without Ollama, a
network connection or the real `memory/memory.jsonl`:

```powershell
python -m evals
```

The default report is written to `.tmp/evals/fixture_report.json`. It always
contains:

- SHA-256 values for the manifest, run bundle and source fixtures,
- complete case-by-system coverage validation,
- per-case results and stable aggregate summaries,
- `benchmark_status`, `review_status` and `publishable`,
- an explicit `FIXTURE ONLY` warning.

Manifest and run-bundle digests use canonical JSON, and committed UTF-8 source
fixture digests normalize line endings to LF. The same checkout therefore has
the same identity on Windows and Linux. Raw live artifacts are hashed byte for
byte because they are evidence, not portable source fixtures.

The committed `offline_fixture_runs.json` is synthetic contract data. Its
perfect scores and zero latency are **not measured model performance**.

To replay normalized live results without calling a model:

```powershell
python -m evals `
  --runs .tmp/evals/live_runs.json `
  --output .tmp/evals/live_report.json
```

A live run bundle must pin the manifest SHA-256, cover every frozen case once
for every declared system, preserve a SHA-256-verified raw artifact for each
run, identify the exact local model/configuration, and set
`uses_external_api` to `false`. `review_status: "draft"` remains
non-publishable. Only a separately reviewed bundle may say
`review_status: "reviewed"`. Even that status remains non-publishable until the
runner has a schema for reviewer identity/version, normalization coverage and
claim-level source spans; those publication gates are intentionally still
closed.

The runner never extracts facts from prose. A person or a separately versioned
normalizer must convert the raw log into `reported_a_facts` and `code_claims`.
That judgment remains visible through `normalization_method` and the raw
artifact hashes.

## Local Ollama raw comparison capture

The default capture follows the comparison plan and runs the frozen ten cases
on the same `qwen3:14b` backbone with three eval systems:

1. `single-tool-agent`
2. `songryeon-no-node4`
3. `songryeon-full`

```powershell
python -m evals.live_capture
```

The command accepts only a loopback Ollama URL. It cannot call an external API.
Every system/case pair receives:

- a fresh temporary `memory.jsonl`,
- a fresh `FileToolbox` rooted at the loaded manifest's project fixture,
- the demo's same 16 KiB Python-file read limit,
- the same `num_ctx`, timeout, keep-alive, temperature and seed,
- the same cooperative per-case wall-clock deadline,
- the exact frozen question and fixture setup.

The capture records the project root relative to the loaded manifest together
with a digest of the declared source tree. It does not substitute a hard-coded
default path when a different manifest is loaded.

`single-tool-agent` is an eval-only baseline with the same `FileToolbox` and a
hard maximum of three tool calls. `songryeon-no-node4` is an explicit eval-only
adapter: it runs the SongRyeon loop but replaces Node4's model call with a
recorded deterministic pass-through. The capture records this bypass separately
from actual model-call count. `songryeon-full` is the unmodified full loop.

The initial 8,000-character frozen memory view and replayed previous turns are
provided to all three variants. Runtime-budget differences remain explicit in
each system's `runtime_contract`: the single agent has at most three total tool
calls and keeps its raw tool history in its own prompt, while SongRyeon can
reach four Node1 rounds (up to twelve calls) after Node2 rejections and exposes
selected evidence through its retention contract. The shared wall-clock cap is
enforced between model calls and also bounds each remaining HTTP timeout.

Variant and backbone are separate metadata fields. A second, optional group can
compare full SongRyeon backbones without mixing those results into the
architecture comparison:

The follow-up case replays its manifest conversation prefix and explicitly
marks the final user request as the evaluated turn. Synthetic conflicting
memory is seeded only inside that case's temporary memory.

The output is a new directory below
`.tmp/evals/local_captures/<UTC-ID>/` containing:

- `capture.json` with model tag/digest/configuration, question, answer,
  latency, model/tool-call counts, Node2/Node4 rejections and exhausted-limit
  flags, failures and artifact hashes;
- `checkpoint.json`, atomically replaced after every completed system/case
  pair so an interrupted long run retains its completed-pair index;
- one exact raw SongRyeon memory JSONL per system/case pair under `raw/`.

Both the final capture and checkpoint remain draft and non-publishable. An
interrupted run has `checkpoint_status: "in_progress"`; a finished run changes
it to `"complete"`.

For an explicit empty destination and configuration:

```powershell
python -m evals.live_capture `
  --variants single-tool-agent songryeon-no-node4 songryeon-full `
  --architecture-backbone qwen3:14b `
  --backbone-compare-models gemma4:26b qwen3:14b `
  --num-ctx 16384 `
  --temperature 0 `
  --seed 42 `
  --case-wall-clock-limit-seconds 600 `
  --output-dir .tmp/evals/my-local-comparison
```

The optional systems are named
`backbone-songryeon-full-gemma4-26b` and
`backbone-songryeon-full-qwen3-14b`. They both include the full SongRyeon
wrapper. They are a backbone comparison, not evidence of SongRyeon's structural
effect. No bare-model baseline is included.

This command does **not** create benchmark scores or `RecordedRun` claims.
Every capture is hard-coded as `live_raw_draft`, `review_status: draft` and
`publishable: false`. A reviewer must inspect the raw JSONL and normalize it
before the offline evaluator can calculate any performance metric.
