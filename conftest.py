import os

from rich import diagnose


def env_fixate():
    os.environ['TERM'] = ''
    os.environ['COLORTERM'] = ''
    os.environ['COLUMNS'] = '58'
    os.environ['FORCE_COLOR'] = '1'
    os.environ['FORCE_TERMSIZE'] = '1'

def pytest_generate_tests(metafunc):
    env_fixate()

env_fixate()
diagnose.report()
