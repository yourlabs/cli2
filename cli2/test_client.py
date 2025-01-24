import cli2
import httpx
import pytest


raised = False


@pytest.mark.asyncio
async def test_error(httpx_mock):
    client = cli2.Client()
    httpx_mock.add_response(url='http://lol', json=[1])

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
            return 'token'

    httpx_mock.add_response(url='http://lol', method='POST', json=[1])
    client = HasToken()
    assert (await client.post('http://lol')).json() == [1]
    assert client.token == 'token'

    class NoToken(cli2.Client):
        pass
    httpx_mock.add_response(url='http://lol', method='POST', json=[1])
    client = NoToken()
    assert (await client.post('http://lol')).json() == [1]
    with pytest.raises(AttributeError):
        client.token


@pytest.mark.asyncio
@pytest.mark.parametrize('kwargs', (
    dict(json=[]),
    dict(status_code=400),
))
async def test_pagination(httpx_mock, kwargs):
    httpx_mock.add_response(url='http://lol/?page=1', json=[dict(a=1)])
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])
    httpx_mock.add_response(url='http://lol/?page=3', **kwargs)
    client = cli2.Client(base_url='http://lol')
    assert await client.paginate('/').list() == [dict(a=1), dict(a=2)]


@pytest.mark.asyncio
async def test_pagination_reverse(httpx_mock):
    httpx_mock.add_response(url='http://lol/?page=1', json=dict(
        total_pages=2,
        items=[dict(a=1)],
    ))
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])

    class PaginatedClient(cli2.Client):
        def pagination_initialize(self, data):
            return data['total_pages'], 1

    client = PaginatedClient(base_url='http://lol')
    assert await client.paginate('/').list() == [dict(a=1), dict(a=2)]


@pytest.mark.asyncio
async def test_token_get(httpx_mock):
    httpx_mock.add_response(url='http://lol/token', json=dict(token=123))
    httpx_mock.add_response(url='http://lol/?page=1', json=[])

    class TokenClient(cli2.Client):
        async def token_get(self):
            response = await self.get('/token')
            return response.json()['token']

    client = TokenClient(base_url='http://lol')
    await client.paginate('/').list()
    assert client.token


@pytest.mark.asyncio
async def test_pagination_model(httpx_mock):
    class Model(dict):
        pass

    httpx_mock.add_response(url='http://lol/?page=1', json=[dict(a=2)])
    httpx_mock.add_response(url='http://lol/?page=2', json=[])
    client = cli2.Client(base_url='http://lol')
    result = await client.paginate('/', model=Model).list()
    assert type(result[0]) == Model


def test_client_model():
    class ModelClient(cli2.Client):
        pass

    @ModelClient.model
    class Model(dict):
        pass

    assert ModelClient._models == [Model]
    assert issubclass(ModelClient().Model, Model)
