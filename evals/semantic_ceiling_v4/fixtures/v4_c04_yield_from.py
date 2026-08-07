def delegated(events):
    events.append("delegated:start")
    received = yield "ready"
    events.append(["delegated:received", received])
    try:
        yield received * 2
    except KeyError:
        events.append("delegated:key_error")
        return received + 4
    finally:
        events.append("delegated:finally")
    return received + 5


def outer(events):
    events.append("outer:start")
    try:
        result = yield from delegated(events)
        events.append(["outer:result", result])
        return result + 1
    finally:
        events.append("outer:finally")


def observe_send():
    events = []
    generator = outer(events)
    first = next(generator)
    second = generator.send(3)
    try:
        next(generator)
    except StopIteration as stop:
        return [first, second, stop.value, events]


def observe_throw():
    events = []
    generator = outer(events)
    first = next(generator)
    second = generator.send(3)
    try:
        generator.throw(KeyError("x"))
    except StopIteration as stop:
        return [first, second, stop.value, events]


def observe_close():
    events = []
    generator = outer(events)
    first = next(generator)
    second = generator.send(3)
    result = generator.close()
    return [first, second, result, events]
