def mark(events, name, value):
    events.append(name)
    return value


def observe_and():
    events = []
    result = mark(events, "left", 0) and mark(events, "right", 5)
    return [result, events]


def observe_or():
    events = []
    result = mark(events, "left", "") or mark(events, "right", "fallback")
    return [result, events]


def observe_chain():
    events = []
    result = (
        mark(events, "a", [])
        or mark(events, "b", 0)
        or mark(events, "c", "done")
    )
    return [result, events]
