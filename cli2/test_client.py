import cli2
import httpx
import pytest


raised = False


@pytest.mark.asyncio
async def test_error(httpx_mock):
    client = cli2.Client()
    httpx_mock.add_response(url="http://lol", json=[1])

    async def raises(*a, **k):
        global raised
        raised = True
        raise httpx.RemoteProtocolError('foo')
    client.client.request = raises
    old_client = client.client
    response = await client.get('http://lol')
    assert client.client is not old_client
    assert raised
    assert response.json() == [1]


@pytest.mark.asyncio
async def test_token(httpx_mock):
    class HasToken(cli2.Client):
        async def token_get(self):
            return "token"

    httpx_mock.add_response(url="http://lol", method="POST", json=[1])
    client = HasToken()
    assert (await client.post("http://lol")).json() == [1]
    assert client.token == "token"

    class NoToken(cli2.Client):
        pass
    httpx_mock.add_response(url="http://lol", method="POST", json=[1])
    client = NoToken()
    assert (await client.post("http://lol")).json() == [1]
    with pytest.raises(AttributeError):
        client.token
