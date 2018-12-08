"""Example cli2 compatible module."""

def run(*args, **kwargs):
    from cli2 import console_script
    return console_script.__dict__


def test(*args, **kwargs):
    """Test command"""
    return 'I am being tested !'
test._cli2_exclude = True  # noqa


class Foo:
    bar = {'baz': [lambda *a, **k: 'test']}


nested = Foo()
nested.bar = lambda: 'bar'
nested.lulz = lambda: 'lulz'
