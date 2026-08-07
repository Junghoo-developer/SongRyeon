def make_readers():
    error = "outer"

    def before_handler():
        return error

    try:
        raise ValueError("x")
    except ValueError as error:
        def inside_handler():
            return error

    return before_handler, inside_handler


def make_saved_reader():
    try:
        raise ValueError("x")
    except ValueError as error:
        return lambda error=error: type(error).__name__


def observe_cleared_cells():
    outcomes = []
    for reader in make_readers():
        try:
            outcomes.append(reader())
        except BaseException as failure:
            outcomes.append(type(failure).__name__)
    return outcomes


def observe_default_capture():
    return make_saved_reader()()


def observe_previous_binding():
    error = "before"
    try:
        raise ZeroDivisionError()
    except ZeroDivisionError as error:
        inside = type(error).__name__

    try:
        after = error
    except NameError as failure:
        after = type(failure).__name__

    return [inside, after, "error" in locals()]
