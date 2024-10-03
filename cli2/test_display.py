import cli2
import io


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


def test_diff():
    stdout = io.StringIO()
    cli2.diff(DIFF, file=stdout)
    stdout.seek(0)
    assert stdout.read() == '\x1b[01mdiff --git a/cli2/__init__.py b/cli2/__init__.py\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[01mindex 3a538ef..577a094 100644\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[91m--- a/cli2/__init__.py\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[32m+++ b/cli2/__init__.py\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[01m\x1b[35m@@ -3,6 +3,7 @@ from .argument import Argument\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[37m \x1b[39;49;00mfrom .colors import colors as c\x1b[37m\x1b[39;49;00m\n\x1b[37m \x1b[39;49;00mfrom .command import Command\x1b[37m\x1b[39;49;00m\n\x1b[37m \x1b[39;49;00mfrom .decorators import arg, cmd\x1b[37m\x1b[39;49;00m\n\x1b[32m+from .display import diff, print\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[37m \x1b[39;49;00mfrom .group import Group\x1b[37m\x1b[39;49;00m\n\x1b[37m \x1b[39;49;00mfrom .node import Node\x1b[37m\x1b[39;49;00m\n\x1b[37m \x1b[39;49;00mfrom .table import Table\x1b[37m\x1b[39;49;00m\n\n'  # noqa


def test_print():
    expected = '\x1b[94ma\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m1\x1b[37m\x1b[39;49;00m\n\n'  # noqa

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
