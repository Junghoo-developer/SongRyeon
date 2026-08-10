"""Synthetic benchmark fixture."""

from hashlib import sha256 as hash_payload


def describe_checksum(payload):
    return {"algorithm": "sha256", "observed_bytes": len(payload)}
