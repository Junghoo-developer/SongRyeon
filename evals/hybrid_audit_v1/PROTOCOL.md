# Hybrid A-only audit pilot v1

## Superseding an infrastructure-aborted canonical attempt

The first sealed execution (`songryeon-hybrid-a-only-audit-pilot-v1`, freeze
`f753551b...`) was aborted after five local rows because OneDrive denied an
atomic checkpoint replacement.  Its canonical attempt was not retried and its
lock and partial artifact remain preserved locally.  The compact hash witness
is committed as `ABORTED_ATTEMPT_V1.json`.

This successor is identified as `songryeon-hybrid-a-only-audit-pilot-v1-1`.
It changes no cohort, prompt, reference label, model contract, router, or
metric.  It relocates raw output to the operating system's local application
data directory, outside the synchronized workspace, and reruns the complete
30-case plan under a new source commit and freeze.  Results from the five
aborted rows are not mixed into the successor score.

The v1.1 local runner later exited successfully after its 30-row plan, but its
raw artifact was written outside the tool workspace and was not visible from
the next isolated shell.  Because the bytes were not durably recoverable, no
v1.1 decision is scored.  `ABORTED_ATTEMPT_V1_1.json` records this second
infrastructure exclusion.

The final successor ID is `songryeon-hybrid-a-only-audit-pilot-v1-2`.  It uses
the synchronized workspace only for append-only journal files: every reserved
and completed row receives a new path, and the canonical condition artifact is
created once after all 30 rows.  It never repeatedly replaces one synced file.
The cohort, prompt, labels, model contracts, router, and metrics remain
unchanged.

## Status and question

This is a **retrospective paired feasibility pilot**, not a new held-out
confirmatory study.  It reuses previously captured synthetic evidence and
Gemma drafts, but it does not regenerate or select drafts after seeing the
cloud auditor.

The narrow research question is:

> Given the exact same frozen local draft and exact same code-observed A,
> does a cloud frontier auditor classify unsupported factual claims better
> than the local auditor, and how much of that gain remains when only a small
> fixed subset is escalated?

The result must not be described as the causal effect of SongRyeon's entire
A/R architecture.  It isolates the final **A-only audit boundary** and the
auditor model tier.

## Frozen source cohort

- Source experiment: `songryeon-arm-consumption-mechanism-exploratory-v1`.
- Local producer: `gemma4:26b`.
- Cohort: every one of the 30 cases at the mechanically chosen smallest seed,
  `42`.
- Draft: the byte-exact `ar-consumer-rule` answer captured before this pilot.
- A packet: only the captured `tool_results` fields that code directly
  observed: tool name, arguments, success, content, error, and the validated
  `information_class=absolute` / `code_verifiable=true` authority labels.
- R excluded from both auditors: active user goal, fixture R memory, earlier
  model reviews, local reviewer reason, oracle labels, and scores.

All 30 cases are included.  Cases may not be dropped, replaced, or chosen
using cloud output.  The three captured seeds are repeated generations of the
same 30 cases and are not counted as 90 independent cases.

## Conditions

The candidate draft bytes and A-only packet bytes are identical across the
auditor conditions.

| ID | Condition | Decision source |
|---|---|---|
| C0 | no audit | every frozen local draft is delivered |
| C1 | local A-only audit | `gemma4:26b` returns `permit` or `reject` |
| C2 | cloud A-only audit | `gpt-5.6-sol`, medium effort, returns the same schema |
| C3 | selective hybrid | C1 for all cases, with C2 replacing C1 on a frozen 8/30 subset |

C1 and C2 receive the same system prompt, same user prompt, same JSON schema,
and same output-token ceiling.  Only the model provider and tier differ.

This first-stage pilot scores the audit decision itself.  It does **not** mix
auditor skill with a later local rewrite.  A reject-and-rewrite evaluation may
be added only as a separately labelled second stage.

## Audit contract

The auditor receives:

1. provenance-labelled A records reconstructed from captured tool results;
2. one candidate local draft, explicitly labelled R.

It returns exactly:

```json
{"verdict":"permit|reject","reason":"..."}
```

The auditor must reject when the draft contains a concrete code or execution
claim that is contradicted by, stronger than, or unsupported by the supplied
A.  It must permit a draft whose concrete claims remain within A.  Completeness,
helpfulness, and user-goal satisfaction are explicitly outside this pilot's label.
It must not infer the user's desired conclusion because the user request is
not shown.

Each runner attempt uses a fresh isolated thread.  Tools, shell, network
browsing, and project-file access are forbidden.  There is one runner
invocation per case; transport, schema, or parsing failure remains a failed
planned row and is not retried by this runner.  Any retry internal to an
upstream transport or SDK is not observable here and is not claimed absent.

## Preliminary reference labels

The expected audit decision is derived mechanically from the already locked,
condition-metadata-masked preliminary score of the frozen draft:

- `no_unsupported_claims == 1` -> expected `permit`
- `no_unsupported_claims == 0` -> expected `reject`

These labels were produced by AI preliminary rating, not independent human
ground truth.  Therefore all resulting accuracy figures remain preliminary.
Before a contest-facing performance claim, a human must inspect every C1/C2
disagreement and every false permit against the raw A packet.

## Frozen selective router

C3 escalates exactly eight cases.  The score is computed without reading any
local/cloud audit decision, reference label, or model answer content:

- any failed A tool result: +4
- any fixture R memory excluded from the audit view: +3
- more than one A tool result: +2
- total A content is at least 500 characters: +1

Ties are ordered by
`SHA256("hybrid-audit-v1|" + case_id)` ascending.  The top eight case IDs are
sealed before the first cloud call.  C3 is a counterfactual replay of the C1
and C2 decisions; it makes no additional model call.

## Primary metrics

- error detection rate: incorrect drafts rejected;
- supported-draft preservation rate: drafts without unsupported factual claims
  permitted;
- false permits: unsupported drafts delivered;
- false rejects: supported drafts withheld;
- balanced accuracy;
- C2 minus C1 net decision correction:
  `local wrong / cloud right - local right / cloud wrong`;
- C3 retention of the C2 gain.

If fewer than five reference-positive or five reference-negative drafts exist,
the corresponding rate is labelled `inconclusive` because of a ceiling or
floor effect.

## Efficiency and trace metrics

- planned runner attempts, valid responses, and invalid/transport rows (a
  client-side failure does not prove that the provider received a call);
- input, cached-input, output, reasoning, and total tokens when reported;
- per-case and aggregate latency;
- prompt, response, A packet, and draft SHA-256;
- provider, execution mode, model name, effort, and SDK/runtime identity;
- cloud runner attempts and tokens per net corrected audit decision;
- selective escalation token reduction relative to C2-all.

Subscription/account token telemetry is not an invoice.  No monetary price is
claimed unless an explicit public price table and calculation date are added
later.

## Predeclared pilot interpretation

The cloud audit signal is considered worth a larger independent study only if:

- C2 improves over C1 by at least three net decisions;
- error detection rises by at least 20 percentage points;
- supported-draft preservation falls by no more than 5 percentage points; and
- C3 preserves at least half of C2's net improvement, fixes at least one
  additional decision, and harms at most one C1-correct decision.

With 30 reused synthetic cases, these are engineering continuation thresholds,
not statistical proof or a general model-ranking claim.

## Integrity rules

Before any C1 or C2 call, freeze and hash:

- all 30 source items and their original artifact hashes;
- A-only prompt renderer and strict parser;
- reference-label join and router source;
- this protocol;
- local and cloud model contracts;
- planned call order and output locations.

The runner must refuse source mutation, duplicate canonical attempts, API-key
environment variables for the Codex-account condition, missing rows, prompt
leakage of oracle/reference fields, and unplanned retries.  Raw responses and
failures are preserved.  Scoring code may not silently discard failed rows.

## Allowed conclusion

The strongest allowed wording is:

> On 30 reused frozen Gemma drafts, under one fixed A-only audit interface,
> the observed local/cloud/selective audit decisions differed by the reported
> amounts.

The pilot cannot establish production safety, all-domain generalisation, the
effect of Node1 or Node2, or the total causal effect of A/R classification.
