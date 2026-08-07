def observe_reverse_window():
    return list(range(6))[4:1:-1]


def observe_negative_stride():
    return list(range(6))[-1:0:-2]


def observe_extended_assignment():
    values = list(range(6))
    values[1:5:2] = [8, 9]
    return values
