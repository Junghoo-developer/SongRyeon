def combine(a, /, b, *, c=3):
    return [a, b, c]


def observe_valid():
    return combine(1, 2, c=4)


def observe_positional_only_error():
    return combine(a=1, b=2)


def observe_default():
    return combine(1, 2)
