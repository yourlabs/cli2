import pytest

from cli2.cli import main

from cli2.test import autotest, Outfile


def test_call():
    result = main('cli2.test_node.example_function', 'x', 'y=z')
    assert "args=('x',)" in result
    assert "kwargs={'y': 'z'}" in result


def test_doc_by_default(mocker):
    main.outfile = Outfile()
    main('cli2.test_node')
    assert 'example_function' in main.outfile


def test_help_argument(mocker):
    main.outfile = Outfile()
    main('help', 'cli2.test_node')
    assert 'example_function' in main.outfile


def test_help_no_argument(mocker):
    main.outfile = Outfile()
    main()
    assert 'help' in main.outfile


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
