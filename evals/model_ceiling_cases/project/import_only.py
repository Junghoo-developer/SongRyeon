"""Negative control: importing a validator does not execute it."""

from validators import validate_payload


def process(payload):
    """Return the payload without calling the imported validator."""

    return payload
