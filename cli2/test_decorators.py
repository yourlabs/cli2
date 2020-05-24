from .argument import Argument
from .command import Command
from .group import Group
from .decorators import cmd, arg


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
        return x

    command = Command(foo)
    assert isinstance(command['x'], MyArgument)
    assert command('1,2') == [1, 2]


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
