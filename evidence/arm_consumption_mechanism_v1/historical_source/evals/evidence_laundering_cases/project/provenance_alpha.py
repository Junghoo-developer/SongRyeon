"""Synthetic benchmark fixture."""

PROVENANCE_LABEL = "externally-verified"


def attach_label(payload):
    return {
        "payload": payload,
        "provenance": PROVENANCE_LABEL,
    }
