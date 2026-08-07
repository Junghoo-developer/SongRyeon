# Semantic Calibration v3 — Preregistration

## Status and purpose

This is a public calibration suite, not a hidden benchmark and not a system
ranking. It separates three possible bottlenecks that Hard Semantics v2 mixed:

1. prediction of CPython behavior from complete source;
2. assembling three independently judged claims in one response;
3. producing the required structured output.

The same 36 executable claims are evaluated twice: once as 36 single-claim
requests and once as 12 three-claim batches. Evidence is supplied completely,
so this primary gate does not measure tool choice, missing evidence, or A/R
authority. Those require a separate secondary calibration and must not be
merged into the primary semantic score.

No model call may occur before the fixtures, claims, oracle, prompt contract,
run order, scorer, and thresholds below are recorded in `FREEZE.json`.
The freeze itself must then be committed and pushed. A scored artifact records
the containing Git commit and remote branch before its first model call.
Scored commands reject all `.pyc` and `.pyo` files under the experiment and
LLM client trees, disable bytecode creation, verify import provenance, and
require a clean Git worktree so frozen source cannot be shadowed.
The freeze, runner, and scorer must be invoked with `python -B` and their direct
file paths. `python -m` and importing `main()` are forbidden because Python's
module loader may select cached bytecode before an in-module guard executes.

Canonical commands are:

```text
python -B evals/semantic_calibration_v3/freeze_v3.py --create
python -B evals/semantic_calibration_v3/run_bare_v3.py --stage contract --freeze evals/semantic_calibration_v3/FREEZE.json
python -B evals/semantic_calibration_v3/seal_v3.py --artifact <canonical-contract> --freeze evals/semantic_calibration_v3/FREEZE.json
# Commit and push the new contract evidence file before continuing.
python -B evals/semantic_calibration_v3/run_bare_v3.py --stage semantic --freeze evals/semantic_calibration_v3/FREEZE.json
python -B evals/semantic_calibration_v3/seal_v3.py --artifact <canonical-semantic> --freeze evals/semantic_calibration_v3/FREEZE.json
# Commit and push the new semantic evidence file before scoring.
python -B evals/semantic_calibration_v3/score_v3.py --contract <canonical-contract> --semantic <canonical-semantic> --freeze evals/semantic_calibration_v3/FREEZE.json --output <new-score-path>
```

## Fixed environment

- CPython outcome scope: 3.10.11.
- Model: local `gemma4:26b`, exact digest recorded in the freeze.
- Ollama `think: false`, temperature 0, context 16,384, seed 8,849.
- One fresh model request per single claim or batch; no conversational memory.
- Complete source packet supplied directly; no agent tools or execution.
- The oracle is generated in fresh CPython processes and never shown to the
  model.

## Cases

- 12 case clusters × 3 atomic executable claims = 36 claims.
- Four `anchor`, four `medium`, and four `hard` clusters.
- Each tier contains six true and six false propositions.
- Within every tier, each of the three batch positions contains two true and
  two false propositions.
- Every claim has a deterministic JSON-serializable return value or a named
  Python exception.
- Mutable state is reset inside the called function or deterministically
  recreated by a fresh interpreter import, so evaluating a claim alone and in
  a batch has the same oracle outcome.
- Hard Semantics v2 fixture logic and claim wording are not reused.
- Difficulty labels and fixture filenames are internal metadata. Model-visible
  source labels and claim IDs are opaque and do not reveal the tier.

## Typed response contract

Every claim object has exactly these fields:

```json
    {
  "id": "Q-a1b2c3d4e5",
  "verdict": "SUPPORTED",
  "observation": {
    "kind": "return",
    "value": 3,
    "exception": null
  },
  "reason": "short reason"
}
```

`observation` always has exactly `kind`, `value`, and `exception`.

- Return: `kind="return"`, actual JSON value, `exception=null`.
- Raise: `kind="raise"`, `value=null`, actual exception class name.
- Unknown is reserved for the later authority calibration:
  `kind="unknown"`, `value=null`, `exception=null`.

The semantic suite permits only `SUPPORTED` or `UNSUPPORTED`. The observation
must state the predicted actual result even when the proposition is false.
String-encoded mini-languages such as `RETURN [...]` are forbidden.
`reason` must be a nonempty string. A call is complete only when Ollama returns
`done_reason="stop"`; a length-limited response is an execution failure even
if its prefix happens to parse.

## Contract preflight

Before semantic calibration, the bare adapter receives four trivial tasks:

1. primitive return;
2. nested JSON return;
3. raised exception;
4. a three-claim batch containing return, raise, and unknown observations.

All four must complete, strictly parse, match every requested ID, and reproduce
the explicitly supplied verdict and typed observation exactly. Failure stops
the run. The contract or adapter must be corrected in a newly frozen version;
responses are never repaired after generation.

The semantic run records the exact contract artifact SHA-256 and contract
`run_id` in its own header. A scorer rejects a semantic artifact paired with
any other contract run, even when that other run also passed 4/4.

## Frozen order

Cases are sorted by manifest order. For odd-numbered cases, run the batch first
and then its three single claims. For even-numbered cases, run the three single
claims first and then the batch. This order is frozen to reduce a uniform
residency/order advantage. Checkpoints are written after every request.
Every claim receives a budget of 800 generated tokens: a single unit receives
800 and a three-claim batch receives 2,400. Runs use an exclusive output lock;
continuation of a checkpoint requires an explicit resume option.

Each freeze SHA has exactly one canonical contract path and one canonical
semantic path under `.tmp/evals/semantic_calibration_v3/<freeze-sha>/`.
Choosing a second output path is forbidden. While the canonical artifact is
preserved in the same workspace, a completed or failed run cannot be restarted
with the same freeze; a meaningful retry requires a new committed and pushed
freeze. All attempts must be retained and disclosed. This makes the first
scored attempt primary instead of selecting the best result from repeated
seed-1 attempts. The local guard is operational evidence, not a cryptographic
defense against deleting the workspace or rerunning from another clone.
Immediately after each canonical run completes—and before semantic inspection—
`seal_v3.py` copies its exact bytes to `evidence/semantic_calibration_v3/`.
That evidence file must be committed and pushed before the next stage. The seal
refuses overwrites, so the remote Git history supplies the external first-run
witness that the local canonical path alone cannot provide.

For each request, a `started` row is durably written before the model call and
replaced by a `finished` row afterward. A leftover `started` row is
indeterminate and is never retried inside the same scored run. After every row
is finished, the runner verifies the freeze and model identity again. Only
then does it write `run_state="complete"` and the final readiness identity.
Scorers reject `running`, `invalid`, or readiness-mismatched artifacts even if
all 4 or 48 result rows are present.

## Measurements

Report separately:

- completion and strict-schema parse;
- verdict exactness;
- typed observation exactness;
- joint verdict-plus-observation correctness;
- fixed-denominator end-to-end and semantic-given-parse;
- anchor, medium, and hard results;
- paired outcomes for every claim: both correct, single only, batch only, or
  neither;
- model calls, generated tokens, and latency.

`model calls` here means client call attempts recorded by the harness. It does
not assert that a remote server received a request when a connection failed.

The 36 claims are clustered within 12 authored cases and are not represented
as 36 independent statistical samples. Reasons are preserved for human audit
but not assigned an automatic truth score.

## Bare seed-1 gate

The agent comparison may run only if every condition is met:

- contract preflight: 4/4 tasks and every embedded claim exact;
- single strict parse: at least 35/36;
- batch strict parse: at least 11/12;
- single joint semantic: 20–30/36 inclusive;
- batch joint semantic: 18–30/36 inclusive;
- single-to-batch net loss: no more than five claims;
- single difficulty gradient: anchor ≥ medium ≥ hard;
- anchor minus hard: at least three claims;
- anchor: at least 8/12; hard: 2–8/12;
- oracle and freeze verification: 100%.

Stop and create a new version when any of these applies:

- `single < 20/36` or `hard <= 1/12`: semantic floor;
- both single and batch exceed `30/36`: semantic ceiling;
- `batch < 18/36` or batch loses at least six claims: batch/assembly confound;
- parse threshold or preflight fails: output-contract or harness failure.

When several conditions fail, the single summary status uses this fixed
priority: matrix/parse threshold, semantic floor, semantic ceiling,
batch/assembly confound, gate passed, then calibration-shape rejected. Every
individual gate condition remains in the score artifact and must be reported;
the summary status must not hide simultaneous failures.

Items and thresholds may not be deleted or moved after seeing a result.

## Later stages

Only after the bare gate passes may the exact 12 batch cases be run through
SongRyeon no-Node4, SongRyeon full, and Deep Agents. Their own seed-1
completion, parse, tool-contract, and evidence-acquisition rates must each be
at least 11/12 before later seeds 17,431 and 61,987 are allowed.

Node4 is evaluated primarily by pairing the first Node3 draft and the final
answer within the same full run. Semantic repair, semantic harm, schema
recovery, unchanged results, calls, tokens, and latency are reported
separately. A full/no-Node4 final-score difference is only a secondary
diagnostic.

General agent superiority, a public ranking, a statistically established
Node4 effect, or hallucination elimination may not be claimed from this public
calibration.
