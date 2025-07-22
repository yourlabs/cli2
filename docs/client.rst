HTTPX Framework
~~~~~~~~~~~~~~~

The goal of chttpx module is to provide a generic framework to
build HTTP client libs and CLIs onto, after carrying this pattern from a
project to another, I've refactored this stuff here:

- great logging: Sent/Received JSON output is dumped as YAML, colored in
  console, and not-colored to file
- ``export LOG_LEVEL=DEBUG`` to enable debug output
- debug output always saved in ``~/.local/cli2/log``, **they will eventually fill
  up your drive and I've not yet decided a solution against that**, but I just
  love this feature,
- absolutely beautiful HTTP Exceptions
- ``export HTTP_DEBUG=1`` for low-level HTTP Debugging output
- **a ORM for REST resources**

Setup
=====

Installation:

    pip install chttpx  # or cli2[httpx]

Then:

.. code-block:: python

   import chttpx

Crash Course
============

Improved httpx client
---------------------

Use the chttpx layer instead of httpx directly and benefit from logging,
retries, reconnections, etc:

.. code-block:: python

    client = chttpx.Client(base_url='http://example.com')
    obj = dict(name='New object')
    response = await client.post('/objects', obj)
    obj = response.json()  # refresh object data

Model classes
-------------

You don't have to spagetti code business logic and object state by creating
:py:class:`~chttpx.Model` classes:

.. code-block:: python

    class Obj(chttpx.Client.Model):
        url_list = '/objects'

        id = chttpx.Field()
        name = chttpx.Field()

        async def save(self):
            response = await self.client.post(self.url_list, self.data)
            self.data.update(response.json())
            return response

    obj = client.Obj(name='New object')
    await obj.save()  # POST {'name': 'New object'} to /objects

Ok but what if you need to debug this? All `python programming techniques
are explained here
<https://yourlabs.org/posts/2025-07-08-python-fu-metaprogramming-object-oriented-testing-debugging-crash-course/>`_

Command Line
------------

And you can also have a CLI if you implement a factory class method into your
client:

.. code-block:: python

    class YourClient(chttpx.Client):
        @classmethod
        def factory(cls):
            return cls(base_url='http://example.com')

Point ``console_scripts`` entry point to:
``your.module:YourClient.cli.entry_point``

Testing
-------

While httpx-mock works, chttpx provides an automated fixture writer, just write
the test and:

- first run calls a real API, writes the responses in a file which you commit
  in git
- subsequent runs will use the responses file instead of hitting the API

.. code-block:: python

    @pytest.mark.chttpx_mock
    def test_object_story(test_name):
        client = YourClient.factory()
        obj = YourClient.Obj(name='New object')
        await obj.save()
        assert obj.id, 'save() method must add the generated id'

Complete Example
================

Of course all this is designed to combine very well with CLIs, because once
you have a library for an API, which you're going to embed in god knows what
(your API server, an Ansible plugin ...), you'll want to work with a CLI to
debug stuff: discover the API and implement features incrementally.

.. _Example Client:

Source code
-----------

.. literalinclude:: ../chttpx/chttpx/example.py

Mind you, the Object can be used in a Django-ish ORM style and all these CLIs
were created with free Sphinx documentation as seen in :ref:`Example CLI`.

Outputs are just beautiful of course:

.. image:: example_client_object_usage.png

See a builtin command with a custom command in action:

.. image:: example_client_rename.png

The debug output is also awesome:

.. image:: example_client_debug.png

It shows:

- the JSON being sent to the server
- request/method/url/timestamp
- the JSON being returned by the server
- response status code returned by the server
- finnaly, the return value of the command, which is the created object, see
  how the returned object was updated with the id and createAt fields which
  came from the response

Of course, you're going to be able to override/customize everything as you dig
into the API that you're implementing a client for.

Architecture
============

The client module is built around 3 main moving parts:

- :py:class:`~chttpx.Client`: A wrapper around the ``httpx.AsyncClient``
  class,
- :py:class:`~chttpx.Handler`: Used by the client to automate response
  handling: do we retry, need to re-create a TCP Session, or get a new token...
- :py:class:`~chttpx.Model`: A Django-like model metaclass, that comes
  with it's :py:class:`~chttpx.Field` classes and their expressions_

Tutorial
========

Creating a Client
-----------------

Start by extending a :py:class:`~chttpx.Client`:

.. code-block:: python

    import chttpx

    class YourClient(chttpx.Client):
        pass

    # you get a CLI for free
    cli = YourClient.cli

There are a few methods that you might want to override:

- :py:meth:`~chttpx.Client.client_factory`: where you can customize the
  actual httpx AsyncClient instance before it is used by cli2 Client.
- :py:meth:`~chttpx.Client.token_get`: if you want your client to do some
  authentication dance to get a token
- :py:attr:`~chttpx.Client.cli_kwargs`: Overrides for the for the
  :py:attr:`~chttpx.Client.cli` :py:class:`~cli2.cli.Group`

Pagination
----------

The default :py:class:`~chttpx.Paginator` doesn't know how to paginate.
Let's teach it to make a page GET parameter:

.. code-block:: python

    class YourClient(chttpx.Client):
        class Paginator(chttpx.Paginator):
            def pagination_parameters(self, params, page_number):
                params['page'] = page_number

That will increments a ``page`` GET parameter until it gets an empty results
list, which works but is still sub-optimal. Let's teach it when to stop by
setting total_pages in :py:meth:`~chttpx.Paginator.pagination_initialize`:

.. code-block:: python

    class YourClient(chttpx):
        class Paginator(chttpx.Paginator):
            def pagination_parameters(self, params, page_number):
                params['page'] = page_number

            def pagination_initialize(self, data):
                self.total_pages = data['total_pages']

Perhaps you don't get the total pages from the API response, but you do get a
total number of items, which you can set
:py:attr:`~chttpx.Paginator.total_items` and
:py:attr:`~chttpx.Paginator.total_pages` will auto-calculate:

.. code-block:: python

    class Paginator(chttpx.Paginator):
        def pagination_initialize(self, data):
            self.total_items = data['total_items']

Perhaps you're dealing with an offset/limit type of pagination, in which case,
``page`` GET parameter won't do, set offlet/limit instead in
:py:meth:`~chttpx.Paginator.pagination_parameters`:

.. code-block:: python

    class OffsetPagination(chttpx.Paginator):
        def pagination_parameters(self, params, page_number):
            self.per_page = 1
            params['offset'] = (page_number - 1) * self.per_page
            params['limit'] = self.per_page

        def pagination_initialize(self, data):
            self.total_items = data['total']

Creating a Model
----------------

Then, register a :py:class:`~chttpx.Model` for this client by subclassing
it's ``.Model`` attribute.

.. code-block:: python

    class YourObject(YourClient.Model):
        pass

Several things are happening here:

- ``YourObject._client_class`` was set to ``YourClient``
- ``YourClient.Models`` was set to ``[YourObject]``

Now, you're not supposed to use ``YourObject`` directly, but instead get it
from the client:

.. code-block:: python

    client = YourClient()
    model_class = client.YourObject

You can also define a specific paginator:

.. code-block:: python

    class YourModel(YourClient.Model):
        paginator = YourPaginator

Model.client
------------

As such, the model class you're using has the ``client`` instance set as
``.client`` class attribute. And magically, you can use ``self.client`` or
``cls.client`` anywhere in your model:

.. code-block:: python

    class YourObject(YourClient.Model):
        @classmethod
        @cli2.cmd
        async def some_command(cls):
            return await cls.client.get('/some-page').json()

Model.paginate
--------------

You can already paginate over objects:

.. code-block:: python

    async for obj in client.YourObject.paginate('/some-url', somefilter='foo'):
        cli2.print(obj)

If you set the :py:attr:`url_list` attribute, then you can also use the
:py:meth:`chttpx.Model.find` method directly:

.. code-block:: python

    class YourObject(YourClient.Model):
        pass

    paginator = YourObject.find(somefilter='test')

Fields
------

You can also define fields for your Model as such:

.. code-block:: python

    class YourModel(YourClient.Model):
        id = chttpx.Field()

You guessed it: this will may the ``id`` key of the :py:attr:`Model.data` to
the ``.id`` property. Which allows for more interesting things as we'll see...

Nested fields
`````````````

If you want to map ``data['company']['name']`` to ``company_name``, use slash
to define a nested data accessor:

.. code-block:: python

    class YourModel(YourClient.Model):
        company_name = chttpx.Field('company/name')

You can also "pythonize" any property with a simple accessor without any slash:

.. code-block:: python

    class YourModel(YourClient.Model):
        company_name = chttpx.Field('companyName')

Default factory
```````````````

Default field values can be computed at runtime with the
:py:meth:`~chttpx.Field.factory` decorator:

.. code-block:: python

    class YourModel(YourClient.Model):
        hasdefault = chttpx.Field()

        @hasdefault.factory
        def default_value(self):
            return 'something'

This will cause :py:attr:`~chttpx.Model.data` to have
``hasdefault='something'``.

If your default value factory depends on other fields, you need to declare
them, pass them as argument to factory:

.. code-block:: python

    class YourModel(YourClient.Model):
        required1 = chttpx.Field()
        required2 = chttpx.Field()
        hasdefault = chttpx.Field()

        @hasdefault.factory(required1, required2)
        def default_value(self):
            return f'something{self.required1}-{self.required2}'

Custom types
````````````

The most painful stuff I've had to deal with in APIs are datetimes and, "json
in json".

The cures for that are :py:class:`~chttpx.JSONStringField` and
:py:class:`~chttpx.DateTimeField`.

.. _expressions:

Expressions
```````````

Sometimes, we want to filter on fields which are not available in GET
parameters, in this case, we can filter in Python with SQL-Alchemy-like
expressions:

.. code-block:: python

   foo_stuff = YourModel.find(YourModel.company_name == 'foo')

You can also pass lambdas:

.. code-block:: python

   foo_stuff = YourModel.find(lambda item: item.company_name.lower() == 'foo')

Combine ands and ors:

.. code-block:: python

    foo_stuff = YourModel.find(
        (
            # all stuff with company starting with foo
            (lambda item: item.company_name.lower().startswith('foo'))
            # AND ending with bar
            & (lambda item: item.company_name.lower().endswith('bar'))
        )
        # OR with name test
        | YourModel.company_name == 'test'
    )

Parameterable
`````````````

Note that we want to delegate as much filtering as we can to the endpoint. To
delegate a filter to the endpoint, add a :py:attr:`~chttpx.Field.parameter`:

.. code-block:: python

    class YourModel(YourClient.Model):
        name = chttpx.Field(parameter='name')

This will indicate to the paginator that, given the following expression:

.. code-block:: python

    YourModel.find(YourModel.name == 'bar')

The paginator will add the ``?name=bar`` parameter to the URL.

This is nice when you want to just start coding then with only expressions and
not bother about which field is parameterable or not.

This looks a bit weak and of limited use as-is, because I haven't open-sourced
the OData part of my code yet, but that is able to generate a query string with
nested or/and/startswith/etc. That part won't end up in the core module anyway,
probably a ``cli2.contrib.odata`` module.

And I'm sure there are several other more or less protocols out there to do
this kind of things, so, we might as well have that here available for free.

Related
```````

If your endpoint returns data of a related model as such:

.. code-block:: yaml

    foo: 1
    related:
      bar: 2

You can normalize it with :py:class:`~chttpx.Related`:

.. code-block:: python

    class YourModel(YourClient.Model):
        foo = chttpx.Field()
        related = cli2.Related('Related')

    class Related(YourClient.Model):
        bar = chttpx.Field()

Due to a pretty ass-kicking :py:class:`~chttpx.MutableField` mechanic,
we're able to deal with it as such:

.. code-block:: python

    obj = await client.YourModel.get(foo=1)
    assert obj.foo == 1
    assert obj.related.bar == 2

    # update a field
    obj.related.bar = 3
    assert obj.related.bar == 3
    assert obj.data['related']['bar'] == 3

    # set a new object
    obj.related = client.Related(bar=4)
    assert obj.related.bar == 4
    assert obj.data['related']['bar'] == 4

Many Related
````````````

Given a list of relations:

.. code-block:: yaml

    foo: 1
    children:
    - bar: 1
    - bar: 2

You can normalize it with :py:attr:`~chttpx.MutableField.many`:

.. code-block:: python

    class YourModel(YourClient.Model):
        foo = cli2.Field()
        related = cli2.Related('Related', many=True)

    class Related(YourClient.Model):
        bar = cli2.Field()

Due to a pretty ass-kicking :py:class:`~chttpx.MutableField` mechanic,
you can work on the list return with the field descriptor:

.. code-block:: python

    obj = await client.YourModel.get(foo=1)
    assert obj.foo == 1
    # obj.related is a list
    assert obj.related[0].bar == 1
    assert obj.related[1].bar == 1

    # in which you can update models
    obj.related[0].bar = 3
    assert obj.related[0].bar == 3
    assert obj.data['related'][0]['bar'] == 3

    # append new items
    obj.related.append(client.Child(bar=4))
    assert obj.related[3].bar == 4
    assert obj.data['related'][3]['bar'] == 4

    # or even just replace
    obj.related = [client.Child(bar=5)]
    assert obj.related[0].bar == 5
    assert obj.data['related'][0]['bar'] == 5

It's just magic I love it!

Virtual fields
``````````````

Virtual fields are just like fields except that they don't live in the payload
:py:attr:`~chttpx.Model.data`. It allows to old attributes which belong to us
while generating defaults for data fields which belong to the remote API:

.. code-block:: python

    class YourModel(YourClient.Model):
        our_name = VirtualField()
        remote_name = Field()

        @remote_name.factory(our_name)
        def default_value(self):
            return f'something{self.our_name}'

Testing
=======

Let's write a test that calls the object create and delete command, say, in the
**tests/test_client_test.py** file:

.. code-block:: python

    @pytest.fixture
    def test_name(ts, chttpx_vars):
        # ts is a fixture provided by this plugin which contains the timestamp
        # chttpx_vars is variables that will be attached to the test fixture
        # doing this ensures you get either the fixture saved test_name either
        # a new one, unique thanks to the timestamp
        return chttpx_vars.setdefault('test_name', f'test{ts}')

    @pytest.mark.chttpx_mock
    def test_object_story(test_name):
        obj = APIClient.cli['object']['create'](f'name={test_name}')
        assert obj.name == test_name

        with pytest.raises(chttpx.RefusedResponseError):
            # test_name already exists!
            APIClient.cli['object']['create'](f'name={test_name}')

        APIClient.cli['object']['delete'](f'{obj.id}')

The first time you run this test, our example APIClient will connect to
localhost:8000 as it's configured by default, and actual queries will be
exeuted::

    [21/Mar/2025 10:35:11] "POST /objects/ HTTP/1.1" 201 38
    Bad Request: /objects/
    [21/Mar/2025 10:35:11] "POST /objects/ HTTP/1.1" 400 50
    [21/Mar/2025 10:35:11] "GET /objects/121/ HTTP/1.1" 200 38
    [21/Mar/2025 10:35:11] "DELETE /objects/121/ HTTP/1.1" 204 0

And the ``chttpx_mock`` pytest marker will cause new contents to be written for
you in **tests/fixtures/tests_test_client_test.py\:\:test_object_story.yaml**:

.. code-block:: yaml

    # first entry is the chttpx_vars that go with the fixture
    - test_name: test123123123
    # remaining entries are request/responses
    - request:
        event: request
        json:
          name: test33312
        level: debug
        method: POST
        timestamp: '2025-03-21 10:38:29'
        url: http://localhost:8000/objects/
      response:
        event: response
        json:
          data: {}
          id: 122
          name: test33312
        level: info
        method: POST
        status_code: '201'
        timestamp: '2025-03-21 10:38:29'
        url: http://localhost:8000/objects/
    - request:
        event: request
        json:
          name: test33312
        level: debug
        method: POST
        timestamp: '2025-03-21 10:38:29'
        url: http://localhost:8000/objects/
      response:
        event: response
        json:
          name:
          - object with this name already exists.
        level: info
        method: POST
        status_code: '400'
        timestamp: '2025-03-21 10:38:29'
        url: http://localhost:8000/objects/
    # and so on ...

You are supposed to add this file in git, because next time you run the test:
the ``chttpx_mock`` marker will provision pytest-httpx's ``httpx_mock`` will
all the request/responses that have been recorded in the fixture file.

As such, two new pytest options are added by the chttpx plugin:

- ``--chttpx-live``: don't use fixtures at all, run against the real network
- ``--chttpx-rewrite``: force rewriting all fixtures

When specifications change, you can remove a given test fixture and run the
test again which will rewrite it, or, run with ``--chttpx-rewrite`` to rewrite
all fixtures.

.. danger:: Because your fixtures are in git, this will cause a diff in the
            fixtures file that you will need to review. It's **your**
            responsibility to review these changes properly, we just write the
            test fixtures for you, but **you** have to proof-read them!

Patterns
========

In this section, we'll document various patterns found over time refactoring
complex clients.

Customizing Commands
--------------------

You can customize the generated commands in the following methods of the
:py:class:`~chttpx.Client` class:

- :py:meth:`~chttpx.setargs`: to set :ref:`cli-only-arguments`.
- :py:meth:`~chttpx.factory`: to construct your Client with the said cli
  only arguments
- :py:meth:`~chttpx.post_call`: to logout or do whatever you want

Example:

.. code-block:: python

    class CyberArkClient(chttpx.Client):
        def __init__(self, something, *args, **kwargs):
            self.something = something
            super().__init__(*args, **kwargs)

        @classmethod
        def setargs(self, cmd):
            # declare an argument that will be visible in command line only
            cmd.arg('something', position=0, kind='POSITIONAL_ONLY')

        async def factory(cls, something):
            # something will be passed by the ClientCommand class
            return cls(something)

        async def token_get(self):
            # do something to get a token
            return token

        async def post_call(self, cmd):
            # release the token
            await self.client.post('/logoff')

Filtering on external data
--------------------------

You may want to be able to filter on fields which won't be returned by the list
API:

.. code-block:: python

    class DynatraceConfiguration(YourClient.Model):
        url_list = '/configurations'

        async def status_fetch(self):
            response = self.client.get(self.url + '/status')
            self.status = response.json()['status']

        @classmethod
        @cli2.cmd
        async def find(cls, *expressions, **params):
            paginator = super().find(
                lambda item: item.status == 'OK',
                *expressions,
                **params,
            )

            async def callback(item):
                await item.status_fetch()

            paginator.callback = callback
            return paginator

Before yielding items, paginator will call the callback for every item in
asyncio.gather, causing an extra async request to the status URL of the object
and set ``self.status``, this will cause a lot of requests, you might want to
set :py:attr:`~chttpx.Client.semaphore` to limit concurrent requests.

API
===

.. automodule:: chttpx
   :members:

.. _Example CLI:

Example CLI
===========

.. cli2:auto:: chttpx-example
