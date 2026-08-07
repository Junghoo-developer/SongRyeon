# Semantic Calibration v3.2 — primary result

## Verdict

The preregistered bare-model gate did **not** pass. The run is complete and
auditable, but its primary status is `output_contract_or_matrix_failure`.
The row matrix itself is valid; the failing component is output-contract
reliability, followed by a non-monotonic calibration shape. Per protocol, no
SongRyeon, no-Node4, Node4, or Deep Agents comparison is authorized from this
freeze.

## Provenance

- frozen source commit: `840833659eded980360b256778e69fadb5917bee`
- freeze publication commit: `5575a1e2d93c507965590ea4d7b297ce1f150cfc`
- sealed contract evidence commit: `ec7b5500100436f46921986c07cc2f0ee96f2e7a`
- sealed semantic evidence commit: `516cbc66280d320523f0d3c498908764d689c028`
- freeze SHA-256: `fb9f26c1cba78eafa7f8b1422b2a19757eaa748bf205b3dc918a6ebe9ed872a0`
- contract artifact SHA-256: `6b4658570ca1b3870805e8763b4697cccaa9d877a9c7629ce8e2935409bf7fd7`
- semantic artifact SHA-256: `e8e8f19245a8755fc6ed412c05b44b7c2273bcb649bc94f2c45ff881f613b9e2`
- original local score SHA-256: `f5bdf66263e441500fd977149618875cfa1271528032f70b4ca234f7a11452ef`
- path-sanitized public score SHA-256: `dfbe62189e35ff3949c63a87ba50eaf8f0405aa408b396783b228b84c66d4cc2`
- model: local `gemma4:26b`, digest
  `5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251`
- Ollama: `0.32.6`; CPython oracle scope: `3.10.11`
- contract run ID: `998a11823e3048e88e93c6cbe5ef1012`
- semantic run ID: `e82546956014423691e7b16f4dfd0976`
- generation contract: seed `8849`, temperature `0`, context `16,384`,
  `think=false`, timeout `300 s`, keep-alive `30m`
- final model readiness: identical to initial readiness

`score.public.json` differs from the original score only in the two local input
path strings. All hashes, scores, details, gates, and raw model-derived fields
are unchanged.

## Contract preflight

V3.2 passed the mandatory preflight before any semantic request:

| Measure | Result |
|---|---:|
| completed tasks | 4/4 |
| outer JSON/wire validation | 4/4 |
| inner `value_json` decode | 4/4 |
| typed normalization | 4/4 |
| exact tasks | 4/4 |
| exact embedded claims | 6/6 |

This establishes wire-adapter compatibility for the trivial contract only. It
is not a semantic reasoning result and is not compared with v3.1 as a model
performance improvement. More precisely, outer provider compatibility recovered;
end-to-end wire reliability had not yet been established.

## Amendment history

- v3 stopped before any response because Ollama rejected an unanchored schema
  pattern; semantic calls: 0.
- v3.1 completed and parsed all four contract tasks but reproduced only 2/4
  tasks and 4/6 claims because mixed-type raw values were wrapped; semantic
  calls: 0.
- v3.2 changed only output serialization and its required instructions, passed
  the trivial contract, and therefore became the first version allowed to run
  the 48 semantic units.

All preceding freezes and artifacts remain in sibling evidence directories.

## Semantic result

The exact same 36 claims were measured once as singles and once in 12 batches
of three.

| Measure | Single | Batch |
|---|---:|---:|
| planned units | 36 | 12 |
| model-call attempts | 36 | 12 |
| execution success | 35 | 12 |
| complete strict parse | 33 | 8 |
| claims in parsed units | 33 | 24 |
| verdict correct | 23/36 | 20/36 |
| typed observation correct | 21/36 | 19/36 |
| joint verdict + observation | **20/36 (55.6%)** | **17/36 (47.2%)** |
| joint correctness given a parsed unit | 20/33 (60.6%) | 17/24 (70.8%) |
| exact three-claim batches | not applicable | 3/12 |
| recorded generated tokens | >= 6,041 | 5,277 |
| measured call latency | 126.19 s | 85.41 s |

Paired claim outcomes were 16 both-correct, 4 single-only, 1 batch-only, and
15 neither. The observed single-to-batch net loss was three claims, but this
must not be interpreted as a clean semantic batch effect because four batch
units failed inner JSON decoding.

An independent rescore reproduced every correctness, parsing, denominator,
and gate value above. The single-lane token value is only a lower bound: the
one `num_predict`-terminated call retained its attempt and latency but not its
provider `eval_count`, so the exact single and combined generated-token totals
cannot be recovered from the sealed artifact. The batch token total is exact.

## Parsing and execution failures

There were no outer JSON/claim-shape failures and no post-decode typed-
normalization failures.

- single: one `num_predict` length termination and two inner-JSON failures;
- batch: four inner-JSON failures;
- total: 48 model-call attempts, 47 execution completions, 41 fully parsed
  units.

Six failed units contained ten malformed `value_json` strings. They included
trailing commas or incomplete arrays, Python-style single-quoted lists, and
fragments of the outer
`exception` field leaking inside the inner JSON string. Thus v3.2 recovered
outer-schema compatibility but moved the remaining serialization vulnerability
into a free string. End-to-end wire reliability still failed under semantic
generation, especially for batches. The observed 4/12 batch versus 2/35
completed-single inner-decode failures are descriptive single-seed counts, not
an inferential batching effect.

## Difficulty calibration

Joint correctness by the preregistered difficulty labels was:

| Tier | Single | Batch |
|---|---:|---:|
| anchor | 5/12 | 2/12 |
| medium | 9/12 | 9/12 |
| hard | 6/12 | 6/12 |

The expected `anchor >= medium >= hard` gradient did not appear. The anchor
floor and anchor-minus-hard gap also failed. Some anchor loss came from output
failures, but the single lane also contained genuine semantic mistakes. The
current labels therefore are not an empirically valid difficulty scale for
this model and must not support claims about performance by difficulty.

## Gate audit

| Condition | Result |
|---|---:|
| matrix valid | pass |
| single parse >= 35/36 | **fail (33/36)** |
| batch parse >= 11/12 | **fail (8/12)** |
| single joint 20–30/36 | pass (20/36) |
| batch joint 18–30/36 | **fail (17/36)** |
| batch net loss <= 5 | pass (3) |
| anchor >= medium >= hard | **fail** |
| anchor-hard gap >= 3 | **fail** |
| anchor >= 8/12 | **fail (5/12)** |
| hard 2–8/12 | pass (6/12) |

The fixed status priority makes the official status
`output_contract_or_matrix_failure`; the other failed conditions remain
reported rather than hidden by that label.

## What this result does and does not show

Supported conclusions:

- parsed outputs contain both correct and incorrect semantic claims, but the
  parse gate prevents a formal semantic ceiling or floor classification;
- structured result assembly is a first-order bottleneck, especially in
  batches;
- the current authored difficulty labels and output wire are not ready to
  support a clean agent comparison;
- several parsed failures are genuine CPython-semantic mistakes, so output
  formatting is not the only limitation.

Unsupported conclusions:

- that SongRyeon or Node4 improves accuracy;
- that agents outperform the bare model;
- that batching itself causes exactly the observed score loss;
- that the hard tier is easier than the anchor tier in general;
- that hallucination is eliminated or that this is a public ranking.

This is one seed of one model. The 36 public claims belong to 12 authored
clusters and are not 36 independent statistical samples. Reasons are retained
for audit but are not automatically scored. Parse-conditioned accuracy excludes
failed units and is therefore subject to selection bias; it must not be used to
compare single and batch semantics. No agent run occurred.

The scientifically correct action is to stop this freeze, preserve it, and
design any later calibration as a newly preregistered version rather than
repairing or rerunning these responses.

In one sentence: **the protocol executed correctly and rejected this fixed
model/configuration as unsuitable for downstream agent comparison.**
