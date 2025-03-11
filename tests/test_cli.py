import pytest

from cli2.cli2 import main, ConsoleScript

from cli2.test import autotest, Outfile


def test_call():
    result = main('cli2.examples.test.example_function', 'x', 'y=z')
    assert "args=('x',)" in result
    assert "kwargs={'y': 'z'}" in result
    result = main('cli2.examples.test.example_function', 'http://?x=bar')
    assert "args=('http://?x=bar',)" in result


def test_doc_by_default(mocker):
    main.outfile = Outfile()
    main('cli2.examples.test')
    assert 'example_function' in main.outfile


def test_help_argument(mocker):
    main.outfile = Outfile()
    main('help', 'cli2.examples.test')
    assert 'example_function' in main.outfile


def test_help_no_argument(mocker):
    main.outfile = Outfile()
    main()
    assert 'help' in main.outfile


@pytest.mark.parametrize('name,command', [
    ('alone', ''),
    ('help', 'help'),
    ('help_module', 'help cli2.examples.test'),
    ('help_function', 'help cli2.examples.test.example_function'),
    ('help_object', 'help cli2.examples.test.example_object'),
    ('call_function_noargs', 'cli2.examples.test.example_function'),
    ('call_function', 'cli2.examples.test.example_function a b c=1 d=2'),
    ('call_method', 'cli2.examples.test.example_object.example_method a b=c'),
    ('call_object', 'cli2.examples.test.example_object_callable a b=1'),
])
def test_cli(name, command):
    autotest(f'tests/{name}.txt', 'cli2 ' + command)


def test_hide():
    autotest('tests/test_hide.txt', 'chttpx-example object find --help')


def test_load_module():
    ConsoleScript.names = []
    group = ConsoleScript()
    from cli2 import asyncio
    group.load_module(asyncio)
    assert 'async_resolve' in group


def test_load_module_str():
    ConsoleScript.names = []
    group = ConsoleScript()
    group.load_module('cli2.asyncio')
    assert 'async_resolve' in group


def test_load_object():
    class Lol:
        def __call__(self): pass  # noqa
    group = ConsoleScript()
    group.load_module(Lol())
    assert 'Lol' in group


@pytest.mark.parametrize('name,command', [
    ('alone', ''),
    ('help', 'help'),
    ('class_method', 'class_method 1'),
    ('instance_method', 'instance_method 1'),
    ('child_class_method', 'class_method 1'),
    ('child_instance_method', 'instance_method 1'),
])
def test_cli(name, command):
    autotest(f'tests/obj2_{name}.txt', 'cli2-example2 ' + command)
