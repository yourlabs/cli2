"""
Test cases for cli2.Node
"""
from cli2.node import Node
from cli2.examples import test as test_node


def test_eq():
    assert Node.factory('cli2') == Node.factory('cli2')


def test_module():
    node = Node.factory('cli2.examples.test')
    assert node.target == test_node
    assert node.type == 'module'
    assert str(node) == 'cli2.examples.test'
    assert repr(node) == 'Node(cli2.examples.test)'
    assert test_node.example_object_callable in node.callables

    node = Node('test_node', test_node)
    assert node.target == test_node
    assert node.type == 'module'


def test_list():
    node = Node.factory('cli2.examples.test.example_list.0')
    assert node.target == test_node.example_list[0]


def test_dict():
    node = Node.factory('cli2.examples.test.example_dict.a')
    assert node.target == test_node.example_dict['a']


def test_unknown():
    node = Node.factory('lollololololololollolool')
    assert not node.module
    assert not node.target


def test_function():
    node = Node.factory('cli2.examples.test.example_function')
    assert node.target == test_node.example_function
    assert node.type == 'function'
    assert not node.callables


def test_class():
    node = Node.factory('cli2.examples.test.ExampleClass')
    assert node.target == test_node.ExampleClass
    assert Node('', test_node.ExampleClass.example_method) in node.callables


def test_object():
    node = Node.factory('cli2.examples.test.example_object')
    assert node.target == test_node.example_object
    assert test_node.example_object.example_method in node.callables


def test_callable_class():
    node = Node.factory('cli2.examples.test.ExampleClassCallable')
    assert node.target == test_node.ExampleClassCallable


def test_callable_object():
    node = Node.factory('cli2.examples.test.example_object_callable')
    assert node.target == test_node.example_object_callable
