import json
import httpx
import structlog

try:
    import truststore
except ImportError:
    truststore = None

from .asyncio import async_resolve
from .decorators import factories


class Paginator:
    """
    Generic pagination class.
    """

    def __init__(self, client, url, params, model=None):
        self.client = client
        self.url = url
        self.params = params
        self.model = model or None
        self.page_start = 1
        self.page_end = None
        self.per_page = None
        self.initialized = False

    async def list(self):
        result = []
        async for item in self:
            result.append(item)
        return result

    async def initialize(self, response=None):
        """
        This method is called once when we get the first response.

        It will call :py:meth:`pagination_initialize` which you are free to
        implement in either the Pagination class or the
        :py:cls:`~cli2.client.Client` class.

        :param response: First response object
        """
        if not response:
            response = await self.page(1)

        data = response.json()
        if isinstance(data, list):
            # we won't figure max page
            self.initialized = True
            return

        self.page_end, self.per_page = self.pagination_initialize(data)
        self.initialized = True

    def pagination_initialize(self, data):
        """
        Return last page number and number of items per page as tuple.

        :param data: Data of the first response
        """
        return self.client.pagination_initialize(data)

    def response_items(self, response):
        """
        Parse a response and return a list of model items.

        :param response: Response to parse
        """
        try:
            data = response.json()
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [self.model(item) for item in data]
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    return [self.model(item) for item in value]

    async def page_items(self, page_number):
        """
        Return the items of a given page number.

        :param page_number: Page number to get the items from
        """
        return self.response_items(await self.page(page_number))

    async def page(self, page_number):
        """
        Return the response for a page.

        :param page_number: Page number to get the items from
        """
        params = self.params.copy()
        params["page"] = page_number
        response = await self.client.get(self.url, params=params)
        if not self.initialized:
            await self.initialize(response)
        return response

    async def __aiter__(self, callback=None):
        """
        Asynchronous iterator.
        """
        page = self.page_start
        while items := await self.page_items(page):
            for item in items:
                yield item

            if page == self.page_end:
                break
            page += 1


class Client:
    """
    HTTPx Client
    """
    paginator = Paginator

    def __init__(self, *args, **kwargs):
        """
        Instanciate a client with httpx.AsyncClient args and kwargs.
        """
        self._client = None
        self._client_args = args
        self._client_kwargs = kwargs
        self._client_attrs = None

        if truststore:
            self._client_kwargs.setdefault('verify', truststore.SSLContext)

        for model in getattr(self, '_models', []):
            model = type(model.__name__, (model,), dict(client=self))
            setattr(self, model.__name__, model)

        self.logger = structlog.get_logger('cli2')

    @property
    def client(self):
        """
        Return last client object used, unless it raised RemoteProtocolError.
        """
        if not self._client:
            self._client = httpx.AsyncClient(
                *self._client_args,
                **self._client_kwargs,
            )
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    @client.deleter
    def client(self):
        self._client = None

    async def request_safe(self, *args, **kwargs):
        """
        Request method that retries with a new client if RemoteProtocolError.
        """
        tries = 30
        while tries:
            try:
                return await self.client.request(*args, **kwargs)
            except httpx.RemoteProtocolError:
                # enforce getting a new awaitable
                del self.client
                tries -= 1
                if not tries:
                    raise

    async def request(self, method, url, **kwargs):
        """
        Request method

        If your client defines a token_get callable, then it will
        automatically play it.

        If your client defines an asyncio semaphore, it will respect it.
        """
        if (
            # we don't have a token
            not getattr(self, 'token', None)
            # but we do have a token_get implementation
            and getattr(self, 'token_get', None)
            # and we're not in the process of getting a token
            and not getattr(self, 'token_getting', None)
        ):
            self.token_getting = True
            self.token = await self.token_get()
            self.token_getting = False

        log = self.logger.bind(method=method, url=url)
        log.debug('request', **kwargs)

        semaphore = getattr(self, 'semaphore', None)
        if semaphore:
            async with semaphore:
                response = await self.request_safe(method, url, **kwargs)
        else:
            response = await self.request_safe(method, url, **kwargs)

        _log = dict(status_code=response.status_code)
        try:
            _log['json'] = response.json()
        except json.JSONDecodeError:
            _log['content'] = response.content

        log.info('response', **_log)

        return response

    async def get(self, url, *args, **kwargs):
        """ GET Request """
        return await self.request('GET', url, *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        """ POST Request """
        return await self.request('POST', url, *args, **kwargs)

    async def put(self, url, *args, **kwargs):
        """ PUT Request """
        return await self.request('PUT', url, *args, **kwargs)

    async def head(self, url, *args, **kwargs):
        """ HEAD Request """
        return await self.request('HEAD', url, *args, **kwargs)

    async def delete(self, url, *args, **kwargs):
        """ DELETE Request """
        return await self.request('DELETE', url, *args, **kwargs)

    @classmethod
    def model(cls, model_class):
        """
        Register a model class for this client.

        You will then be able to access the model class as an attribute of the
        client object, with the ``.client`` attribute bound.
        """
        models = getattr(cls, '_models', None)
        if not models:
            models = cls._models = []

        self_overrides = getattr(cls, 'cli2_self', {})
        self_factory = self_overrides.get('factory', None)
        if isinstance(self_factory, str):
            if self_factory == '__init__':
                def self_factory():
                    return cls()
            else:
                self_factory = getattr(cls, self_factory)

        async def factory():
            result = await async_resolve(self_factory())
            return getattr(result, model_class.__name__)

        factories(cls=factory)(model_class)
        models.append(model_class)
        return model_class

    def paginate(self, url, params=None, model=None):
        """
        Return a paginator to iterate over results

        :param url: URL to paginate on
        :param params: GET parameters
        :param model: Model class to cast for items
        """
        return self.paginator(self, url, params or {}, model or dict)

    def pagination_initialize(self, data):
        """
        You need to implement the logic to return last_page and per_page if
        possible based on the data you are given.
        """
        return None, None
