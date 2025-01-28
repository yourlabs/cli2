Tutorial for cli2.Client: HTTP Client framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Experimental feature, to enjoy it fully, install cli2 with ``client`` as such::

    pip install cli2[client]

The goal of cli2.client module is to provide a generic framework to
build HTTP client libs and CLIs onto, after carrying this pattern from a
project to another, I've refactored this stuff here:

- great logging: Sent/Received JSON output is dumped as YAML, colored in
  console, and not-colored to file
- ``export LOG_LEVEL=DEBUG`` to enable debug output
- debug output always saved in ``~/.local/cli2/log``, **they will eventually fill
  up your drive and I've not yet decided a solution against that**, but I just
  love this feature,
- ``export HTTP_DEBUG=1`` for low-level HTTP Debugging output
- **a ORM for REST resources**

Tutorial
========

Creating a Client
-----------------

Start by extending a :py:class:`~cli2.client.Client`:

.. code-block:: python

    import cli2

    class YourClient(cli2.Client):
        pass

There are a few methods that you might want to override:

- :py:meth:`~cli2.client.Client.token_get`: if you want your client to do some
  authentication dance to get a token
- :py:meth:`~cli2.client.Client.pagination_initialize`: this is supposed to
  parse the first response in a paginated query and setup attributes like
  :py:attr:`~cli2.client.Paginator.total_pages`
- :py:meth:`~cli2.client.Client.pagination_parameters`: if the endpoint dosen't
  support a ``page`` GET parameter

Creating a Model
----------------

Then, register a :py:class:`~cli2.client.Model` for this client by subclassing
it's ``.model`` attribute.

.. code-block:: python

    class YourObject(YourClient.model):
        pass

Several things are happening here:

- ``YourObject._client_class`` was set to ``YourClient``
- ``YourClient.models`` was set to ``[YourObject]``

Now, you're not supposed to use ``YourObject`` directly, but instead get it
from the client:

.. code-block:: python

    client = YourClient()
    model_class = client.YourObject

Model.client
------------

As such, the model class you're using has the ``client`` instance set as
``.client`` class attribute. And magically, you can use ``self.client``
anywhere in your model:

.. code-block:: python

    class YourObject(YourClient.model):
        @classmethod
        async def some_command(cls):
            return await self.client.get('/some-page').json()

Model.paginate
--------------

You can already paginate over objects:

.. code-block:: python

    async for obj in client.YourObject.paginate('/some-url', somefilter='foo'):
        cli2.print(obj)

If you set the :py:attr:`url_list` attribute, then you can also use the
:py:meth:`cli2.client.Model.find` method directly:

.. code-block:: python

    class YourObject(YourClient.model):
        pass

    paginator = YourObject.find(somefilter='test')

You can also customize pagination per-model, in the same fashion as we already
can per-client, by implementing and
:py:meth:`~cli2.client.Model.pagination_initialize`,
:py:meth:`~cli2.client.Model.pagination_parameters` in your Model class.

Fields
------

You can also define fields for your Model as such:

.. code-block:: python

    class YourModel(YourClient.model):
        id = cli2.Field()

You guessed it: this will may the ``id`` key of the :py:attr:`Model.data` to
the ``.id`` property. Which allows for more interesting things as we'll see...

Nested fields
`````````````

If you want to map ``data['company']['name']`` to ``company_name``, use slash
to define a nested data accessor:

.. code-block:: python

    class YourModel(YourClient.model):
        company_name = cli2.Field('company/name')

You can also "pythonize" any property with a simple accessor without any slash:

.. code-block:: python

    class YourModel(YourClient.model):
        company_name = cli2.Field('companyName')

Custom types
````````````

The most painful stuff I've had to deal with in APIs are datetimes and, "json
in json".

The cures for that are :py:class:`JSONStringField` and :py:class:`DateTimeField`.

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
        | item.company_name == 'test'
    )

Parameterable
`````````````

Note that we want to delegate as much filtering as we can to the endpoint. To
delegate a filter to the endpoint, add a :py:attr:`Field.parameter`:

.. code-block:: python

    class YourModel(YourClient.model):
        name = cli2.Field(parameter='name')

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

Step 3 Profit
`````````````

The previous paragraph mumbles something about a future ``cli2.contrib``
module. Indeed, I'm planning on contributing API-specific clients in a new
``cli2.contrib`` module, for a bunch of proprietary stuff that big corps love
to buy, we'll have ``cli2.contrib.delphi``, ``cli2.contrib.dynatrace``, etc,
etc

Then, I'll have beautiful SDKs for everything, for making Ansible action
plugins and CLIs.

Example
=======

And of course all this is designed to combine very well with CLIs, because once
you have a library for an API, which you're going to embed in god knows what
(your API server, an Ansible plugin ...), you'll want to work with a CLI to
debug stuff: discover the API and implement features incrementally.

Source code
-----------

.. literalinclude:: ../cli2/example_client.py

Result CLI
----------

.. cli2:auto:: cli2-example-client

API
===

.. automodule:: cli2.client
   :members:
