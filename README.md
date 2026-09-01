# SongRyeon Audit for Codex

SongRyeon Audit is an experimental local black-box recorder and evidence-linked
self-audit plugin for Codex. It records selected observable lifecycle events,
keeps runtime observations (**A**) separate from semantic claims (**R**), and
lets Codex reconstruct an action with event IDs and explicit unknowns.

This is an **alpha research prototype**, not a production security control. It
does not expose hidden chain-of-thought, enforce permissions, guarantee complete
capture, or make recorded claims true.

## Install

Python 3.10 or newer and a Codex build with plugin and hook support are required.

```powershell
codex plugin marketplace add Junghoo-developer/SongRyeon --ref songryeon-audit --sparse .agents/plugins --sparse plugins/songryeon-audit
codex plugin add songryeon-audit@songryeon
```

Start a new Codex task, open `/hooks` in the Codex CLI, inspect the exact
`SongRyeon Audit` commands, and explicitly trust them. Installation alone does
not authorize hook execution.

Before enabling the hooks, read the plugin's
[privacy notes](plugins/songryeon-audit/PRIVACY.md). Prompts, tool inputs,
tool outputs, local paths, and assistant messages can be retained in a plaintext
local SQLite database and can enter the active model context when queried.

## Smoke test

In the new instrumented task:

1. Ask: `SONGRYEON_TEST_한글_🧪 를 기록하고 현재 폴더를 한 번 확인해줘.`
2. Then ask: `송련 스킬로 방금 행동을 감사하고 근거 이벤트 ID와 관측 공백을 알려줘.`

The audit should state its session observation boundary and cite recorded event
IDs without claiming access to private reasoning.

Implementation details, limits, and optional subagent setup are documented in
the [plugin README](plugins/songryeon-audit/README.md) and
[design contract](plugins/songryeon-audit/DESIGN_CONTRACT.md).

Licensed under the [MIT License](LICENSE).
