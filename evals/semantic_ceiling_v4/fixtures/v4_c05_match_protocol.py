EVENTS = []


class Point:
    __match_args__ = ("x", "y")

    def __init__(self, x, y):
        self._x = x
        self._y = y

    @property
    def x(self):
        EVENTS.append("x")
        return self._x

    @property
    def y(self):
        EVENTS.append("y")
        return self._y


class Broken:
    __match_args__ = ["x"]
    x = 1


def guard(value):
    EVENTS.append("guard:" + str(value))
    return value > 0


def classify(value):
    match value:
        case Point(1, y) if guard(y):
            return "first"
        case Point(x, 2):
            return "second"
        case _:
            return "other"


def observe_guard_fallback():
    EVENTS.clear()
    result = classify(Point(1, 0))
    return [result, list(EVENTS)]


def observe_second_case():
    EVENTS.clear()
    result = classify(Point(0, 2))
    return [result, list(EVENTS)]


def observe_invalid_match_args():
    match Broken():
        case Broken(value):
            return value
