"""Synthetic benchmark fixture."""


def accept_name(name):
    """Reject blank names with ValueError."""

    if not name.strip():
        raise ValueError("name must not be blank")
    return True
