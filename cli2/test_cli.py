import pytest

from freezegun import freeze_time

import cli2


@pytest.mark.parametrize('name,command', [
    ('cli2', ''),
    ('help', 'help'),
    ('help_debug', 'help debug'),
    ('run_help', 'run cli2.help'),
    ('run_help_debug', 'run cli2.help debug'),
    ('run_help_implicit', 'cli2.help'),
    ('run_module', 'cli2'),
    ('run_module_missing_attr', 'cli2.missing'),
    ('run_module_missing', 'missinggggggg.foo'),
    ('run_module_nodoc', 'test_cli2.test_cli2'),
    ('run_module_builtin', 'datetime.datetime.now'),
    ('run_module_args_int', 'datetime.datetime 2019 2 1'),
    ('run_module_kwds_int', 'datetime.datetime year=2019 month=2 day=1'),
    ('run_module_args_None', 'datetime.datetime.now None'),
    ('run_module_args_float', 'builtins.round 1.888 1'),
    ('help_module', 'help cli2'),
    ('help_module_attr_notfound', 'help cli2.skipppp'),
    ('help_module_no_callables', 'help datetime'),
    ('help_module_no_signature', 'help datetime.date.fromtimestamp'),
    ('docmod', 'docmod cli2'),
    ('docmod_noargs', 'docmod'),
    ('docfile', 'docfile cli2/cli.py'),
    ('docfile_missing', 'docfile missing.py'),
    ('debug', 'debug cli2.run to see=how -it --parses=me'),
])
@freeze_time("2010-02-01")  # so datetime.datetime.now() output is unchanging
def test_cli2(name, command):

    cli2.autotest(
        f'tests/{name}.txt',
        'cli2 ' + command,
    )
