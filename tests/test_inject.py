import cli2
import inspect
import pytest
from unittest import mock


with open(__file__, 'r') as f:
    lines = f.read().split('\n')


@pytest.mark.parametrize(
    'kwargs, command, expected',
    [
        (
            # test default enabled by default
            dict(default=None),
            [],
            None,
        ),
        (
            # default should not be enabled
            dict(),
            [],
            ValueError,
        ),
        # test bools
        (
            # test default enabled by default
            dict(default=True),
            [],
            True,
        ),
        (
            # note how defaults don't need annotation: they are enforced
            dict(default=False),
            [],
            False,
        ),
        (
            # test enable
            dict(default=False, annotation=bool),
            ['test'],
            True,
        ),
        (
            # test disable, note how the annotation is needed
            dict(default=True, annotation=bool),
            ['no-test'],
            False,
        ),
    ],
)
def test_syntaxes(kwargs, command, expected):
    kinds = [
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ]
    for kind in kinds:
        kwargs['kind'] = kind

        class TestCommand(cli2.Command):
            def setargs(self):
                super().setargs()
                param = inspect.Parameter('test', **kwargs)
                self[param.name] = cli2.Argument(self, param)

        cbs = (
            lambda: True,
            lambda *a: True,
            lambda *a, **k: True,
            lambda **k: True,
            lambda *a, test=False: True,
            lambda *a, test=True: True,
        )
        for cb in cbs:
            cmd = TestCommand(cb)
            cmd.parse(*command)
            code = lines[cb.__code__.co_firstlineno]

            if isinstance(expected, type):
                with pytest.raises(expected):
                    assert cmd['test'].value == expected, code
            else:
                assert cmd['test'].value == expected, code


def test_call():
    sentinel = mock.sentinel.test_call

    class TestCommand(cli2.Command):
        def setargs(self):
            super().setargs()
            param = inspect.Parameter(
                'test',
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=sentinel,
            )
            self[param.name] = cli2.Argument(self, param)

    # argument is passed when defined in signature
    cmd = TestCommand(lambda test: test)
    assert cmd() is sentinel

    # but is not passed when not in signature
    cmd = TestCommand(lambda: None)
    assert cmd() is None

    # we don't want no ValueError though
    class TestCommand2(TestCommand):
        def call(self, *args, **kwargs):
            return self['test'].value

    # argument value is available and passed as seen above
    cmd = TestCommand2(lambda test: test)
    assert cmd() is sentinel

    # argument value is available and not passed as seen above
    cmd = TestCommand2(lambda: None)
    assert cmd() is sentinel
