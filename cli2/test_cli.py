import pytest

from cli2.cli import main

from cli2.test import autotest


def test_call():
    result = main('cli2.test_node.example_function', 'x', 'y=z')
    assert "args=('x',)" in result
    assert "kwargs={'y': 'z'}" in result


def test_doc():
    result = main('cli2.test_node')
    assert 'example_function' in result

    result = main('help', 'cli2.test_node')
    assert 'example_function' in result

    result = main()
    assert 'help' in result


@pytest.mark.parametrize('name,command', [
    ('alone', ''),
    ('help', 'help'),
    ('help_module', 'help cli2.test_node'),
    ('help_function', 'help cli2.test_node.example_function'),
    ('help_object', 'help cli2.test_node.example_object'),
    ('call_function_noargs', 'cli2.test_node.example_function'),
    ('call_function', 'cli2.test_node.example_function a b c=1 d=2'),
    ('call_method', 'cli2.test_node.example_object.example_method a b=c'),
    ('call_object', 'cli2.test_node.example_object_callable a b=1'),
])
def test_cli(name, command):
    autotest(f'tests/{name}.txt', 'cli2 ' + command)
