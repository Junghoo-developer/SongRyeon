def run_sort(reverse=False):
    events = []
    items = [["a", 2], ["b", 1], ["c", 2]]

    def key(item):
        events.append(item[0])
        return item[1]

    ordered = sorted(items, key=key, reverse=reverse)
    return [[item[0] for item in ordered], events]


def observe_labels():
    return run_sort(False)[0]


def observe_key_calls():
    return run_sort(False)[1]


def observe_reverse_labels():
    return run_sort(True)[0]
