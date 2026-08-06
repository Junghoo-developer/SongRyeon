from lilac import check_frame


def encode_frame(payload: str) -> bytes:
    return payload.encode("utf-8")
