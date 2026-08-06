def check_frame(payload: str) -> None:
    if len(payload) > 72:
        raise ValueError("frame is too long")
