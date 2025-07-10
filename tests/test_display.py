import cli2
import io
import os
import sys


DIFF = '''
diff --git a/cli2/__init__.py b/cli2/__init__.py
index 3a538ef..577a094 100644
--- a/cli2/__init__.py
+++ b/cli2/__init__.py
@@ -3,6 +3,7 @@ from .argument import Argument
 from .colors import colors as c
 from .command import Command
 from .decorators import arg, cmd
+from .display import diff, print
 from .group import Group
 from .node import Node
 from .table import Table
'''.strip().split('\n')


def test_diff(monkeypatch):
    stdout = io.StringIO()
    cli2.diff(DIFF, file=stdout)
    stdout.seek(0)
    assert stdout.read() == '\x1b[38;5;15mdiff --git a/cli2/__init__.py b/cli2/__init__.py\x1b[39m\n\x1b[38;5;15mindex 3a538ef..577a094 100644\x1b[39m\n\x1b[38;5;204m--- a/cli2/__init__.py\x1b[39m\n\x1b[38;5;148m+++ b/cli2/__init__.py\x1b[39m\n\x1b[38;5;245m@@ -3,6 +3,7 @@ from .argument import Argument\x1b[39m\n\x1b[38;5;15m \x1b[39m\x1b[38;5;15mfrom .colors import colors as c\x1b[39m\n\x1b[38;5;15m \x1b[39m\x1b[38;5;15mfrom .command import Command\x1b[39m\n\x1b[38;5;15m \x1b[39m\x1b[38;5;15mfrom .decorators import arg, cmd\x1b[39m\n\x1b[38;5;148m+from .display import diff, print\x1b[39m\n\x1b[38;5;15m \x1b[39m\x1b[38;5;15mfrom .group import Group\x1b[39m\n\x1b[38;5;15m \x1b[39m\x1b[38;5;15mfrom .node import Node\x1b[39m\n\x1b[38;5;15m \x1b[39m\x1b[38;5;15mfrom .table import Table\x1b[39m\n'  # noqa


def test_print(monkeypatch):
    expected = '\x1b[38;5;204ma\x1b[39m\x1b[38;5;15m:\x1b[39m\x1b[38;5;15m \x1b[39m\x1b[38;5;141m1\x1b[39m\n'  # noqa

    def test(arg):
        stdout = io.StringIO()
        cli2.print(arg, file=stdout)
        stdout.seek(0)
        assert stdout.read() == expected

    fixture = '{"a": 1}'
    test(fixture)
    test(dict(a=1))

    class Response:
        def json(self):
            return fixture

    test(Response())

    fixture = 'a: 1'
    test(Response())
    test(fixture)

    class Test(dict):
        pass
    test(Test(a=1))


def test_highlight(monkeypatch):
    colored = '\x1b[38;5;204ma\x1b[39m\x1b[38;5;15m:\x1b[39m\x1b[38;5;15m \x1b[39m\x1b[38;5;141m1\x1b[39m'  # noqa
    from cli2 import display

    assert cli2.highlight('a: 1', 'Yaml') == colored

    os.environ['FORCE_COLOR'] = ''
    assert cli2.highlight('a: 1', 'Yaml') == 'a: 1'
    os.environ['FORCE_COLOR'] = '1'
