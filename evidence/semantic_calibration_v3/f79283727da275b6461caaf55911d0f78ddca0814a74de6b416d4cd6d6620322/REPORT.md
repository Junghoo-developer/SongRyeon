# Semantic Calibration v3.1 — primary preflight result

## Status

The primary v3.1 run stopped at the preregistered contract gate. No semantic
calibration request was made.

- frozen source commit: `cd31bb53afcdf1042893f12f08650ec2d2d8b360`
- sealed contract evidence commit: `62571f9c51dffa1aa6ff399ea0fc18b9046c5888`
- freeze SHA-256: `f79283727da275b6461caaf55911d0f78ddca0814a74de6b416d4cd6d6620322`
- contract artifact SHA-256: `924d62ae9f089a7e4c1426f1783c0ddb97f27635cf20fec77b3d3e06a4e1d0e7`
- execution matrix: valid, 4/4 rows present
- completed model responses: 4/4
- strict-schema parses: 4/4
- exact contract tasks: 2/4
- exact embedded claims: 4/6
- semantic model calls: 0

## Failure

The nested-object return, raised exception, and two non-return claims in the
batch were exact. The primitive Boolean return and array return were not.
Both failures had the same shape: the model changed the supplied raw return
value into an extra object containing `value` and `exception`.

Expected primitive value:

```json
true
```

Observed primitive value:

```json
{"exception": null, "value": true}
```

The array return was wrapped in the same way. These were valid JSON responses
under the provider schema because the frozen return `value` field used an
unconstrained JSON schema (`{}`). They were nevertheless rejected by the
strict exact-value scorer.

## Interpretation and next amendment

This is an output-contract failure, not a semantic score. V3.1 proved that the
Ollama compatibility fix allowed all four model calls to complete, but the
mixed-type unconstrained value field was not reliable enough for the required
4/4 transcription gate.

The sealed v3.1 artifact remains primary and is not overwritten. A later
freeze may change only the wire representation of return values: the model
emits a JSON string and the strict local parser converts that string back into
the same typed `{kind, value, exception}` observation used by the existing
oracle and scorer. Fixtures, oracle outcomes, run order, semantic claims,
thresholds, and stopping rules remain unchanged. The revised contract gate
must still pass 4/4 before any semantic request.
