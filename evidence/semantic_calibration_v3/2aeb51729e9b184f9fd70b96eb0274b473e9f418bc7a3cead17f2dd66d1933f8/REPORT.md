# Semantic Calibration v3 — primary preflight result

## Status

The primary v3 run stopped at the preregistered contract gate. No semantic
calibration request was made.

- frozen source commit: `b81ae3ee48622fd12a75b684a98bb923b53b1de1`
- sealed contract evidence commit: `cd2763568aa29a45e19bb9ad5d5ff14b940abefa`
- freeze SHA-256: `2aeb51729e9b184f9fd70b96eb0274b473e9f418bc7a3cead17f2dd66d1933f8`
- contract artifact SHA-256: `33ecb9e8dd3fe8891d4b17167e97f3e14dd8d55a4359fecba115f850564758ec`
- execution matrix: valid, 4/4 rows present
- exact contract tasks: 0/4
- exact embedded claims: 0/6
- semantic model calls: 0

## Failure

Every contract row contains the same pre-response client failure:

```text
Ollama HTTP 400: Field 'json_schema': JSON schema conversion failed:
Pattern must start with '^' and end with '$'
```

The frozen response schema used the unanchored pattern `\S` for a nonempty
`reason`. The current Ollama structured-output converter rejected that schema
before the model produced an answer. Therefore this result is an output-
contract/harness compatibility failure, not evidence of semantic model
performance.

## Amendment rule

The sealed v3 result remains the primary record and is not overwritten. A new
freeze may remove only the provider-side unanchored `reason` pattern. The
strict local parser continues to reject empty or whitespace-only reasons, so
the scored response contract is not relaxed. Fixtures, oracle results, order,
prompts, scoring thresholds, and the preregistered gate remain unchanged.

This amendment is permitted before v3.1 because no semantic response was
observed. The next run must receive a new freeze SHA and repeat the complete
4/4 contract gate before any semantic request.
