import sys

from types import ModuleType

from unittest.mock import Mock

from bunch import Bunch

import cli2
import cli2_example

import pytest


def test_command_factory_cli2_example():
    group = cli2.Group('cli2-example')
    assert list(group.commands.keys()) == [
        'alias',
        'dead',
        'run',
        'cli2-example',
        'help',
    ]
    assert group.commands['run'].target == 'cli2_example.run'


def test_command_call():
    cmd = cli2.Command(
        '* = cli2.help:cli2_example',
        'cli2.help',
        ['cli2-example']
    )
    cmd.path.callable = Mock()
    cmd()
    cmd.path.callable.assert_called_once_with('cli2-example')


def test_group_command_alias():
    group = cli2.Group('a', [
        Bunch(
            module_name='cli2.run',
            name='a b',
            attrs=None
        )
    ])
    assert len(list(group.commands.keys())) == 2
    assert group.commands['a b'].line == 'a b'
    assert group.commands['a b'].target == 'cli2.run'


def test_group_doc():
    group = cli2.Group('cli2-example')
    #assert group.doc_short == 'Example cli2 compatible module.'
    assert group.doc == '''
Example cli2 compatible module.

Dummy script used for demonstration and testing purposes.
'''.lstrip()


def test_path_resolve_callable():
    path = cli2.Path('cli2.run')
    assert path.module == cli2
    assert path.callable == cli2.run


def test_path_resolve_module():
    path = cli2.Path('cli2')
    assert path.module == cli2
    assert path.callable is None


def test_path_empty_string():
    path = cli2.Path('')
    assert path.module is None


def test_path_resolve_nested_attribute():
    path = cli2.Path('cli2_example.Foo.bar.baz.0')
    assert path.callable == cli2_example.Foo.bar['baz'][0]
    assert path.module == cli2_example


def test_path_resolve_submodule():
    package = ModuleType('package')
    package.__file__ = 'package/__init__.py'
    sys.modules[package.__name__] = package
    module = ModuleType('module')
    module.__file__ = 'package/module.py'
    sys.modules['.'.join((package.__name__, module.__name__))] = module
    module.foo = lambda: True

    path = cli2.Path('package.module.foo')
    assert path.module == module
    assert path.callable == module.foo


def test_path_unresolvable():
    path = cli2.Path('cli2.aoeuaoeuaoeu')
    assert path.module == cli2
    assert path.callable is None


@pytest.mark.parametrize('fixture', ['cli2', 'cli2.run', 'cli2.MISSING'])
def test_path_module_name(fixture):
    path = cli2.Path(fixture)
    assert path.module_name == 'cli2'


def test_path_module_callables():
    path = cli2.Path('cli2.run')
    assert 'console_script' not in path.module_callables
    assert 'run' in path.module_callables


def test_path_module_docstring():
    assert 'Example' in cli2.Path('cli2_example').module_docstring


def test_path_callable_docstring():
    assert 'Test' in cli2.Path('cli2_example.test').callable_docstring


def test_path_docstring():
    assert 'Example' in cli2.Path('cli2_example').docstring
    assert 'Test' in cli2.Path('cli2_example.test').docstring


def test_path_str():
    assert 'cli2_example.test' == str(cli2.Path('cli2_example.test'))


def test_consolescript_valid_command_with_args():
    cs = cli2.ConsoleScript(['/cli2', 'run', 'foo.bar'])
    assert str(cs.command) == 'cli2.run'
    assert cs.command.path.module == cli2
    assert cs.command.path.callable == cli2.run
    assert cs.argv_extra == ['foo.bar']


def test_parser_init():
    parser = cli2.Parser(['a', 'b=c', '-d', '--e=g'])
    assert parser.funcargs == ['a']
    assert parser.funckwargs == dict(b='c')
    assert parser.dashargs == ['d']
    assert parser.dashkwargs == dict(e='g')


@pytest.mark.parametrize('fixture', [
    ['aoeu'],
    ['help', 'aoeu'],
    [],
])
def test_console_script_resolve_help(fixture):
    cs = cli2.ConsoleScript(['/cli2-example'] + fixture)
    assert str(cs.command.target) == 'cli2.help'


def test_console_script_resolve():
    cs = cli2.ConsoleScript(['cli2-example', 'run'])
    assert str(cs.command.target) == f'cli2_example.run'


def test_console_script_resolve_alias():
    cs = cli2.ConsoleScript(['cli2-example', 'alias'])
    assert str(cs.command.target) == f'cli2_example.test'


def test_docfile():
    assert 'callback' in cli2.docfile('cli2.py')


def test_docfile_none():
    assert cli2.docfile('test_cli2.py') is None


def test_help_callable():
    assert 'Docstring for cli2.help' in list(cli2.help('cli2.help'))


def test_help_module():
    return
    assert ' '.join(list(cli2.help('cli2'))) == '''
cli2 makes your python callbacks work on CLI too !

cli2 provides sub-commands to introspect python modules or callables docstrings
or to execute callables or help working with cli2 itself.
'''.lstrip()
