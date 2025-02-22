import cli2


def test_retrieve():
    result = cli2.retrieve('cli2')
    assert isinstance(result, cli2.EntryPoint)
    assert result.name == 'cli2'
    assert result.path == 'cli2'

    result = cli2.retrieve('cli2-example nested nested')
    assert result.path == 'cli2-example nested nested'
    assert isinstance(result, cli2.Group)

    result = cli2.retrieve('cli2-example post')
    assert result.path == 'cli2-example post'
    assert isinstance(result, cli2.Command)
