from pathlib import Path
import cli2
from cli2.test import autotest


def test_traceback_demo():
    autotest(
        'tests/traceback.txt',
        'cli2-traceback',
        ignore=[
            str(Path(cli2.__path__[0]).parent),
            str(Path(__file__).parent.parent.parent),
        ],
    )
