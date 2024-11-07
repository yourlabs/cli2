import cli2
import cli2.test


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
    cli2.test.console_reset()
    cli2.diff(DIFF)
    cli2.test.fixture_test('diff')


def test_print():
    def test(arg):
        cli2.test.console_reset()
        cli2.print(arg)
        cli2.test.fixture_test('print')

    # detect json
    test('{"a": 1}')
    # print dict
    test(dict(a=1))

    # print response.json()
    class Response:
        def json(self):
            return '{"a": 1}'
    test(Response())

    # print yaml
    test('a: 1')

    # print dict subclass
    class Test(dict):
        pass
    test(Test(a=1))
