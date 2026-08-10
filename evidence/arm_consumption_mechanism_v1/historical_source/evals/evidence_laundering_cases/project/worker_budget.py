"""Synthetic benchmark fixture."""

WORKER_POLICY = {"maximum": 2}


def reserve_workers(requested):
    if requested > WORKER_POLICY["maximum"]:
        raise ValueError("worker budget exceeded")
    return requested
