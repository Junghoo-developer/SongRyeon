# Codex-account Sol medium hard-batch pilot v1

## Purpose

This is a four-call, non-official ceiling diagnostic. It asks whether the four
`hard` three-claim batches from Semantic Calibration v3.2 are already too easy
for the ChatGPT-account Codex runtime using `gpt-5.6-sol` at `medium` effort.

This is **not** a bare-model result. The Codex SDK adds its own runtime context.
The client runs every request in an empty ephemeral directory, read-only
sandbox, denies approvals, instructs the runtime not to use tools, and rejects
the result if any non-passive thread item appears.

It is also not a contest score, a SongRyeon score, or evidence that Sol is
better than Gemma. The result may only decide whether to author a harder v4
calibration bank before an agent comparison.

## Billing and authentication boundary

- Required account root: `ChatgptAccount`.
- Required model: `gpt-5.6-sol`.
- Required reasoning effort: `medium`.
- Required SDK: `openai-codex==0.144.4`.
- `OPENAI_API_KEY`, `CODEX_API_KEY`, and `CODEX_ACCESS_TOKEN` must all be absent.
- The run therefore refuses the OpenAI Platform API-key billing path. It still
  consumes the account's shared ChatGPT/Codex allowance or credits.
- This verifies the authentication route, not the account billing ledger or
  zero incremental cost; purchased or workspace credits may still be consumed.

OpenAI documents ChatGPT login as subscription access and API-key login as
usage-based access: <https://developers.openai.com/codex/auth>. Current Codex
plan usage is documented at <https://developers.openai.com/codex/pricing>.

## Frozen source dependencies

The runner refuses to start unless these bytes still match:

| Path | SHA-256 |
|---|---|
| `evals/semantic_calibration_v3/FREEZE.json` | `fb9f26c1cba78eafa7f8b1422b2a19757eaa748bf205b3dc918a6ebe9ed872a0` |
| `evals/semantic_calibration_v3/control/run_plan.json` | `5f54b9b6dd972b6ad01fe2e1db5bc8d8f2edbfb9bffbd6846361798517c19522` |
| `evals/semantic_calibration_v3/control/oracle_results.json` | `4358ae9a4e583591263885b674636a8f07598adc5e7189ed4a41c08305ffd5f2` |
| `evals/semantic_calibration_v3/manifest.json` | `98b29c0c50440723f34afcc8f3e66054862aca754aed6fb5bcec24bd57d3dc6b` |
| `evals/semantic_calibration_v3/schemas.py` | `5d187d5117d7fe63fb2b31685133e877e72d5b781e2ead2c55976d6be08362b4` |
| `llm/codex_account.py` | `20e465fff8aa6ac656609103bb879b8106be7da7cb4082a01dd195a7d04d6cdc` |

The protocol, runner, and tests must be committed and pushed with a clean
worktree before the first model call. The runner records that exact commit and
requires it to equal the upstream branch.

## Frozen requests

The runner selects exactly the following existing v3.2 plan rows, in this
order, without changing their system prompt, user prompt, JSON schema, IDs, or
2,400-token post-hoc output budget:

1. `semantic-33-batch-cal-h01-reflected-operator-Q-59fd981294_Q-fb72e27640_Q-c1f4f9aa46`
2. `semantic-40-batch-cal-h02-metaclass-order-Q-8ea116cd1b_Q-2dff061d7b_Q-2932ec0e9c`
3. `semantic-41-batch-cal-h03-new-return-type-Q-37bd519fff_Q-d0109ae755_Q-0de4b040cb`
4. `semantic-48-batch-cal-h04-exec-namespaces-Q-c9f97f02a0_Q-2ca0af488a_Q-885d3c76eb`

No request is retried. A leftover started row is indeterminate and remains a
failure. The fixed canonical output is:

`.tmp/evals/semantic_calibration_codex_pilot/sol-medium-hard-batches-v1.json`

## Fixed decision rule

Each of the 12 claims is jointly correct only when both its verdict and typed
observation match the v3.2 CPython 3.10.11 oracle.

- `harder_v4_triggered`: all 4 units strictly parse and at least 10/12 claims
  are jointly correct. This is a conservative trigger to author harder cases.
- `screen_threshold_not_met`: all 4 units strictly parse and fewer than 10/12
  claims are jointly correct. This does not establish that the bank is hard
  enough or that a ceiling is absent.
- `output_or_runtime_failure`: any request fails, attempts a forbidden tool or
  extra action, exceeds its recorded budget, or fails strict parsing.

The 10/12 cutoff is a preregistered design heuristic, not a statistical
confidence threshold. The 12 claims are nested in four authored clusters and
are not treated as independent samples. Reasons are retained for audit but not
automatically scored. Even `harder_v4_triggered` is only a screening result on
four clusters; it is not a general capability estimate.

Canonical command after the protocol commit is pushed:

```powershell
.\.venv\Scripts\python.exe -B evals/semantic_calibration_codex_pilot.py
```
