import cli2

import pytest


@pytest.mark.parametrize('name,command', [
    ('cli2', ''),
    ('help', 'help'),
    ('help_debug', 'help debug'),
    ('run_help', 'run cli2.help'),
    ('run_help_debug', 'run cli2.help debug'),
    ('run_help_implicit', 'cli2.help'),
    ('run_module', 'cli2'),
    ('run_module_missing_attr', 'cli2.missing'),
    ('run_module_missing', 'missinggggggg.foo'),
    ('run_module_nodoc', 'test_cli2.test_cli2'),
    ('help_module', 'help cli2'),
    ('help_module_attr_notfound', 'help cli2.skipppp'),
    ('docmod', 'docmod cli2'),
    ('docmod_noargs', 'docmod'),
    ('docfile', 'docfile cli2.py'),
    ('docfile_missing', 'docfile cli2aoeuoeauoaeu.py'),
    ('debug', 'debug cli2.run to see=how -it --parses=me'),
])
def test_cli2(name, command):
    cli2.autotest(
        f'tests/{name}.txt',
        'cli2 ' + command,
    )


def test_autotest():
    cli2.autotest('tests/cli2_help.txt', 'cli2 help')


def test_importable_factory():
    importable = cli2.Importable.factory('cli2')
    assert importable.name == 'cli2'
    assert importable.module == cli2


def test_importable_get_callables():
    importable = cli2.Importable.factory('cli2')
    result = [*importable.get_callables()]
    assert cli2.Callable('run', cli2.run) in result
    assert cli2.Callable('help', cli2.help) in result


def test_config_default():
    def foo():
        pass
    assert cli2.Command('foo', foo).cli2['color'] == cli2.YELLOW


def test_config_override_on_target():
    def foo():
        pass
    foo.cli2 = dict(color=cli2.RED)
    config = cli2.Command('foo', foo).cli2
    assert config['color'] == cli2.RED


def test_config_override_on_command():
    class MyCommand(cli2.Command):
        cli2 = cli2.Config(color=cli2.RED)
    config = MyCommand('foo', lambda: True).cli2
    assert config['color'] == cli2.RED
