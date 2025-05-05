from cli2.test import autotest


def test_traceback_demo():
    autotest(
        'tests/traceback.txt',
        'cli2-traceback',
    )
