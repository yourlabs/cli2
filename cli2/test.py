import cli2
import io
import os
import re
import subprocess
from pathlib import Path
from rich.console import Console


REWRITE = os.getenv('FIXTURE_REWRITE') or os.getenv('TEST_REWRITE')


def autotest(path, cmd, ignore=None, env=None):
    """
    The autowriting test pattern, minimal for testing cli2 scripts.

    Example::

        from cli2.test import autotest
        autotest(
            'tests/djcli_save_user.txt',
            'djcli save auth.User username="test"',
        )
    """
    environ = os.environ.copy()
    if env:
        for key, value in env.items():
            environ[key] = value
    environ['PATH'] = ':'.join([
        environ.get('HOME', '') + '/.local/bin',
        environ.get('PATH', '')
    ])

    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        env=environ,
    )

    fixture = '\n'.join([
        'command: ' + cmd,
        'retcode: ' + str(proc.returncode),
        'stdout:',
        proc.stdout.decode('utf8'),
    ])
    if proc.stderr:
        fixture += '\n'.join([
            'stderr:',
            proc.stderr.decode('utf8'),
        ])

    for r in ignore or []:
        fixture = re.compile(r).sub('redacted', fixture)

    exists = os.path.exists(path)
    if REWRITE and exists:
        os.unlink(path)
        exists = False

    if not exists:
        # dirname = '/'.join(path.split('/')[:-1])
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        with open(path, 'w+') as f:
            f.write(fixture)

        if REWRITE:
            return

        raise type('FixtureCreated', (Exception,), {})(
            f'''
{path} was not in workdir and was created with:
{fixture}
            '''.strip(),
        )

    diff_cmd = 'diff -U 1 - "%s" | sed "1,2 d"' % path
    proc = subprocess.Popen(
        diff_cmd,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True
    )

    diff_out, diff_err = proc.communicate(input=fixture.encode('utf8'))
    if diff_out:
        raise type(f'''
DiffFound
- {cmd}
+ {path}
        '''.strip(), (Exception,), {})('\n' + diff_out.decode('utf8'))


class Outfile:
    def __init__(self):
        self.out = ''

    def write(self, content):
        self.out += content

    def flush(self):
        pass

    def __contains__(self, value):
        return value in self.out

    def __repr__(self):
        return self.out

    def reset(self):
        self.__init__()


def fixture_test(name):
    output = cli2.display.console.file.getvalue().encode('utf8')
    fixture_test = Path(__file__).parent.parent / f'tests/test_{name}'
    if fixture_test.exists() and not os.getenv('FIXTURE_REWRITE'):
        with fixture_test.open('rb') as f:
            expected = f.read()
    else:
        with fixture_test.open('wb') as f:
            f.write(output)
        raise Exception(f'{fixture_test} written')

    import difflib
    diff = difflib.unified_diff(
        expected.decode('utf8').split('\n'),
        output.decode('utf8').split('\n'),
        fromfile=str(fixture_test),
        tofile='actual_output',
    )
    diff = '\n'.join(diff)
    if diff:
        raise type('DiffFound', (Exception,), {})('\n' + diff)


def console_reset():
    cli2.display.console = Console(
        file=io.StringIO(),
        force_terminal=True,
    )
