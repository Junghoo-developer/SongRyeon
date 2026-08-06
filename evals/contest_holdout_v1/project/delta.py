from lilac import check_frame


def encode_frame(payload: str) -> bytes:
    check_frame(payload)
    return payload.encode("utf-8")
