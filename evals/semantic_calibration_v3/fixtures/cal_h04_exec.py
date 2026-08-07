SOURCE = """
y = x + 1

def read_x():
    return x

def read_y():
    return y
"""


def make_namespaces():
    globals_namespace = {"x": 10}
    locals_namespace = {"x": 20}
    exec(SOURCE, globals_namespace, locals_namespace)
    return globals_namespace, locals_namespace


def observe_top_level_y():
    globals_namespace, locals_namespace = make_namespaces()
    return locals_namespace["y"]


def observe_function_x():
    globals_namespace, locals_namespace = make_namespaces()
    return locals_namespace["read_x"]()


def observe_function_y():
    globals_namespace, locals_namespace = make_namespaces()
    return locals_namespace["read_y"]()
