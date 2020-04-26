from .command import Command


def test_int():
    def foo(one: int): return one
    cmd = Command(foo)
    cmd.parse('1')
    assert cmd['one'].value == 1
    assert not cmd['one'].accepts
    assert cmd(['1']) == 1


def test_vararg():
    def foo(*one): return one
    cmd = Command(foo)
    cmd.parse('a', 'b')
    assert cmd['one'].value == ['a', 'b']
    assert cmd['one'].accepts
    assert cmd(['a', 'b']) == ('a', 'b')


def test_kwarg():
    def foo(one=None): return one
    cmd = Command(foo)
    cmd.parse('one=b')
    assert cmd['one'].value == 'b'
    assert not cmd['one'].accepts
    assert cmd(['one=b']) == 'b'


def test_varkwarg():
    def foo(**one): return one
    cmd = Command(foo)
    cmd.parse('a=b', 'c=d')
    assert cmd['one'].value == dict(a='b', c='d')
    assert cmd['one'].accepts


def test_vararg_varkwarg_natural():
    def foo(*one, **two): return (one, two)
    cmd = Command(foo)
    cmd.parse('x', 'y', 'a=b', 'c=d')
    assert cmd['one'].value == ['x', 'y']
    assert cmd['two'].value == dict(a='b', c='d')
    assert cmd(['x', 'y', 'a=b', 'c=d']) == (('x', 'y'), dict(a='b', c='d'))


def test_vararg_varkwarg_asterisk():
    def foo(*one, **two): return (one, two)
    cmd = Command(foo)
    cmd.parse('*["x"]', '**{"y" :"z"}')
    assert cmd['one'].value == ['x']
    assert cmd['two'].value == dict(y='z')


def test_bool():
    def foo(one: bool): return one
    cmd = Command(foo)

    cmd.parse('yes')
    assert cmd['one'].value is True
    assert not cmd['one'].accepts
    assert cmd(['yes']) is True

    for i in ('0', 'no', 'False'):
        cmd.parse(i)
        assert cmd['one'].value is False
        assert not cmd['one'].accepts
        assert cmd([i]) is False


def test_bool_flag():
    def foo(one: bool): return one
    foo.cli2_one = dict(alias='-o')
    cmd = Command(foo)
    cmd.parse('-o')
    assert cmd['one'].value is True


def test_bool_flag_negate():
    def foo(one: bool): return one
    foo.cli2_one = dict(alias='-o', negate='!o')
    cmd = Command(foo)
    cmd.parse('!o')
    assert cmd['one'].value is False


def test_json_cast():
    import json
    def foo(one): return one
    foo.cli2_one = dict(cast=lambda v: json.loads(v))
    cmd = Command(foo)
    cmd.parse('[1]')
    assert cmd['one'].value == [1]


def test_further_search():
    def foo(a=None, one: bool = None): return one
    cmd = Command(foo)
    assert cmd['one'].match('one=yes') == 'yes'

    cmd.parse('one=yes')
    assert cmd['one'].value is True
    assert not cmd['one'].accepts
    assert cmd(['one=yes']) is True


def test_list():
    def foo(one: list = None): return one
    cmd = Command(foo)
    assert cmd['one'].match('one=[1]') == '[1]'

    cmd.parse('one=[1]')
    assert cmd['one'].value == [1]
    assert not cmd['one'].accepts

    assert cmd(['one=[1]']) == [1]
    assert cmd(['[1]']) == [1]

    # simple syntax for simple list of strings
    assert cmd(['one=a,b']) == ['a', 'b']


def test_dict():
    def foo(one: dict = None): return one
    cmd = Command(foo)
    assert cmd['one'].match('one={"a": 1}') == '{"a": 1}'

    cmd.parse('one={"a": 1}')
    assert cmd['one'].value == {"a": 1}
    assert not cmd['one'].accepts

    assert cmd(['one={"a": 1}']) == {"a": 1}
    assert cmd(['{"a": 1}']) == {"a": 1}

    # simple syntax for simple dict of strings
    assert cmd(['one=a:b,c:d']) == {"a": "b", "c": "d"}


def test_cast_override():
    def foo(one): return one
    foo.cli2_one = dict(cast=lambda v: [int(i) for i in v.split(',')])
    cmd = Command(foo)
    cmd.parse('1,2')
    assert cmd['one'].value == [1, 2]
    assert cmd(['1,2']) == [1, 2]


def test_weird_pattern():
    # show off our algorithms weakness, while it's still fresh in my head :)
    def foo(a=None, b=None):
        return (a, b)
    cmd = Command(foo)

    cmd.parse('b=x')
    assert cmd['b'].value == 'x'
    assert cmd(['b=x']) == (None, 'x')

    cmd = Command(foo)
    cmd.parse('a=b=x')
    assert cmd['a'].value == 'b=x'
    assert cmd(['a=b=x']) == ('b=x', None)


class Foo:
    def __call__(self, one: int, two: list, three: bool, *vararg, **varkwarg):
        self.one = one
        self.two = two
        self.three = three
        self.vararg = vararg
        self.varkwarg = varkwarg


def test_stress():
    cmd = Command(Foo())
    cmd(['1', '[2]', 'yes', 'var1', 'var2', 'kw1=1', 'kw2=2'])
    assert cmd.target.one == 1
    assert cmd.target.two == [2]
    assert cmd.target.three is True
    assert cmd.target.vararg == ('var1', 'var2')
    assert cmd.target.varkwarg == dict(kw1='1', kw2='2')


def test_missing():
    cmd = Command(lambda a: True)
    assert 'missing 1 required' in cmd([])


def test_extra():
    cmd = Command(lambda: True)
    assert 'No parameters for these' in cmd(['a'])


def test_asyncio():
    async def test():
        return 'foo'
    assert Command(test)([]) == 'foo'
