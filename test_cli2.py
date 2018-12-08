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
    ]
    assert group.commands['run'].target == 'cli2_example.run'


def test_group_command_alias():
    group = cli2.Group('a', [
        Bunch(
            module_name='cli2.run',
            name='a b',
            attrs=None
        )
    ])
    assert len(list(group.commands.keys())) == 1
    assert group.commands['a b'].line == 'a b'
    assert group.commands['a b'].target == 'cli2.run'


def test_path_resolve_callable():
    path = cli2.Path('cli2.run')
    assert path.module == cli2
    assert path.callable == cli2.run


def test_path_resolve_module():
    path = cli2.Path('cli2')
    assert path.module == cli2
    assert path.callable == None


def test_path_resolve_nested_attribute():
    path = cli2.Path('cli2_example.Foo.bar.baz.0')
    assert path.callable == cli2_example.Foo.bar['baz'][0]
    assert path.module == cli2_example


def test_path_unresolvable():
    path = cli2.Path('cli2.aoeuaoeuaoeu')
    assert path.module == cli2
    assert path.callable == None


@pytest.mark.parametrize('fixture', ['cli2', 'cli2.run', 'cli2.MISSING'])
def test_path_module_name(fixture):
    path = cli2.Path(fixture)
    assert path.module_name == 'cli2'


def test_path_module_callables():
    path = cli2.Path('cli2.run')
    assert 'console_script' not in path.module_callables
    assert 'run' in path.module_callables


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
