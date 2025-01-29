"""
HTTP Client boilerplate code to conquer the world.
"""

import copy
import json
import httpx
import math
import structlog
from datetime import datetime

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

    def __init__(self, client, url, params=None, model=None, expressions=None):
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
        self.expressions = []
        for expression in (expressions or []):
            if not isinstance(expression, Expression):
                expression = Filter(expression)
            self.expressions.append(expression)

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
        self.results = []
        async for item in self:
            self.results.append(item)
        return self.results

    async def initialize(self, response=None):
        """
        This method is called once when we get the first response.

        :param response: First response object
        """
        if not response:
            response = await self.page_response(1)

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

        You should implement something like this in your model or client to
        enable pagination:

        .. code-block:: python

            def pagination_parameters(self, paginator, page_number):
                return dict(page=page_number)
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

        items_list = []
        if isinstance(data, list):
            items_list = data
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    items_list = value
                    break

        items = [self.model(item) for item in items_list]
        if not self.per_page:
            self.per_page = len(items_list)

        return items

    def python_filter(self):
        filters = [
            f
            for f in self.expressions
            if not f.parameterable
        ]
        if filters:
            return And(*filters)

    async def page_items(self, page_number):
        """
        Return the items of a given page number.

        :param page_number: Page number to get the items from
        """
        try:
            return self.response_items(await self.page_response(page_number))
        except NotImplementedError:
            return []

    async def page_response(self, page_number):
        """
        Return the response for a page.

        :param page_number: Page number to get the items from
        """
        params = self.params.copy()
        pagination_parameters = self.pagination_parameters(page_number)
        if pagination_parameters:
            params.update(pagination_parameters)
        elif page_number != 1:
            raise NotImplementedError(
                'pagination_parameters returned None, cannot paginate',
            )
        for expression in self.expressions:
            if expression.parameterable:
                expression.params(params)
        response = await self.client.get(self.url, params=params)
        if not self.initialized:
            await self.initialize(response)
        return response

    async def __aiter__(self, callback=None):
        """
        Asynchronous iterator.
        """
        if self._reverse and not self.total_pages:
            first_page_response = await self.page_response(1)
            page = self.total_pages
        else:
            page = self.page_start

        python_filter = self.python_filter()

        while items := await self.page_items(page):
            if items == 'continue':
                continue

            if self._reverse:
                items = reversed(items)

            for item in items:
                if not python_filter or python_filter.matches(item):
                    yield item

            if self._reverse:
                page -= 1
                if not page:
                    break
                if page == 1:
                    # use cached first page response
                    items = self.response_items(first_page_response)
                    for item in reversed(items):
                        if not python_filter or python_filter.matches(item):
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

        cls._fields = dict()

        def process_cl(cl):
            for key, obj in cl.__dict__.items():
                if not isinstance(obj, Field):
                    continue

                if not obj.data_accessor:
                    obj.data_accessor = key

                cls._fields[key] = obj
                obj.name = key

        process_cl(cls)

        def process_bases(cl):
            for base in cl.__bases__:
                process_cl(base)
                process_bases(base)

        process_bases(cls)

        super().__init_subclass__(**kwargs)

    def __init__(self, data=None, **values):
        """
        Instanciate a model.

        :param data: JSON Data
        """
        self._data = data or dict()
        self._data_updating = False
        self._dirty_fields = []
        self._field_cache = dict()

        for key, value in values.items():
            setattr(self, key, value)

    @property
    def data(self):
        """
        Just ensure we update dirty data prior to returning the data dict.
        """
        if self._dirty_fields and not self._data_updating:
            self._data_updating = True
            for field in self._dirty_fields:
                field.clean(self)
            self._dirty_fields = []
            self._data_updating = False
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @classmethod
    def find(cls, *expressions, **params):
        """
        Find objects filtered by GET params

        :param params: GET URL parameters
        :param expressions: :py:class:`Expression` list
        """
        return cls.paginate(cls.url_list, *expressions, **params)

    @classmethod
    def paginate(cls, url, *expressions, **params):
        """
        Return a :py:class:`Paginator` based on :py:attr:`url_list`
        :param expressions: :py:class:`Expression` list
        """
        return cls.paginator(cls.client, url, params, cls, expressions)

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

    @property
    def cli2_display(self):
        return self.data


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

        self.logger = structlog.get_logger('cli2')
        self.token_getting = False
        self.token = None

        for model in self.models:
            model = type(model.__name__, (model,), dict(client=self))
            setattr(self, model.__name__, model)

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
                del self.token
                tries -= 1
                if not tries:
                    raise

    async def token_get(self):
        """
        Authentication dance to get a token.

        This method will automatically be called by :py:meth:`request` if it
        finds out that :py:attr:`token` is None.

        This is going to depend on the API you're going to consume, basically
        it's very client-specific.

        By default, this method does nothing. Implement it to your likings.

        This method is supposed to return the token, but doesn't do anything
        with it by itself: it's up to you to call something like:

        .. code-block::

            async def token_get(self):
                response = await self.post('/login', dict(...))
                token = response.json()['token']
                self.client.headers['token'] = f'Bearer {token}'
                return token
        """
        raise NotImplementedError()

    async def request(self, method, url, **kwargs):
        """
        Request method

        If your client defines a token_get callable, then it will
        automatically play it.

        If your client defines an asyncio semaphore, it will respect it.
        """
        if not self.token and not self.token_getting:
            self.token_getting = True
            try:
                self.token = await self.token_get()
            except NotImplementedError:
                self.token = True
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

        response.raise_for_status()

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

    def pagination_initialize(self, paginator, data):
        """
        Implement Model-specific pagination initialization here.

        Refer to :py:meth:`Paginator.pagination_initialize` for
        details.
        """


class Expression:
    def __init__(self, field, value):
        self.field = field
        self.value = value
        self.parameterable = bool(field.parameter)

    def params(self, params):
        raise NotImplementedError()

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __str__(self):
        return self.compile()


class Equal(Expression):
    def params(self, params):
        params[self.field.parameter] = self.value

    def matches(self, item):
        return self.field.__get__(item) == self.value


class Filter(Expression):
    def __init__(self, function):
        self.function = function
        # This filter works with Python functions
        self.parameterable = False

    def matches(self, item):
        return self.function(item)


class LesserThan(Expression):
    def matches(self, item):
        value = self.field.__get__(item)
        if not value:
            return False
        return value < self.value


class GreaterThan(Expression):
    def matches(self, item):
        value = self.field.__get__(item)
        if not value:
            return False
        return value > self.value


class StartsWith(Expression):
    def matches(self, item):
        value = self.field.__get__(item)
        if not value:
            return False
        return str(value).startswith(self.value)


class Expressions(Expression):
    def __init__(self, *expressions):
        self.expressions = expressions
        self.parameterable = all(exp.parameterable for exp in expressions)


class Or(Expressions):
    def matches(self, value):
        for exp in self.expressions:
            if exp.matches(value):
                return True
        return False


class And(Expressions):
    def matches(self, value):
        for exp in self.expressions:
            if not exp.matches(value):
                return False
        return True


class Field:
    """
    Field descriptor for models.

    The basic Field descriptor manages (get and set) data from within the
    :py:attr:`Model.data` JSON.

    Since sub-classes are going to convert data, we need to understand the
    concepts of internal and external data:

    - external: the Python value, this can be any kind of Python object
    - internal: the Python representation of the JSON value, this can be any
      Python type that will work given json.dumps
    - internalizing: process of converting a Python value into a JSON one
    - externalizing: process of converting a JSON value into something Python

    .. py:attribute:: data_accessor

        Describes how to access the Field's data inside the model's data dict.
        If data_accessor is ``foo`` then this field will control the ``foo``
        key in the model's data dict.
        Use ``/`` to separate keys when nesting, if data_accessor is
        ``foo/bar`` then it will control the ``bar`` key of the ``foo`` dict in
        the model's data dict.

    .. py:attribute:: parameter

        Name of the GET parameter on the model's :py:attr:`Model.url_list`, if
        any. So that the filter will be converted to a GET parameter.
        Otherwise, filtering will happen in Python.
    """
    def __init__(self, data_accessor=None, parameter=None):
        self.data_accessor = data_accessor
        self.parameter = parameter

    def __get__(self, obj, objtype=None):
        """
        Get the value of a field for an object.

        A simple process:

        - Get the internal value from :py:meth:`internal_get`
        - Pass it through the :py:meth:`externalize` method prior to returning
          it.
        """
        if obj is None:
            return self

        data = self.internal_get(obj)
        return self.externalize(obj, data)

    def __set__(self, obj, value):
        """
        Set the value in the internal :py:attr:`Model.json` dict.

        A two-step process:

        - Use :py:meth:`internalize` to convert the Python external value into
          a Python representation of the JSON value
        - Use :py:meth:`internal_set` to actually set the internal
          :py:attr:`Model.data`
        """
        value = self.internalize(obj, value)
        self.internal_set(obj, value)

    def internal_get(self, obj):
        """
        Get the "raw" value from the object, which is a Python representation
        of the JSON internal value, using :py:attr:`data_accessor`.
        """
        data = obj.data
        if not isinstance(data, dict):
            return self.__get__(data, type(data))

        for key in self.data_accessor.split('/'):
            if not data:
                return ''
            try:
                data = data[key]
            except KeyError:
                return
        return data

    def internal_set(self, obj, value):
        """
        Using :py:attr:`data_accessor`, set the value in :py:attr:`Model.data`
        """
        parts = self.data_accessor.split('/')
        data = obj.data
        for number, key in enumerate(parts, start=1):
            if number == len(parts):
                data[key] = value
                break
            if key not in data:
                data[key] = dict()
            data = data[key]

    def internalize(self, obj, value):
        """
        Transform external value into JSON internal value.

        Any kind of processing from the Python value to the JSON value can be
        done in this method.
        """
        return value

    def externalize(self, obj, value):
        """
        Transform internal JSON value to Python value, based on
        :py:attr:`data_accessor`.

        Any kind of processing from the JSON value to the Python value can be
        done in this method.
        """
        return value

    def mark_dirty(self, obj):
        """
        Tell the model that the data must be cleaned.
        """
        obj._dirty_fields.append(self)

    def clean(self, obj):
        """
        Clean the data.

        Called by the Model when requested a :py:attr:`data`, this method:

        - Gets the externalized value from :py:meth:`__get__`
        - Convert it into a JSON object with :py:meth:`internalize`
        - Uses :py:meth:`internal_set` to update :py:attr:`Model.data`
        """
        externalized = self.__get__(obj)
        internalized = self.internalize(obj, externalized)
        self.internal_set(obj, internalized)

    def __eq__(self, value):
        return Equal(self, value)

    def __gt__(self, value):
        return GreaterThan(self, value)

    def __lt__(self, value):
        return LesserThan(self, value)

    def startswith(self, value):
        return StartsWith(self, value)


class MutableField(Field):
    """
    Base class for mutable value fields like :py:class:`JSONStringField`

    Basically, this field:

    - caches the externalized value, so that you can mutate it
    - marks the field as dirty so you get the internalized mutated value that
      next time you get the :py:attr:`Model.data`
    """
    def cache_set(self, obj, value):
        """
        Cache a computed value for obj

        :param obj: Model object
        """
        obj._field_cache[self.name] = value

    def cache_get(self, obj):
        """
        Return cached value for obj

        :param obj: Model object
        """
        return obj._field_cache[self.name]

    def __get__(self, obj, objtype=None):
        """
        Return safely mutable value.

        If the value is not found in cache, externalize the internal value and
        cache it.

        Always mark the field as dirty given the cached external data may
        mutate.
        """
        if not obj:
            return super().__get__(obj, objtype)

        try:
            return self.cache_get(obj)
        except KeyError:
            externalized = self.externalize(obj, self.internal_get(obj))
            self.cache_set(obj, externalized)
            return externalized
        finally:
            if not obj._data_updating:
                self.mark_dirty(obj)

    def __set__(self, obj, value):
        """
        Cache the value prior to setting it normally.
        """
        self.cache_set(obj, value)
        super().__set__(obj, value)


class JSONStringField(MutableField):
    """
    Yes, some proprietary APIs have JSON fields containing JSON strings.

    This Field is the cure the world needed for that disease.

    .. py:attribute:: options

        Options dict for json.dumps, ie. ``options=dict(indent=4)``
    """
    def __init__(self, *args, options=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = options or dict()

    def internalize(self, obj, data):
        return json.dumps(data, **self.options)

    def externalize(self, obj, value):
        return json.loads(value)


class DateTimeField(Field):
    """
    JSON has no datetime object, which means different APIs will serve us
    different formats in string variables.

    Heck, I'm pretty sure there are even some APIs which use different formats.
    This is the cure the world needed against that disease.

    .. py:attribute:: fmt

        The datetime format for Python's strptime/strftime.

    .. py:attribute:: fmts

        A list of formats, in case you don't have one. This list will be
        populated with :py:attr:`default_fmts` by default.

    .. py:attribute:: default_fmts

        A class property containing a list of formats we're going to try to
        figure `fmt` and have this thing "work by default". Please contribute
        to this list with different formats.
    """
    default_fmts = [
        '%Y-%m-%dT%H:%M:%S',
    ]

    def __init__(self, *args, fmt=None, fmts=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fmt = fmt
        self.fmts = fmts
        if not self.fmt and not self.fmts:
            self.fmts = self.default_fmts

    def externalize(self, obj, value):
        """
        Convert the internal string into an external datetime.
        """
        if self.fmt:
            return datetime.strptime(value, self.fmt)

        # try a bunch of formats and hope for the best
        for fmt in self.default_fmts:
            try:
                value = datetime.strptime(value, fmt)
            except ValueError:
                continue
            else:
                self.fmt = fmt
                return value
        raise Exception(
            f'Could not figure how to parse {value}, use fmt option'
        )

    def internalize(self, obj, value):
        """
        Convert a datetime into an internal string.
        """
        if isinstance(value, str):
            return value
        if not self.fmt:
            raise Exception('fmt required')
        return value.strftime(self.fmt)


class Related(MutableField):
    """
    Related model field.

    .. py:attribute:: model

        *STRING* name of the related model class.
    """
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def internalize(self, obj, data):
        """
        Return the related object's data.
        """
        return data.data

    def externalize(self, obj, value):
        """
        Instanciate the related model class with the value.
        """
        return getattr(obj.client, self.model)(value)
