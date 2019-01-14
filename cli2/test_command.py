from .command import command, option


def test_command_decorator_alone():
    @command(color='test')
    def foo():
        pass

    assert foo.cli2.color == 'test'


def test_option_decorator_alone():
    @option('bar', color='test')
    def foo():
        pass

    assert foo.cli2.options['bar'].color == 'test'


def test_chain():
    @option('bar', color='barcolor')
    @command(color='commandcolor')
    @option('foo', color='foocolor')
    def foo():
        pass

    assert foo.cli2.options['bar'].color == 'barcolor'
    assert foo.cli2.options['foo'].color == 'foocolor'
    assert foo.cli2.color == 'commandcolor'

    # try overriding a command attribute
    command(color='test')(foo)
    assert foo.cli2.color == 'test'
    # should not have removed any option
    assert foo.cli2.options['foo'].color == 'foocolor'
