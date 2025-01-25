import copy
import json
import httpx
import math
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

    You don't have to override that class to do basic paginator customization,
    instead, you can also implement pagination specifics into:

    - the :py:class:`~Client` class with the
      :py:meth:`~Client.pagination_initialize` and
      :py:meth:`~Client.pagination_parameters` methods

    - or also, per model, in the :py:class:`~Model` class with the
      :py:meth:`~Model.pagination_initialize` and
      :py:meth:`~Model.pagination_parameters` methods

    Refer to :py:meth:`pagination_parameters` and
    :py:meth:`pagination_initialize` for details.

    .. py:attribute:: total_pages

        Total number of pages.

    .. py:attribute:: total_items

        Total number of items.

    .. py:attribute:: per_page

        Number of items per page

    .. py:attribute:: url

        The URL to query

    .. py:attribute:: url

        The URL to query

    .. py:attribute:: params

        Dictionnary of GET parameters

    .. py:attribute:: model

        :py:class:`Model` class or ``dict`` by default.
    """

    def __init__(self, client, url, params=None, model=None):
        """
        Initialize a paginator object with a client on a URL with parameters.

        :param client: :py:class:`Client` object
        :param url: URL to query
        :param params: Dictionnary of GET parameters
        :params model: Model class, can be a dict, or :py:class:`Model`
        """
        self.client = client
        self.url = url
        self.params = params or {}
        self.model = model or dict
        self.page_start = 1
        self.per_page = None
        self.initialized = False

        self._total_pages = None
        self._total_items = None
        self._reverse = False

    def reverse(self):
        """
        Return a copy of this :py:class:`Paginator` object to iterate in
        reverse order.

        For this to work, :py:meth:`pagination_initialize` **must** set
        :py:attr:`per_page` and either of :py:attr:`total_pages` or
        :py:attr:`total_items`, which is up to you to implement.
        """
        obj = copy.deepcopy(self)
        obj._reverse = True
        return obj

    @property
    def total_items(self):
        return self._total_items

    @total_items.setter
    def total_items(self, value):
        self._total_items = value

    @property
    def total_pages(self):
        if self._total_pages:
            return self._total_pages
        if self.total_items and self.per_page:
            self._total_pages = math.ceil(self.total_items / self.per_page)
            return self._total_pages

    @total_pages.setter
    def total_pages(self, value):
        self._total_pages = value

    async def list(self):
        result = []
        async for item in self:
            result.append(item)
        return result

    async def initialize(self, response=None):
        """
        This method is called once when we get the first response.

        :param response: First response object
        """
        if not response:
            response = await self.page(1)

        data = response.json()
        if isinstance(data, list):
            # we won't figure max page
            self.initialized = True
            return

        self.pagination_initialize(data)
        self.initialized = True

    def pagination_initialize(self, data):
        """
        Initialize paginator based on the data of the first response.

        If at least, you can set :py:attr:`total_items` or
        :py:attr:`total_pages`, :py:attr:`per_page` would also be nice.

        :param data: Data of the first response
        """
        try:
            self.model.pagination_initialize
        except AttributeError:
            return self.client.pagination_initialize(self, data)
        else:
            return self.model.pagination_initialize(self, data)

    def pagination_parameters(self, page_number):
        """
        Return GET parameters for a given page.

        Calls :py:meth:`Model.pagination_parameters` if possible otherwise
        :py:meth:`Client.pagination_parameters`.
        """
        try:
            self.model.pagination_parameters
        except AttributeError:
            return self.client.pagination_parameters(self, page_number)
        else:
            return self.model.pagination_parameters(self, page_number)

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
            items = [self.model(item) for item in data]
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    items = [self.model(item) for item in value]
                    break
        if not self.per_page:
            self.per_page = len(items)
        return items

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
        params.update(self.pagination_parameters(page_number))
        response = await self.client.get(self.url, params=params)
        if not self.initialized:
            await self.initialize(response)
        return response

    async def __aiter__(self, callback=None):
        """
        Asynchronous iterator.
        """
        if self._reverse and not self.total_pages:
            first_page_response = await self.page(1)
            page = self.total_pages
        else:
            page = self.page_start

        while items := await self.page_items(page):
            if self._reverse:
                items = reversed(items)
            for item in items:
                yield item

            if self._reverse:
                page -= 1
                if not page:
                    break
                if page == 1:
                    # use cached first page response
                    items = self.response_items(first_page_response)
                    for item in reversed(items):
                        yield item
                    break
            else:
                if page == self.total_pages:
                    break
                page += 1


class Model:
    """

    You should never call this class directly, instead, get it from the
    :py:class:`Client` object after decorating your model classes with a
    client as such:

    .. code-block:: python



    .. py:attribute:: paginator

        :py:class:`Paginator` class, you can leave it by default and just
        implement :py:meth:`pagination_initialize` and
        :py:meth:`pagination_parameters`.

    .. py:attribute:: url_list

        The URL to get the list of objects, you're supposed to configure it as
        a model attribute in your model subclass.

    .. py:attribute:: url_detail

        The URL to get the details of an object, you're supposed to configure
        it as a model attribute in your model subclass.
    """
    paginator = Paginator
    url_list = None
    url_detail = '{cls.url_list}/{self.id}'

    def __init_subclass__(cls, **kwargs):
        if 'client' not in cls.__dict__:
            cls._client_class.models.append(cls)

            # we're going to want to ensure cls for Model does get the
            # Client().ModelClass

            # Which means we want to get the self factory for the Client class
            self_overrides = getattr(cls._client_class, 'cli2_self', {})
            self_factory = self_overrides.get('factory', None)
            if isinstance(self_factory, str):
                if self_factory == '__init__':
                    def self_factory():
                        return cls._client_class()
                else:
                    self_factory = getattr(cls._client_class, self_factory)

            # And create a factory of our own for cls of this Model so that
            # it calls the Client's ``self`` factory instanciated Client(),
            # and then the Model from that object
            async def factory():
                result = await async_resolve(self_factory())
                return getattr(result, cls.__name__)

            factories(cls=factory)(cls)
        super().__init_subclass__(**kwargs)

    def __init__(self, data=None):
        """
        Instanciate a model.

        :param data: JSON Data
        """
        self.data = data or dict()

    @classmethod
    def find(cls, **params):
        """
        Find objects filtered by GET params

        :param params: GET URL parameters
        """
        return cls.paginate(**params)

    @classmethod
    def paginate(cls, **params):
        """
        Return a :py:class:`Paginator` based on :py:attr:`url_list`
        """
        return cls.paginator(cls.client, cls.url_list, params, cls)

    @classmethod
    def pagination_initialize(cls, paginator, data):
        """
        Implement Model-specific pagination initialization here.

        Otherwise, :py:meth:`Client.pagination_initialize` will
        take place.

        Refer to :py:meth:`Paginator.pagination_initialize` for
        details.
        """
        cls.client.pagination_initialize(paginator, data)

    @classmethod
    def pagination_parameters(cls, paginator, page_number):
        """
        Implement Model-specific pagination parameters here.

        Otherwise, :py:meth:`Client.pagination_parameters` will
        take place.

        Refer to :py:meth:`Paginator.pagination_parameters` for
        details.
        """
        return cls.client.pagination_parameters(paginator, page_number)


class Client:
    """
    HTTPx Client

    .. py:attribute:: paginator

        :py:class:`Paginator` class, you can leave it by default and just
        implement :py:meth:`pagination_initialize` and
        :py:meth:`pagination_parameters`.
    """
    paginator = Paginator
    model = Model
    models = []

    def __init_subclass__(cls, **kwargs):
        # Registering the client class for this model
        cls.model = type(
            cls.model.__name__,
            (cls.model,),
            dict(_client_class=cls),
        )
        if not getattr(cls, 'cli2_self', {}):
            factories(cls)
        cls.models = []
        super().__init_subclass__(**kwargs)

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

        for model in self.models:
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

    '''
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
    '''

    def paginate(self, url, params=None, model=None):
        """
        Return a paginator to iterate over results

        :param url: URL to paginate on
        :param params: GET parameters
        :param model: Model class to cast for items
        """
        return self.paginator(self, url, params or {}, model or dict)

    def pagination_parameters(self, paginator, page_number):
        """
        Implement Model-specific pagination parameters here.

        Refer to :py:meth:`Paginator.pagination_parameters` for
        details.
        """
        return dict(page=page_number)

    def pagination_initialize(self, paginator, data):
        """
        Implement Model-specific pagination initialization here.

        Refer to :py:meth:`Paginator.pagination_initialize` for
        details.
        """
