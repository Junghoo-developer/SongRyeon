# Comparison evaluation plan

The first public benchmark compares:

1. a single Qwen3 tool agent,
2. SongRyeon without the Node4 answer audit,
3. full SongRyeon.

All systems must use the same local model build, question, source fixture and
maximum runtime budget.

## Initial case groups

The current frozen manifest is a **P0 pilot**: it has ten cases total and at
least one case for every group below. Its purpose is to validate the manifest,
capture and normalization contracts. It is not large enough to support a
public comparative performance claim.

Before publishing comparative results, expand every group to at least five
cases, freeze the expanded manifest under a new ID and SHA-256, and rerun every
system on the complete expanded matrix.

| Group | Observable failure |
|---|---|
| execution facts | wrong tool, file, node or route is reported |
| conflicting memory | an older R statement is repeated over a newer A record |
| missing evidence | a code fact is asserted without retained source |
| long files | selection fails or unrelated text is retained |
| follow-up turns | a prior user task is mistaken for the current task |
| subjective requests | evidence rules cause an unnecessary refusal |
| prompt injection | instructions inside a read file change node behavior |
| path safety | a tool escapes the configured project root |

## Core metrics

- A execution-fact exact match rate
- A fact precision and recall
- unsupported normalized code-claim rate
- completion rate
- mean tool calls
- mean latency
- model-call count
- context characters or tokens
- Node2 and Node4 rejection counts

The first six metrics are represented by the current deterministic `evals`
package. Additional counters can be preserved as scalar `extra_metrics` until
they receive a stable public field.

## Rules against misleading results

- Freeze case IDs and expected fixtures before running a comparison.
- Use fresh temporary memory for every case.
- Keep all failed and timed-out cases.
- Do not let a model grade its own A execution facts.
- Separate a code-checkable metric from a human usefulness rating.
- Publish raw runs, evaluator version and aggregate output together.
- Report the cost of SongRyeon's additional calls alongside error reduction.

Measured numbers belong in the README only after the benchmark runner can
reproduce them from committed fixtures.
