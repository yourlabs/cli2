from .command import Command
from .group import Group
from .test import Outfile


def test_group_command_not_found():
    group = Group(outfile=Outfile())
    group('a', 'b')
    assert 'Command a not found' in group.outfile


def test_group_subcommand_not_found():
    group = Group(outfile=Outfile())
    group['a'] = Group(name='a')
    group('a', 'b')
    assert 'Command b not found' in group.outfile


def test_group_no_command():
    group = Group(outfile=Outfile())
    group()
    assert 'No sub-command' in group.outfile


def test_missing_arg():
    cmd = Group(outfile=Outfile()).add(lambda b: True, name='a')
    cmd('a')
    assert "missing 1 required positional argument: 'b'" in cmd.outfile


def test_repr():
    assert repr(Group('foo')) == 'Group(foo)'


def test_help():
    def foo():
        """foodoc"""

    group = Group('lol', doc='loldoc', outfile=Outfile())
    group.add(foo)
    group()
    assert 'foodoc' in group.outfile
    assert 'loldoc' in group.outfile

    group.outfile.reset()
    group('help')
    assert 'foodoc' in group.outfile

    group.outfile.reset()
    group('help', 'foo')
    assert 'foodoc' in group.outfile

    group.outfile.reset()
    group('help', 'lol')
    assert 'not found' in group.outfile


def test_help_nested():
    def c(): 'cdoc'
    a = Group('a', outfile=Outfile())
    b = a.group('b')
    b.cmd(c)

    a('help', 'b', 'c')
    assert 'cdoc' in a.outfile

    a.outfile.reset()
    a('b', 'help', 'c')
    assert 'cdoc' in a.outfile


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


class TestCmd(Command):
    pass


def example():
    pass


def test_cmd_cls():
    group = Group()
    group.cmd(cls=TestCmd)(example)
    assert isinstance(group['example'], TestCmd)


def test_group_cmdclass():
    group = Group(cmdclass=TestCmd)
    group.cmd()(example)
    assert isinstance(group['example'], TestCmd)
    assert not isinstance(group['help'], TestCmd)
