MAX_NAME_CHARS = 12


def normalize_name(name: str) -> str:
    if len(name) > MAX_NAME_CHARS:
        raise ValueError("name is too long")
    return name.strip().lower()
