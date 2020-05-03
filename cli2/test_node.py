"""
Test cases for cli2.Node
"""
from cli2 import Node


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


def test_eq():
    assert Node.factory('cli2') == Node.factory('cli2')


def test_module():
    from cli2 import test_node
    node = Node.factory('cli2.test_node')
    assert node.target == test_node
    assert node.type == 'module'
    assert str(node) == 'cli2.test_node'
    assert repr(node) == 'Node(cli2.test_node)'
    assert example_object_callable in node.callables

    node = Node('test_node', test_node)
    assert node.target == test_node
    assert node.type == 'module'


example_list = [lambda: True]


def test_list():
    node = Node.factory('cli2.test_node.example_list.0')
    assert node.target == example_list[0]


example_dict = dict(a=lambda: True)


def test_dict():
    node = Node.factory('cli2.test_node.example_dict.a')
    assert node.target == example_dict['a']


def test_unknown():
    node = Node.factory('lollololololololollolool')
    assert not node.module
    assert not node.target


def test_function():
    node = Node.factory('cli2.test_node.example_function')
    assert node.target == example_function
    assert node.type == 'function'
    assert not node.callables


def test_class():
    node = Node.factory('cli2.test_node.ExampleClass')
    assert node.target == ExampleClass
    assert Node('', ExampleClass.example_method) in node.callables


def test_object():
    node = Node.factory('cli2.test_node.example_object')
    assert node.target == example_object
    assert example_object.example_method in node.callables


def test_callable_class():
    node = Node.factory('cli2.test_node.ExampleClassCallable')
    assert node.target == ExampleClassCallable


def test_callable_object():
    node = Node.factory('cli2.test_node.example_object_callable')
    assert node.target == example_object_callable
