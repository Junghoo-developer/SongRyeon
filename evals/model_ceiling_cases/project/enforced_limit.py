"""Positive control: the declared limit is used by executable validation."""

MAX_PAYLOAD_CHARACTERS = 128


def accept_payload(payload):
    """Reject payloads whose character length exceeds the declared limit."""

    if len(payload) > MAX_PAYLOAD_CHARACTERS:
        raise ValueError("payload is too long")
    return payload
