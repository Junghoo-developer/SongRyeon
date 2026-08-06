MAX_PACKET_CHARACTERS = 64


def store_packet(payload: str) -> int:
    if len(payload) > MAX_PACKET_CHARACTERS:
        raise ValueError("packet is too long")
    return len(payload)
