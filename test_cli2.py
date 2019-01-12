import cli2


def test_importable_factory():
    importable = cli2.Importable.factory('cli2')
    assert importable.name == 'cli2'
    assert importable.module == cli2


def test_importable_get_callables():
    importable = cli2.Importable.factory('cli2')
    result = [*importable.get_callables()]
    assert result == [cli2.Callable('help', cli2.help)]
