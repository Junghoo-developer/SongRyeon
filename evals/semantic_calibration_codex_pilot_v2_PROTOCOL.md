# Codex-account Sol medium hard-batch pilot v2

## Purpose and prior invalid attempt

This is a new, four-call maximum, non-official ceiling diagnostic. Pilot v1 is
not retried or overwritten. Its immutable artifact has SHA-256
`6e944771338e7e1887a448673e723508173b7173e3627895eda9443e00a418a9` and
was invalid because the server rejected the nested observation `oneOf` before
answer generation.

V2 asks only whether the same four authored hard batches should trigger work on
a harder v4 bank. It is not a bare-model, contest, SongRyeon, or comparative
performance result.

## Authentication and billing boundary

- Required account root: `ChatgptAccount`.
- Required model and effort: `gpt-5.6-sol`, `medium`.
- Required SDK: `openai-codex==0.144.4`.
- `OPENAI_API_KEY`, `CODEX_API_KEY`, and `CODEX_ACCESS_TOKEN` must be absent.
- The runner therefore refuses the Platform API-key billing route, but a
  successful run consumes ChatGPT/Codex plan allowance or credits.
- Authentication-route checks do not prove zero incremental account cost or
  inspect auto-top-up settings.

## The dialect-only transport repair

The four source packets, claim propositions, system prompts, user prompts,
public IDs, oracle observations, token budgets, and strict post-hoc parser are
unchanged from the frozen v3.2 plan.

Only this nested response-schema path changes:

`properties.claims.items.properties.observation`

The source schema's mutually exclusive `oneOf(return, raise)` becomes a nested
`anyOf` with the same two branches. Each `const: X` becomes the equivalent
`type: "string", enum: [X]`:

```json
{
  "anyOf": [
    {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "value_json", "exception"],
      "properties": {
        "kind": {"type": "string", "enum": ["return"]},
        "value_json": {"type": "string", "minLength": 1},
        "exception": {"type": "null"}
      }
    },
    {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "value_json", "exception"],
      "properties": {
        "kind": {"type": "string", "enum": ["raise"]},
        "value_json": {"type": "string", "enum": ["null"]},
        "exception": {
          "type": "string",
          "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"
        }
      }
    }
  ]
}
```

The two branches remain mutually exclusive because their `kind` singleton
enums cannot overlap. Therefore this dialect translation accepts the same JSON
documents as the source schema; it does not relax cross-field rules. The
unchanged local parser still independently enforces the complete contract.

OpenAI's current Structured Outputs guide lists nested `anyOf`, `enum`,
`pattern`, and the retained array/string constraints in the supported subset,
while unsupported schemas return an error:
<https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas>.

## Frozen inputs and provenance

The selected plan rows and their order remain:

1. `semantic-33-batch-cal-h01-reflected-operator-Q-59fd981294_Q-fb72e27640_Q-c1f4f9aa46`
2. `semantic-40-batch-cal-h02-metaclass-order-Q-8ea116cd1b_Q-2dff061d7b_Q-2932ec0e9c`
3. `semantic-41-batch-cal-h03-new-return-type-Q-37bd519fff_Q-d0109ae755_Q-0de4b040cb`
4. `semantic-48-batch-cal-h04-exec-namespaces-Q-c9f97f02a0_Q-2ca0af488a_Q-885d3c76eb`

The v1 runner source, v1 raw evidence, and all six v3.2 dependencies are
SHA-256 checked before execution. V2 also freezes the four actual transport
request hashes in code. The protocol, runner, tests, and prior-failure evidence
must be committed and pushed with a clean worktree; local HEAD, tracking HEAD,
and the live remote branch must match before the first request.

The canonical direct-file runner also installs a minimal in-memory `evals`
package before importing the hashed evaluator modules. This prevents
`evals/__init__.py` and its unrelated transitive imports from loading stale
bytecode outside the declared dependency boundary. Bytecode caches for the
v1 runner, frozen v3.2 modules, and model client are refused.

## Attempt and stopping rule

- Canonical output:
  `.tmp/evals/semantic_calibration_codex_pilot/sol-medium-hard-batches-v2.json`
- One canonical attempt only; no request retry.
- At most four requests, one per frozen batch.
- If a client/runtime contract error occurs, record it and stop immediately so
  an identical transport failure cannot consume the remaining requests.
- A strict semantic parse failure is recorded, but later batches still run.

## Fixed diagnostic rule

Each of the 12 claims is jointly correct only when both verdict and typed
observation match the CPython 3.10.11 oracle.

- `harder_v4_triggered`: all 4 units strictly parse and at least 10/12 claims
  are jointly correct. This only triggers authoring a harder bank.
- `screen_threshold_not_met`: all 4 units strictly parse and fewer than 10/12
  are jointly correct. It does not prove that the bank is hard enough.
- `output_or_runtime_failure`: fewer than 4 units strictly parse for any output
  or runtime reason.

The threshold is a design heuristic over four authored clusters, not a
statistical confidence claim. Reasons are retained but not automatically
scored.

Canonical command after the v2 preregistration commit is pushed:

```powershell
.\.venv\Scripts\python.exe -B evals/semantic_calibration_codex_pilot_v2.py
```
