# Semantic Ceiling v4 preregistration

## Purpose

Semantic Ceiling v4 is a small, public, non-official diagnostic created after
one preregistered Sol-medium run scored 12/12 on the four v3.2 hard clusters.
Its only purpose is to test whether a new bank of composite CPython semantics
avoids that observed ceiling. It is not a hidden benchmark, a SongRyeon score,
a general coding score, or a comparison against Gemma or another model.

No target-model answer may be generated until every fixture, proposition,
oracle result, effective prompt, response schema, order, output budget,
classification rule, runner, scorer, and test is frozen, committed, and pushed.

## Bank

- Runtime scope: CPython 3.10.11.
- Eight separate authored case clusters; no claim- or cluster-level statistical
  independence is assumed.
- Three atomic claims per cluster, supplied as one batch.
- Twenty-four claims and at most eight model requests.
- Twelve supported and twelve unsupported propositions.
- Every batch position contains exactly four supported and four unsupported
  propositions.
- Every claim has a deterministic JSON return value or named exception.
- Each claim is executed by the oracle in a fresh isolated interpreter.
- Reasons are retained for audit but are not automatically scored.

The bank composes class construction, duplicated slots, zero-argument
`super()`, generator delegation, structural matching, exception-cell lifetime,
augmented assignment through a descriptor, and nested context-manager exception
arbitration. False propositions are one-delta near misses rather than unrelated
answers.

The fixtures were authored with assistance from the same GPT-5.6 Sol model
family used by the target run. They were not constructed or independently
validated by humans alone. Therefore the bank must not be represented as
training-data-hidden, human-authored, or statistically independent. The 24
claims are clustered in eight cases.

## Oracle and determinism

The control builder executes every function with `python -B -I` in a fresh
CPython 3.10.11 process. Unexpected stdout or stderr, timeout, path escape,
symlink escape, non-JSON values, duplicate IDs, or nondeterministic canonical
results fail the build. Multiple fixed hash seeds and repeated builds must
produce byte-identical plan and oracle documents.

The oracle is never included in a model prompt. Public claim IDs and source
labels are opaque hashes that do not reveal case names or proposition truth.

## Model and authentication contract

- Provider: Codex account integration.
- Account root: `ChatgptAccount`.
- Model: `gpt-5.6-sol`.
- Reasoning effort: `medium`.
- SDK: `openai-codex==0.144.4`.
- Fresh ephemeral thread for each cluster.
- No conversational memory and no executed agent tools.
- `OPENAI_API_KEY`, `CODEX_API_KEY`, and `CODEX_ACCESS_TOKEN` are forbidden.
- No runner-level retry. The maximum application-level inference-request count
  is eight. This does not claim that SDK or transport internals never retry.

This rules out the Platform API-key billing route. It does not prove zero
monetary debit or inspect plan allowance, credits, overage, or auto-top-up.
The client sends inference to OpenAI rather than a local Ollama backend, but no
whole-machine or server-side GPU telemetry claim is made.

Backend revision, temperature, and seed are not exposed or fixed by this route.
The result is one stochastic realization. It cannot causally attribute a
difference from v2 to item difficulty alone.

## Response contract

The schema is authored directly in the accepted Structured Outputs dialect:

- root `type: object`;
- nested `anyOf` for return and raise observations;
- `type: string` plus singleton `enum` as the branch discriminator;
- every object closes additional properties and requires every declared field;
- no `oneOf`, `const`, or runtime schema translation.

Each output claim contains exactly `id`, `verdict`, `observation`, and `reason`.
`value_json` is a string containing one strict JSON document and is decoded
exactly once. Return and raise observations are compared as typed values.
Duplicate keys, non-finite values, trailing text, incorrect IDs, missing or
extra fields, and invalid cross-field combinations fail strict parsing.

The observable post-hoc generated-token limit is 2,400 per three-claim batch.
The SDK does not attribute batch usage to individual claims, so no per-claim
token limit is asserted. The runner never repairs or accepts a JSON prefix: it
accepts only a complete strict JSON document from an SDK-completed turn. The
client does not expose an independent server finish-reason witness.

## Execution and checkpointing

The experiment has one canonical attempt per freeze. Before the first request,
the runner verifies all frozen hashes, a clean worktree, and equality of local
HEAD, tracking HEAD, and the live remote branch. Bytecode caches for evaluated
code and the client are refused; isolated `python -I -B` execution is mandatory.
The installed Codex SDK's hashed RECORD entries are rehashed and size-checked,
not merely identified by the distribution version or RECORD filename.

The initial account/model readiness check is a no-inference preflight. A failed
initial check creates neither the canonical artifact nor its attempt sentinel.
After that preflight succeeds, a freeze-scoped sentinel is created once and is
never removed, so an interrupted or deleted canonical attempt cannot be rerun.

Each row is atomically checkpointed as `started` before its one client call and
as `finished` afterward. A runtime or client-contract error is recorded and
stops immediately. A semantic strict-parse failure is recorded and later
clusters continue, but the final classification is output failure. There is no
score-based early stopping and no retry of an indeterminate call.

Usage totals include every structurally valid SDK usage witness, including a
call later rejected for an output-budget or item-contract violation.

Initial and final account/model/effort/SDK readiness must match. Only passive
user, reasoning, and final-agent SDK items are allowed. Any tool item, tool
request, readiness drift, missing usage, or output-budget breach invalidates
the run.

## Scoring and fixed interpretation

A claim is jointly correct only when both its verdict and its typed return
value or exception exactly match the frozen oracle. Classification follows this
priority:

1. `output_or_runtime_failure`: fewer than eight strict parses or readiness
   mismatch.
2. `ceiling_persists`: 24 of 24 jointly correct.
3. `near_ceiling`: 21--23 jointly correct.
4. `anti_ceiling_pass`: 14--20 jointly correct, at least four non-perfect
   clusters, at most one zero-score cluster, and at least four jointly correct
   claims whose frozen truth is `UNSUPPORTED`.
5. `semantic_floor_or_topic_cliff`: 13 or fewer jointly correct, or at least
   two zero-score clusters.
6. `shape_inconclusive`: every other fully parsed distribution.

Because a `SUPPORTED` proposition already contains its true observation, the
fixed copy-and-always-`SUPPORTED` baseline scores 12/24 overall: 12 supported
and 0 unsupported claims. The artifact separately reports supported and
unsupported joint correctness; the anti-ceiling rule requires at least four
unsupported claims.

These are design heuristics, not statistical confidence thresholds. An
`anti_ceiling_pass` supports only the statement that this public v4 screen was
more discriminating in this single Sol-medium run. A `ceiling_persists` result
supports authoring a harder bank; it does not establish general perfection. A
`near_ceiling` result is reported separately rather than being called a ceiling.
