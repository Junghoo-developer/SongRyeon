# Security policy

SongRyeon Core is an alpha research runtime. Its current file tools are
read-only and restricted to a configured project root, but the project is not
a sandbox for untrusted code.

## Sensitive data

The real `memory/memory.jsonl` may contain prompts, model responses, local
paths and tool output. It is excluded from Git and must not be attached to a
public issue. Use a synthetic fixture or a newly created temporary memory file
when reporting a problem.

Do not commit:

- credentials or API keys
- private conversation logs
- personal documents
- local model caches
- raw files from `.codex-remote-attachments/`

## Current trust boundary

SongRyeon prevents its LLM nodes from directly authoring records classified as
code-verified execution facts in the built-in workflow. It does not currently
provide:

- cryptographic tamper evidence for the JSONL file
- process isolation for model or tool execution
- concurrent-writer locking
- safe execution of untrusted Python code
- a guarantee that model judgments are true

Security claims and demonstrations must stay inside this boundary.

## Reporting

Until a dedicated private reporting channel exists, do not publish an
unpatched vulnerability with private reproduction data. Open a minimal issue
that states a security report is available, without including secrets or raw
memory content.
