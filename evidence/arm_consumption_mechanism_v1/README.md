# SongRyeon ARM public evidence bundle v1

This bundle makes the narrow RC5 ARM mechanism claim independently recountable without private files or network access.

## Verify in one command

```text
python verify.py
python -m unittest discover -s tests -v
```

The verifier uses only the Python standard library. It verifies every declared file hash, joins 540 final blind-score rows back to the sanitized public key and condition-masked answer packets, and recomputes:

- negative evidence laundering: `style-placebo-enforced` **15/45** versus `evidence-enforced` **1/45**;
- positive semantic grounded success: **43/45** versus **45/45**.

## Claim ceiling

Status is **`exploratory_not_publishable`**. This is a reused-synthetic-case, single-model, blind-AI preliminary mechanism signal. It is not a confirmatory or held-out result and does not establish SongRyeon-wide, final-recheck-stage-only, production, real-world, or general performance superiority. The original predeclared decision was `NO-GO`.

## What is included

- `data/public_score_rows.{jsonl,csv}`: 540 sanitized final score rows;
- `upstream_records/`: exact condition-masked answer packets, rating/final-score locks, adjudication records, capture index, and evidence packets;
- `historical_source/`: exact selected blobs from commit `3eaad35a93d0a2184864de8f4e169855cb3ada9f` (protocol, synthetic cases, harness, scorer, verifier, and tests);
- `CLAIMS.json`, `SOURCE_LINEAGE.json`, `SOURCE_HASHES.json`, and `TRANSFORMATION_PROVENANCE.json`;
- `MANIFEST.json` and `SHA256SUMS`.

## What is deliberately excluded

Raw model-call artifacts were not copied because they contain prompt/attempt internals and may contain hidden model reasoning. The original `blind_key.json` was not copied because it contains `blinding_secret_hex`; `data/blind_key_public.json` retains only the completed identity mapping and source hashes. The path-bearing upstream `unblinded_summary.json` was not copied; its SHA-256 is anchored in `CLAIMS.json`, and all presented counts are recomputed from public rows.

Full model regeneration additionally requires a complete SongRyeon checkout at the historical commit and local Ollama `gemma4:26b` with the recorded digest. Model regeneration is not guaranteed byte-deterministic across runtime/hardware changes; recounting this archived result is deterministic and self-contained here.
