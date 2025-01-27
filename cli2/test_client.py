import cli2
import httpx
import pytest


class Client(cli2.Client):
    pass


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
    assert client.token


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
async def test_pagination_initialize(httpx_mock):
    httpx_mock.add_response(url='http://lol/?page=1', json=dict(
        total_pages=2,
        items=[dict(a=1)],
    ))
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])

    class PaginatedClient(cli2.Client):
        def pagination_initialize(self, paginator, data):
            paginator.total_pages = data['total_pages']

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
    assert isinstance(result[0], Model)


def test_paginator_fields():
    paginator = cli2.Paginator(cli2.Client(), '/')
    paginator.total_items = 95
    paginator.per_page = 10
    assert paginator.total_pages == 10


@pytest.mark.asyncio
async def test_pagination_patterns(httpx_mock):
    # I'm dealing with APIs which have a different pagination system on
    # different resources, and on some resources no pagination at all
    # Would like to define that per model
    class Client(cli2.Client):
        pass

    class TotalModel(Client.model):
        url_list = '/foo'

        @classmethod
        def pagination_initialize(cls, paginator, data):
            paginator.total_items = data['total_items']
            paginator.per_page = len(data['items'])

    httpx_mock.add_response(
        url='http://lol/foo?page=1',
        json=dict(total_items=2, items=[dict(a=1)]),
    )

    class Pages(Client.model):
        url_list = '/bar'

        @classmethod
        def pagination_initialize(cls, paginator, data):
            paginator.total_pages = data['total_pages']
            paginator.per_page = len(data['items'])

    httpx_mock.add_response(
        url='http://lol/bar?page=1',
        json=dict(total_pages=1, items=[dict(a=1)]),
    )

    class Offset(Client.model):
        url_list = '/off'

        @classmethod
        def pagination_initialize(cls, paginator, data):
            paginator.total_items = data['total']

        @classmethod
        def pagination_parameters(cls, paginator, page_number):
            paginator.per_page = 1
            return dict(
                offset=(page_number - 1) * paginator.per_page,
                limit=paginator.per_page,
            )

    httpx_mock.add_response(
        url='http://lol/off?offset=0&limit=1',
        json=dict(total=2, items=[dict(a=1)]),
    )

    client = Client(base_url='http://lol')

    paginator = client.TotalModel.find()
    await paginator.initialize()
    assert paginator.total_items == 2
    assert paginator.total_pages == 2
    assert paginator.per_page == 1

    paginator = client.Pages.find()
    await paginator.initialize()
    assert paginator.total_pages == 1
    assert paginator.per_page == 1

    paginator = client.Offset.find()
    await paginator.initialize()
    assert paginator.total_pages == 2
    assert paginator.per_page == 1
    assert paginator.pagination_parameters(2) == dict(offset=1, limit=1)


@pytest.mark.asyncio
async def test_pagination_reverse(httpx_mock):
    httpx_mock.add_response(
        url='http://lol/bar?page=1',
        json=dict(total_pages=3, items=[dict(a=1), dict(a=2)]),
    )
    httpx_mock.add_response(
        url='http://lol/bar?page=2',
        json=dict(total_pages=3, items=[dict(a=3), dict(a=4)]),
    )
    httpx_mock.add_response(
        url='http://lol/bar?page=3',
        json=dict(total_pages=3, items=[dict(a=5)]),
    )

    class Client(cli2.Client):
        def pagination_initialize(self, paginator, data):
            paginator.total_pages = data['total_pages']

    client = Client(base_url='http://lol')
    paginator = client.paginate('/bar')
    paginator = paginator.reverse()
    results = await paginator.list()
    assert [x['a'] for x in results] == [5, 4, 3, 2, 1]


@pytest.mark.asyncio
async def test_subclass():
    class Client(cli2.Client):
        pass

    assert Client.cli2_self['factory'] == '__init__'

    class Model(Client.model):
        pass
    assert Model in Client.models
    assert Model._client_class == Client
    cls = await Model.cli2_cls['factory']()
    assert isinstance(cls.client, Client)


@pytest.mark.asyncio
async def test_cli():
    from cli2 import example_client

    # Test that Client's __init_subclass__ did setup a factory for self
    client = example_client.cli['get']['self'].factory()
    assert isinstance(client, example_client.APIClient)

    # Test that Model's __init_subclass__ did setup a factory for cls
    model = await example_client.cli['find']['cls'].factory()
    assert isinstance(model.client, example_client.APIClient)
    assert issubclass(model, example_client.Object)


def test_descriptor():
    class Model(Client.model):
        url_list = '/foo'
