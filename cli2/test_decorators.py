from .argument import Argument
from .command import Command
from .group import Group
from .decorators import cmd, arg, factories


class YourThingCommand(Command):
    def call(self):
        self.target.is_CLI = True
        return self.target(*self.bound.args, **self.bound.kwargs)


class MyArgument(Argument):
    def cast(self, value):
        return [int(i) for i in value.split(',')]


def test_cmd():
    @cmd(some='thing')
    def foo(): pass
    assert foo.cli2['some'] == 'thing'


def test_cmd_cls():
    class MyCommand(Command):
        pass

    @cmd(cls=MyCommand)
    def foo(): pass
    assert isinstance(Command(foo), MyCommand)


def test_cmd_obj_cls():
    @cmd(cls=YourThingCommand)
    class YourThing:
        def __call__(self):
            pass

    # try class based
    assert isinstance(Command(YourThing), YourThingCommand)

    # now object based
    target = YourThing()
    command = Command(target)
    assert isinstance(command, YourThingCommand)
    command()
    assert target.is_CLI


def test_command_cmd():
    @YourThingCommand.cmd(name='lol')
    class YourThing:
        def __call__(self):
            pass

    # try class based
    assert isinstance(Command(YourThing), YourThingCommand)
    assert Command(YourThing).name == 'lol'


def test_command_cmd_noargs():
    @YourThingCommand.cmd
    class YourThing:
        def __call__(self):
            pass
    assert isinstance(Command(YourThing), YourThingCommand)


def test_arg():
    @arg('x', color='y')
    def foo(x): pass
    assert foo.cli2_x['color'] == 'y'


def test_arg_cls():
    @arg('x', cls=MyArgument)
    def foo(x):
        return dict(result=x)

    command = Command(foo)
    assert isinstance(command['x'], MyArgument)
    assert command('1,2') == dict(result=[1, 2])


def test_group_cmd():
    group = Group()

    @group.cmd
    def bar(): pass
    assert group['bar'].target == bar


def test_group_arg():
    group = Group()

    @group.cmd
    @group.arg('x', doc='lol')
    def bar(x): pass
    assert group['bar']['x'].doc == 'lol'


def test_group_cmd_and_cmd():
    group = Group()

    @group.cmd(name='x')
    @cmd(name='y')
    def foo(): pass

    assert group['x'].target == foo
    assert Command(foo).name == 'y'


def test_default():
    @arg('aa', default='test')
    def foo(aa): return aa
    cmd = Command(foo)
    assert cmd() == 'test'


def test_factories_simple():
    @factories
    class Foo:
        def bar(self, a):
            return a

        @classmethod
        def x(cls, b):
            return b

    assert Foo.bar.cli2_self['factory']
    assert Foo.x.cli2_cls['factory']

    bar = Command(Foo.bar)
    assert bar.keys() == ['a']
    assert bar(1) == 1

    foo = Command(Foo.x)
    assert foo.keys() == ['b']
    assert foo(1) == 1


def test_factories_args():
    @factories(a=lambda: 1, b='factory')
    class Foo:
        @classmethod
        async def factory(cls):
            return 'fact'

        def bar(self, a):
            return a

        @classmethod
        def x(cls, b):
            return b

    assert Foo.bar.cli2_self['factory']
    assert Foo.x.cli2_cls['factory']

    bar = Command(Foo.bar)
    assert not bar.keys()
    assert bar() == 1

    foo = Command(Foo.x)
    assert not foo.keys()
    assert foo() == 'fact'
