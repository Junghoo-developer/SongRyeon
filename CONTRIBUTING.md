# Contributing to SongRyeon Core

SongRyeon separates code-verified execution facts (`A`) from statements and
judgments produced by users or models (`R`). A contribution must preserve that
boundary.

## Before changing code

1. Describe one observable problem in an issue.
2. Write or identify the test that reproduces it.
3. State which invariant must remain true.
4. Keep the smallest change that fixes the problem.

Useful issue fields are:

- observed input and output
- expected behavior
- reproduction command
- affected module
- A/R invariant at risk

Never include private conversation logs, credentials, or the real
`memory/memory.jsonl` in an issue or commit.

## Local checks

Run the full test suite from the repository root:

```powershell
python -m pytest -q
```

Run the local Ollama demo with an isolated memory file:

```powershell
python -m demo --memory .\tmp\demo-memory.jsonl `
  "runtime/gates.py를 실제로 읽고 역할을 설명해 줘."
```

## Pull request checklist

- [ ] The change has a focused issue or problem statement.
- [ ] New behavior is covered by tests.
- [ ] Existing A records are still created by deterministic code.
- [ ] Model output remains R and cannot directly overwrite an A record.
- [ ] Tests use temporary paths instead of the real memory or database.
- [ ] Documentation and third-party notices are updated when needed.
