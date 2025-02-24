import cli2
import functools
import cli2.test


def test_group_command_not_found():
    group = cli2.Group(outfile=cli2.test.Outfile())
    group('a', 'b')
    assert 'Command a not found' in group.outfile


def test_group_subcommand_not_found():
    group = cli2.Group(outfile=cli2.test.Outfile())
    group['a'] = cli2.Group(name='a')
    group('a', 'b')
    assert 'Command b not found' in group.outfile


def test_group_no_command():
    group = cli2.Group(outfile=cli2.test.Outfile())
    group()
    assert 'No sub-command' in group.outfile


def test_missing_arg():
    cmd = cli2.Group(outfile=cli2.test.Outfile()).add(lambda b: True, name='a')
    cmd('a')
    assert "missing 1 required argument: b" in cmd.outfile


def test_repr():
    assert repr(cli2.Group('foo')) == 'Group(foo)'


def test_help():
    def foo():
        """foodoc"""

    group = cli2.Group('lol', doc='loldoc', outfile=cli2.test.Outfile())
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
    assert group.outfile.out.endswith("le faux texte\n")
    group.outfile.reset()
    group('help', 'test')


def test_help_nested():
    def c(): 'cdoc'
    a = cli2.Group('a', outfile=cli2.test.Outfile())
    b = a.group('b')
    b.cmd(c)

    a('help', 'b', 'c')
    assert 'cdoc' in a.outfile

    a.outfile.reset()
    a('b', 'help', 'c')
    assert 'cdoc' in a.outfile


def test_posix_group():
    def foo():
        """foodoc"""
    group = cli2.Group(posix=True)
    group.add(foo)
    assert group.posix
    assert group['foo'].posix


class CommandSubject(cli2.Command):
    pass


def example():
    pass


def test_cmd_cls():
    group = cli2.Group()
    group.cmd(cls=CommandSubject)(example)
    assert isinstance(group['example'], CommandSubject)


def test_group_cmdclass():
    group = cli2.Group(cmdclass=CommandSubject)
    group.cmd()(example)
    assert isinstance(group['example'], CommandSubject)
    assert not isinstance(group['help'], CommandSubject)


def test_inject():
    outer = cli2.Group(name="outer")
    inner = cli2.Group()
    outer["inner"] = inner
    assert inner.name == "inner"


def test_group_cmdclass_override():
    class MyCmd(cli2.Command):
        pass

    outer = cli2.Group(name="outer")
    inner = outer.group("test", cmdclass=MyCmd)
    assert inner.cmdclass == MyCmd


def test_factories():
    """ Test group level factories """

    # test takes factory by default
    group = cli2.Group(name='test')

    def test(foo):
        return foo
    group.overrides['foo']['factory'] = lambda: 1

    group.cmd(test)
    assert group['test']() == 1

    def test2(foo):
        return foo
    # test explicit factory wins
    test2.cli2_foo = dict(factory=lambda: 2)

    group.cmd(test2)
    assert group['test2']() == 2

    # test the example in documentation
    cli = cli2.Group('foo')
    cli.overrides['self']['factory'] = lambda: Foo.factory()

    class Foo:
        def __init__(self, x=None):
            self.x = x

        @classmethod
        def factory(cls):
            return cls()

        @cli.cmd
        def send(self, something):
            return self, something

        @cli.cmd
        # this should always have priority
        @cli.arg('self', factory=lambda: Foo(3))
        def other(self, something):
            return self.x, something

    self, something = cli['send'](1)
    assert isinstance(self, Foo)
    assert something == 1

    assert cli['other'](4) == (3, 4)


def test_overrides():
    group = cli2.Group('foo')
    group.overrides['self']['factory'] = lambda: 1
    assert group.overrides['self']['factory']() == 1


def test_load():
    class BarMetaclass(type):
        @property
        def fails3(self):
            raise Exception('fails')

    class Bar(metaclass=BarMetaclass):
        @cli2.cmd
        def test(self):
            pass

        @classmethod
        @cli2.cmd
        def classmeth(cls, arg):
            return cls, arg

    class Foo(Bar):
        def bar(self):
            pass

        @cli2.cmd
        def test2(self):
            return self

        @cli2.cmd(condition=lambda cls: False)
        def exclude(self):
            pass

        @property
        def fails(self):
            raise Exception('Loading should not eval properties')

        @functools.cached_property
        def fails2(self):
            raise Exception('Loading should not eval properties')

    group = cli2.Group()
    group.load(Foo)
    assert list(group.keys()) == ['help', 'test', 'classmeth', 'test2']

    group = cli2.Group(overrides=dict(self=dict(factory=lambda: Foo())))
    group.load(Foo())
    assert list(group.keys()) == ['help', 'classmeth', 'test', 'test2']

    assert isinstance(group['test2'](), Foo)

    class Child(Foo):
        test2 = None

    group = cli2.Group()
    group.load(Child)
    assert list(group.keys()) == ['help', 'test', 'classmeth']

    group = cli2.Group(overrides=dict(cls=dict(factory=lambda: Child)))
    group.load(Child())
    assert list(group.keys()) == ['help', 'classmeth', 'test']
    assert group['classmeth'](1) == (Child, 1)
