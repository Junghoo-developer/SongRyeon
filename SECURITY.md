# Security policy

SongRyeon Audit is an experimental alpha. Do not use it as a production access
control, compliance system, or tamper-proof audit log.

For a vulnerability report, open a minimal, redacted issue in the
[SongRyeon repository](https://github.com/Junghoo-developer/SongRyeon/issues).
Never attach an audit SQLite database, WAL/SHM sidecar, prompt transcript,
credential, private key, or unredacted local path to a public issue.

The recorder intentionally retains selected prompt and tool content. Review
[`plugins/songryeon-audit/PRIVACY.md`](plugins/songryeon-audit/PRIVACY.md)
before enabling its hooks.
