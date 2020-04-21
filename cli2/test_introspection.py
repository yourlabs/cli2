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


def test_callable_object():
    result = cli2.Callable.factory('cli2.console_script.ConsoleScript.singleton')
    assert result.target == cli2.ConsoleScript.singleton
    assert not result.required_args
    assert [*result.get_callables()]


def test_boundmethod():
    result = cli2.Callable.factory(
        'cli2.console_script.ConsoleScript.singleton.result_handler'
    )
    assert result.target == cli2.ConsoleScript.singleton.result_handler
    assert result.required_args == ['result']
    assert not [*result.get_callables()]


def test_callable_function():
    from cli2.cli import run
    result = cli2.Callable.factory('cli2.cli.run')
    assert result.target == run
    assert result.required_args
    assert not [*result.get_callables()]


def test_callable_function_async():
    async def foo():
        pass

    assert cli2.Callable('foo', foo).is_async


def test_callable_object_async():
    class Foo:
        async def __call__(self):
            pass
    assert cli2.Callable('foo', Foo()).is_async
