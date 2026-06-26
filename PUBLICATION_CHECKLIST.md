# Publication Checklist

This checklist is for publishing SongRyeon Core as a public GitHub portfolio repository.

## Before First Push

- [ ] Decide repository visibility: public or private first, then public later.
- [ ] Decide license.
  - Recommended for a portfolio/open-source style repo: MIT License.
  - If no license is added, people can view the code but do not automatically receive reuse rights.
- [ ] Run the safety checks:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
rg -n -i "(api[_-]?key|secret|password|private[_-]?key|BEGIN (RSA|OPENSSH|PRIVATE)|authorization:|bearer |sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|hf_[A-Za-z0-9]{20,})" . -g "!PUBLICATION_CHECKLIST.md"
rg -n "C:\\\\Users|OneDrive|바탕 화면" . -g "!Administrative_Reform_1/05_Execution_Records/runtime_runs/**" -g "!PUBLICATION_CHECKLIST.md"
```

- [ ] Confirm generated artifacts are not staged:
  - `.songryeon_core_cache/`
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

## First Push Commands

After creating an empty GitHub repository:

```powershell
git init
git add .gitignore README.md PUBLICATION_CHECKLIST.md AGENTS.md AGENTS.en.md dry_run.py main.py songryeon_core Administrative_Reform_1
git status --short
git commit -m "Publish SongRyeon Core baseline"
git branch -M main
git remote add origin https://github.com/<your-id>/<repo-name>.git
git push -u origin main
```

Do not use `git add .` until the staged file list has been checked at least once.

## After Publishing

- [ ] Add repository topics:
  - `llm`
  - `agents`
  - `provenance`
  - `traceability`
  - `local-first`
  - `python`
- [ ] Pin the repository on your GitHub profile.
- [ ] Write a short Korean or English post explaining:
  - what problem you were trying to solve,
  - what absolute/relative/mixed information means,
  - what the smoke tests prove,
  - what is intentionally not production-ready yet.
