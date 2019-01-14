import cli2


def test_importable_factory():
    importable = cli2.Importable.factory('cli2')
    assert importable.name == 'cli2'
    assert importable.module == cli2


def test_importable_get_callables():
    importable = cli2.Importable.factory('cli2')
    result = [*importable.get_callables()]
    assert cli2.Callable('run', cli2.run) in result
    assert cli2.Callable('help', cli2.help) in result


def test_command_color_default():
    def foo():
        pass
    assert cli2.Callable('foo', foo).color == cli2.YELLOW
