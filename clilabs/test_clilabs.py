import io
import clilabs


class Foo:
    bar = {'baz': [lambda *a, **k: 'test']}


CB_NAME = 'clilabs.test_clilabs:Foo.bar.baz.0'


def test_funcimp():
    result = clilabs.funcimp(CB_NAME)
    assert result == Foo.bar['baz'][0]


def test_expand(monkeypatch):
    monkeypatch.setattr('sys.stdin', io.StringIO('in'))
    result = clilabs.expand('-', '-a', '--b=1', 'c', 'd=1')
    assert result == (['in', 'c'], {'d': '1'})


def test_cli():
    result = clilabs.cli('clilabs', CB_NAME, '1')
    assert result == 'test'
