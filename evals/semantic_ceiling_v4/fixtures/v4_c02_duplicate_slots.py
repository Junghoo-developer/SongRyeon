class Root:
    __slots__ = ("value",)


class Child(Root):
    __slots__ = ("value",)


def make_child():
    instance = Child()
    Root.value.__set__(instance, "root")
    Child.value.__set__(instance, "child")
    return instance


def observe_distinct_slots():
    instance = make_child()
    return [
        instance.value,
        Root.value.__get__(instance, Child),
        Child.value.__get__(instance, Child),
    ]


def observe_after_child_delete():
    instance = make_child()
    Child.value.__delete__(instance)
    return instance.value


def observe_normal_assignment():
    instance = make_child()
    instance.value = "new"
    return [instance.value, Root.value.__get__(instance, Child)]
