import cli2


class YourThingCommand(cli2.Command):
    def call(self):
        self.target.is_CLI = True
        return self.target(*self.bound.args, **self.bound.kwargs)


class MyArgument(cli2.Argument):
    def cast(self, value):
        return [int(i) for i in value.split(',')]


def test_cmd():
    @cli2.cmd(some='thing')
    def foo(): pass
    assert foo.cli2['some'] == 'thing'


def test_cmd_cls():
    class MyCommand(cli2.Command):
        pass

    @cli2.cmd(cls=MyCommand)
    def foo(): pass
    assert isinstance(cli2.Command(foo), MyCommand)


def test_cmd_obj_cls():
    @cli2.cmd(cls=YourThingCommand)
    class YourThing:
        def __call__(self):
            pass

    # try class based
    assert isinstance(cli2.Command(YourThing), YourThingCommand)

    # now object based
    target = YourThing()
    command = cli2.Command(target)
    assert isinstance(command, YourThingCommand)
    command()
    assert target.is_CLI


def test_command_cmd():
    @YourThingCommand.cmd(name='lol')
    class YourThing:
        def __call__(self):
            pass

    # try class based
    assert isinstance(cli2.Command(YourThing), YourThingCommand)
    assert cli2.Command(YourThing).name == 'lol'


def test_command_cmd_noargs():
    @YourThingCommand.cmd
    class YourThing:
        def __call__(self):
            pass
    assert isinstance(cli2.Command(YourThing), YourThingCommand)


def test_arg():
    @cli2.arg('x', color='y')
    def foo(x): pass
    assert foo.cli2_x['color'] == 'y'


def test_arg_cls():
    @cli2.arg('x', cls=MyArgument)
    def foo(x):
        return dict(result=x)

    command = cli2.Command(foo)
    assert isinstance(command['x'], MyArgument)
    assert command('1,2') == dict(result=[1, 2])


def test_group_cmd():
    group = cli2.Group()

    @group.cmd
    def bar(): pass
    assert group['bar'].target == bar


def test_group_arg():
    group = cli2.Group()

    @group.cmd
    @group.arg('x', doc='lol')
    def bar(x): pass
    assert group['bar']['x'].doc == 'lol'


def test_group_cmd_and_cmd():
    group = cli2.Group()

    @group.cmd(name='x')
    @cli2.cmd(name='y')
    def foo(): pass

    assert group['x'].target == foo
    assert cli2.Command(foo).name == 'y'


def test_default():
    @cli2.arg('aa', default='test')
    def foo(aa): return aa
    cmd = cli2.Command(foo)
    assert cmd() == 'test'
