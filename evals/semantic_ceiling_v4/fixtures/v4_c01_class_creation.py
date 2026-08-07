EVENTS = []


class TrackingNamespace(dict):
    def __setitem__(self, key, value):
        if key not in {"__module__", "__qualname__"}:
            EVENTS.append("set:" + key)
        super().__setitem__(key, value)


class Meta(type):
    @classmethod
    def __prepare__(metaclass, name, bases, **kwargs):
        EVENTS.append("prepare:" + ",".join(base.__name__ for base in bases))
        return TrackingNamespace()

    def __new__(metaclass, name, bases, namespace, **kwargs):
        EVENTS.append("meta:new:before")
        cls = super().__new__(metaclass, name, bases, namespace, **kwargs)
        EVENTS.append("meta:new:after")
        return cls

    def __init__(cls, name, bases, namespace, **kwargs):
        EVENTS.append("meta:init")
        super().__init__(name, bases, namespace)


class Marker:
    def __set_name__(self, owner, name):
        EVENTS.append("set_name:" + name)
        self.owner = owner
        self.name = name


class Base:
    def __init_subclass__(cls, flag, **kwargs):
        EVENTS.append("init_subclass:" + cls.__name__ + ":" + str(flag))
        super().__init_subclass__(**kwargs)


class Replacement:
    def __mro_entries__(self, bases):
        EVENTS.append("mro_entries")
        return (Base,)


replacement = Replacement()
EVENTS.clear()


def decorate(cls):
    EVENTS.append("decorate")
    return cls


@decorate
class Target(replacement, flag=3, metaclass=Meta):
    field = Marker()


def observe_creation_events():
    return list(EVENTS)


def observe_rewritten_bases():
    return [
        [base.__name__ for base in Target.__bases__],
        Target.__orig_bases__[0] is replacement,
    ]


def observe_marker_binding():
    return [Target.field.owner.__name__, Target.field.name]
