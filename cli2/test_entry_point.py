import cli2
from cli2.entry_point import EntryPoint
from cli2.group import Group
from cli2.command import Command


def test_retrieve():
    result = cli2.retrieve('cli2')
    assert isinstance(result, EntryPoint)
    assert result.name == 'cli2'
    assert result.path == 'cli2'

    result = cli2.retrieve('cli2-example nested nested')
    assert result.path == 'cli2-example nested nested'
    assert isinstance(result, Group)

    result = cli2.retrieve('cli2-example post')
    assert result.path == 'cli2-example post'
    assert isinstance(result, Command)
