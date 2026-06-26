# AGENTS.md - Working Rules for SongRyeon Core Collaborators

This document adapts the main `SongRyeon_Project/AGENTS.md` rules for the SongRyeon Core practice repository.
Codex and other AI collaborators must follow these rules when working here.

## 1. Encoding Rules

Treat `.md`, `.py`, `.json`, `.yml`, and `.txt` files as **UTF-8 without BOM**.

On Windows, default PowerShell `Get-Content`, `Set-Content`, `cat`, and redirection may display or write Korean text incorrectly.
If Korean text appears as mojibake, do not assume the file is corrupted. First suspect the reader configuration.

Read files in PowerShell like this:

```powershell
Get-Content path\to\file.md -Encoding UTF8
Get-Content path\to\file.md -Raw -Encoding UTF8
```

Avoid reading Korean documents like this:

```powershell
Get-Content path\to\file.md
cat path\to\file.md
```

If a document appears broken, diagnose before rewriting:

1. Verify the actual file encoding.
2. Re-read with explicit UTF-8.
3. Only consider repair if the file is still broken.

Document rewriting is the last resort.

## 2. Role Split

| Role | Owner |
| --- | --- |
| Vision, architecture philosophy, final approval | Junghoo |
| Vision discussion, problem framing, review support | External reviewer/advisor |
| Code edits, tests, execution records | Codex |
| Runtime report generation | SongRyeon nodes/LLMs |

Codex must not replace the user's vision decisions.
When a policy decision is unclear, document it or ask instead of silently pushing ahead.

## 3. Core Practice Repository Priority

Use this approximate priority order:

1. `AGENTS.md`
2. `Administrative_Reform_1/01_Maintenance_System/`
3. `Administrative_Reform_1/03_Maps/`
4. `Administrative_Reform_1/04_Orders/`
5. `Administrative_Reform_1/05_Execution_Records/`
6. Code and test results

Runtime demos and user logs are evidence, not automatic design authority.
If a code change is needed, preserve the boundary through an explicit request, order, maintenance policy, or execution record.

## 4. Meta-Information Rules

SongRyeon Core separates absolute, relative, and mixed information.

- Absolute information: IDs, paths, existence, counts, schema status, tool results.
- Relative information: LLM interpretation, semantic judgement, goal achievement assessment, summaries.
- Mixed information: LLM output generated from specific absolute sources.

Code must not pretend to perform semantic judgement.
LLM judgements must expose `generated_by`, `info_class`, `semantic_judgement_status`, and `source_data_ids`.

## 5. Safe Editing

- Do not revert user changes.
- Do not delete or move unrelated files.
- Document or ask before large route, prompt, database, answer-mode, or file-structure changes.
- Record tests and failures.
- Do not use broad staging such as `git add .`.

## 6. Update Trigger

If the same mistake happens twice, add the rule here or in the maintenance-system documents.

