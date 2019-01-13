import os
import sys
from io import TextIOWrapper, BytesIO

import cli2


def save_result(self, result):
    self.__dict__.setdefault('_result', [])
    self._results.append(result)


def patch(console_script, result_handler):
    console_script.handle_result = result_handler.__get__(
        console_script, 
        type(console_script)
    )


def test_help():
    cli2.autotest('tests/cli2_help.txt', 'cli2', 'help')


def test_run_help():
    cli2.autotest('tests/cli2_help.txt', 'cli2', 'run', 'cli2.help')


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
