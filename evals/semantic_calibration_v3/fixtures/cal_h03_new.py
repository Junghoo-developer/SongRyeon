EVENTS = []


class Product:
    def __init__(self):
        EVENTS.append("product:init")


class Factory:
    def __new__(cls, mode):
        EVENTS.append("new:" + mode)
        if mode == "other":
            return Product()
        return super().__new__(cls)

    def __init__(self, mode):
        EVENTS.append("factory:init")
        self.mode = mode


class Child(Factory):
    pass


def observe_other_type():
    EVENTS.clear()
    result = Factory("other")
    return type(result).__name__


def observe_other_events():
    EVENTS.clear()
    Factory("other")
    return list(EVENTS)


def observe_child():
    EVENTS.clear()
    result = Child("self")
    return [type(result).__name__, list(EVENTS)]
