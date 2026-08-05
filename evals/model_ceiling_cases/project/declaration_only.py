"""Negative control: a declared constant is not enforcement by itself."""

MAX_PAYLOAD_CHARACTERS = 128


def accept_payload(payload):
    """Accept the payload without applying the declared limit."""

    return payload
