"""Synthetic benchmark fixture."""

AUDIT_LOG = []


def record_event(event):
    """Append the supplied event to AUDIT_LOG."""

    AUDIT_LOG.append(event)
