from willow import REQUEST_TIMEOUT as RECORDED_TIMEOUT

REQUEST_TIMEOUT = 8


def current_timeout() -> int:
    return REQUEST_TIMEOUT
