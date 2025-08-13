import asyncio
import chttpx
import cli2
import httpx
import pytest
from chttpx.example import APIClient


@pytest.fixture
def test_name(ts, chttpx_vars):
    return chttpx_vars.setdefault('test_name', f'test{ts}')


@pytest.mark.chttpx_mock
def test_object_story(test_name):
    obj = APIClient.cli['object']['create'](f'name={test_name}')
    assert obj.name == test_name

    cli2.log.info('bogus')

    with pytest.raises(chttpx.RefusedResponseError):
        APIClient.cli['object']['create'](f'name={test_name}')
    result = APIClient.cli['object']['delete'](f'{obj.id}')


@pytest.mark.asyncio
async def test_async_fixture(chttpx_fixture, chttpx_log):
    cli2.configure(str(chttpx_log))
    client = chttpx.Client(base_url='http://localhost:8000')
    try:
        responses = await asyncio.gather(
            client.get('/sleep/2/'),
            client.get('/sleep/1/'),
        )
    except httpx.ConnectError:
        pytest.skip('runserver required')
    chttpx_fixture.load(chttpx_log)
    assert chttpx_fixture.requests
    for entry in chttpx_fixture.requests:
        assert entry['request']
        assert entry['response']


@pytest.mark.asyncio
@pytest.mark.chttpx_mock
async def test_async():
    client = chttpx.Client(base_url='http://localhost:8000')
    r1, r2 = await asyncio.gather(
        client.get('/sleep/2/'),
        client.get('/sleep/1/'),
    )
    assert r1.content.decode() == 'Slept 2 secs'
    assert r2.content.decode() == 'Slept 1 secs'
