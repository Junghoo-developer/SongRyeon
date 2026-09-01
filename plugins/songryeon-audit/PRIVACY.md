# SongRyeon Audit privacy notes

SongRyeon Audit is a local black-box recorder. Review this document and the
exact hook commands before trusting the plugin hooks.

## What it records

When enabled and trusted, the bundled hooks can record the event envelope and
available content for these Codex lifecycle events:

- session, turn, tool, agent, model, permission-mode, and working-directory
  metadata;
- user prompts and final assistant messages supplied to the hook;
- proposed tool inputs and returned tool outputs supplied to the hook;
- compaction, permission, subagent, and session lifecycle events; and
- digests, byte counts, links, truncation markers, and coverage gaps derived by
  the local recorder.

The collector does not read the transcript path on its own. It records only the
fields Codex sends to a configured hook. Some hosted or specialized tool paths
may not be observable.

## Where it goes

The current plugin code does not send audit records over the network. It writes
an SQLite database under the active operating-system user's Codex plugin data
directory. A typical installed path is:

```text
~/.codex/plugins/data/songryeon-audit-<marketplace>/songryeon-audit.sqlite3
```

Standalone fallback runs can instead use the operating-system local application
data directory. Separate Windows accounts normally receive separate user data
directories, but this is not a cryptographic multi-user access-control system.

The SQLite database, its WAL, and its SHM sidecar are plaintext and are not
encrypted by this plugin. Access is inherited from the operating-system account
and filesystem. A task with SongRyeon MCP access can request records from an
exact session ID; the required working-directory filter reduces accidental
cross-task discovery but is not an authorization boundary.

When Codex calls a SongRyeon MCP read tool, the selected records enter the
active Codex or delegated-agent context. Depending on the user's Codex execution
environment and model settings, that context may be processed outside the local
machine even though the plugin code itself makes no network request. Do not use
the recorder for material that must never enter the configured model context.

## Redaction and retention

The recorder masks several common credential keys and token patterns before
storage, then bounds large previews. This is risk reduction, not complete data
loss prevention. Prompts, source code, document text, file paths, tool output,
and credentials that do not match a known pattern can still be stored.

There is no automatic expiry policy. Do not attach the SQLite database to a
public issue or share it with another person unless you have reviewed its
contents. Do not assume that removing the plugin deletes retained audit data.
Database growth is not quota-limited. Plaintext values from unknown future hook
fields are omitted by an allowlist capture policy (the overall event digest can
still depend on the received payload), and SongRyeon's own MCP input/output is replaced by
an omission marker to avoid recursive copies, but known prompt and tool fields
can still be large. Oversized hook input, SQLite contention, hook timeouts, and
unsupported tool paths can produce silent gaps because recording is explicitly
best effort and non-enforcing.

## Disable or remove

Review and disable an unneeded hook in Codex's hook trust UI. To remove the
public plugin and its marketplace from the Codex CLI configuration:

```powershell
codex plugin remove songryeon-audit@songryeon
codex plugin marketplace remove songryeon
```

Close Codex before separately inspecting or deleting retained SQLite files.
Removing stored audit data is a separate, destructive action and is not
performed automatically by this project.
