# Publication Checklist

This checklist is for publishing SongRyeon Core as a public GitHub portfolio repository.

## Before First Push

- [ ] Decide repository visibility: public or private first, then public later.
- [ ] Decide license.
  - Recommended for a portfolio/open-source style repo: MIT License.
  - If no license is added, people can view the code but do not automatically receive reuse rights.
- [ ] Confirm the no-model first demo works:

```powershell
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty
```

- [ ] Confirm the output includes `상태: ok` and `node_4 gatekeeper: pass`, and does not include `FINAL_BLOCKED_BY_GATEKEEPER`.
- [ ] Run the safety checks:

```powershell
python -m pip install -r requirements-dev.txt
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
rg -n -i "(api[_-]?key|secret|password|private[_-]?key|BEGIN (RSA|OPENSSH|PRIVATE)|authorization:|bearer |sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|hf_[A-Za-z0-9]{20,})" . -g "!PUBLICATION_CHECKLIST.md"
rg -n "C:\\\\Users|OneDrive|바탕 화면" . -g "!Administrative_Reform_1/05_Execution_Records/runtime_runs/**" -g "!PUBLICATION_CHECKLIST.md"
```

- [ ] Confirm generated artifacts are not staged:
  - `.songryeon_core_cache/`
  - `.pytest_cache/`
  - `Administrative_Reform_1/05_Execution_Records/runtime_runs/`
  - `output/`
  - `tmp/`
  - `__pycache__/`

## Suggested GitHub Description

```text
Local-first agent runtime experiment focused on provenance, traceable LLM judgments, and smoke-tested runtime honesty.
```

## Suggested README Pitch

```text
SongRyeon Core separates code-verified facts, single-source semantic judgments, and multi-source synthesis inside a small local agent runtime.
```

## Safe Commit / Push Commands

For an existing repository, stage only reviewed files.
Do not stage generated caches, local env files, or unrelated dirty work.

```powershell
git status --short
git add -- README.md README.ko.md DEMO.md PUBLICATION_CHECKLIST.md
git add -- AGENTS.md Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md
git add -- Administrative_Reform_1/04_Orders/<reviewed-order-file>.md
git add -- Administrative_Reform_1/05_Execution_Records/<reviewed-execution-record>.md
git add -- songryeon_core/<reviewed-code-file>.py tests/<reviewed-test-file>.py
git status --short
git commit -m "<clear change summary>"
git push
```

For a brand-new empty GitHub repository, add the remote separately after the staged file list has been reviewed.
Never use `git add .` for release staging.

## After Publishing

- [ ] Add repository topics:
  - `llm`
  - `agents`
  - `provenance`
  - `traceability`
  - `local-first`
  - `python`
- [ ] Pin the repository on your GitHub profile.
- [ ] Open the public README and follow the three-layer demo path:
  - no-model `fake-turn`
  - `smoke-test`
  - optional Neo4j Vessel / R traversal
- [ ] Write a short Korean or English post explaining:
  - what problem you were trying to solve,
  - what absolute/relative/mixed information means,
  - what the smoke tests prove,
  - what is intentionally not production-ready yet.
