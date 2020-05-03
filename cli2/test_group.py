from .group import Group


def test_group_command_not_found():
    assert 'Command a not found' in Group()('a', 'b')


def test_group_subcommand_not_found():
    group = Group()
    group['a'] = Group(name='a')
    assert 'Command b not found' in group('a', 'b')


def test_group_no_command():
    assert 'No sub-command' in Group()()


def test_missing_arg():
    cmd = Group().add(lambda b: True, name='a')
    assert "missing 1 required positional argument: 'b'" in cmd('a')


def test_repr():
    assert repr(Group('foo')) == 'Group(foo)'


def test_help():
    def foo():
        """foodoc"""
    group = Group('lol', doc='loldoc')
    group.add(foo)
    assert 'foodoc' in group()
    assert 'loldoc' in group()
    assert 'foodoc' in group('help')
    assert 'foodoc' in group('help', 'foo')
    assert 'not found' in group('help', 'lol')


def test_help_nested():
    def c(): 'cdoc'
    a = Group('a')
    b = a.group('b')
    b.cmd(c)
    assert 'cdoc' in a('help', 'b', 'c')
    assert 'cdoc' in a('b', 'help', 'c')


def test_load_module():
    from cli2 import test_group
    group = Group()
    group.load(test_group)
    assert 'test_load_module' in group


def test_load_module_str():
    group = Group()
    group.load('cli2.test_group')
    assert 'test_load_module' in group


def test_load_object():
    class Lol:
        def __call__(self): pass  # noqa
    group = Group()
    group.load(Lol())
    assert 'Lol' in group


def test_posix_group():
    def foo():
        """foodoc"""
    group = Group(posix=True)
    group.add(foo)
    assert group.posix
    assert group['foo'].posix
