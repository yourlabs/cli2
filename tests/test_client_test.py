import chttpx
import cli2
import pytest
from chttpx.example import APIClient


@pytest.mark.chttpx_mock
def test_object_story(ts, chttpx_vars):
    chttpx_vars.setdefault('test_name', f'test{ts}')
    test_name = chttpx_vars['test_name']

    obj = APIClient.cli['object']['create'](f'name={test_name}')
    assert obj.name == test_name

    cli2.log.info('bogus')

    with pytest.raises(chttpx.RefusedResponseError):
        APIClient.cli['object']['create'](f'name={test_name}')
    result = APIClient.cli['object']['delete'](f'{obj.id}')
