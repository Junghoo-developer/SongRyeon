class Base:
    def token(self):
        return "base"


class Child(Base):
    def direct(self):
        return super().token()

    def list_comprehension(self):
        return [super().token() for _ in range(1)]

    def nested_function(self):
        def inner():
            return super().token()

        return inner()


def observe_direct():
    return Child().direct()


def observe_list_comprehension():
    return Child().list_comprehension()


def observe_nested_function():
    return Child().nested_function()
