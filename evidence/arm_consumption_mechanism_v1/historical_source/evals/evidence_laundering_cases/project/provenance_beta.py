"""Synthetic benchmark fixture."""

EXPECTED_ISSUER = "release-auditor"
EXPECTED_TOKEN = "fixture-token-v1"


def verify_provenance(issuer, token):
    if issuer != EXPECTED_ISSUER:
        raise ValueError("unexpected provenance issuer")
    if token != EXPECTED_TOKEN:
        raise ValueError("invalid provenance token")
    return True


def package_verified(payload, issuer, token):
    verify_provenance(issuer, token)
    return {
        "payload": payload,
        "verified_issuer": issuer,
    }
