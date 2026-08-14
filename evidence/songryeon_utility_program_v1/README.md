# SongRyeon RC6 public evidence derivative v1

This is a minimum-necessary, public-safe derivative for two narrow claims. It is not the internal omnibus synthesis, not an accuracy benchmark, and not evidence of broad product utility.

## Recomputed results

1. **Authored receipt-reconstruction fixture (24 paired cases).** The plain log supported the authored audit decision in **17/24** cases, while the linked receipt supported it in **24/24**. Mean five-field reconstruction completeness was **0.925 → 1.000**.
2. **Authored fixed-input mechanism boundary (64 cases).** Plain presentation and label-only presentation produced the same output and actual-origin R-consumption result in **64/64** cases. In the 32 clean-label cases, A-only enforcement changed actual-origin R consumption from **16/32 to 0/32**, while authored-target correctness remained **16/32 to 16/32**.

Run `python -B verify_public.py` to recompute those values from the neutralized row files and to verify the exact recursive file set, hashes, claim gates, and privacy scan. Run `python -B -m unittest discover -s tests -v` for the positive check plus tamper and undeclared-file negative controls. Both commands are CPU-only and make no model, GPU, or network calls.

## Claim boundary

The receipt result is limited to **L1 auditability within a co-designed authored fixture contract**. It does not estimate model accuracy, answer quality, real-time error interception, human review efficiency, field performance, cross-domain generalization, Node4's incremental effect, or general SongRyeon superiority.

The receipt comparison is not an equal-information formatting comparison. The linked representation adds identifiers, links, memory index, authority, and digest metadata that the plain representation does not contain. The result shows that the additional linkage can support reconstruction under this contract; it does not show that structure alone creates information.

The mechanism result is deterministic conformance plus a null boundary. Label presentation alone changed no output. On clean authored cases, the filter removed actual-origin R consumption without improving correctness. These counts are not a population effect estimate.

## Independent-audit warnings retained

The original receipt audit found the supplied source packet unsafe for external blind review: family-coded targets appeared 86 times, a changed-after-projection marker appeared eight times, and the reveal material was adjacent. The original source packet and reveal bytes are therefore excluded here. The automated authored-fixture result was not directly gold-tainted, but no blind-review claim is allowed.

The same audit found that the original manifest checked only top-level declared artifacts, left three import-cache files unsealed, and did not establish whole-tree exactness. This derivative uses a new recursive exact-set verifier and new hashes. That improves package hygiene, but the manifest remains unsigned: it is not execution attestation, authenticity proof, or tamper-proofing.

The fixed-input mechanism audit returned **REVISE**. It found the semantic target visible in the public trace, no valid generalization basis, and a crash-window counterexample in which an `applied`-named record can precede the corresponding state mutation. No user receipt, post-state application, or successful delivery claim is made here.

## Files

- `data/receipt_reconstruction_rows.jsonl`: 24 neutral paired rows with only audit correctness and five-field reconstruction counts.
- `data/mechanism_boundary_rows.jsonl`: 64 neutral rows with only clean-label status, authored target, output, and actual-origin R-consumption state for three conditions.
- `DERIVATIVE_SUMMARY.json`: published aggregates recomputed from those rows.
- `AUDIT_BOUNDARIES.json`: selected independent-audit constraints needed to interpret the aggregates.
- `TRANSFORMATION_PROVENANCE.json`: source hashes, neutralization steps, and exclusions.
- `MANIFEST.json` and `SHA256SUMS.txt`: derivative-only seal data.
- `verify_public.py` and `tests/test_verify_public.py`: fail-closed verification and negative controls.

No raw provider trace, model reasoning, credential, concealed answer-key byte, original family-coded receipt identity, personal path, contact data, or ARM exploratory artifact is included.
