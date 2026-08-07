# Sol medium hard-batch pilot v2: ceiling-diagnostic report

## Status

This is an immutable record of one preregistered, non-official ceiling
diagnostic. It is not a bare-model result, a SongRyeon result, a contest score,
or a controlled comparison against Gemma or another model.

- Raw artifact: `pilot.json`
- Raw artifact SHA-256:
  `bafd2c35dd3b0b63e6bc644cfcf45ae76fd78a3d498a2f0a17b59365f29800f3`
- Preregistered source commit:
  `b09c0297aedab6a8c1eccd240ce8a636f47f3584`
- Protocol SHA-256:
  `6605f8807ac6bc2c4ede3afa78f56f576c452f8ed1c7054bec0b50c75c2adac9`
- Runtime: ChatGPT-account Codex integration
- Model contract: `gpt-5.6-sol`, `medium`, SDK `0.144.4`
- Recorded local time: 2026-08-07 18:16:01--18:16:49 KST

The exact raw bytes were copied from the canonical ignored `.tmp` artifact and
verified against the SHA-256 above.

## Independently recomputed result

| Field | Value |
|---|---:|
| Planned/attempted units | 4/4 |
| Strictly parsed units | 4/4 |
| Scored claims | 12 |
| Verdict-correct claims | 12/12 |
| Typed-observation-correct claims | 12/12 |
| Jointly correct claims | 12/12 |
| Client calls | 4 |
| Agent tool calls | 0 |
| Input/output/reasoning/total tokens | 42,800 / 1,249 / 416 / 44,049 |
| Summed row latency | 45,957.3268 ms |
| Preregistered classification | `harder_v4_triggered` |

A read-only verifier that did not import the project scorer independently
decoded the wire answers, mapped the frozen public claim IDs to the CPython
3.10.11 oracle, and checked verdict plus typed return value or exception. It
found no discrepancy across 224 invariants. Details are in
`INDEPENDENT_AUDIT.json`.

## Allowed conclusion

The supported conclusion is deliberately narrow:

> In this one preregistered Codex-account Sol-medium run, all 12 claims in the
> four authored hard-batch clusters strictly parsed and matched the frozen
> CPython 3.10.11 oracle on both verdict and typed observation.

The fixed trigger was 10/12 with all four units parsed, so 12/12 correctly
triggers authoring a harder v4 bank. A perfect result on this small screen is a
strong ceiling warning: these four clusters did not discriminate the upper end
of Sol-medium performance in this run.

## Interpretation limits

The 12 claims are nested inside four authored clusters, not 12 independent
trials. This result does not establish:

- 100% accuracy on the full v3.2 bank, a future v4 bank, or general coding;
- a statistical ceiling-effect magnitude or confidence interval;
- superiority over Gemma, SongRyeon, or any other baseline under matched
  conditions;
- correctness of the unscored natural-language reasons;
- behavior under another prompt, effort, seed, SDK, or authentication route;
- zero monetary cost or zero account-credit/plan-allowance consumption.

The artifact therefore remains `publishable=false`, `official_score=false`,
and `diagnostic_score=true`.

## Authentication and hardware boundary

The runner rejected API/access-token environment variables and the app-server
logs recorded `auth_mode=Chatgpt`, `gpt-5.6-sol`, and `Medium` for four distinct
turns. No shell, function, MCP, or custom tool call was emitted. This blocks the
Platform API-key billing route, but does not inspect the account ledger,
subscription allowance, credits, or auto-top-up settings.

The experiment used the remote Codex-account client rather than the local
Ollama client. No whole-machine GPU telemetry was collected, so the stronger
claim that no unrelated process touched the GPU is not made. Safe log metadata
is preserved in `RUNTIME_ATTESTATION.json`; raw log bodies are intentionally
excluded because they may contain authentication material.

## Next experiment

Create and freeze a v4 bank before seeing any new model answers. It should use
more independent semantic clusters, adversarial near-miss claims, longer
cross-file dependencies, and matched Sol/Gemma or bare/SongRyeon conditions.
Only that controlled comparison can support a comparative performance claim.
