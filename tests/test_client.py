from datetime import datetime
import cli2
import chttpx
import httpx
import inspect
import mock
import pytest


async def _response(**kwargs):
    return httpx.Response(**kwargs)


class HandlerSentinel(chttpx.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    async def __call__(self, client, response, tries, log):
        self.calls.append((client, response.status_code, tries))
        return await super().__call__(client, response, tries, log)


@pytest.fixture
def client_class():
    class TestClient(chttpx.Client):
        """ doc """
        class Paginator(chttpx.Paginator):
            def pagination_parameters(self, params, page_number):
                if page_number > 1:
                    params['page'] = page_number

        def __init__(self, *args, **kwargs):
            kwargs.setdefault('base_url', 'http://lol')
            super().__init__(*args, **kwargs)
    return TestClient


@pytest.mark.asyncio
async def test_client_cli(client_class, httpx_mock):
    class TestModel(client_class.Model):
        url_list = '/'

    class TestModel2(client_class.Model):
        pass

    class TestModel3(client_class.Model):
        @cli2.cmd
        def find():
            pass

    assert client_class.cli
    factory = client_class.cli.overrides['self']['factory']
    assert isinstance(factory(), client_class)

    httpx_mock.add_response(url='http://lol', json=[1])
    response = await client_class.cli['get'].async_call('http://lol')
    assert response.json() == [1]

    assert 'testmodel' in client_class.cli
    assert client_class.cli['testmodel']['get'].overrides['cls']['factory']
    assert not inspect.ismethod(client_class.cli['testmodel']['get'].target)
    command = client_class.cli['testmodel']['get']
    command.parse()
    await command.factories_resolve()
    result = client_class.cli['testmodel']['get']['cls'].value
    assert issubclass(result, TestModel)
    assert isinstance(result.client, client_class)

    httpx_mock.add_response(url='http://lol/', json=[dict(a=1)])
    httpx_mock.add_response(url='http://lol/?page=2', json=[])
    await client_class.cli['testmodel']['find'].async_call()

    assert 'testmodel2' not in client_class.cli

    assert list(client_class.cli['testmodel3'].keys()) == ['help', 'find']


def test_client_cli_func(client_class):
    # test adding a normal function
    @client_class.cli.cmd
    def foo(test):
        pass
    client_class.cli['foo']('bar')


@pytest.mark.asyncio
async def test_client_cli_override(client_class, httpx_mock):
    class Client(client_class):
        def __init__(self, *args, **kwargs):
            self.test = 'bar'
            super().__init__(*args, **kwargs)

    class TestModel(Client.Model):
        url_list = '{client.test}/foo'

        @classmethod
        @cli2.cmd
        async def find(cls, foo):
            return cls.url_list

    @Client.cli.cmd
    def test():
        pass

    class TestModel2(Client.Model):
        @classmethod
        @cli2.cmd
        async def find(cls):
            return 'foo'

    class TestModel3(Client.Model):
        url_list = '{client.test}/foo'
        create = None

    assert await Client.cli['testmodel']['find'].async_call('bar') == 'bar/foo'

    assert await Client.cli['testmodel2']['find'].async_call() == 'foo'
    assert 'get' not in Client.cli['testmodel2']

    assert 'create' not in Client.cli['testmodel3']


def test_client_model(client_class):
    assert issubclass(client_class.Model, chttpx.Model)
    assert client_class.Model._client_class == client_class

    class TestModel(client_class.Model):
        pass
    assert TestModel._client_class == client_class

    assert TestModel in client_class.models

    client = client_class()
    assert client.TestModel.client == client


@pytest.mark.asyncio
async def test_async_factory(httpx_mock, client_class):
    class TestClient(client_class):
        @classmethod
        async def factory(cls):
            return cls(base_url='http://bar')

    class TestModel(TestClient.Model):
        url_list = '/2'

    TestClient.cli.overrides['self']['factory'] = TestClient.factory
    httpx_mock.add_response(url='http://bar/', json=[dict(a=1)])
    assert await TestClient.cli['get'].async_call('/')

    httpx_mock.add_response(url='http://bar/2', json=[dict(a=1)])
    httpx_mock.add_response(url='http://bar/2?page=2', json=[])
    await TestClient.cli['testmodel']['find'].async_call()


@pytest.mark.asyncio
async def test_client_cli_side_effect(client_class, httpx_mock):
    from chttpx import example

    # test that this didn't spill over client_class
    test_client_cli(client_class, httpx_mock)

    # Test that Client's __init_subclass__ did setup a factory for self
    assert isinstance(
        await example.APIClient.cli['get']['self'].factory_value(),
        example.APIClient,
    )

    # Test that Model's __init_subclass__ did setup a factory for cls
    httpx_mock.add_response(url='http://localhost:8000/1', json=[1])
    result = await example.cli['get'].async_call('/1')
    assert result.json() == [1]

    httpx_mock.add_response(
        url='http://localhost:8000/objects/1/',
        json=dict(id=1, a=2),
    )
    result = await example.cli['object']['get'].async_call('id=1')
    assert result.id == 1
    assert result.data['a'] == 2


raised = False


@pytest.mark.asyncio
async def test_error_remote(httpx_mock, client_class):
    class TokenClient(client_class):
        async def token_get(self):
            return 'token'

    client = TokenClient()
    httpx_mock.add_response(url='http://lol', json=[1])

    async def raises(*a, **k):
        global raised
        raised = True
        raise httpx.RemoteProtocolError('foo')
    client.client.send = raises
    old_client = client.client
    response = await client.get('http://lol')
    assert client.client is not old_client
    assert raised
    assert response.json() == [1]

    httpx_mock.add_response(url='http://lol', json=[1])
    assert (await client.get('http://lol')).json() == [1]


@pytest.mark.asyncio
async def test_factory(httpx_mock, client_class):
    class Client(client_class):
        token_str = 'lol'

        def client_factory(self):
            client = super().client_factory()
            client.headers['X-ApiKey'] = self.token_str
            return client

    client = Client()
    assert client.client.headers['X-ApiKey'] == 'lol'
    del client.client
    client.token_str = 'bar'
    assert client.client.headers['X-ApiKey'] == 'bar'


@pytest.mark.asyncio
async def test_client_handler(httpx_mock, client_class):
    class Client(client_class):
        def client_factory(self):
            client = super().client_factory()
            client.send = mock.Mock()
            return client

    client = Client(handler=HandlerSentinel())

    # test response retry
    client.client.send.side_effect = [
        _response(status_code=500),
        _response(status_code=200),
    ]
    response = await client.request('GET', '/')
    assert response.status_code == 200
    assert client.handler.calls == [
        (client, 500, 0),
        (client, 200, 1),
    ]

    # test TransportError retry
    client.client.send.side_effect = [
        httpx.TransportError("foo"),
        _response(status_code=200),
    ]
    assert response.status_code == 200
    assert client.handler.calls == [
        (client, 500, 0),
        (client, 200, 1),
    ]


@pytest.mark.asyncio
async def test_handler(client_class):
    log = mock.Mock()
    client = client_class()
    client.client_reset = mock.AsyncMock()
    client.token_reset = mock.AsyncMock()
    handler = chttpx.Handler(accepts=[201], refuses=[218], retokens=[418])

    response = httpx.Response(status_code=201)
    result = await handler(client, response, 0, log)
    assert result == response

    response = httpx.Response(status_code=200)
    result = await handler(client, response, 0, log)
    log.info.assert_called_once_with(
        'retry', status_code=200, tries=0, sleep=.0
    )
    assert not result

    response = httpx.Response(status_code=200, content='[2]')
    response.request = httpx.Request('POST', '/', json=[1])
    with pytest.raises(chttpx.RetriesExceededError) as exc:
        await handler(client, response, handler.tries + 1, log)
    log.info.assert_called_once_with(
        'retry', status_code=200, tries=0, sleep=.0
    )

    msg = 'Unacceptable response <Response [200 OK]> after 31 tries\n\x1b[0m\x1b[1mPOST /\x1b[0m\n-\x1b[37m \x1b[39;49;00m1\x1b[37m\x1b[39;49;00m\n\n\x1b[1mHTTP 200\x1b[0m\n-\x1b[37m \x1b[39;49;00m2\x1b[37m\x1b[39;49;00m\n'  # noqa
    assert str(exc.value) == msg

    response = httpx.Response(status_code=200)
    response.request = httpx.Request('GET', '/')
    with pytest.raises(chttpx.RetriesExceededError) as exc:
        await handler(client, response, handler.tries + 1, log)

    msg = 'Unacceptable response <Response [200 OK]> after 31 tries\n\x1b[0m\x1b[1mGET /\x1b[0m\n\x1b[1mHTTP 200\x1b[0m'  # noqa
    assert str(exc.value) == msg

    response = httpx.Response(status_code=218)
    response.request = httpx.Request('POST', '/')
    with pytest.raises(chttpx.RefusedResponseError) as exc:
        await handler(client, response, 1, log)

    assert exc.value.response
    assert exc.value.request
    assert exc.value.url
    assert exc.value.status_code
    assert exc.value.response

    response = httpx.Response(status_code=418)
    response.request = httpx.Request('POST', '/')
    with pytest.raises(chttpx.TokenGetError):
        await handler(client, response, 1, log)

    assert not client.client_reset.await_count
    exc = httpx.TransportError('foo')
    exc.request = response.request
    result = await handler(client, exc, 0, log)
    log.warn.assert_called_once_with(
        'reconnect',
        error="TransportError('foo')",
        method='POST',
        url='/',
    )
    assert not result
    assert client.client_reset.await_count == 1

    with pytest.raises(httpx.TransportError) as exc:
        await handler(
            client, httpx.TransportError('x'), handler.tries + 1, log
        )

    response = httpx.Response(status_code=418)
    assert not client.token_reset.await_count
    log.warn.reset_mock()
    result = await handler(client, response, 0, log)
    log.warn.assert_called_once_with(
        'retoken', status_code=418, tries=0, sleep=.0
    )
    assert not result
    assert client.token_reset.await_count == 1

    handler = chttpx.Handler(accepts=[], refuses=[222])

    response = httpx.Response(status_code=123)
    result = await handler(client, response, 0, log)
    assert result == response


@pytest.mark.asyncio
async def test_retry(httpx_mock, client_class):
    class Client(client_class):
        return_token = 1

        async def token_get(self):
            return self.return_token

        def client_factory(self):
            client = super().client_factory()
            client.send = mock.Mock()
            return client

    client = Client()

    current_client = client.client
    client.client.send.side_effect = [
        _response(status_code=500),
        _response(status_code=500),
        _response(status_code=200),
    ]
    response = await client.request('GET', '/')
    assert response.status_code == 200
    assert client.client == current_client
    assert client.token == 1


@pytest.mark.asyncio
async def test_token(httpx_mock, client_class):
    class HasToken(client_class):
        async def token_get(self):
            return 'token'

    httpx_mock.add_response(url='http://lol', method='POST', json=[1])
    client = HasToken()
    assert (await client.post('http://lol')).json() == [1]
    assert client.token == 'token'

    class NoToken(client_class):
        pass
    httpx_mock.add_response(url='http://lol', method='POST', json=[1])
    client = NoToken()
    assert (await client.post('http://lol')).json() == [1]
    assert client.token


@pytest.mark.asyncio
async def test_pagination(httpx_mock, client_class):
    httpx_mock.add_response(url='http://lol/', json=[dict(a=1)])
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])
    httpx_mock.add_response(url='http://lol/?page=3', json=[])
    client = client_class(base_url='http://lol')

    async def callback(item):
        item['b'] = item['a']

    paginator = client.paginate(
        '/',
        lambda item: item['b'] == 2,
        callback=callback,
    )
    assert await paginator.list() == [
        dict(a=2, b=2)
    ]


def test_paginator(client_class):
    class Client(client_class):
        paginator = 'foo'

    class Model1(Client.Model):
        pass

    class Model2(Client.Model):
        paginator = 'bar'

    client = Client()
    assert client.Model1.paginator == 'foo'
    assert client.Model2.paginator == 'bar'


@pytest.mark.asyncio
async def test_pagination_initialize(httpx_mock, client_class):
    httpx_mock.add_response(url='http://lol/', json=dict(
        total_pages=2,
        items=[dict(a=1)],
    ))
    httpx_mock.add_response(url='http://lol/?page=2', json=[dict(a=2)])
    httpx_mock.add_response(url='http://lol/?page=3', json=[])

    class PaginatedClient(client_class):
        def pagination_initialize(self, paginator, data):
            paginator.total_pages = data['total_pages']

    client = PaginatedClient(base_url='http://lol')
    assert await client.paginate('/').list() == [dict(a=1), dict(a=2)]

    httpx_mock.add_response(url='http://lol/', json=dict(
        total_pages=2,
        items=[dict(a=1)],
    ))
    assert await client.paginate('/').first() == dict(a=1)


@pytest.mark.asyncio
async def test_token_get(httpx_mock, client_class):
    httpx_mock.add_response(url='http://lol/token', json=dict(token=123))
    httpx_mock.add_response(url='http://lol/', json=[])

    class TokenClient(client_class):
        async def token_get(self):
            response = await self.get('/token')
            return response.json()['token']

    client = TokenClient(base_url='http://lol')
    await client.paginate('/').list()
    assert client.token


@pytest.mark.asyncio
async def test_pagination_model(httpx_mock, client_class):
    class Model(dict):
        pass

    httpx_mock.add_response(url='http://lol/', json=[dict(a=2)])
    httpx_mock.add_response(url='http://lol/?page=2', json=[])
    client = client_class(base_url='http://lol')
    result = await client.paginate('/', model=Model).list()
    assert isinstance(result[0], Model)


def test_paginator_fields(client_class):
    paginator = chttpx.Paginator(client_class(), '/')
    paginator.total_items = 95
    paginator.per_page = 10
    assert paginator.total_pages == 10


@pytest.mark.asyncio
async def test_pagination_patterns(httpx_mock, client_class):
    # I'm dealing with APIs which have a different pagination system on
    # different resources, and on some resources no pagination at all
    # Would like to define that per model

    class TotalModel(client_class.Model):
        url_list = '/foo'

        class Paginator(client_class.Paginator):
            def pagination_initialize(self, data):
                self.total_items = data['total_items']
                self.per_page = len(data['items'])

    httpx_mock.add_response(
        url='http://lol/foo',
        json=dict(total_items=2, items=[dict(a=1)]),
    )

    class Pages(client_class.Model):
        url_list = '/bar'

        class Paginator(client_class.Paginator):
            def pagination_initialize(self, data):
                self.total_pages = data['total_pages']
                self.per_page = len(data['items'])

    httpx_mock.add_response(
        url='http://lol/bar',
        json=dict(total_pages=1, items=[dict(a=1)]),
    )

    class Offset(client_class.Model):
        url_list = '/off'

        class Paginator(chttpx.Paginator):
            def pagination_initialize(self, data):
                self.total_items = data['total']

            def pagination_parameters(self, params, page_number):
                params['offset'] = (page_number - 1) * self.per_page
                params['limit'] = self.per_page

    httpx_mock.add_response(
        url='http://lol/off',
        json=dict(total=2, items=[dict(a=1)]),
    )

    client = client_class(base_url='http://lol')

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
    params = dict()
    paginator.pagination_parameters(params, 2)
    assert params == dict(offset=1, limit=1)


@pytest.fixture
def reverse_client(httpx_mock, client_class):
    class Paginator(client_class.Paginator):
        def pagination_initialize(self, data):
            self.total_pages = data['total_pages']

    # test that we can reverse pagination too
    class Client(client_class):
        paginator = Paginator

    return Client(base_url='http://lol')


@pytest.mark.asyncio
async def test_pagination_reverse(reverse_client, httpx_mock):
    httpx_mock.add_response(
        url='http://lol/bar',
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
    paginator = reverse_client.paginate('/bar')
    paginator = paginator.reverse()
    results = await paginator.list()
    assert [x['a'] for x in results] == [5, 4, 3, 2, 1]


@pytest.mark.asyncio
async def test_pagination_last(httpx_mock, reverse_client):
    httpx_mock.add_response(
        url='http://lol/bar',
        json=dict(total_pages=3, items=[dict(a=1), dict(a=2)]),
    )
    httpx_mock.add_response(
        url='http://lol/bar?page=3',
        json=dict(total_pages=3, items=[dict(a=5)]),
    )
    paginator = reverse_client.paginate('/bar')
    last_item = await paginator.last_item()
    assert last_item['a'] == 5


@pytest.mark.asyncio
async def test_paginator_call(httpx_mock):
    httpx_mock.add_response(
        url='http://lol/bar',
        json=dict(items=[dict(a=1), dict(a=2)]),
    )
    client = chttpx.Client(base_url='http://lol')
    paginator = client.paginate('/bar')
    cb = mock.AsyncMock()
    await paginator.call(cb)
    assert cb.call_args_list == [mock.call({'a': 1}), mock.call({'a': 2})]


def test_descriptor(client_class):
    class Model(client_class.Model):
        id = chttpx.Field()
        bar = chttpx.Field('nested/bar')
        foo = chttpx.Field('undeclared/foo')

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

    model = Model()
    assert model.foo == ''
    assert not model.changed_fields
    model.foo = 'bar'
    assert model.changed_fields == dict(foo='')
    model = Model(foo='bar')
    model.foo = 'foo'
    assert model.changed_fields == dict(foo='bar')


def test_jsonstring(client_class):
    class Model(client_class.Model):
        json = chttpx.JSONStringField()

    client = client_class()
    model = client.Model(data=dict(json='{"foo": 1}'))
    assert model.json == dict(foo=1)

    model.json['foo'] = 2
    assert model.json == dict(foo=2)
    assert model.data['json'] == '{"foo": 2}'

    model = client.Model()
    model.json = dict(a=1)
    assert model.data['json'] == '{"a": 1}'

    model = client.Model(data=dict(json=''))
    assert model.json == ''


def test_datetime(client_class):
    class Model(client_class.Model):
        dt = chttpx.DateTimeField()

    model = Model(dict(dt='2020-11-12T01:02:03'))
    assert model.dt == datetime(2020, 11, 12, 1, 2, 3)
    model.dt = datetime(2020, 10, 12, 1, 2, 3)
    assert model.data['dt'] == '2020-10-12T01:02:03'


def test_model_inheritance(client_class):
    class Model(client_class.Model):
        foo = chttpx.Field()

    class Model2(Model):
        bar = chttpx.Field()

    client = client_class()
    assert [*client.Model._fields.keys()] == ['foo']
    assert [*client.Model2._fields.keys()] == ['bar', 'foo']


def test_relation_simple(client_class):
    class Child(client_class.Model):
        foo = chttpx.Field()

    class Father(client_class.Model):
        child = chttpx.Related('Child')

    client = client_class()
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


def test_relation_many(client_class):
    class Child(client_class.Model):
        foo = chttpx.Field()

    class Father(client_class.Model):
        children = chttpx.Related('Child', many=True)

    client = client_class()
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
async def test_python_expression(httpx_mock, client_class):
    class Paginator(client_class.Paginator):
        def pagination_initialize(self, data):
            self.total_pages = data['total_pages']

    class Model(client_class.Model):
        url_list = '/foo'
        a = chttpx.Field()
        b = chttpx.Field()
        paginator = Paginator

    def mock():
        httpx_mock.add_response(url='http://lol/foo', json=dict(
            total_pages=2,
            items=[dict(a=1, b=1), dict(a=2, b=2), dict(a=3, b=1)],
        ))

        httpx_mock.add_response(url='http://lol/foo?page=2', json=dict(
            total_pages=2,
            items=[dict(a=4, b=1), dict(a=5, b=2)],
        ))

    client = client_class(base_url='http://lol')

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
async def test_expression_parameter(httpx_mock, client_class):
    class Model(client_class.Model):
        url_list = '/foo'
        a = chttpx.Field()
        b = chttpx.Field(parameter='b')

    httpx_mock.add_response(url='http://lol/foo?b=1', json=dict(
        items=[dict(a=1, b=1), dict(a=3, b=1)],
    ))
    httpx_mock.add_response(url='http://lol/foo?page=2&b=1', json=dict())
    client = client_class(base_url='http://lol')
    ones = await client.Model.find(Model.b == 1).list()
    assert [x.a for x in ones] == [1, 3]


@pytest.mark.asyncio
async def test_model_crud(httpx_mock, client_class):
    class Model(client_class.Model):
        url_list = '/foo'
    assert Model(id=1).url == '/foo/1'

    httpx_mock.add_response(url='http://lol/foo/2', json=dict(id=2, a=1))
    client = client_class(base_url='http://lol')
    result = await client.Model.get(id=2)
    assert result.data == dict(id=2, a=1)

    httpx_mock.add_response(url='http://lol/foo/2', method='DELETE')
    await result.delete()


@pytest.mark.asyncio
async def test_client_cli2(httpx_mock, client_class):
    class Foo(client_class.Model):
        id = chttpx.Field()
        url_list = '/foo'

    assert client_class.cli.name == 'test'
    assert client_class.cli.doc == 'doc'

    httpx_mock.add_response(url='http://lol/foo', json=[1])
    meth = client_class.cli['get']
    resp = await meth.async_call('/foo')
    assert resp.json() == [1]

    meth = client_class.cli['foo']['get']
    httpx_mock.add_response(url='http://lol/foo/1', json=dict(id=1, a=2))
    result = await meth.async_call('id=1')
    assert isinstance(result, Foo)
    assert result.data == dict(id=1, a=2)

    meth = client_class.cli['foo']['find']
    httpx_mock.add_response(
        url='http://lol/foo',
        json=[dict(id=1, a=2)],
    )
    httpx_mock.add_response(url='http://lol/foo?page=2', json=[])
    result = await meth.async_call()


@pytest.mark.asyncio
async def test_object_command(httpx_mock, client_class):
    class Model(client_class.Model):
        url_list = '/foo'
    httpx_mock.add_response(url='http://lol/foo/1', json=dict(id=1))
    httpx_mock.add_response(url='http://lol/foo/1', method='DELETE')
    await client_class.cli['model']['delete'].async_call('1')


@pytest.mark.parametrize('intern,extern', (
    ('2025-02-13T16:09:30.745517', datetime(2025, 2, 13, 16, 9, 30, 745517)),
    ('2025-02-13T16:09:30', datetime(2025, 2, 13, 16, 9, 30)),
))
def test_datetime_fmts(intern, extern, client_class):
    class DtModel(client_class.Model):
        dt = chttpx.DateTimeField()
    model = client_class().DtModel(dict(dt=intern))
    assert model.dt == extern


def test_datetime_fmt(client_class):
    class DtModel(client_class.Model):
        dt = chttpx.DateTimeField(fmt='%d/%m/%Y %H:%M:%S')
    model = client_class().DtModel(dict(dt='13/02/2025 12:34:56'))
    assert model.dt == datetime(2025, 2, 13, 12, 34, 56)

    model.dt = datetime(2025, 2, 14, 12, 34, 56)
    assert model.data['dt'] == '14/02/2025 12:34:56'


def test_datetime_error(client_class):
    class DtModel(client_class.Model):
        dt = chttpx.DateTimeField()
    model = client_class().DtModel(dict(dt='13/024:56'))
    with pytest.raises(chttpx.FieldExternalizeError):
        model.dt


def test_datetime_default_fmt(client_class):
    class DtModel(client_class.Model):
        dt = chttpx.DateTimeField()
    model = client_class().DtModel()
    model.dt = datetime(2025, 2, 13, 16, 9, 30)
    assert model.data['dt'] == '2025-02-13T16:09:30.000000'

    str_dt = '2025-02-14T16:09:30.000000'
    model.dt = str_dt
    assert model.data['dt'] == str_dt


@pytest.mark.asyncio
async def test_mask_recursive(client_class, monkeypatch):
    client = client_class(mask=chttpx.Mask(['scrt', 'password']))
    client.client.send = mock.AsyncMock()

    log = mock.Mock()
    monkeypatch.setattr(chttpx, 'log', log)
    response = httpx.Response(
        status_code=200,
        content='{"pub": 1, "foo": [{"scrt": "pass"}]}',
    )
    data = [dict(foo=[dict(src='pass')])]
    response.request = httpx.Request('POST', '/', json=data)
    client.client.send.return_value = response
    await client.post('/', json=data)
    log.bind.assert_called_once_with(
        method='POST',
        url='http://lol/',
    )
    log = log.bind.return_value
    log.debug.assert_called_once_with(
        'request',
        json=[{'foo': [{'src': 'pass'}]}],
    )
    log.info.assert_called_once_with(
        'response',
        status_code=200,
        json={'pub': 1, 'foo': [{'scrt': '***MASKED***'}]},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'key', ('json', 'data'),
)
async def test_mask_logs(client_class, key, monkeypatch):
    client = client_class(mask=chttpx.Mask(['scrt', 'password']))
    client.client.send = mock.AsyncMock()

    log = mock.Mock()
    monkeypatch.setattr(chttpx, 'log', log)
    response = httpx.Response(
        status_code=200,
        content='{"pub": 1, "scrt": "pass"}',
    )
    data = dict(foo='bar', password='secret')
    response.request = httpx.Request('POST', '/', **{key: data})
    client.client.send.return_value = response
    await client.post('/', **{key: data})
    log.bind.assert_called_once_with(
        method='POST',
        url='http://lol/',
    )
    log = log.bind.return_value
    log.debug.assert_called_once_with(
        'request',
        **{key: dict(foo='bar', password='***MASKED***')},
    )
    log.info.assert_called_once_with(
        'response',
        status_code=200,
        json=dict(pub=1, scrt='***MASKED***'),
    )


@pytest.mark.asyncio
async def test_mask_exceptions(client_class):
    class TestClient(client_class):
        mask_keys = ['foo']

    client = TestClient()

    response = httpx.Response(status_code=218, content='{"c": 3, "d": 4}')
    response.request = httpx.Request('POST', '/', json=dict(a=1, b=2))
    client.mask.keys.add('a')
    client.mask.keys.add('c')
    error = chttpx.ResponseError(client, response, 1)
    expected = "\n\x1b[0m\x1b[1mPOST /\x1b[0m\n\x1b[94ma\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[94mb\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m2\x1b[37m\x1b[39;49;00m\n\n\x1b[1mHTTP 218\x1b[0m\n\x1b[94mc\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[94md\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m4\x1b[37m\x1b[39;49;00m\n"  # noqa
    assert str(error) == expected

    # this needs to work with form data too
    response = httpx.Response(status_code=218, content='{"c": 3, "d": 4}')
    response.request = httpx.Request('POST', '/', data=dict(a=1, b=2))
    client.mask = chttpx.Mask(['a', 'c'])
    error = chttpx.ResponseError(client, response, 1)
    expected = "\n\x1b[0m\x1b[1mPOST /\x1b[0m\n\x1b[94ma\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[94mb\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m2\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\n\x1b[1mHTTP 218\x1b[0m\n\x1b[94mc\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[94md\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m4\x1b[37m\x1b[39;49;00m\n"  # noqa
    assert str(error) == expected


@pytest.mark.asyncio
async def test_request_mask(client_class, monkeypatch):
    client = client_class(mask=chttpx.Mask(['password']))
    client.client.send = mock.AsyncMock()

    log = mock.Mock()
    monkeypatch.setattr(chttpx, 'log', log)
    response = httpx.Response(
        status_code=200,
        content='{"pub": 1, "scrt": "pass"}',
    )
    data = dict(foo='bar', password='secret')
    response.request = httpx.Request('POST', '/', json=data)
    client.client.send.return_value = response
    client.mask.keys.add('scrt')
    await client.post('/', json=data)
    log.bind.assert_called_once_with(
        method='POST',
        url='http://lol/'
    )
    log = log.bind.return_value
    log.debug.assert_called_once_with(
        'request',
        json=dict(foo='bar', password='***MASKED***'),
    )
    log.info.assert_called_once_with(
        'response',
        status_code=200,
        json=dict(pub=1, scrt='***MASKED***'),
    )


@pytest.mark.asyncio
async def test_log_content(client_class, monkeypatch):
    client = client_class()
    client.client.send = mock.AsyncMock()
    log = mock.Mock()
    monkeypatch.setattr(chttpx, 'log', log)
    response = httpx.Response(status_code=200, content='lol:]bar')
    response.request = httpx.Request('POST', '/')
    client.client.send.return_value = response
    await client.post('/', content='lol:]foo')
    log.bind.assert_called_once_with(
        method='POST',
        url='http://lol/'
    )
    log = log.bind.return_value
    log.debug.assert_called_once_with('request', content='lol:]foo')
    log.info.assert_called_once_with(
        'response', status_code=200, content=b'lol:]bar'
    )


@pytest.mark.asyncio
async def test_log_quiet(client_class, monkeypatch):
    client = client_class()
    client.client.send = mock.AsyncMock()
    log = mock.Mock()
    monkeypatch.setattr(chttpx, 'log', log)
    response = httpx.Response(status_code=200, content='[1]')
    response.request = httpx.Request('GET', '/')
    client.client.send.return_value = response
    await client.get('/', json=[1], quiet=True)
    log.bind.assert_called_once_with(
        method='GET',
        url='http://lol/',
    )
    log = log.bind.return_value
    assert not log.debug.call_args_list
    log.info.assert_called_once_with('response', status_code=200)


def test_class_override(client_class):
    class TestClient(client_class):
        semaphore = 'foo'
        mask_keys = ['bar']
        debug = True

    assert TestClient().semaphore == 'foo'
    assert TestClient().mask.keys == {'bar'}
    assert TestClient().debug


@pytest.mark.asyncio
async def test_save(client_class, httpx_mock):
    class TestModel(client_class.Model):
        id = chttpx.Field()
        foo = chttpx.Field()

    client = client_class()
    model = client.TestModel(id=1, foo='bar')

    with pytest.raises(Exception):
        await model.save()

    client.TestModel.url_list = '/test'
    httpx_mock.add_response(
        method='POST',
        url='http://lol/test/1',
        json=dict(id=1, foo=2),
        match_json=dict(id=1, foo='bar'),
    )
    await model.save()
    assert model.id == 1
    assert model.foo == 2

    model = client.TestModel(foo='bar')
    httpx_mock.add_response(
        method='POST',
        url='http://lol/test',
        json=dict(id=1, foo='bar'),
        match_json=dict(foo='bar'),
    )
    await model.save()
    assert model.id == 1
    assert model.foo == 'bar'


def test_id_value(client_class):
    class TestModel(client_class.Model):
        id = chttpx.Field()
    assert client_class().TestModel(id=1).id_value == 1

    class TestModel2(client_class.Model):
        bar = chttpx.Field()
        id_field = 'bar'
    assert client_class().TestModel2(bar=1).id_value == 1


@pytest.mark.asyncio
async def test_debug(client_class, monkeypatch):
    client = client_class(mask=chttpx.Mask(['scrt', 'password']), debug=True)
    client.client.send = mock.AsyncMock()

    log = mock.Mock()
    monkeypatch.setattr(chttpx, 'log', log)

    response = httpx.Response(
        status_code=200,
        content='{"pub": 1, "scrt": "pass"}',
    )
    data = dict(foo='bar', password='secret')
    response.request = httpx.Request('POST', '/', json=data)
    client.client.send.return_value = response
    await client.post('/', json=data, quiet=True)
    log.bind.assert_called_once_with(
        method='POST',
        url='http://lol/',
    )
    log = log.bind.return_value
    log.debug.assert_called_once_with(
        'request',
        json=dict(foo='bar', password='secret'),
    )
    log.info.assert_called_once_with(
        'response',
        status_code=200,
        json=dict(pub=1, scrt='pass'),
    )


@pytest.mark.asyncio
async def test_url_list(client_class):
    class Client(client_class):
        def __init__(self, *args, **kwargs):
            self.foo = '/foo'
            super().__init__(*args, **kwargs)

    class TestModel(Client.Model):
        url_list = '{client.foo}/bar'

    client = Client()
    assert client.TestModel.url_list == '/foo/bar'


@pytest.mark.asyncio
async def test_client_token_apply(client_class, httpx_mock):
    class TokenClient(client_class):
        async def token_get(self):
            return self._token

        def client_token_apply(self, client):
            client.token = self.token

    client = TokenClient()
    client._token = 1
    await client.token_refresh()
    assert client.token == 1
    assert client.client.token == 1

    # token_reset will cause a new token
    client._token = 2
    await client.token_reset()
    await client.token_refresh()
    assert client.token == 2
    assert client.client.token == 2

    # client_reset on its own doesn't refresh token
    client._token = 3
    await client.client_reset()
    assert client.token == 2
    assert client.client.token == 2


def test_client_command(client_class, httpx_mock):
    class Client(client_class):
        post_call_called = False

        def __init__(self, base_url, *args, **kwargs):
            kwargs['base_url'] = base_url
            super().__init__(*args, **kwargs)

        @classmethod
        async def factory(self, base_url):
            return Client(base_url)

        @classmethod
        def setargs(self, cmd):
            cmd.arg('base_url', position=0, kind='POSITIONAL_ONLY')

        async def post_call(self, cmd):
            await self.client.post('/logoff')

    class Model(Client.Model):
        url_list = '/foo'

    assert 'get' in Client.cli['model']

    assert Client.cli['get'].client is None
    cmd = Client.cli['get']
    assert isinstance(cmd, Client.cmdclass)
    httpx_mock.add_response(url='http://x/foo', json=[])
    httpx_mock.add_response(url='http://x/logoff')
    result = cmd('http://x', '/foo')
    assert result.status_code == 200

    httpx_mock.add_response(url='http://x/foo', json=[])
    httpx_mock.add_response(url='http://x/logoff')
    assert Client.cli['model']['get'].client is None
    cmd = Client.cli['model']['find']
    cmd('http://x')

    Client.post_call_called = False
    cmd = Client.cli['model']['get']
    cmd()
    assert not Client.post_call_called

    cmd = Client.cli['request']
    cmd()
    assert not Client.post_call_called
