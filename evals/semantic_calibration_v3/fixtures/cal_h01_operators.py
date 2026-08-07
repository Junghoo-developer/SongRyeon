def observe_forward():
    events = []

    class Left:
        def __add__(self, other):
            events.append("L.add")
            return "left"

    class Right(Left):
        def __radd__(self, other):
            events.append("R.radd")
            return "right"

    return [Left() + Right(), events]


def observe_reverse():
    events = []

    class Left:
        def __add__(self, other):
            events.append("L.add")
            return "left"

    class Right(Left):
        def __radd__(self, other):
            events.append("R.radd")
            return "right"

    return [Right() + Left(), events]


def observe_not_implemented():
    events = []

    class Neutral:
        def __add__(self, other):
            events.append("N.add")
            return NotImplemented

    class Reflected:
        def __radd__(self, other):
            events.append("R.radd")
            return 7

    return [Neutral() + Reflected(), events]
