import cli2

import pytest


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
    ('help_module', 'help cli2'),
    ('help_module_attr_notfound', 'help cli2.skipppp'),
    ('help_module_no_callables', 'help datetime'),
    ('help_module_no_signature', 'help datetime.datetime'),
    ('docmod', 'docmod cli2'),
    ('docmod_noargs', 'docmod'),
    ('docfile', 'docfile cli2/cli.py'),
    ('docfile_missing', 'docfile missing.py'),
    ('debug', 'debug cli2.run to see=how -it --parses=me'),
])
def test_cli2(name, command):
    cli2.autotest(
        f'tests/{name}.txt',
        'cli2 ' + command,
    )
