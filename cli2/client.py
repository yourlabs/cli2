"""
HTTP Client boilerplate code to conquer the world.
"""

from urllib.parse import parse_qs

import asyncio
import copy
import httpx
import inspect
import json
import math
import os
import ssl
import structlog
from datetime import datetime

try:
    import truststore
except ImportError:
    truststore = None

from . import display
from .asyncio import async_resolve
from .command import Command
from .colors import colors
from .group import Group
from .decorators import cmd, hide


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
        obj = copy.copy(self)
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
        response = await self.client.get(self.url, params=params, quiet=True)
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
    iso_fmt = '%Y-%m-%dT%H:%M:%S.%f'
    default_fmts = [
        iso_fmt,
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
        raise FieldExternalizeError(
            f'Could not figure how to parse {value}, use fmt option',
            self, obj, value,
        )

    def internalize(self, obj, value):
        """
        Convert a datetime into an internal string.
        """
        if isinstance(value, str):
            return value
        return value.strftime(self.fmt or self.iso_fmt)


class Related(MutableField):
    """
    Related model field.

    .. py:attribute:: model

        *STRING* name of the related model class.

    .. py:attribute:: many

        Set this to True if you're expecting a list of models in the field.
    """
    def __init__(self, model, many=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.many = many

    def internalize(self, obj, data):
        """
        Return the related object's data.
        """
        if not self.many:
            return data.data

        return [item.data for item in data]

    def externalize(self, obj, value):
        """
        Instanciate the related model class with the value.
        """
        model_class = getattr(obj.client, self.model)
        if not self.many:
            return model_class(value)
        return [model_class(item) for item in value]


class ModelCommand(Command):
    """
    Command class for Model class.
    """
    def __init__(self, target, *args, **kwargs):
        # unbound method by force
        target = getattr(target, '__func__', target)
        super().__init__(target, *args, **kwargs)
        self.overrides['self']['factory'] = self.get_object
        self.overrides['cls']['factory'] = self.get_model

    def setargs(self):
        super().setargs()
        if 'self' in self:
            self.arg('id', position=1, kind='POSITIONAL_ONLY', doc='ID')

    async def get_client(self):
        client = self.group.parent.overrides['self']['factory']()
        return await async_resolve(client)

    async def get_model(self):
        return getattr(await self.get_client(), self.model.__name__)

    async def get_object(self):
        model = await self.get_model()
        return await model.get(id=self['id'].value)


class ModelGroup(Group):
    def __init__(self, cls):
        super().__init__(
            name=cls.__name__.lower(),
            doc=inspect.getdoc(cls),
            cmdclass=type(
                'ModelCommand',
                (cls.model_command,),
                dict(model=cls),
            )
        )

        if cls.url_list:
            self.cmd(cls.find)
            self.cmd(cls.get)
            self.cmd(cls.delete)

        for name, method in cls.__dict__.items():
            wrapped_method = getattr(method, '__func__', None)
            if hasattr(wrapped_method, 'cli2'):
                self.cmd(wrapped_method)
            elif hasattr(method, 'cli2'):
                self.cmd(method)


class ModelMetaclass(type):
    def __new__(cls, name, bases, attributes):
        cls = super().__new__(cls, name, bases, attributes)
        client = getattr(cls, 'client', None)
        if client:
            return cls

        client_class = getattr(cls, '_client_class', None)
        if client_class:
            client_class.models.append(cls)
            client_cli = getattr(client_class, 'cli', None)
            if client_cli:
                cls.cli = client_cli[cls.__name__.lower()] = ModelGroup(cls)

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

        return cls


class Model(metaclass=ModelMetaclass):
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

    .. py:attribute:: id_field

        Name of the field that should be used as resource identifier, `id` by
        default.

    .. py:attribute:: url

        Object URL based on :py:attr:`url_detail` and :py:attr:`id_field`.
    """
    paginator = Paginator
    model_command = ModelCommand
    model_group = ModelGroup
    url_list = None
    url_detail = '{self.url_list}/{self.id_value}'
    id_field = 'id'

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
    @hide('expressions')
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

    @property
    def url(self):
        if 'url_list' in self.url_detail and not self.url_list:
            raise Exception(f'{type(self).__name__}.url_list not set')
        return self.url_detail.format(self=self)

    async def delete(self):
        """
        Delete model

        DELETE request on :py:attr:`url`
        """
        return await self.client.delete(self.url)

    @classmethod
    @cmd(doc="""
    POST request to create. Example:

        create name=foo
    """)
    async def create(cls, **kwargs):
        """
        Instanciate a model with kwargs and run :py:meth:`save`.
        """
        obj = cls(**kwargs)
        await obj.save()
        return obj

    @classmethod
    @cmd(doc="""
    Get a model based on kwargs. Example:

        get id=3
    """)
    async def get(cls, **kwargs):
        """
        Instanciate a model with kwargs and run :py:meth:`hydrate`.
        """
        obj = cls(**kwargs)
        await obj.hydrate()
        return obj

    async def hydrate(self):
        """
        Refresh data with GET requset on :py:attr:`url_detail`
        """
        response = await self.client.get(self.url)
        self.data.update(response.json())

    async def save(self):
        """
        Call :py:meth:`update` if `self.id` otherwise :py:meth:`instanciate`.

        Then updates :py:attr:`data` based on the response.json if possible.

        You might want to override this.
        """
        if self.id_value:
            response = await self.update()
        else:
            response = await self.instanciate()

        try:
            data = response.json()
        except json.JSONDecodeError:
            pass
        else:
            self.data = data

        return response

    async def instanciate(self):
        """
        POST :py:attr:`data` to :py:attr:`url_list`, update data with response
        json.

        You might want to override this.
        """
        if not self.url_list:
            raise Exception(f'{type(self).__name__}.url_list not set')
        return await self.client.post(self.url_list, json=self.data)

    async def update(self):
        """
        POST :py:attr:`data` to :py:attr:`url_list`, update data with response
        json.

        You might want to override this.
        """
        return await self.client.post(self.url, json=self.data)

    @property
    def id_value(self):
        """
        Return value of the :py:attr:`id_field`.
        """
        return getattr(self, self.id_field)


class ClientMetaclass(type):
    def __new__(cls, name, bases, attributes):
        cls = super().__new__(cls, name, bases, attributes)

        # bind ourself as _client_class to any inherited model
        cls.Model = type('Model', (Model,), dict(_client_class=cls))
        cls.models = []

        cli_kwargs = dict(
            name=cls.__name__.lower().replace('client', '') or 'client',
            doc=inspect.getdoc(cls),
            overrides=dict(
                cls=dict(factory=lambda: cls),
                self=dict(factory=lambda: cls())
            ),
        )
        cli_kwargs.update(cls.__dict__.get('cli_kwargs', dict()))
        cls.cli = Group(**cli_kwargs)
        cls.cli.cmd(cls.get)
        return cls


class Handler:
    """
    .. py:attribute:: tries

        Number of retries for an un-accepted request prior to failing.
        Default: 30

    .. py:attribute:: backoff

        Will sleep ``number_of_tries * backoff`` prior to retrying.
        Default: `.1`

    .. py:attribute:: accepts

        Accepted status codes, you should always set this to ensure responses
        with an unexpected status either retry or raise.
        Default: range(200, 299)

    .. py:attribute:: refuses

        List of refused status codes, responses returning those will not retry
        at all and raise directly.
        Default: [400, 404]

    .. py:attribute:: retokens

        Status codes which trigger a new call of :py:meth:`~Client.token_get`
        prior to a retry. Only one retry is done then by this handler,
        considering that authenticating twice in a row is useless: there's a
        problem in your credentials instead.
        Default: [401, 403, 407, 511]
    """
    retokens_defaults = [401, 403, 407, 511]
    accepts_defaults = range(200, 299)
    refuses_defaults = [400, 404]
    tries_default = 30
    backoff_default = .1

    def __init__(self, accepts=None, refuses=None, retokens=None, tries=None,
                 backoff=None):

        if retokens is None:
            self.retokens = copy.copy(self.retokens_defaults)
        else:
            self.retokens = retokens

        if accepts is None:
            self.accepts = copy.copy(self.accepts_defaults)
        else:
            self.accepts = accepts

        if refuses is None:
            self.refuses = copy.copy(self.refuses_defaults)
        else:
            self.refuses = refuses

        self.tries = self.tries_default if tries is None else tries
        self.backoff = self.backoff_default if backoff is None else backoff

    async def __call__(self, client, response, tries, mask):
        if isinstance(response, Exception):
            if tries >= self.tries:
                raise response
            # httpx session is rendered unusable after a TransportError
            if isinstance(response, httpx.TransportError):
                await client.client_reset()
            return

        if self.accepts:
            if response.status_code in self.accepts:
                return response
        elif response.status_code not in self.refuses:
            return response

        if response.status_code in self.refuses:
            raise RefusedResponseError(client, response, tries, mask)

        if tries >= self.tries:
            raise RetriesExceededError(client, response, tries, mask)

        if response.status_code in self.retokens:
            if tries:
                # our authentication is just not working, no need to retry
                raise TokenGetError(client, response, tries, mask)
            await client.token_reset()

        await asyncio.sleep(tries * self.backoff)


class ClientError(Exception):
    pass


class ResponseError(ClientError):
    def __init__(self, client, response, tries, mask, msg=None):
        self.client = client
        self.response = response
        self.tries = tries
        self.mask = mask
        msg = msg or getattr(self, 'msg', '').format(self=self)
        super().__init__(self.enhance(msg))

    def enhance(self, msg):
        """
        Enhance an httpx.HTTPStatusError

        Adds beatiful request/response data to the exception.

        :param exc: httpx.HTTPStatusError
        """
        output = [msg]
        request_msg = ' '.join([
            self.response.request.method,
            str(self.response.request.url),
        ])

        output.append(
            f'{colors.reset}{colors.bold}{request_msg}{colors.reset}',
        )
        request = self.client.request_log_data(
            self.response.request,
            self.mask,
        )
        if request:
            output.append(display.render(request))

        output.append(
            f'{colors.bold}HTTP {self.response.status_code}{colors.reset}',
        )
        response = self.client.response_log_data(self.response, self.mask)
        if response:
            output.append(display.render(response))

        return '\n'.join(output)


class TokenGetError(ResponseError):
    msg = 'Authentication failed after {self.tries} tries'


class RefusedResponseError(ResponseError):
    msg = 'Response {self.response} refused'


class RetriesExceededError(ResponseError):
    msg = 'Unacceptable response {self.response} after {self.tries} tries'


class FieldError(ClientError):
    pass


class FieldValueError(FieldError):
    def __init__(self, msg, field, obj, value):
        super().__init__(msg)
        self.obj = obj
        self.field = field
        self.value = value


class FieldExternalizeError(FieldValueError):
    pass


class Client(metaclass=ClientMetaclass):
    """
    HTTPx Client Wrapper

    .. py:attribute:: paginator

        :py:class:`Paginator` class, you can leave it by default and just
        implement :py:meth:`pagination_initialize` and
        :py:meth:`pagination_parameters`.

    .. py:attribute:: semaphore

        Optionnal asyncio semaphore to throttle requests.

    .. py:attribute:: handler

        A callback that will take responses objects and decide wether or not to
        retry the request, or raise an exception, or return the request.
        Default is a :py:class:`Handler`

    .. py:attribute:: mask

        List of keys to mask in logging, ie.: ``['password', 'secret']``

    .. py:attribute:: debug

        Enforce full logging: quiet requests are logged, masking does not
        apply. This is also enabled with environment variable ``DEBUG``.

    .. py:attribute:: models

        Declared models for this Client.
    """
    paginator = Paginator
    models = []
    semaphore = None
    mask = []
    debug = False

    def __init__(self, *args, handler=None, semaphore=None, mask=None,
                 debug=False, **kwargs):
        """
        Instanciate a client with httpx.AsyncClient args and kwargs.
        """
        self._client = None
        self._client_args = args
        self._client_kwargs = kwargs
        self._client_attrs = None

        self.handler = handler or Handler()
        self.semaphore = semaphore if semaphore else self.semaphore
        self.mask = mask if mask else self.mask
        self.debug = debug or os.getenv('DEBUG', self.debug)

        if truststore:
            self._client_kwargs.setdefault(
                'verify',
                truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
            )

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
            self._client = self.client_factory()
        return self._client

    def client_factory(self):
        """
        Return a fresh httpx async client instance.
        """
        return httpx.AsyncClient(*self._client_args, **self._client_kwargs)

    @client.setter
    def client(self, value):
        self._client = value

    @client.deleter
    def client(self):
        self._client = None

    async def request_safe(self, *args, handler, mask, retries=True,
                           semaphore=None, **kwargs):
        """
        Internal request method
        """
        semaphore = semaphore or self.semaphore
        tries = 0

        async def _request():
            if semaphore:
                async with semaphore:
                    return await self.client.request(*args, **kwargs)
            return await self.client.request(*args, **kwargs)

        while retries or tries > 1:
            try:
                response = await _request()
            except Exception as exc:
                await handler(self, exc, tries, mask)
            else:
                if response := await handler(self, response, tries, mask):
                    return response

            tries += 1

        return response

    async def client_reset(self):
        del self.client

    async def token_reset(self):
        self.token = None

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

    async def request(self, method, url, handler=None, quiet=False,
                      accepts=None, refuses=None, tries=None, backoff=None,
                      retries=True, semaphore=None, mask=None, **kwargs):
        """
        Request method

        If your client defines a token_get callable, then it will
        automatically play it.

        If your client defines an asyncio semaphore, it will respect it.

        .. code-block:: python

            client = Client()

            await client.request(
                'GET',
                '/',
                # extend the current handler with 10 tries with 200 accepted
                # status code only
                tries=10,
                accepts=[200],
            )

            await client.request(
                'GET',
                '/',
                # you can also pass your own handler callable
                handler=Handler(tries=10, accepts=[200]),
                # that could also have been a function
            )


        :param method: HTTP Method name, GET, POST, etc
        :param url: URL to query
        :param handler: If a callable, will be called, if a dict, will extend
                        the client's :py:attr:`handler`.
        :param quiet: Wether to log or not, used by :py:class:`Paginator` to
                      not clutter logs with pagination. Meaning if you want to
                      debug pagination, you'll have to make it not quiet from
                      there.
                      If you really want to see all results, set
                      :py:attr:`debug` to True.
        :param retries: Wether to retry or not in case handler dosen't accept
                        the response, set to False if you want only 1 try.
        :param accepts: Override for :py:attr:`Handler.accepts`
        :param refuses: Override for :py:attr:`Handler.refuses`
        :param retries: Override for :py:attr:`Handler.retries`
        :param tries: Override for :py:attr:`Handler.tries`
        :param backoff: Override for :py:attr:`Handler.backoff`
        :param semaphore: Override for :py:attr:`Client.semaphore`
        :param mask: Override for :py:attr:`Client.mask`
        """
        if not self.token and not self.token_getting:
            self.token_getting = True
            try:
                self.token = await self.token_get()
            except NotImplementedError:
                self.token = True
            self.token_getting = False

        if handler is None:
            if accepts or refuses or tries or backoff:
                # if any handler kwarg, clone our handler and override
                handler = copy.deepcopy(self.handler)
                if accepts is not None:
                    handler.accepts = accepts
                if refuses is not None:
                    handler.refuses = refuses
                if tries is not None:
                    handler.tries = tries
                if backoff is not None:
                    handler.backoff = backoff
            else:
                handler = self.handler

        log = self.logger.bind(method=method, url=url)
        if not quiet or self.debug:
            log.debug('request', **self.kwargs_log_data(kwargs, mask, quiet))

        response = await self.request_safe(
            method,
            url,
            handler=handler,
            retries=retries,
            semaphore=semaphore,
            mask=lambda data: self.mask_data(data, mask),
            **kwargs,
        )

        _log = dict(status_code=response.status_code)
        if not quiet or self.debug:
            self.response_log_data(response, mask, _log)

        log.info('response', **_log)

        return response

    def response_log_data(self, response, mask, log=None):
        try:
            data = self.mask_data(response.json(), mask)
            key = 'json'
        except json.JSONDecodeError:
            data = self.mask_content(response.content, mask)
            key = 'content'

        if log:
            log[key] = data
        return data

    def request_log_data(self, request, mask, quiet=False):
        content = request.content.decode()
        try:
            return self.mask_data(json.loads(content), mask)
        except json.JSONDecodeError:
            pass

        parsed = parse_qs(content)
        if parsed:
            data = {
                key: value[0] if len(value) == 1 else value
                for key, value in parsed.items()
            }
            return self.mask_data(data, mask)

        return self.mask_content(content, mask)

    def kwargs_log_data(self, kwargs, mask, quiet=False):
        _log = kwargs.copy()
        if 'content' in kwargs:
            _log['content'] = self.mask_content(kwargs['content'], mask)
        for key in ('json', 'data'):
            if key in kwargs:
                _log[key] = self.mask_data(kwargs[key], mask)
        return _log

    def mask_content(self, content, mask=None):
        """
        Implement content masking for non JSON content here.
        """
        return content

    def mask_data(self, data, mask=None):
        """
        Apply mask for all :py:attr:`mask` in data.
        """
        if self.debug:
            return data

        mask = mask if mask is not None else self.mask

        if isinstance(data, list):
            return [self.mask_data(item, mask) for item in data]

        if isinstance(data, dict):
            for key, value in data.items():
                if key in mask:
                    data[key] = '***MASKED***'
                if isinstance(value, dict):
                    data[key] = self.mask_data(value, mask)
            return data

        return data

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
