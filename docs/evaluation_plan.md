# Evaluation plan and completed contest holdout

The public contest evaluation compares three agent structures while keeping the
local model fixed:

1. a single `gemma4:26b` tool agent without Node2 or Node4,
2. SongRyeon with the Node4 model audit replaced by a deterministic bypass,
3. full SongRyeon with Node1 through Node4.

All structures use the same model digest, temperature, context size, source
fixture and per-turn limits. `qwen3:14b` was used only in earlier model-scale
exploration and is not part of this official structural comparison.

## Frozen v2 matrix

The valid frozen matrix contains 24 synthetic Python cases, three structures
and three seeds: 216 recorded runs in total. Case definitions, source fixtures,
scoring rules and HMAC commitments were frozen before the first valid output.
Failures and incomplete responses remain in the denominator.

The first-verdict mechanical results were:

| Structure | Result |
|---|---:|
| single agent | 71 / 72 |
| SongRyeon, deterministic Node4 bypass | 72 / 72 |
| full SongRyeon | 72 / 72 |

The single-agent miss was an incomplete `ModelResponseError`, not a reviewed
semantic error. Full SongRyeon and the deterministic-bypass structure tied on
all 72 paired verdicts, so this benchmark does not establish a causal benefit
for Node4 or general system superiority.

The project owner audited 18 precommitted blind items plus the one invalid/null
row that the protocol adds automatically, for 19 items in total. Parse status
matched 19/19; fixture support and A/R authority/source labeling each matched
18/19. The automatically included item had a null model response and therefore
no explanation to audit. This owner audit is not an independent external review
and does not validate all 216 explanations.

## Case groups

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

## Claim boundary

The publication integrity gate permits publication of the frozen evidence
chain. It does not establish statistical significance, real-workload
generalization, complete explanation accuracy, elimination of hallucination or
the isolated causal effect of Node4. Future work should reuse identical Node3
drafts for the Node4 and no-Node4 arms to measure that effect directly.

The canonical protocol, hashes and public artifacts are in
[`evals/contest_holdout_v1/README.md`](../evals/contest_holdout_v1/README.md)
and `evals/contest_holdout_v1/frozen/contest-20260806-v2/`.
