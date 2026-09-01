# SongRyeon Audit v0 design contract

This plugin is a local, read-only audit prototype for Codex. A source branch does
not establish whether it is active in a particular task, and it does not change
agent permissions or block tool calls.

## Product boundary

The product surface is not a fixed incident-report template. Hooks record a
structured black box, MCP tools expose that evidence, and the
`songryeon-self-audit` skill lets an agent reconstruct its behavior in natural
language for the user's actual question.

The reconstruction itself is model-generated **R**. It must cite event IDs and
must not be presented as hidden chain-of-thought or as an **A** fact.

## Atom classification

- **A** means the recorder can establish that a runtime event or field was
  observed: hook name, recording time, session/turn/tool IDs, payload presence,
  payload digest and size, and event links.
- **R** means semantic content supplied by a user, document, model, tool output,
  or later auditor: prompt text, proposed tool arguments, assistant text, generic
  tool-result content, interpretations, intentions, and explanations.
- An event may contain both A and R atoms. There is no whole-event A/R label.
- R is never promoted or relabeled as A. Verification creates a separate linked
  A observation while the original R atom remains R.
- A tool result's arrival, size, and digest are A; every semantic field inside
  the generic `tool_response` remains R until a tool-specific recorder contract
  independently establishes otherwise.
- Unknown actor identity and unobserved paths remain explicit unknowns.

## Storage API

`scripts/songryeon_store.py` owns the SQLite schema and exposes:

- `resolve_db_path(explicit=None) -> pathlib.Path`
- `SongRyeonStore(path=None)`
- `append_hook_event(payload, hook_name=None) -> dict`
- `get_event(event_id) -> dict | None`
- `search(query="", session_id=None, limit=50, max_sequence=None) -> list[dict]`
- `trace(event_id, direction="both", depth=2) -> dict`
- `list_sessions(limit=20) -> list[dict]` (internal store API)
- `get_session_status(session_id) -> dict`
- `find_gaps(session_id=None, limit=50, max_sequence=None) -> list[dict]`

The store API stays general for local tests and maintenance. The user-facing MCP
layer is stricter: every content-bearing operation requires an explicit
`session_id`, verifies event membership, and will not perform a cross-session
search or traversal. Session listing exposes metadata only and may apply an
exact working-directory filter.

The MCP session-list tool additionally requires an exact working-directory
scope; it does not expose an unfiltered inventory of local sessions. The status
API and MCP status tool expose metadata only. Their states mean:

- `observed_from_session_start`: the first recorded event is `SessionStart` with
  `source=startup`; this does not guarantee every runtime path or hook was
  captured.
- `observed_partial_start_missing`: the startup receipt is missing. This includes
  a first `SessionStart` with `source=resume`, `clear`, or `compact`; only the
  observed interval is auditable and earlier history is unmeasured.
- `no_songryeon_record`: this local store has no row for the exact session ID;
  this does not prove the plugin was absent or that the session did not happen.

If the exact session ID itself cannot be selected, status is unknown rather than
`no_songryeon_record`. Non-instrumented material may be analyzed as R using
ordinary reasoning, but its runtime path is not measurable by SongRyeon.

The exact-session status receipt also returns a snapshot maximum sequence. Every
content-bearing MCP tool accepts that value as `max_sequence` and excludes later
events. A delegated auditor must use the frozen cutoff so its later hooks and
tool calls cannot become evidence about the action it is auditing. The
parent-side proposal that invoked the status tool may already be inside the
snapshot; it is audit scaffolding and must not be treated as evidence about the
earlier action.

## Subagent isolation boundary

The optional personal `songryeon` profile moves raw-log interpretation into one
subagent and returns a compact R digest. The parent verifies each material event
ID's exact-session membership and cutoff but need not ingest all atom content.
The profile's read-only sandbox and tool restrictions are configured defaults
and behavioral instructions, not a hard capability boundary: parent live
permission overrides and inherited tools can still apply. Hard read-only
enforcement requires the parent turn to use read-only permissions too.

The installed collector writes beneath `PLUGIN_DATA`. The MCP process does not
receive hook-only environment variables, so the store maps its installed
`cache/<marketplace>/<plugin>/<version>` identity to the matching
`data/<plugin>-<marketplace>` directory. Standalone tests may pass an explicit
path. Transactions and hash chaining make interrupted/concurrent local writes
diagnosable; they are not a tamper-proof guarantee.

## Read interface

The local stdio MCP server exposes structured search, event, trace, session, and
coverage-gap tools. These tools never produce a fixed human-facing verdict and
never mutate external systems.

Session scoping prevents accidental reads from an unrelated local task. It is
not a multi-user ACL or a cryptographic security boundary; separate trust domains
must use separate data stores and operating-system access controls.

## Capture boundary

The hook collector is silent and non-enforcing: it never returns a deny,
rewrite, approval, or continuation decision. Codex still waits briefly for this
synchronous collector, bounded by the configured timeout. It records only events
Codex actually sends to configured hooks. Coverage gaps, truncation, and
redaction are data, not reasons to invent missing context. Basic secret
redaction reduces risk but is not a complete DLP system.

The capture contract is an allowlist. Plaintext values from unknown future hook
fields are not persisted as atoms; the overall payload digest can still depend
on them, and the recorder adds an `unclassified_payload_omitted` coverage gap.
For SongRyeon's own MCP calls, `tool_input` and `tool_response` semantic
content is replaced with an omission marker so a retrieved audit record is not
recursively copied into later audit events. The arrival envelope and digest
remain observable. Collector input and stored previews are bounded, and a busy
database can cause a silent best-effort gap before the three-second hook timeout.

The SQLite database is plaintext, has no built-in expiry or quota, and relies on
the operating-system account and filesystem for access control. MCP results
become part of the active model or subagent context; local storage therefore
does not imply that selected audit content stays off remote model infrastructure.
