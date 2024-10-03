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
    assert "missing 1 required argument: b" in cmd.outfile


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

    group.group(
        "test",
        doc="""
        Le Lorem Ipsum est simplement du faux texte employé dans la composition
        et la mise en page avant impression. Le Lorem Ipsum est le faux texte

        standard de l'imprimerie depuis les années 1500, quand un imprimeur
        anonyme assembla ensemble des morceaux de texte pour réaliser un livre
        applications de mise en page de texte, comme Aldus PageMaker.
        """
    )
    group.outfile.reset()
    group('help')
    assert group.outfile.out.endswith("impression\n")
    group.outfile.reset()
    group('help', 'test')


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


class CommandSubject(Command):
    pass


def example():
    pass


def test_cmd_cls():
    group = Group()
    group.cmd(cls=CommandSubject)(example)
    assert isinstance(group['example'], CommandSubject)


def test_group_cmdclass():
    group = Group(cmdclass=CommandSubject)
    group.cmd()(example)
    assert isinstance(group['example'], CommandSubject)
    assert not isinstance(group['help'], CommandSubject)


def test_inject():
    outer = Group(name="outer")
    inner = Group()
    outer["inner"] = inner
    assert inner.name == "inner"


def test_group_cmdclass_override():
    class MyCmd(Command):
        pass

    outer = Group(name="outer")
    inner = outer.group("test", cmdclass=MyCmd)
    assert inner.cmdclass == MyCmd
