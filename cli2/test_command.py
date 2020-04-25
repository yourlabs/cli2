from cli2 import cast, Command, Group, Argument

import pytest



def test_asyncio():
    async def test():
        return 'foo'
    assert Command(test)([]) == 'foo'


def test_group_command_not_found():
    assert 'Command a not found' in Group()(['a', 'b'])


def test_group_subcommand_not_found():
    group = Group()
    group['a'] = Group(name='a')
    assert 'Command b not found' in group(['a', 'b'])


def test_group_no_command():
    assert 'No command' in Group()([])


def test_missing_arg():
    cmd = Group().add_command(lambda b: True, name='a')
    assert 'Missing required args: b' in cmd(['a'])


def test_extra_args():
    cmd = Command(lambda: True)
    assert 'Extra args: b' in cmd(['b'])


def test_unknown_kwarg():
    cmd = Command(lambda: True)
    assert 'Extra args: c=d' in cmd(['c=d'])


def test_kwarg_looking_arg():
    cmd = Command(lambda a: a)
    assert cmd(['b=c']) == 'b=c'


@pytest.mark.parametrize('args', [
    ['c', 'b=d'],
    ['a=c', 'b=d'],
    ['b=d', 'a=c'],
])
def test_args_parse_basic(args):
    """Convert all argv to kwargs properly"""
    cmd = Command(lambda a, c=None, b=None: 1)
    cmd.parse(*args)
    assert cmd.defaults == dict(c=None, b=None)
    assert cmd.vars == dict(a='c', b='d')
    assert cmd.args == ['c']
    assert cmd.kwargs == dict(b='d')
    assert repr(cmd) == 'Command(<lambda>)'


def test_reminder():
    """Collect extra args properly"""
    cmd = Command(lambda a: 1)
    cmd.parse(*['-a', '-b'])
    assert cmd.vars == {'a': '-a'}
    assert cmd.reminder == ['-b']


def test_varargs():
    """Varargs parsed into list kwarg"""
    cmd = Command(lambda a, *b: 1)
    cmd.parse('1', '2', '3')
    assert cmd.vars == dict(a='1', b=['2', '3'])
    assert cmd.args == ['1', '2', '3']


@pytest.mark.parametrize('args', [
    ['a=b', '1', '2', 'c=d', 'r'],
    ['a=b', '1', 'c=d', '2', 'r'],
    ['1', '2', 'c=d', 'a=b', 'r'],
])
def test_varkwargs(args):
    """Support **kwargs"""
    cmd = Command(lambda e, i=None, **a: 1)
    cmd.parse(*args)
    assert cmd.vars == {'a': 'b', 'c': 'd', 'e': '1', 'i': '2'}
    assert cmd.args == ['1', '2']
    assert cmd.kwargs == {'a': 'b', 'c': 'd'}
    assert cmd.defaults == dict(i=None)
    assert cmd.reminder == ['r']


def test_list_single_arg():
    """Support list type annotation for single argument"""
    def foo(a: list): pass
    cmd = Command(foo)
    cmd.parse('b')
    assert cmd.vars['a'] == ['b']
    assert cmd.types['a'] == list


def test_parse_list_repeated_arg():
    """Support list type annotation for single argument"""
    def foo(a: list): pass
    cmd = Command(foo)
    cmd.parse('a=b', 'a=c')
    assert cmd.vars['a'] == ['b', 'c']


def test_cast_list():
    """Support list of strings with a simple syntax"""
    assert cast(list, '[b,c, d]') == ['b', 'c', 'd']


def test_cast_json_list():
    """Support json list when decodable"""
    assert cast(list, '[1,2, "c"]') == [1, 2, 'c']


def test_parse_dict_dotted_args():
    """Support dotted kwarg names to build a dict"""
    cmd = Command(lambda a: 1)
    cmd.parse('a.b=c', 'a.d=e')
    cmd.vars['a'] == dict(b='c', d='e')


def test_cast_string_dict():
    """Support string dict"""
    assert cast(dict, '{a: b, c: d}') == dict(a='b', c='d')


def test_cast_json_dict():
    """Support string dict"""
    assert cast(dict, '{"a": 2}') == dict(a=2)


def test_parse_json_dict():
    """Support dotted kwarg names to build a dict"""
    def foo(a, b: dict, c): pass
    cmd = Command(foo)

    # json
    cmd.parse('d', '{"e": 1}', '2')
    assert cmd.vars == {'a': 'd', 'b': {'e': 1}, 'c': '2'}

    # simple
    cmd.parse('d', '{e: 1}', '2')
    assert cmd.vars == {'a': 'd', 'b': {'e': "1"}, 'c': '2'}


def test_cast_bool():
    """Support bool type"""
    assert cast(bool, 'True') is True
    assert cast(bool, '1') is True
    assert cast(bool, 'yes') is True
    assert cast(bool, 'Yes') is True
    assert cast(bool, 'true') is True

    assert cast(bool, '') is False
    assert cast(bool, 'False') is False
    assert cast(bool, 'false') is False
    assert cast(bool, 'no') is False
    assert cast(bool, 'NO') is False
    assert cast(bool, '0') is False


def test_parse_bool():
    def foo(a, b=False): pass
    cmd = Command(foo)

    cmd.parse('a', '1')
    assert cmd.vars['b'] is True

    cmd.parse('a', '0')
    assert cmd.vars['b'] is False

    cmd.parse('a', 'b=0')
    assert cmd.vars['b'] is False


def test_cast_int():
    """Support string dict"""
    assert cast(int, '1') == 1


def test_alias():
    """Alias support"""
    def foo(age: int, debug=False): pass
    cmd = Command(foo, arguments=[
        Argument('debug', alias='-d'),
        Argument('age', alias='-a'),
    ])

    cmd.parse('1', '-d')
    assert cmd.vars['debug'] is True

    cmd.parse('1', '-d=no')
    assert cmd.vars['debug'] is False

    cmd.parse('-a=12')
    assert cmd.vars['age'] == 12

    # test that it becomes non-positional
    cmd.parse('-d', '-a=3')
    assert cmd.vars['age'] == 3
    assert cmd.vars['debug'] == True


def test_cast_override():
    def foo(ages): pass
    class AgesArgument(Argument):
        def cast(self, value):
            return [int(i) for i in value.split(',')]
    cmd = Command(foo, arguments=[AgesArgument('ages')])
    cmd.parse('ages=1,2')
    assert cmd.vars['ages'] == [1, 2]

    # try with alias, should have been stripped fine by default in match()
    cmd = Command(foo, arguments=[AgesArgument('ages', alias='-a')])
    cmd.parse('-a=1,2')
    assert cmd.vars['ages'] == [1, 2]


def test_command_override():
    def foo(): pass
    foo.cli2 = dict(name='lol', doc='test')
    assert Command(foo).name == 'lol'
    assert Command(foo).doc == 'test'

    group = Group()
    group.add_command(foo)
    assert 'lol' in group


def test_argument_override():
    def foo(a, b=None): pass
    foo.cli2_a = dict(
        alias='-a',
        cast=lambda v: int(v),
    )
    cmd = Command(foo)
    cmd.parse('-a=3')
    assert cmd.vars['a'] == 3
