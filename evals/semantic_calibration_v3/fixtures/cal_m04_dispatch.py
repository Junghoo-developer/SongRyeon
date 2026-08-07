from functools import singledispatch


@singledispatch
def classify(value):
    return "object"


@classify.register(int)
def classify_int(value):
    return "int"


@classify.register(bool)
def classify_bool(value):
    return "bool"


class Flag(int):
    pass


def observe_bool():
    return classify(True)


def observe_flag():
    return classify(Flag(1))


def observe_float():
    return classify(3.0)
