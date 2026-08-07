def observe_equal_keys():
    values = {True: "bool"}
    values[1] = "int"
    values[1.0] = "float"
    return [len(values), list(values)[0], values[True]]


def observe_update_order():
    values = {"a": 1, "b": 2}
    values["a"] = 3
    values["c"] = 4
    return list(values)


def observe_setdefault():
    events = []
    values = {"x": 1}

    def make_default():
        events.append("default")
        return 9

    result = values.setdefault("x", make_default())
    return [result, events, values["x"]]
