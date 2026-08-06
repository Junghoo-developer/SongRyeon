from cedar import audit_event


def publish_event(event: str) -> str:
    return audit_event(event)
