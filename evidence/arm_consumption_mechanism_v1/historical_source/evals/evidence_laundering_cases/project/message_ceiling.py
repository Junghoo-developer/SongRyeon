"""Synthetic benchmark fixture."""

MAX_MESSAGE_CHARACTERS = 96


def validate_message(message):
    if len(message) > MAX_MESSAGE_CHARACTERS:
        raise ValueError("message is too long")
    return message
