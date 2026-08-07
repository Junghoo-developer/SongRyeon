# Sol medium hard-batch pilot v1: runtime-failure report

## Status

This is an immutable record of a failed, non-official pilot attempt. It is not
a Sol accuracy result, a bare-model result, a SongRyeon result, or a contest
score.

- Raw artifact: `pilot.json`
- Raw artifact SHA-256:
  `6e944771338e7e1887a448673e723508173b7173e3627895eda9443e00a418a9`
- Preregistered source commit:
  `fe0c5315dab2a8a3041e4889372348e0e0b1b090`
- Remote branch at execution:
  `origin/codex/contest-release-2026`
- Runtime: ChatGPT-account Codex integration
- Model contract: `gpt-5.6-sol`, `medium`, SDK `0.144.4`
- Recorded local time: 2026-08-07 17:51:45--17:51:53 KST

The exact raw bytes were copied from the canonical ignored `.tmp` artifact and
verified against the SHA-256 above.

## Independently recomputed result

| Field | Value |
|---|---:|
| Attempted units | 4 |
| Strictly parsed units | 0 |
| Parsed claims | 0/12 |
| Jointly correct parsed claims | 0 |
| Returned input/output/total token metrics | 0/0/0 |
| Summed row latency | 6460.0964 ms |
| Preregistered classification | `output_or_runtime_failure` |

Every row records one client call attempt, no returned answer, no SDK thread
items, and a `ModelCallError` wrapping a `RuntimeError`. `run_state=complete`
only means that the harness recorded all four failures and finalized the file.
It does not mean that inference completed.

## Read-only runtime forensics

The raw artifact intentionally preserves only the wrapped exception type. A
read-only query of the existing Codex app-server log database identified the
underlying server response for the first three turns. Each was HTTP 400 with:

> `invalid_json_schema`: `oneOf` is not permitted at
> `properties.claims.items.properties.observation`.

The supporting log excerpts and identifiers are preserved in
`RUNTIME_FORENSICS.json`. The fourth row used the same frozen response schema
and has the same wrapped exception type, but its detailed server error was not
flushed to the log database before the SDK process closed. Therefore the exact
fourth underlying message is not claimed as directly observed.

The logs also record `auth_mode="Chatgpt"` and both API-key presence flags as
false. The first three requests were rejected during response-schema
validation, before any usable model result or token-usage event was returned.

## Allowed conclusion

The only semantic conclusion is:

> Pilot v1 is invalid because its transport response schema was rejected. It
> generated no evidence about whether the four hard batches are easy or hard
> for Sol medium.

In particular, `joint_correct=0` is not a 0/12 model score. The zero-valued
usage summary means that the SDK returned no usage metrics; it does not prove
zero account-credit consumption or zero incremental cost.

## Follow-up boundary

The preregistered v1 attempt must not be retried or overwritten. A follow-up
must use a new experiment ID and output path, preserve the same claim packet
and strict post-hoc parser, and preregister an API-compatible transport schema
that does not use `oneOf`.
