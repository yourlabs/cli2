import clitoo


class Foo:
    bar = {'baz': [lambda *a, **k: 'test']}


def test_Callback_nested_attribute():
    cb = clitoo.Callback.factory('test_clitoo.Foo.bar.baz.0')
    assert cb.cb == Foo.bar['baz'][0]


def test_Callback_nested_module():
    from clitoo.git import clone
    cb = clitoo.Callback.factory('clitoo.git.clone')
    assert cb.cb == clone


def test_Callback_fail():
    cb = clitoo.Callback.factory('clitoooooooolaaaawwwwllllzz')
    assert cb.cb is None


def test_Callback_callables():
    cb = clitoo.Callback.factory('clitoo')
    assert 'help' in cb.callables


def test_help(capsys):
    clitoo.help('clitoo')
