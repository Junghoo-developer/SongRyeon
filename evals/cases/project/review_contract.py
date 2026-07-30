"""Small deterministic source fixture for code-review evaluation cases."""

ALLOWED_VERDICTS = ("permit", "reject")
MAX_REJECTIONS = 3


def should_route_again(verdict, rejection_count):
    """Return whether a rejected answer may be routed back for revision."""

    if verdict not in ALLOWED_VERDICTS:
        raise ValueError("unknown verdict")

    return verdict == "reject" and rejection_count < MAX_REJECTIONS
