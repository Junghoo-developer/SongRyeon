EVENTS = []


class Left:
    def __iadd__(self, other):
        EVENTS.append("iadd")
        return NotImplemented

    def __add__(self, other):
        EVENTS.append("add")
        return "left"


class Right(Left):
    def __radd__(self, other):
        EVENTS.append("radd")
        return "right"


class Stored:
    def __get__(self, instance, owner):
        if instance is None:
            return self
        EVENTS.append("get")
        return instance._value

    def __set__(self, instance, value):
        EVENTS.append("set:" + type(value).__name__)
        instance._value = value


class Box:
    value = Stored()

    def __init__(self):
        self._value = Left()


def observe_subclass_fallback():
    EVENTS.clear()
    box = Box()
    box.value += Right()
    return [box.value, list(EVENTS)]


def observe_same_type_fallback():
    EVENTS.clear()
    box = Box()
    box.value += Left()
    return [box.value, list(EVENTS)]


def observe_assignment_events():
    EVENTS.clear()
    box = Box()
    box.value += Right()
    return list(EVENTS)
