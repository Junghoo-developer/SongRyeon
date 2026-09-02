# SongRyeon Audit

SongRyeon Audit is a local, read-only Codex audit prototype. It records selected
Codex lifecycle events as a structured black box, exposes that evidence through
local MCP read tools, and provides the `songryeon-self-audit` skill for questions
such as:

> 송련 스킬 써서 방금 왜 이 파일을 바꿨는지 확인해줘.

The skill locates the relevant session and events, follows their relationships,
checks recording gaps, and answers the user's question in natural language with
event-ID citations. It does not use a fixed incident-report template.

## Public installation

This alpha release requires Python 3.10 or newer and a Codex build with plugin
and hook support. From a terminal running as the operating-system user who will
use the plugin:

```powershell
codex plugin marketplace add Junghoo-developer/SongRyeon --ref songryeon-audit --sparse .agents/plugins --sparse plugins/songryeon-audit
codex plugin add songryeon-audit@songryeon
```

Then start a new Codex task. Before the hooks can record anything, review and
trust the exact `SongRyeon Audit` hook definition. The Codex CLI exposes this
review through `/hooks`; installing or enabling the plugin alone does not trust
its hooks. A changed hook definition must be reviewed again.

### Field-review doctor

Version 0.1.1 adds the read-only `songryeon_doctor` tool. In a new task, ask:

> 송련 doctor로 MCP 연결, Python, DB, 마지막 수집 성공·실패와 현재 세션 상태를 확인해줘.

The doctor reports content-free local diagnostics and can include the metadata
receipt for one exact session. Last-success and last-error markers are global to
the plugin data directory, not automatically facts about that session. A local
SHA-256 session correlation reports match, mismatch, or unknown without exposing
the raw session ID; even a match does not prove complete capture or freshness.
The doctor cannot read Codex's hook-trust registry, so
`hook_trust.status` deliberately remains `unknown_not_exposed_to_plugin` and
manual `/hooks` review is still required. MCP connectivity alone does not prove
that the collector hook was trusted or that a session was captured completely.

The recorder can store prompts, tool inputs, tool outputs, local paths, and
assistant messages in a local SQLite database. Read [`PRIVACY.md`](PRIVACY.md)
before trusting the hooks. Secret redaction is deliberately described as basic
risk reduction, not complete DLP.

Quick smoke test in the new task:

1. Submit `SONGRYEON_TEST_한글_🧪 를 기록하고 현재 폴더를 한 번 확인해줘.`
2. Run the doctor request above and confirm that the plaintext marker indicates
   a timestamped success while hook trust remains explicitly unknown.
3. Ask `송련 스킬로 방금 행동을 감사하고 근거 이벤트 ID와 관측 공백을 알려줘.`
4. Confirm that the answer names an exact session boundary instead of claiming
   access to hidden reasoning.

## Prototype status

This directory is the development source for a locally installable prototype.
A source checkout or marketplace entry does not prove that any particular Codex
task was instrumented: an install or reinstall is picked up by new tasks, and
the local hook commands must be reviewed and trusted before use. After each
install or hook-definition change, open `/hooks`, review `SongRyeon Audit`, and
trust the current definition before starting the test task. Trust is bound to
the hook hash, so a changed hook is skipped until it is reviewed again. The
prototype does not modify the original contest submission, tags, releases, or
external accounts.

The bundled MCP configuration is declared directly in `plugin.json`, which the
official schema supports without a companion wrapper. Its script and working
directory are plugin-root-relative. Hooks receive `PLUGIN_DATA` directly. The
read-only MCP server derives that same plugin-scoped data directory from its
installed `cache/<marketplace>/<plugin>/<version>` path because the MCP process
does not receive hook-only environment variables. Standalone runs may still
use an explicit database path or the stable local fallback implemented by
`songryeon_store.py`.

## Evidence boundary

- The existence and envelope of an observed runtime event can be **A**.
- User, model, document, and generic tool-result meaning remains **R**.
- The audit explanation is a new model-generated inference, not a runtime fact.
- R is never promoted to A. A later verification is a separate linked A
  observation; the original R atom remains R.
- Unobserved, redacted, truncated, or ambiguous context remains unknown.
- An account or session does not establish the real-world identity of its actor.

Events may contain both A and R atoms. In particular, observing a generic tool
response establishes its arrival, size, and digest—not that `exit_code`,
`status`, prose, or any external-world claim inside it is true.

## Session boundary

Session discovery and status checks return metadata only. A status check reports
one of three boundaries: observed from a first `SessionStart` whose source is
`startup`, partial observation because that startup receipt is missing, or no
matching record in this local store. A first source of `resume`, `clear`, or
`compact` is partial because earlier history is unmeasured. The first state is
not a complete-capture guarantee; the last does not prove that the plugin was
absent. There is no retroactive capture.

Evidence-bearing MCP operations require one explicit `session_id`, and event
lookup and graph traversal reject events from any other session. The skill may
list only sessions matching one required exact working directory. That discovery
uses a bounded recent event-sequence window and returns whether older events were
excluded; an empty truncated scan is not proof that no older match exists.
Recency alone is not proof. When candidates remain ambiguous it asks for the smallest
distinguishing detail before reading content. If no exact SongRyeon scope
exists, the skill can perform ordinary reasoning over user-provided material as
R, but must label the SongRyeon runtime path unmeasurable.

This is accidental-cross-session protection for a single local user, not a
multi-user authorization or cryptographic access-control system. Separate users
or trust domains need separate plugin data stores and operating-system controls.
Raw working-directory filters are normalized against the redacted stored scope,
so a Windows path under `C:\Users\<name>` can match its `[USER_HOME]` receipt
without returning the account name.

## Product boundary

The hooks are silent and non-enforcing, and the MCP surface is read-only. Codex
does briefly wait for each synchronous collector invocation, bounded by its
timeout. The plugin cannot reveal hidden chain-of-thought, expand Codex
permissions, block tool calls, or guarantee complete capture. Hash chaining
helps diagnose local recording problems but is not a tamper-proof guarantee. See
[`DESIGN_CONTRACT.md`](DESIGN_CONTRACT.md) for the normative v0 boundary.

The collector keeps two small content-free health markers beside the database:
the last observed success and the last observed error. They contain only a
timestamp, allowlisted hook name, observed input byte count, status, exception
type, and a one-way session-scope digest when a session ID was supplied. They
help distinguish a collector failure from an empty store, but they are global
last-attempt markers and do not prove hook trust, currentness, full coverage, or
the truth of recorded content.

For a scoped audit, the skill delegates raw-log reading to one read-only custom
agent named `songryeon` when it is available. The parent selects the session and
receives a compact cited digest instead of carrying the entire log trail in its
own context. The returned explanation is still R.

Codex custom-agent profiles are a separate configuration surface, so the plugin
manifest does not silently activate or copy one. The reviewed optional profile
source is [`custom-agents/songryeon.toml`](custom-agents/songryeon.toml). A user
who wants delegation must review and copy that file separately to
`~/.codex/agents/songryeon.toml`, then start a new task. Without it, the skill
can still perform a scoped inline audit, but that fallback does not isolate raw
audit content from the parent agent's context.

The profile requests `sandbox_mode = "read-only"` and forbids non-SongRyeon
tools, but this is not a hard tool allowlist: Codex subagents inherit parent
settings, and a live parent permission override can supersede the profile
default. A hard read-only run therefore requires the parent turn itself to start
read-only. The MCP evidence boundary is enforced separately with an immutable
sequence cutoff, so events generated after that snapshot—including delegated
subagent work—cannot enter the selected evidence window.

`evals/codex_intent_audit_pilot_v0/EXAMPLE_REPORT.md` is a deterministic
evaluation fixture. It is not the product UI, a response schema, or a template
the skill must reproduce.
