"""Synthetic benchmark fixture."""

ALLOWED_RETRIES = 2


def next_attempt(current_attempt):
    return current_attempt + 1
