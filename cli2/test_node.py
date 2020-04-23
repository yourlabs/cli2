from cli2 import Node


def example_function():
    pass


class ExampleClass:
    def example_method(self):
        pass
example_object = ExampleClass()


class ExampleClassCallable:
    def __call__(self):
        pass
example_object_callable = ExampleClassCallable()


def test_eq():
    assert Node.factory('cli2') == Node.factory('cli2')


def test_module():
    from cli2 import test_node
    node = Node.factory('cli2.test_node')
    assert node.target == test_node
    assert node.type == 'module'
    assert example_object_callable in node.callables


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
