EVENTS = []


class Tracking(dict):
    def __setitem__(self, key, value):
        if key not in {"__module__", "__qualname__"}:
            EVENTS.append("set:" + key)
        super().__setitem__(key, value)


class Meta(type):
    @classmethod
    def __prepare__(metaclass, name, bases):
        EVENTS.append("prepare")
        return Tracking()

    def __new__(metaclass, name, bases, namespace):
        EVENTS.append("new:" + str(namespace["x"]))
        return super().__new__(metaclass, name, bases, namespace)


def decorate(cls):
    EVENTS.append("decorate")
    cls.decorated = True
    return cls


EVENTS.clear()


@decorate
class Demo(metaclass=Meta):
    x = 1

    def method(self):
        return None

    x = 2


def observe_events():
    return list(EVENTS)


def observe_x():
    return Demo.x


def observe_decorated():
    return Demo.decorated
