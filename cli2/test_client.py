from datetime import datetime
import cli2
import httpx
import inspect
import pytest
import textwrap


@pytest.fixture
def client_class():
    class TestClient(cli2.Client):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('base_url', 'http://lol')
            super().__init__(*args, **kwargs)
    return TestClient


@pytest.mark.asyncio
async def test_client_cli(client_class, httpx_mock):
    assert client_class.cli
    factory = client_class.cli.overrides['self']['factory']
    assert isinstance(factory(), client_class)

    httpx_mock.add_response(url='http://lol', json=[1])
    response = await client_class.cli['get'].async_call('http://lol')
    assert response.json() == [1]

    class TestModel(client_class.Model):
        url_list = '/'
    assert 'testmodel' in client_class.cli
    assert client_class.cli['testmodel']['get'].overrides['cls']['factory']
    assert not inspect.ismethod(client_class.cli['testmodel']['get'].target)
    result = await client_class.cli['testmodel']['get']['cls'].factory_value()
    assert issubclass(result, TestModel)
    assert isinstance(result.client, client_class)

    httpx_mock.add_response(url='http://lol/', json=[dict(a=1)])
    await client_class.cli['testmodel']['find'].async_call()


def test_client_model(client_class):
    assert issubclass(client_class.Model, cli2.Model)
    assert client_class.Model._client_class == client_class

    class TestModel(client_class.Model):
        pass
    assert TestModel._client_class == client_class

    assert TestModel in client_class.models

    client = client_class()
    assert client.TestModel.client == client


@pytest.mark.asyncio
async def test_async_factory(httpx_mock):
    class TestClient(cli2.Client):
        @classmethod
        async def factory(cls):
            return cls(base_url='http://bar')

    TestClient.cli.overrides['self']['factory'] = TestClient.factory
    httpx_mock.add_response(url='http://bar/', json=[dict(a=1)])
    assert await TestClient.cli['get'].async_call('/')

    class TestModel(TestClient.Model):
        url_list = '/2'

    httpx_mock.add_response(url='http://bar/2', json=[dict(a=1)])
    await TestClient.cli['testmodel']['find'].async_call()


@pytest.mark.asyncio
async def test_client_cli_side_effect(client_class, httpx_mock):
    from cli2 import example_client

    # test that this didn't spill over client_class
    test_client_cli(client_class, httpx_mock)

    # Test that Client's __init_subclass__ did setup a factory for self
    assert isinstance(
        example_client.APIClient.cli['get']['self'].factory_value(),
        example_client.APIClient,
    )

    # Test that Model's __init_subclass__ did setup a factory for cls
    httpx_mock.add_response(url='https://api.restful-api.dev/1', json=[1])
    result = await example_client.cli['get'].async_call('/1')
    assert result.json() == [1]

    httpx_mock.add_response(
        url='https://api.restful-api.dev/objects/1',
        json=dict(id=1, a=2),
    )
    result = await example_client.cli['object']['get'].async_call('id=1')
    assert result.id == 1
    assert result.data['a'] == 2


class Client(cli2.Client):
    """ doc """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'http://lol')
        super().__init__(*args, **kwargs)

    def pagination_parameters(self, paginator, page_number):
        return dict(page=page_number)


raised = False


@pytest.mark.asyncio
async def test_error_remote(httpx_mock):
    client = Client()
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
async def test_error_status(httpx_mock):
    client = Client()
    httpx_mock.add_response(url='http://lol', status_code=403, json=[1])

    async def request():
        await client.post('http://lol', json=[2])
    cmd = cli2.Command(request)
    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await cmd.async_call()
    expected = textwrap.dedent('''
    Request data:
    - 2

    Response data:
    - 1
    ''').strip()
    assert excinfo.value.args[0].strip().endswith(expected)


@pytest.mark.asyncio
async def test_token(httpx_mock):
    class HasToken(Client):
        async def token_get(self):
            return 'token'

    httpx_mock.add_response(url='http://lol', method='POST', json=[1])
    client = HasToken()
    assert (await client.post('http://lol')).json() == [1]
    assert client.token == 'token'

    class NoToken(Client):
        pass
    httpx_mock.add_response(url='http://lol', method='POST', json=[1])
    client = NoToken()
    assert (await client.post('http://lol')).json() == [1]
    assert client.token


@pytest.mark.asyncio
async def test_pagination(httpx_mock):
    httpx_mock.add_response(url='http://lol/?page=1', json=[dict(a=1)])
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])
    httpx_mock.add_response(url='http://lol/?page=3', json=[])
    client = Client(base_url='http://lol')
    assert await client.paginate('/').list() == [dict(a=1), dict(a=2)]


@pytest.mark.asyncio
async def test_pagination_initialize(httpx_mock):
    httpx_mock.add_response(url='http://lol/?page=1', json=dict(
        total_pages=2,
        items=[dict(a=1)],
    ))
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])

    class PaginatedClient(Client):
        def pagination_initialize(self, paginator, data):
            paginator.total_pages = data['total_pages']

    client = PaginatedClient(base_url='http://lol')
    assert await client.paginate('/').list() == [dict(a=1), dict(a=2)]


@pytest.mark.asyncio
async def test_token_get(httpx_mock):
    httpx_mock.add_response(url='http://lol/token', json=dict(token=123))
    httpx_mock.add_response(url='http://lol/?page=1', json=[])

    class TokenClient(Client):
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
    client = Client(base_url='http://lol')
    result = await client.paginate('/', model=Model).list()
    assert isinstance(result[0], Model)


def test_paginator_fields():
    paginator = cli2.Paginator(Client(), '/')
    paginator.total_items = 95
    paginator.per_page = 10
    assert paginator.total_pages == 10


@pytest.mark.asyncio
async def test_pagination_patterns(httpx_mock):
    # I'm dealing with APIs which have a different pagination system on
    # different resources, and on some resources no pagination at all
    # Would like to define that per model
    class TotalModel(Client.Model):
        url_list = '/foo'

        @classmethod
        def pagination_initialize(cls, paginator, data):
            paginator.total_items = data['total_items']
            paginator.per_page = len(data['items'])

    httpx_mock.add_response(
        url='http://lol/foo?page=1',
        json=dict(total_items=2, items=[dict(a=1)]),
    )

    class Pages(Client.Model):
        url_list = '/bar'

        @classmethod
        def pagination_initialize(cls, paginator, data):
            paginator.total_pages = data['total_pages']
            paginator.per_page = len(data['items'])

    httpx_mock.add_response(
        url='http://lol/bar?page=1',
        json=dict(total_pages=1, items=[dict(a=1)]),
    )

    class Offset(Client.Model):
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

    # test that we can reverse pagination too
    class Client(cli2.Client):
        def pagination_initialize(self, paginator, data):
            paginator.total_pages = data['total_pages']

        def pagination_parameters(self, paginator, page_number):
            return dict(page=page_number)

    client = Client(base_url='http://lol')
    paginator = client.paginate('/bar')
    paginator = paginator.reverse()
    results = await paginator.list()
    assert [x['a'] for x in results] == [5, 4, 3, 2, 1]


def test_descriptor():
    class Model(Client.Model):
        id = cli2.Field()
        bar = cli2.Field('nested/bar')
        foo = cli2.Field('undeclared/foo')

    model = Model(data=dict(id=1, nested=dict(bar=2)))
    assert model.data['id'] == 1
    assert model.id == 1
    model.id = 2
    assert model.data['id'] == 2
    assert model.id == 2

    assert model.bar == 2
    model.bar = 3
    assert model.bar == 3
    assert model.data['nested']['bar'] == 3

    assert not model.foo
    model.foo = 1
    assert model.foo == 1
    assert model.data['undeclared']['foo'] == 1

    model = Model(foo=3)
    assert model.foo == 3
    assert model.data['undeclared']['foo'] == 3


def test_jsonstring():
    class Model(Client.Model):
        json = cli2.JSONStringField()

    client = Client()
    model = client.Model(data=dict(json='{"foo": 1}'))
    assert model.json == dict(foo=1)

    model.json['foo'] = 2
    assert model.json == dict(foo=2)
    assert model.data['json'] == '{"foo": 2}'

    model = client.Model()
    model.json = dict(a=1)
    assert model.data['json'] == '{"a": 1}'


def test_datetime():
    class Model(Client.Model):
        dt = cli2.DateTimeField()

    model = Model(dict(dt='2020-11-12T01:02:03'))
    assert model.dt == datetime(2020, 11, 12, 1, 2, 3)
    model.dt = datetime(2020, 10, 12, 1, 2, 3)
    assert model.data['dt'] == '2020-10-12T01:02:03'


def test_model_inheritance():
    class Model(Client.Model):
        foo = cli2.Field()

    class Model2(Model):
        bar = cli2.Field()

    client = Client()
    assert [*client.Model._fields.keys()] == ['foo']
    assert [*client.Model2._fields.keys()] == ['bar', 'foo']


def test_relation_simple():
    class Child(Client.Model):
        foo = cli2.Field()

    class Father(Client.Model):
        child = cli2.Related('Child')

    client = Client()
    model = client.Father(dict(child=dict(foo=1)))
    assert model.child.foo == 1
    assert model.data['child']['foo'] == 1

    model.child.foo = 2
    assert model.child.foo == 2
    assert model.data['child']['foo'] == 2

    new = client.Child(dict(foo=3))
    model.child = new
    assert model.child.foo == 3
    assert model.data['child']['foo'] == 3


def test_relation_many():
    class Child(Client.Model):
        foo = cli2.Field()

    class Father(Client.Model):
        children = cli2.Related('Child', many=True)

    client = Client()
    model = client.Father(dict(children=[dict(foo=1)]))
    assert model.children[0].foo == 1
    assert model.data['children'][0]['foo'] == 1

    model.children.append(client.Child(foo=2))
    assert model.data['children'][1]['foo'] == 2
    assert model.children[1].foo == 2

    new = [client.Child(dict(foo=3))]
    model.children = new
    assert len(model.children) == 1
    assert model.children[0].foo == 3
    assert model.data['children'][0]['foo'] == 3


@pytest.mark.asyncio
async def test_python_expression(httpx_mock):
    class Model(Client.Model):
        url_list = '/foo'
        a = cli2.Field()
        b = cli2.Field()

        @classmethod
        def pagination_initialize(cls, paginator, data):
            paginator.total_pages = data['total_pages']

    def mock():
        httpx_mock.add_response(url='http://lol/foo?page=1', json=dict(
            total_pages=2,
            items=[dict(a=1, b=1), dict(a=2, b=2), dict(a=3, b=1)],
        ))

        httpx_mock.add_response(url='http://lol/foo?page=2', json=dict(
            total_pages=2,
            items=[dict(a=4, b=1), dict(a=5, b=2)],
        ))

    client = Client(base_url='http://lol')

    # test equal
    mock()
    result = await client.Model.find(Model.b == 1).list()
    assert [x.a for x in result] == [1, 3, 4]

    # test or
    mock()
    result = await client.Model.find((Model.a == 1) | (Model.a == 5)).list()
    assert [x.a for x in result] == [1, 5]

    # test and
    mock()
    result = await client.Model.find((Model.a == 4) & (Model.b == 1)).list()
    assert [x.a for x in result] == [4]

    # test lt
    mock()
    result = await client.Model.find(Model.a < 3).list()
    assert [x.a for x in result] == [1, 2]

    # test gt
    mock()
    result = await client.Model.find(Model.a > 3).list()
    assert [x.a for x in result] == [4, 5]

    # test lambda
    mock()
    result = await client.Model.find(lambda obj: obj.a > 2).list()
    assert [x.a for x in result] == [3, 4, 5]


@pytest.mark.asyncio
async def test_expression_parameter(httpx_mock):
    class Model(Client.Model):
        url_list = '/foo'
        a = cli2.Field()
        b = cli2.Field(parameter='b')

    httpx_mock.add_response(url='http://lol/foo?page=1&b=1', json=dict(
        items=[dict(a=1, b=1), dict(a=3, b=1)],
    ))
    httpx_mock.add_response(url='http://lol/foo?page=2&b=1', json=dict())
    client = Client(base_url='http://lol')
    ones = await client.Model.find(Model.b == 1).list()
    assert [x.a for x in ones] == [1, 3]


@pytest.mark.asyncio
async def test_model_crud(httpx_mock):
    class Model(Client.Model):
        url_list = '/foo'
    assert Model(id=1).url == '/foo/1'

    httpx_mock.add_response(url='http://lol/foo/2', json=dict(id=2, a=1))
    client = Client(base_url='http://lol')
    result = await client.Model.get(id=2)
    assert result.data == dict(id=2, a=1)

    httpx_mock.add_response(url='http://lol/foo/2', method='DELETE')
    await result.delete()


@pytest.mark.asyncio
async def test_client_cli2(httpx_mock):
    assert Client.cli.name == 'client'
    assert Client.cli.doc == 'doc'

    httpx_mock.add_response(url='http://lol/foo', json=[1])
    meth = Client.cli['get']
    resp = await meth.async_call('/foo')
    assert resp.json() == [1]

    class Foo(Client.Model):
        id = cli2.Field()
        url_list = '/foo'

    meth = Client.cli['foo']['get']
    httpx_mock.add_response(url='http://lol/foo/1', json=dict(id=1, a=2))
    result = await meth.async_call('id=1')
    assert isinstance(result, Foo)
    assert result.data == dict(id=1, a=2)

    meth = Client.cli['foo']['find']
    httpx_mock.add_response(
        url='http://lol/foo?page=1',
        json=[dict(id=1, a=2)],
    )
    httpx_mock.add_response(url='http://lol/foo?page=2', json=[])
    result = await meth.async_call()


@pytest.mark.asyncio
async def test_object_command(httpx_mock):
    class Model(Client.Model):
        url_list = '/foo'
    httpx_mock.add_response(url='http://lol/foo/1', json=dict(id=1))
    httpx_mock.add_response(url='http://lol/foo/1', method='DELETE')
    await Client.cli['model']['delete'].async_call('1')
