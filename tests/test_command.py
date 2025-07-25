import asyncio
import cli2
import cli2.test
import inspect
import pytest
import os
from unittest import mock


def test_int():
    def foo(one: int): return one
    cmd = cli2.Command(foo)
    cmd.parse('1')
    assert cmd['one'].value == 1
    assert not cmd['one'].accepts
    assert cmd('1') == 1
    assert repr(cmd['one']) == 'one'


def test_vararg():
    def foo(*one): return dict(result=one)
    cmd = cli2.Command(foo)
    cmd.parse('a', 'b')
    assert cmd['one'].value == ['a', 'b']
    assert cmd['one'].accepts
    assert cmd('a', 'b') == dict(result=('a', 'b'))


def test_kwarg():
    def foo(one=None): return one
    cmd = cli2.Command(foo, posix=False)
    cmd.parse('one=b')
    assert cmd['one'].value == 'b'
    assert not cmd['one'].accepts
    assert cmd('one=b') == 'b'


def test_kwarg_posix():
    def foo(one=None): return one
    cmd = cli2.Command(foo, posix=True)
    assert cmd('--one=b') == 'b'


def test_varkwarg():
    def foo(**one): return one
    cmd = cli2.Command(foo)
    cmd.parse('a=b', 'c=d')
    assert cmd['one'].value == dict(a='b', c='d')
    assert cmd['one'].accepts


def test_skip():
    def foo(a=None, b=None, c=None):
        return dict(result=(a, b, c))
    cmd = cli2.Command(foo)
    assert cmd('b=x') == dict(result=(None, 'x', None))

    cmd = cli2.Command(foo, posix=True)
    assert cmd('-b=x') == dict(result=(None, 'x', None))


def test_nested_typeerror():
    # Test that TypeError unrelated to top level function call are not
    # swallowed to display help
    def foo():
        raise TypeError('Lol')
    cmd = cli2.Command(foo)
    with pytest.raises(TypeError):
        cmd()


def test_vararg_varkwarg_natural():
    def foo(*one, **two): return dict(result=(one, two))
    cmd = cli2.Command(foo)
    cmd.parse('x', 'y', 'a=b', 'c=d')
    assert cmd['one'].value == ['x', 'y']
    assert cmd['two'].value == dict(a='b', c='d')
    assert cmd('x', 'y', 'a=b', 'c=d') == dict(
        result=(
            ('x', 'y'),
            dict(a='b', c='d'),
        )
    )


def test_vararg_varkwarg_asterisk():
    def foo(*one, **two): return (one, two)
    cmd = cli2.Command(foo)
    cmd.parse('*["x"]', '**{"y" :"z"}')
    assert cmd['one'].value == ['x']
    assert cmd['two'].value == dict(y='z')


def test_vararg_after_kwarg():
    def foo(one=None, *two): return (one, two)
    cmd = cli2.Command(foo)

    cmd.parse('x')
    assert cmd['one'].value == 'x'
    with pytest.raises(cli2.Cli2ValueError):
        cmd['two'].value


def test_positional_only_looksahead():
    def foo(one=None, /, *two, three=None, **kwargs):  # noqa
        return (one, two)
    cmd = cli2.Command(foo)

    cmd.parse('z=w', 'three=z', 'x', 'y')
    assert cmd['one'].value == 'x'
    assert cmd['two'].value == ['y']
    assert cmd['three'].value == 'z'
    # make sure it takes weird keywords too
    assert cmd['kwargs'].value['z'] == 'w'


def test_keyword_only():
    def foo(*one, two=None): return (one, two)
    cmd = cli2.Command(foo)

    cmd.parse('x')
    assert cmd['one'].value == ['x']
    assert cmd['two'].value is None


def test_bool():
    def foo(one: bool): return one
    cmd = cli2.Command(foo)

    cmd.parse('yes')
    assert cmd['one'].value is True
    assert not cmd['one'].accepts
    assert cmd('yes') is True

    for i in ('0', 'no', 'False'):
        cmd.parse(i)
        assert cmd['one'].value is False
        assert not cmd['one'].accepts
        assert cmd(i) is False


def test_bool_flag():
    def foo(one: bool): return one
    foo.cli2_one = dict(alias='-o')
    cmd = cli2.Command(foo)
    assert cmd['one'].alias == ('-o',)
    cmd.parse('-o')
    assert cmd['one'].value is True


def test_bool_flag_posix():
    def foo(fuzz=None, hi: bool = None): return hi
    cmd = cli2.Command(foo, posix=True)
    assert cmd('-nh') is False
    assert cmd('--no-hi') is False
    assert cmd('--hi') is True
    assert cmd('-h') is True


def test_bool_flag_negate():
    def foo(one: bool): return one
    foo.cli2_one = dict(alias='-o', negate='!o')
    cmd = cli2.Command(foo)
    cmd.parse('!o')
    assert cmd['one'].value is False


def test_bool_kwarg_negate():
    def foo(one: bool = True): return one
    cmd = cli2.Command(foo)
    assert cmd['one'].negates == ['no-one']

    cmd.parse('no-one')
    assert cmd.bound.arguments['one'] is False

    cmd.parse('one')
    assert cmd.bound.arguments['one'] is True

    cmd.posix = True
    assert cmd['one'].negates == ['-no', '--no-one']

    cmd.parse('--no-one')
    assert cmd.bound.arguments['one'] is False
    cmd.parse('--one')
    assert cmd.bound.arguments['one'] is True


def test_json_cast():
    import json
    def foo(one): return one
    foo.cli2_one = dict(cast=lambda v: json.loads(v))
    cmd = cli2.Command(foo)
    cmd.parse('[1]')
    assert cmd['one'].value == [1]


def test_further_search():
    def foo(a=None, one: bool = None): return one
    cmd = cli2.Command(foo)
    assert cmd['one'].match('one=yes') == 'yes'

    cmd.parse('one=yes')
    assert cmd['one'].value is True
    assert not cmd['one'].accepts
    assert cmd('one=yes') is True


def test_list():
    def foo(one: list = None): return dict(result=(one))
    cmd = cli2.Command(foo)
    assert cmd['one'].match('one=[1,2]') == '[1,2]'

    cmd.parse('one=[1,2]')
    assert cmd['one'].value == [1, 2]
    assert not cmd['one'].accepts

    assert cmd('one=[1,2]') == dict(result=[1, 2])
    assert cmd('[1,2]') == dict(result=[1, 2])

    # simple syntax for simple list of strings
    assert cmd('one=a,b') == dict(result=['a', 'b'])


def test_dict():
    def foo(one: dict = None): return one
    cmd = cli2.Command(foo)
    assert cmd['one'].match('one={"a": 1}') == '{"a": 1}'

    cmd.parse('one={"a": 1}')
    assert cmd['one'].value == {"a": 1}
    assert not cmd['one'].accepts

    assert cmd('one={"a": 1}') == {"a": 1}
    assert cmd('{"a": 1}') == {"a": 1}

    # simple syntax for simple dict of strings
    assert cmd('one=a:b,c:d') == {"a": "b", "c": "d"}


def test_override():
    def foo(one): return one
    foo.cli2 = dict(color=1, name='lol', doc='foodoc')
    cmd = cli2.Command(foo)
    assert cmd.color == 1
    assert cmd.name == 'lol'
    assert cmd.doc == 'foodoc'


def test_cast_override():
    def foo(one): return dict(result=one)
    foo.cli2_one = dict(cast=lambda v: [int(i) for i in v.split(',')])
    cmd = cli2.Command(foo)
    cmd.parse('1,2')
    assert cmd['one'].value == [1, 2]
    assert cmd('1,2') == dict(result=[1, 2])


def test_weird_pattern():
    # show off our algorithms weakness, while it's still fresh in my head :)
    def foo(a=None, b=None):
        return dict(result=(a, b))
    cmd = cli2.Command(foo)

    cmd.parse('b=x')
    assert cmd['b'].value == 'x'
    assert cmd('b=x') == dict(result=(None, 'x'))

    cmd = cli2.Command(foo)
    cmd.parse('a=b=x')
    assert cmd['a'].value == 'b=x'
    assert cmd('a=b=x') == dict(result=('b=x', None))


class Foo:
    def __call__(self, a: int, b: list, c: bool = False, *d, e=None, **f):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f


def test_mixed():
    cmd = cli2.Command(Foo())
    cmd('1', '[2]', 'yes', 'var1', 'var2', 'kw1=1', 'kw2=2')
    assert cmd.target.a == 1
    assert cmd.target.b == [2]
    assert cmd.target.c is True
    assert cmd.target.d == ('var1', 'var2')
    assert cmd.target.f == dict(kw1='1', kw2='2')


def test_mixed_posix():
    cmd = cli2.Command(Foo(), posix=True)
    cmd('1', '[2]', 'yes', 'var1', 'var2', '--kw1=1', '--kw2=2')
    assert cmd.target.a == 1
    assert cmd.target.b == [2]
    assert cmd.target.c is True
    assert cmd.target.d == ('var1', 'var2')
    assert cmd.target.f == dict(kw1='1', kw2='2')


def test_missing():
    def foo(missing):
        """docstring"""
    cmd = cli2.Command(foo, outfile=cli2.test.Outfile())
    cmd()
    assert 'missing 1 required' in cmd.outfile
    assert 'docstring' in cmd.outfile


def test_kwarg_priority():
    def foo(missing, **kwarg):
        """docstring"""
    cmd = cli2.Command(foo)
    cmd.parse('foo=bar')
    with pytest.raises(cli2.Cli2ValueError):
        cmd['missing'].value


def test_kwargs_find_their_values():
    def foo(*a, b: str = '', c: str = '', **d):
        """docstring"""
    cmd = cli2.Command(foo)
    cmd.parse('c=3', 'e=5', '1', 'b=2')
    assert cmd['a'].value == ['1']
    assert cmd['b'].value == '2'
    assert cmd['c'].value == '3'
    assert cmd['d'].value == dict(e='5')


def test_kwarg_priority_doesnt_break_positional():
    def foo(missing, **kwarg):
        return missing
    cmd = cli2.Command(foo, outfile=cli2.test.Outfile())
    cmd.parse('y', 'foo=bar')
    assert cmd['missing'].value == 'y'
    assert cmd['kwarg'].value == dict(foo='bar')

    # can't call foo("foo=bar") as such:
    cmd('foo=bar')
    assert "missing 1 required argument: missing" in cmd.outfile

    # needs to specify missing by name
    assert cmd('missing=foo=bar') == 'foo=bar'


def test_extra():
    cmd = cli2.Command(lambda: True, outfile=cli2.test.Outfile())
    cmd('a')
    assert 'No parameters for these' in cmd.outfile


def test_asyncio():
    async def test():
        return 'foo'

    class AsyncCommand(cli2.Command):
        async def post_call(self):
            return 'hi'

    cmd = AsyncCommand(test)
    assert cmd() == 'foo'
    assert cmd.post_result == 'hi'


def test_aliases():
    def foo(he_llo):
        pass
    foo.cli2_he_llo = dict(alias=['-h', '--he-llo'])

    cmd = cli2.Command(foo)
    assert cmd['he_llo'].aliases == ['-h', '--he-llo']
    cmd('-h=x')
    assert cmd['he_llo'].value == 'x'

    cmd('--he-llo=y')
    assert cmd['he_llo'].value == 'y'


def test_posix_style():
    def foo(he_llo=None):
        pass

    cmd = cli2.Command(foo, posix=True)
    assert cmd['he_llo'].alias == ['-h', '--he-llo']

    cmd.parse('-h=x')
    assert cmd['he_llo'].value == 'x'

    cmd('--he-llo=y')
    assert cmd['he_llo'].value == 'y'


def test_negates():
    def foo(he_llo=None):
        pass
    foo.cli2_he_llo = dict(negate=['nh', 'no-he_llo'])
    cmd = cli2.Command(foo)
    assert cmd['he_llo'].negates == ['nh', 'no-he_llo']
    cmd('nh')
    assert cmd['he_llo'].value is False


def test_posix_style_spaces():
    def foo(aa=None, *args): pass
    cmd = cli2.Command(foo, posix=True)
    cmd('--aa', 'foo', 'bar')
    assert cmd['aa'].value == 'foo'
    assert cmd['args'].value == ['bar']


def test_docstring():
    def foo(bar, lol):
        '''
        Do something

        Do something that will span over multiple lines if i find enough to
        type in this line.

        :param str bar: Some argument documentation that's unfortunnately going
                        to span over multiple lines
        :param lol:
            Another argument documentation that's unfortunnately going
            to span over multiple lines and without type annotation inside
        '''
    cmd = cli2.Command(foo)
    assert cmd['lol'].doc == (
        "Another argument documentation that's unfortunnately going"
        " to span over multiple lines and without type annotation inside"
    )
    assert cmd['bar'].doc == (
        "Some argument documentation that's unfortunnately going to span over"
        " multiple lines"
    )


def test_print():
    cmd = cli2.Command(lambda: True, outfile=mock.Mock())
    cmd.print('orange', 'foo', 'bar')
    assert cmd.outfile.write.call_args_list[0].args == (
        '\x1b[38;5;202mfoo bar\x1b[0m',
    )

    cmd = cli2.Command(lambda: True, outfile=mock.Mock())
    cmd.print('ORANGE', 'foo', 'bar')
    assert cmd.outfile.write.call_args_list[0].args == (
        '\x1b[1;38;5;202mfoo bar\x1b[0m',
    )

    # backward compatibility
    cmd = cli2.Command(lambda: True, outfile=mock.Mock())
    cmd.print('BLUE2', 'foo', 'bar')
    assert cmd.outfile.write.call_args_list[0].args == (
        '\x1b[1;38;5;75mfoo bar\x1b[0m',
    )


@pytest.mark.parametrize('name,command,env', [
    (
        'yourcmd_posix',
        'python src/cli2/cli2/examples/example.py',
        {},
    ),
    (
        'yourcmd_help',
        'python src/cli2/cli2/examples/example.py',
        {'POSIX': ''}
    ),
])
def test_help(name, command, env):
    cli2.test.autotest(f'tests/{name}.txt', command, env)


def test_arg_reorder():
    class TestCommand(cli2.Command):
        def call(self, *args, **kwargs):
            return (args, kwargs)

    cmd = TestCommand(lambda: True)
    cmd['vk'] = cli2.Argument(
        cmd,
        inspect.Parameter(
            'vk',
            inspect.Parameter.VAR_KEYWORD,
        )
    )
    cmd['vargs'] = cli2.Argument(
        cmd,
        inspect.Parameter(
            'varg',
            inspect.Parameter.VAR_POSITIONAL,
        )
    )
    cmd['kwarg'] = cli2.Argument(
        cmd,
        inspect.Parameter(
            'kwarg',
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    )
    cmd['kw'] = cli2.Argument(
        cmd,
        inspect.Parameter(
            'kw',
            inspect.Parameter.KEYWORD_ONLY,
        )
    )
    cmd['arg'] = cli2.Argument(
        cmd,
        inspect.Parameter(
            'arg',
            inspect.Parameter.POSITIONAL_ONLY,
        )
    )
    assert list(cmd.keys()) == ['arg', 'kwarg', 'vargs', 'kw', 'vk']
    cmd.parse('a')
    assert cmd['arg'].value == 'a'

    cmd.parse('a', 'b', 'c', 'd')
    assert cmd['arg'].value == 'a'
    assert cmd['kwarg'].value == 'b'
    assert cmd['vargs'].value == ['c', 'd']


def test_arg():
    cmd = cli2.Command(lambda foo: foo)
    cmd.arg('bar', position=0)
    assert list(cmd.keys()) == ['bar', 'foo']
    assert cmd('bar', 'foo') == 'foo'
    assert cmd['bar'].value == 'bar'
    del cmd['bar']
    cmd.help()


def test_helphack():
    class TestCommand(cli2.Command):
        def help(self):
            self.help_shown = True

    def foo(*one): return one
    cmd = TestCommand(foo)
    cmd('a', 'b', '--help')
    assert cmd.exit_code == 1
    assert getattr(cmd, 'help_shown', False)

    cmd = TestCommand(foo, help_hack=False)
    cmd('a', 'b', '--help')
    assert cmd.exit_code == 0
    assert not getattr(cmd, 'help_shown', False)


def test_generator(capsys):
    def foo():
        yield 'foo'
    cmd = cli2.Command(foo)
    result = cmd()
    assert result is None
    captured = capsys.readouterr()
    assert captured.out == '\x1b[38;5;141mfoo\x1b[39m\n'


async def async_factory():
    return 'autoval'


def non_async_factory():
    return 'autoval'


@pytest.mark.parametrize('factory, isasync', (
    (async_factory, True),
    (non_async_factory, False),
))
def test_factory(factory, isasync):
    class Foo:
        @cli2.arg('self', factory=lambda cmd, arg: Foo())
        @cli2.arg('auto', factory=factory)
        def test(self, auto, arg):
            return dict(result=(auto, arg))

    cmd = cli2.Command(Foo.test)
    assert cmd.async_mode() == isasync
    assert cmd('hello') == dict(result=('autoval', 'hello'))


def test_factory_async():
    async def get_stuff():
        return 'stuff'

    class Foo:
        @cli2.arg('self', factory=lambda cmd, arg: Foo())
        @cli2.arg('auto', factory=lambda: 'autoval')
        @cli2.arg('afact', factory=get_stuff)
        @cli2.arg('afact2', factory=get_stuff)
        async def test(self, auto, arg, afact, afact2):
            return auto, arg, afact, afact2

    class AsyncCommand(cli2.Command):
        async def post_call(self):
            yield 'hello'

    cmd = AsyncCommand(Foo.test)
    assert cmd('hello') == ('autoval', 'hello', 'stuff', 'stuff')
    assert cmd.post_result == ['hello']


def test_async_resolve():
    async def foo():
        yield 'bar'

    async def test():
        return foo()

    cmd = cli2.Command(test)
    cmd()


def test_async_yield(capsys):
    async def async_yield():
        yield 'foo'

    cmd = cli2.Command(async_yield)
    assert cmd() is None
    captured = capsys.readouterr()
    assert captured.out == '\x1b[38;5;141mfoo\x1b[39m\n'


def test_async_iter(capsys):
    class Foo:
        async def __aiter__(self):
            yield 'foo'

    async def async_iter():
        return Foo()

    cmd = cli2.Command(async_iter)
    assert cmd() is None
    captured = capsys.readouterr()
    assert captured.out == '\x1b[38;5;141mfoo\x1b[39m\n'


def test_class_method():
    def factory():
        return Foo()

    class Foo:
        @classmethod
        @cli2.arg('cls', factory=factory)
        def bar(cls, foo):
            return foo

        @classmethod
        def foo(cls, foo):
            return foo

    cmd = cli2.Command(Foo.bar)
    assert cmd['cls'].factory == factory
    assert cmd('x') == 'x'

    cmd = cli2.Command(Foo.foo)
    assert cmd('a') == 'a'


def test_self():
    def factory():
        return Foo(2)

    class Foo:
        def __init__(self, x):
            self.x = x

        @cli2.arg('self', factory=factory)
        def bar(self, foo):
            return self.x, foo

        def foo(self, foo):
            return self.x, foo

    cmd = cli2.Command(Foo.bar)
    assert cmd['self'].factory == factory
    assert cmd('x') == (2, 'x')

    group = cli2.Group(overrides=dict(self=dict(factory=lambda: Foo(1))))
    group.cmd(Foo.foo)
    assert group['foo']('a') == (1, 'a')
    assert group['foo']['self'].factory


def test_cli2():
    def test(some, _cli2=None):
        return some, _cli2

    cmd = cli2.Command(test)
    assert cmd('x') == ('x', cmd)


def test_keyboard_interrupt():
    def func():
        raise KeyboardInterrupt()

    cmd = cli2.Command(func)
    cmd()
    assert cmd.exit_code == 1


def test_keyboard_interrupt_async():
    class YourCommand(cli2.Command):
        async def post_call(self):
            return 'foo'

    async def foo():
        raise KeyboardInterrupt()

    async def func():
        await asyncio.gather(foo())

    cmd = YourCommand(func)
    cmd()
    assert cmd.exit_code == 1
    assert cmd.post_result == 'foo'


def test_factory_value_args():
    def myfactory(foo):
        return foo

    @cli2.arg('bar', factory=myfactory)
    def mycmd(foo, bar):
        return foo

    cmd = cli2.Command(mycmd)
    assert cmd('a') == 'a'
