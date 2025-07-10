example_list = [lambda: True]
example_dict = dict(a=lambda: True)


def example_function(*args, **kwargs):
    """
    Example function docstring where the first sentence unfortunnately spreads
    over the next line.

    :param args: All arguments you want but this line will spread over
                 multiple lines just for the sake of it
    """
    return f"""
    You have called example_function with:

    args={args}
    kwargs={kwargs}
    """


example_function.cli2 = dict(color='pink')


class ExampleClass:
    def example_method(self, *args, **kwargs):
        return (args, kwargs)


example_object = ExampleClass()


class ExampleClassCallable:
    @classmethod
    def __call__(cls, *args, **kwargs):
        return (args, kwargs)


example_object_callable = ExampleClassCallable()
