def observe_order():
    events = []

    def value(number):
        events.append("v" + str(number))
        return number * 10

    def keep(number):
        events.append("k" + str(number))
        return number % 2

    values = [value(x) for x in range(4) if keep(x)]
    return [values, events]


def observe_scope():
    x = "outer"
    values = [x * 2 for x in range(3)]
    return [x, values]


def observe_nested():
    return [
        [i, j]
        for i in [1, 2]
        for j in [3, 4]
        if (i + j) % 2
    ]
