"""Synthetic benchmark fixture."""

ACTION = "export_summary"
STATUS = "completed"
OUTPUT = "summary.json"


def action_record():
    return {"action": ACTION, "status": STATUS, "output": OUTPUT}
