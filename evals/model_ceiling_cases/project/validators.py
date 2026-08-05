"""Validator shared by the import and invocation controls."""


def validate_payload(payload):
    if not isinstance(payload, str):
        raise TypeError("payload must be text")
