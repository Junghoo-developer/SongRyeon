"""Positive control: the imported validator is explicitly called."""

from validators import validate_payload


def process(payload):
    """Validate before returning the payload."""

    validate_payload(payload)
    return payload
