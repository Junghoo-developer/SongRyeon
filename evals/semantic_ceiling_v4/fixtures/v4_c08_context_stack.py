EVENTS = []


class Manager:
    def __init__(self, name, mode):
        self.name = name
        self.mode = mode

    def __enter__(self):
        EVENTS.append("enter:" + self.name)
        return self

    def __exit__(self, kind, value, traceback):
        EVENTS.append(
            ["exit:" + self.name, None if kind is None else kind.__name__]
        )
        if self.mode == "replace":
            raise KeyError(self.name)
        if self.mode == "suppress":
            return True
        return False


def run_suppressed_stack():
    EVENTS.clear()
    with Manager("outer", "pass"):
        with Manager("middle", "suppress"):
            with Manager("inner", "replace"):
                EVENTS.append("body")
                raise ValueError("body")
    EVENTS.append("after")
    return list(EVENTS)


def observe_suppressed_trace():
    return run_suppressed_stack()


def observe_after_marker():
    return run_suppressed_stack()[-1]


def observe_unsuppressed_replacement():
    EVENTS.clear()
    with Manager("outer", "pass"):
        with Manager("inner", "replace"):
            raise ValueError("body")
