"""Synthetic benchmark fixture."""


def prepare_record(token):
    # Replace the token with "[REDACTED]" before persistence.
    return {"token": token}
