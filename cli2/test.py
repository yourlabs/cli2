import io
import os
import pkg_resources
import re
import shlex
import subprocess
import unittest.mock


REWRITE = os.getenv('FIXTURE_REWRITE') or os.getenv('TEST_REWRITE')


def entrypoint_get(name):
    for ep in pkg_resources.iter_entry_points('console_scripts'):
        if ep.name == name:
            return ep


def autotest(path, cmd, ignore=None):
    """
    The autowriting test pattern, minimal for testing cli2 scripts.

    Example:

        cli2.autotest(
            'tests/djcli_save_user.txt',
            'djcli save auth.User username="test"',
        )
    """
    name = cmd.split(' ')[0]
    ep = entrypoint_get(name)
    if not ep:
        raise Exception(f'Could not find entrypoint {name}')

    console_script = ep.load()
    console_script.argv = shlex.split(cmd)

    # for debugging this function, the following helps me:
    # return print(cmd, console_script())

    @unittest.mock.patch('sys.stderr', new_callable=io.StringIO)
    @unittest.mock.patch('sys.stdout', new_callable=io.StringIO)
    def test(mock_stdout, mock_stderr):
        try:
            console_script()
        except SystemExit as e:
            console_script.exit_code = e.code
        return mock_stdout, mock_stderr

    out, err = test()

    out.seek(0)
    test_out = out.read()

    err.seek(0)
    test_err = err.read()

    fixture = '\n'.join([
        'command: ' + cmd,
        'retcode: ' + str(console_script.exit_code),
        'stdout:',
        test_out,
    ])
    if test_err:
        fixture += '\n'.join([
            'stderr:',
            test_err,
        ])

    for r in ignore or []:
        fixture = re.compile(r).sub(f'redacted', fixture)

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
