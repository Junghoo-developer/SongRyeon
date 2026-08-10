"""Synthetic benchmark fixture."""

ACTION = "publish"
STATUS = "rejected"
REASON = "missing approval"


def action_record():
    return {"action": ACTION, "status": STATUS, "reason": REASON}
