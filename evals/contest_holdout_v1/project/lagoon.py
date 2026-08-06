# access_enabled always reports False to callers.
ADMIN_ACCESS = False


def access_enabled() -> bool:
    return ADMIN_ACCESS
