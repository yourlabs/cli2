from .group import Group


def test_group_command_not_found():
    assert 'Command a not found' in Group()(['a', 'b'])


def test_group_subcommand_not_found():
    group = Group()
    group['a'] = Group(name='a')
    assert 'Command b not found' in group(['a', 'b'])


def test_group_no_command():
    assert 'No command' in Group()([])


def test_missing_arg():
    cmd = Group().cmd(lambda b: True, name='a')
    assert "missing 1 required positional argument: 'b'" in cmd(['a'])
