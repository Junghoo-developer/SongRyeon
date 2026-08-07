class Explicit:
    def __init__(self, events):
        self.events = events

    def __contains__(self, item):
        self.events.append("contains")
        return "nonempty"


class Iterable:
    def __init__(self, events):
        self.events = events

    def __iter__(self):
        self.events.append("iter")
        return iter([1, 2, 3])

    def __getitem__(self, index):
        self.events.append("getitem")
        return 99


class Legacy:
    def __init__(self, events):
        self.events = events

    def __getitem__(self, index):
        self.events.append("get:" + str(index))
        if index < 3:
            return index * 2
        raise IndexError


def observe_contains():
    events = []
    return [2 in Explicit(events), events]


def observe_iter():
    events = []
    return [2 in Iterable(events), events]


def observe_legacy():
    events = []
    return [3 in Legacy(events), events]
