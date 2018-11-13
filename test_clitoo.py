import io
import clilabs
import clilabs.builtins


class Foo:
    bar = {'baz': [lambda *a, **k: 'test']}


CB_NAME = 'clilabs.test_clilabs:Foo.bar.baz.0'


def test_funcexpand():
    expected = ('clilabs.builtins', 'help')
    assert clilabs.funcexpand('help') == expected
    assert clilabs.funcexpand('clilabs.builtins:help') == expected


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


def test_help(capsys):
    clilabs.builtins.help()
    assert 'clilabs' in capsys.readouterr().out


def test_help_builtin(capsys):
    clilabs.builtins.help('help')
    assert 'help' in capsys.readouterr().out


def test_help_module(capsys):
    clilabs.builtins.help('clilabs')
    assert 'cli' in capsys.readouterr().out
