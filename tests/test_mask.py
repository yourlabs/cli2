import cli2
import pytest


def test_mask():
    mask = cli2.Mask(['seckey'], ['secval'])
    fixture = {
        'a': {
            'b': 'secval b secret',
            'seckey': 'secret',
        },
        'b': ['secval foo secret'],
    }

    expected = {
        'a': {
            'b': '***MASKED*** b ***MASKED***',
            'seckey': '***MASKED***',
        },
        'b': ['***MASKED*** foo ***MASKED***']
    }
    assert mask(fixture) == expected
